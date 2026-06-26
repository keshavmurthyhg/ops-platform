"""
wvs_queue_scraper.py  Live WVS Job Queue scraper
v2 fixes:
  - Failed Jobs: scroll from TOP (newest jobs are at top position 1,2,3...)
    Old code scrolled DOWN which got the oldest. Failed Jobs filter shows
    5000+ but we only want the most recent 30-40.
  - Returns grid_count per filter (Ready=134, Executing=13, Failed=approx 30)
  - Saves grid counts to result for dashboard KPI accuracy
"""
import csv, os, time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

WVS_HISTORY_CSV = os.path.join("data", "history", "wvs_queue_history.csv")
WVS_FIELDNAMES  = ["position","queue","job","status","number","name","version","context","user","captured_at"]
WVS_MONITOR_URL = ("https://vcewindchill.got.volvo.net/Windchill/ptc1/wvs/queueMonitorMain"
                   "?containerOid=OR:wt.inf.container.OrgContainer:4678&u8=1")
DEBUG_PORT     = 9222
# (label, scroll_needed, max_rows, scroll_direction)
# Failed: scroll=True, take top 35 rows (newest = highest position numbers shown first)
FILTERS = [
    ("Ready Jobs",     False, 200, "down"),
    ("Executing Jobs", False, 100, "down"),
    ("Failed Jobs",    True,  35,  "top"),   # top = read without scrolling (newest at top)
]
FILTER_WAIT    = 30
FULL_LOAD_WAIT = 120
POLL_INTERVAL  = 3
STABLE_POLLS   = 3
SCROLL_PAUSE   = 0.5

STATUS_WORDS = {"READY","EXECUTING","JOB SUCCESSFUL","JOB FAILED","WAITING","SUSPENDED","PENDING","QUEUED","DELETED","FAILED"}

def _build_driver():
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    opts = Options()
    opts.use_chromium = True
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(30)
    return driver

def _get_wvs_handle(driver):
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "queueMonitorMain" in driver.current_url: return h
        except Exception: continue
    return None

def _get_dom_count(driver):
    try: return driver.execute_script("return document.querySelectorAll('div.x-grid3-row').length;")
    except Exception: return 0

def _wait_stable(driver, timeout, min_rows=5):
    deadline = time.time() + timeout
    prev, stable = -1, 0
    while time.time() < deadline:
        live = _get_dom_count(driver)
        if live >= min_rows and live == prev:
            stable += 1
            if stable >= STABLE_POLLS: return live
        else: stable = 0
        prev = live
        time.sleep(POLL_INTERVAL)
    return _get_dom_count(driver)

def _get_grid_total_count(driver):
    """Read the (N objects) count from the grid header."""
    try:
        import re
        src = driver.page_source
        m = re.search(r'\(\s*(\d+)\s*(?:of more than (\d+)\s*)?objects?\s*\)', src)
        if m:
            if m.group(2):  # "5000 of more than 5000"
                return int(m.group(2))
            return int(m.group(1))
    except Exception: pass
    return 0

def _select_filter(driver, label):
    try:
        from selenium.webdriver.support.ui import Select
        for sel_el in driver.find_elements(By.TAG_NAME, "select"):
            try:
                sel = Select(sel_el)
                if label in [o.text.strip() for o in sel.options]:
                    sel.select_by_visible_text(label); return True
            except Exception: continue
    except Exception: pass

    r = driver.execute_script(f"""
        try{{
            var combos=Ext.ComponentQuery.query('combo');
            for(var i=0;i<combos.length;i++){{
                var c=combos[i],store=c.getStore?c.getStore():null;
                if(!store) continue;
                var recs=store.getRange();
                for(var j=0;j<recs.length;j++){{
                    var txt=recs[j].get(c.displayField||'text')||'';
                    if(txt.trim()==='{label}'){{
                        c.setValue(recs[j].get(c.valueField||'field1'));
                        c.fireEvent('select',c,recs[j]);
                        return 'ok';
                    }}
                }}
            }} return 'no';
        }}catch(e){{return 'err:'+e.message;}}
    """)
    if r == "ok": return True

    try:
        triggers = [t for t in driver.find_elements(By.CSS_SELECTOR,".x-form-trigger,.x-combo-trigger") if t.is_displayed()]
        for trigger in triggers:
            driver.execute_script("arguments[0].click();", trigger)
            time.sleep(0.8)
            items = driver.find_elements(By.CSS_SELECTOR,".x-combo-list-item,.x-boundlist-item")
            for item in items:
                if item.text.strip() == label:
                    driver.execute_script("arguments[0].click();", item); return True
            try: driver.find_element(By.TAG_NAME,"body").click()
            except Exception: pass
    except Exception: pass
    return False

