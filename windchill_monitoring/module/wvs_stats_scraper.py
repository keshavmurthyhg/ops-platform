"""
wvs_stats_scraper.py  WVS Job Statistics scraper (manual-click mode)
Workflow:
  1. Open Job Statistics popup via Actions -> Job Statistics
  2. User clicks 'Display Summary Statistics' manually in Edge
  3. Script waits for frame to clear then repopulate
  4. Parses + saves to worker_stats_history.csv

v2 fix: MIN_GROWTH lowered to 500b (actual data growth is ~1170b, not 5000b)
        Phase 2 starts immediately after frame clears, no false-empty check
"""
import csv, os, time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

WORKER_HISTORY_CSV = os.path.join("data", "history", "worker_stats_history.csv")
WORKER_FIELDNAMES  = ["name","total","failed","success","failed_pct","success_pct","busy_time","captured_at"]
WVS_MONITOR_URL    = ("https://vcewindchill.got.volvo.net/Windchill/ptc1/wvs/queueMonitorMain"
                      "?containerOid=OR:wt.inf.container.OrgContainer:4678&u8=1")
DEBUG_PORT    = 9222
MIN_GROWTH    = 500    # lowered from 5000 — actual growth is ~1170b
POLL_INTERVAL = 5

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
            if "queueMonitorMain" in driver.current_url:
                return h
        except Exception:
            continue
    return None

def _close_stale_stats(driver, keep):
    for h in list(driver.window_handles):
        if h == keep: continue
        try:
            driver.switch_to.window(h)
            if "edrpubstat" in driver.current_url or "Job Statistics" in driver.title:
                driver.close()
        except Exception:
            pass
    driver.switch_to.window(keep)

def _click_text(driver, text):
    for xpath in [f"//a[normalize-space(.)='{text}']",
                  f"//button[normalize-space(.)='{text}']",
                  f"//*[normalize-space(text())='{text}']"]:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.8)
                return True
        except Exception:
            continue
    return False

def _frame_size(driver, frame_name):
    driver.switch_to.default_content()
    try:
        f = driver.find_element(By.NAME, frame_name)
        driver.switch_to.frame(f)
        size = len(driver.page_source)
        driver.switch_to.default_content()
        return size
    except Exception:
        driver.switch_to.default_content()
        return 0

def open_stats_popup(driver, monitor_handle):
    driver.switch_to.window(monitor_handle)
    before = set(driver.window_handles)
    _click_text(driver, "Actions")
    time.sleep(0.8)
    _click_text(driver, "Job Statistics")
    deadline = time.time() + 20
    while time.time() < deadline:
        new = set(driver.window_handles) - before
        if new:
            h = new.pop()
            driver.switch_to.window(h)
            for _ in range(20):
                url = driver.current_url
                if url and url != "about:blank":
                    time.sleep(2)
                    return h
                time.sleep(0.5)
            return h
        time.sleep(0.5)
    return None

def wait_for_data_after_manual_click(driver, stats_handle, timeout=600):
    """
    Two-phase detection:
      Phase 1: wait for pubstatisticslist frame to CLEAR (drop to near 0)
               This happens immediately after user clicks Display Summary Statistics
      Phase 2: wait for frame to GROW above baseline by MIN_GROWTH bytes
               Growth of just 500b is enough — actual data adds ~1170b

    Returns True when data detected, False on timeout.
    """
    driver.switch_to.window(stats_handle)
    baseline = _frame_size(driver, "pubstatisticslist")
    print(f"[WVSStats] Baseline: {baseline}b  (waiting for button click...)")

    deadline = time.time() + timeout
    elapsed  = 0
    cleared  = False

    while time.time() < deadline:
        try:
            driver.switch_to.window(stats_handle)
        except Exception:
            print("[WVSStats] Stats tab closed.")
            return False

        size   = _frame_size(driver, "pubstatisticslist")
        growth = size - baseline

        if not cleared:
            # Phase 1: detect the clear event (frame drops to near 0)
            if size < max(baseline * 0.1, 200):
                cleared = True
                print(f"[WVSStats] [{elapsed}s] Frame cleared — button clicked ✔ Computing...")
            else:
                print(f"[WVSStats] [{elapsed}s] {size}b waiting for click")
        else:
            # Phase 2: detect repopulation — any positive growth above baseline
            print(f"[WVSStats] [{elapsed}s] {size}b growth={growth:+d}b")
            if size > baseline and growth >= MIN_GROWTH:
                print(f"[WVSStats] ✔ Data loaded! ({size}b, +{growth}b)")
                return True
            # Don't exit on small growth — wait for more data to load

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    print(f"[WVSStats] Timeout after {timeout}s — saving what's available.")
    return False