def _wait_filter(driver, timeout):
    deadline = time.time() + timeout
    prev, stable_s = -999, 0
    while time.time() < deadline:
        live = _get_dom_count(driver)
        if live == prev: stable_s += POLL_INTERVAL; 
        if stable_s >= 3: return live
        else: stable_s = 0
        prev = live
        time.sleep(POLL_INTERVAL)
    return _get_dom_count(driver)

def _parse_html(html):
    soup = BeautifulSoup(html, "lxml")
    records = []
    for row in soup.select("div.x-grid3-row"):
        cells = row.select("div.x-grid3-cell-inner")
        raw   = [c.get_text(strip=True) for c in cells]
        if not any(raw): continue
        status_idx = next((i for i,v in enumerate(raw) if v.strip().upper() in STATUS_WORDS), None)
        if status_idx is None: continue
        def g(i): return raw[i].strip() if 0<=i<len(raw) else ""
        rec = {"position":g(status_idx-4),"queue":g(status_idx-3),"job":g(status_idx-2),
               "status":g(status_idx),"number":g(status_idx+1),"name":g(status_idx+2),
               "version":g(status_idx+3),"context":g(status_idx+4),"user":g(status_idx+5)}
        if rec["queue"] and rec["job"]: records.append(rec)
    return records

def _row_key(r): return f"{r.get('queue','')}|{r.get('job','')}".strip("|")
def _job_id_int(r):
    try: return int(r.get("job","0").replace(",",""))
    except ValueError: return 0

_SCROLL_JS_DOWN = """
var el=document.querySelector('.x-grid3-scroller');
if(!el) return 'no-scroller';
var before=el.scrollTop;
el.scrollTop+=arguments[0];
el.dispatchEvent(new Event('scroll',{bubbles:true}));
return el.scrollTop>before?'moved':'bottom';
"""
_SCROLL_JS_TOP = """
var el=document.querySelector('.x-grid3-scroller');
if(!el) return 'no-scroller';
el.scrollTop=0;
el.dispatchEvent(new Event('scroll',{bubbles:true}));
return 'top';
"""

def _harvest_failed_top(driver, max_rows):
    """
    For Failed Jobs: scroll to TOP first (newest jobs are position 1,2,3...
    shown at top). Read the first max_rows without scrolling down.
    """
    # Scroll to top first
    driver.execute_script(_SCROLL_JS_TOP)
    time.sleep(SCROLL_PAUSE)
    seen = {}
    # Read what's visible at the top
    for r in _parse_html(driver.page_source):
        k = _row_key(r)
        if k and k not in seen:
            seen[k] = r
        if len(seen) >= max_rows:
            break
    # Scroll down a bit to get more if needed
    idle, step = 0, 0
    step_px = 200
    while len(seen) < max_rows and idle < 5:
        result = driver.execute_script(_SCROLL_JS_DOWN, step_px)
        time.sleep(SCROLL_PAUSE)
        before = len(seen)
        for r in _parse_html(driver.page_source):
            k = _row_key(r)
            if k and k not in seen:
                seen[k] = r
            if len(seen) >= max_rows:
                break
        idle = 0 if len(seen) > before else idle + 1
        if result in ("bottom","no-scroller"):
            break
        step += 1
    return list(seen.values())