def parse_stats_from_frame(driver, stats_handle):
    driver.switch_to.window(stats_handle)
    driver.switch_to.default_content()
    try:
        driver.switch_to.frame(driver.find_element(By.NAME, "pubstatisticslist"))
    except Exception:
        try: driver.switch_to.frame(1)
        except Exception:
            driver.switch_to.default_content()
            return [], []

    SKIP = {"( 0 objects )", "0 objects", "", " "}
    s_raw, w_raw = [], []
    for i, grid in enumerate(driver.find_elements(By.CSS_SELECTOR, "div.x-grid3")):
        rows_data = []
        for row_el in grid.find_elements(By.CSS_SELECTOR, "div.x-grid3-row"):
            cells = row_el.find_elements(By.CSS_SELECTOR, "div.x-grid3-cell-inner")
            texts = [c.text.strip() for c in cells]
            if any(t for t in texts if t and t not in SKIP and "objects" not in t.lower()):
                rows_data.append(texts)
        if i == 0: s_raw = rows_data
        elif i == 1: w_raw = rows_data

    if not s_raw and not w_raw:
        soup = BeautifulSoup(driver.page_source, "lxml")
        for tbl in soup.find_all("table"):
            trs  = tbl.find_all("tr")
            if len(trs) < 2: continue
            hdrs = [c.get_text(strip=True) for c in trs[0].find_all(["th","td"])]
            rows = []
            for tr in trs[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                cells = [c for c in cells if c and c not in SKIP and "objects" not in c.lower()]
                if cells: rows.append(cells)
            if "Authoring Application" in hdrs and rows: s_raw = rows
            elif any("Worker" in h for h in hdrs) and rows: w_raw = rows

    driver.switch_to.default_content()
    SH = ["Authoring Application","Worker Type","Total Jobs","Failed Jobs","Successful Jobs","% Failed Jobs","% Successful Jobs"]
    WH = ["Worker Name","Total Jobs","Failed Jobs","Successful Jobs","% Failed Jobs","% Successful Jobs","Busy Time"]

    def to_dicts(raw, hdrs):
        result = []
        for row in raw:
            while len(row) < len(hdrs): row.append("")
            result.append(dict(zip(hdrs, row[:len(hdrs)])))
        return result
    return to_dicts(s_raw, SH), to_dicts(w_raw, WH)

def save_worker_history(worker_rows, csv_path=WORKER_HISTORY_CSV):
    try:
        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        write_header = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        normalised = []
        for r in worker_rows:
            vals = list(r.values())
            normalised.append({
                "name":        vals[0] if len(vals) > 0 else "",
                "total":       vals[1] if len(vals) > 1 else "",
                "failed":      vals[2] if len(vals) > 2 else "",
                "success":     vals[3] if len(vals) > 3 else "",
                "failed_pct":  vals[4] if len(vals) > 4 else "",
                "success_pct": vals[5] if len(vals) > 5 else "",
                "busy_time":   vals[6] if len(vals) > 6 else "",
                "captured_at": ts,
            })
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=WORKER_FIELDNAMES)
            if write_header: writer.writeheader()
            writer.writerows(normalised)
        print(f"[WVSStats] Saved {len(normalised)} workers to {csv_path}")
        return True
    except PermissionError:
        print("[WVSStats] File locked. Skipping.")
        return False
    except Exception as e:
        print(f"[WVSStats] Save error: {e}")
        return False