def _harvest_all(driver, max_rows):
    """For Ready/Executing: scroll down to get all rows."""
    seen = {}
    info = driver.execute_script("""
        var el=document.querySelector('.x-grid3-scroller');
        if(!el) return null;
        return {sh:el.scrollHeight,ch:el.clientHeight};
    """)
    step_px = (info["ch"] if info else 200) or 200
    idle, step = 0, 0
    while True:
        for r in _parse_html(driver.page_source):
            k = _row_key(r)
            if k and k not in seen: seen[k] = r
        if len(seen) >= max_rows or idle >= 8: break
        result = driver.execute_script(_SCROLL_JS_DOWN, step_px)
        time.sleep(SCROLL_PAUSE)
        step += 1
        before = len(seen)
        for r in _parse_html(driver.page_source):
            k = _row_key(r)
            if k and k not in seen: seen[k] = r
        idle = 0 if len(seen) > before else idle + 1
        if result in ("bottom","no-scroller"): break
    return list(seen.values())

def _save_history(queue_list, grid_counts):
    try:
        os.makedirs(os.path.dirname(WVS_HISTORY_CSV), exist_ok=True)
        write_header = not os.path.exists(WVS_HISTORY_CSV) or os.path.getsize(WVS_HISTORY_CSV) == 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(WVS_HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=WVS_FIELDNAMES)
            if write_header: writer.writeheader()
            for row in queue_list:
                writer.writerow({k: {**row, "captured_at": ts}.get(k, "") for k in WVS_FIELDNAMES})
        print(f"[WVSQueue] Saved {len(queue_list)} rows")
    except PermissionError: print("[WVSQueue] File locked.")
    except Exception as e: print(f"[WVSQueue] Save error: {e}")

def scrape_wvs_queue_live(save_history=True):
    all_rows = {}
    grid_counts = {"ready": 0, "executing": 0, "failed_approx": 0}
    try:
        driver = _build_driver()
        monitor_handle = _get_wvs_handle(driver)
        if not monitor_handle:
            driver.switch_to.window(driver.window_handles[0])
            driver.get(WVS_MONITOR_URL); time.sleep(3)
            monitor_handle = driver.current_window_handle
        else:
            driver.switch_to.window(monitor_handle)

        _wait_stable(driver, timeout=FULL_LOAD_WAIT, min_rows=5)

        for label, needs_scroll, max_rows, scroll_dir in FILTERS:
            ok = _select_filter(driver, label)
            if not ok:
                print(f"[WVSQueue] Could not select '{label}'"); continue
            time.sleep(1)
            _wait_filter(driver, timeout=FILTER_WAIT)
            time.sleep(0.5)

            # Get actual grid count from Windchill
            grid_total = _get_grid_total_count(driver)
            print(f"[WVSQueue] '{label}': grid shows {grid_total} objects")

            # Store for KPI
            if "Ready" in label:
                grid_counts["ready"] = grid_total
            elif "Executing" in label:
                grid_counts["executing"] = grid_total
            elif "Failed" in label:
                grid_counts["failed_approx"] = min(max_rows, grid_total)

            # Harvest rows
            if needs_scroll and scroll_dir == "top":
                records = _harvest_failed_top(driver, max_rows=max_rows)
            elif needs_scroll:
                records = _harvest_all(driver, max_rows=max_rows)
            else:
                records = _parse_html(driver.page_source)

            added = 0
            for r in records:
                k = _row_key(r)
                if k and k not in all_rows: all_rows[k] = r; added += 1
            print(f"[WVSQueue] '{label}': {added} rows captured")

    except Exception as e:
        print(f"[WVSQueue] Error: {e}")

    STATUS_ORDER = {"READY":0,"EXECUTING":1,"JOB FAILED":2,"FAILED":2}
    result = sorted(all_rows.values(),
                    key=lambda r:(STATUS_ORDER.get(r.get("status","").upper(),9),-_job_id_int(r)))
    print(f"[WVSQueue] Total: {len(result)} active jobs")
    if save_history and result:
        _save_history(result, grid_counts)
    # Attach grid counts to each row so routes can extract them
    if result:
        result[0]["_grid_counts"] = grid_counts
    return result
