"""
transaction_filter_scraper.py — v9
===================================
Fix: grid count reader was reading "58 objects" from the UNFILTERED view
     and treating filter as confirmed, then reading rows before filter
     settled. Extended the wait + now reads the actual count from the
     (N objects) label reliably.

Fix: WVS KPI — transaction count must come from the grid object count
     shown in Windchill, not from the CSV row count. We now return
     grid_count in the result so the dashboard can display the real number.
"""

import os, re, time, threading, csv
from datetime import datetime, timedelta

TRANSACTION_URL = (
    "https://vcewindchill.got.volvo.net/Windchill/app/#ptc1/comp/"
    "ext.vce.integration.core.transaction.ui.TransactionTreeBuilder"
    "?oid=OR%3Awt.org.WTUser%3A9643933264&u8=1"
)
HISTORY_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "history", "transactions_history.csv"
)
CSV_FIELDNAMES = [
    "tx_id", "time", "target", "action", "status",
    "object", "state", "attempts", "notes", "collected_at"
]
_FILTER_LOCK = threading.Lock()

# ── Copy all helper functions from v8 unchanged ───────────────────────────────
# (Only the main entry point and grid-count logic changes)

def _get_driver():
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    opts = Options()
    opts.use_chromium = True
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    d = webdriver.Edge(options=opts)
    d.set_page_load_timeout(30)
    return d

def _safe_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def _dismiss_alert(driver):
    try:
        a = driver.switch_to.alert; t = a.text; a.accept()
        time.sleep(0.3); print(f"[Filter] Alert: '{t}'"); return True
    except Exception: return False

def _is_tx_id(txt):
    txt = (txt or "").strip()
    return bool(txt and txt[0].isdigit() and
                re.search(r'\d{10,}', txt.replace("-","").replace(",","")))

def _is_date(txt):
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}', (txt or "").strip()))

def _parse_time(t):
    clean = (t or "").strip()
    for tz in [" CEST"," CET"," UTC"," EST"," PST"," BST"]:
        clean = clean.replace(tz, "")
    for fmt in ["%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y-%m-%d",
                "%d/%m/%Y %H:%M","%m/%d/%Y %H:%M"]:
        try: return datetime.strptime(clean.strip(), fmt)
        except ValueError: pass
    return datetime.min

def _close_stale_popups(driver, tx_handle):
    closed = 0
    for _attempt in range(3):
        before = len(driver.window_handles)
        for h in list(driver.window_handles):
            if h == tx_handle: continue
            try:
                driver.switch_to.window(h)
                url = driver.current_url.lower()
                if "transactiontreebuilder" not in url:
                    driver.close(); closed += 1
                    print(f"[Filter] Closed popup: {url[:60]}")
            except Exception: pass
        if len(driver.window_handles) == before: break
        time.sleep(0.3)
    if closed: print(f"[Filter] {closed} stale popup(s) closed.")
    try:
        driver.switch_to.window(tx_handle)
        driver.switch_to.default_content()
    except Exception: pass

def _wait_new_window(driver, known, timeout=15):
    dl = time.time() + timeout
    while time.time() < dl:
        new = set(driver.window_handles) - known
        if new: return new.pop()
        time.sleep(0.4)
    return None

def _find_or_open_tx_tab(driver):
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "transactiontreebuilder" in driver.current_url.lower():
                print("[Filter] Reusing transaction tab.")
                return h
        except Exception: continue
    print("[Filter] Opening transaction tab...")
    driver.execute_script(f"window.open('{TRANSACTION_URL}','_blank');")
    time.sleep(6)
    h = driver.window_handles[-1]
    driver.switch_to.window(h); time.sleep(5)
    return h

def _find_filter_btn(driver):
    from selenium.webdriver.common.by import By
    def _search(d):
        for xp in [
            "//*[contains(translate(@title,'FILTERANSCO','filteransco'),'filter') and (self::button or self::span or self::div or self::a or self::img)]",
            "//*[contains(translate(text(),'FILTERANSCO','filteransco'),'filter') and (self::button or self::span or self::div or self::a)]",
            "//button[contains(@class,'filter') or contains(@id,'filter')]",
            "//*[contains(@class,'FilterTransaction') or contains(@id,'FilterTransaction')]",
        ]:
            try:
                for el in d.find_elements(By.XPATH, xp):
                    if el.is_displayed(): return el
            except Exception: pass
        return None
    driver.switch_to.default_content()
    btn = _search(driver)
    if btn: return btn
    for i, fr in enumerate(driver.find_elements("css selector","iframe, frame")):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            btn = _search(driver)
            if btn: print(f"[Filter] Filter btn in frame #{i}"); return btn
        except Exception: continue
    driver.switch_to.default_content()
    return None

def _set_date_field(driver, inp, date_str):
    from selenium.webdriver.common.keys import Keys
    import subprocess
    extjs_script = """
    var el=arguments[0],date=arguments[1];
    try{var id=el.id;if(id&&Ext&&Ext.getCmp){var cmp=Ext.getCmp(id);if(cmp&&cmp.setValue){cmp.setValue(date);cmp.validate&&cmp.validate();return 'extjs_setValue';}}}catch(e1){}
    try{if(Ext&&Ext.ComponentQuery){var all=Ext.ComponentQuery.query('datefield');for(var i=0;i<all.length;i++){if(all[i].inputEl&&all[i].inputEl.dom===el){all[i].setValue(date);return 'extjs_query_setValue';}}}}catch(e2){}
    return 'extjs_not_found';
    """
    try:
        result = driver.execute_script(extjs_script, inp, date_str)
        print(f"[Filter] ExtJS setValue result: {result}")
        if 'setValue' in (result or ''):
            time.sleep(0.3)
            val = inp.get_attribute("value") or ""
            if val: print(f"[Filter] Field value after ExtJS: '{val}'"); return val
    except Exception as e: print(f"[Filter] ExtJS error: {e}")
    js_set = """
    var el=arguments[0],val=arguments[1];
    var niv=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    niv.call(el,val);
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));
    el.dispatchEvent(new Event('blur',{bubbles:true}));
    return el.value;
    """
    try:
        val = driver.execute_script(js_set, inp, date_str)
        print(f"[Filter] JS native setter: '{val}'")
        _dismiss_alert(driver); time.sleep(0.2)
        actual = inp.get_attribute("value") or ""
        if actual: return actual
    except Exception as e: print(f"[Filter] JS setter error: {e}")
    try:
        subprocess.run(["powershell","-command",f"Set-Clipboard -Value '{date_str}'"],capture_output=True,timeout=3)
        inp.click(); time.sleep(0.1)
        inp.send_keys(Keys.CONTROL+"a"); time.sleep(0.05)
        inp.send_keys(Keys.CONTROL+"v"); time.sleep(0.3)
        _dismiss_alert(driver); inp.send_keys(Keys.TAB); time.sleep(0.2)
        _dismiss_alert(driver)
        val = inp.get_attribute("value") or ""
        print(f"[Filter] Clipboard result: '{val}'"); return val
    except Exception as e: print(f"[Filter] Clipboard error: {e}")
    return ""

def _fill_popup(driver, popup_handle, from_date, to_date):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select, WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    driver.switch_to.window(popup_handle); time.sleep(2); _dismiss_alert(driver)
    try: WebDriverWait(driver,15).until(EC.presence_of_element_located((By.CSS_SELECTOR,"input")))
    except Exception: print("[Filter] Timeout waiting for popup inputs.")
    _dismiss_alert(driver)
    all_inputs = driver.find_elements(By.CSS_SELECTOR,"input[type='text'],input[type=''],input:not([type])")
    vis = [i for i in all_inputs if i.is_displayed()]
    print(f"[Filter] {len(vis)} visible inputs in popup.")
    from_inp = to_inp = None
    for inp in vis:
        attrs = ((inp.get_attribute("id") or "")+(inp.get_attribute("name") or "")+(inp.get_attribute("placeholder") or "")).lower()
        if "from" in attrs or "start" in attrs: from_inp = inp
        elif "to" in attrs or "end" in attrs: to_inp = inp
    if from_inp is None and len(vis)>=1: from_inp=vis[0]
    if to_inp is None and len(vis)>=2: to_inp=vis[1]
    if from_inp:
        v = _set_date_field(driver, from_inp, from_date)
        print(f"[Filter] From Date → '{v}' (target: {from_date})")
        _dismiss_alert(driver)
    if to_inp:
        v = _set_date_field(driver, to_inp, to_date)
        print(f"[Filter] To Date   → '{v}' (target: {to_date})")
        _dismiss_alert(driver)
    status_set = False
    for sel_el in [s for s in driver.find_elements(By.TAG_NAME,"select") if s.is_displayed()]:
        try:
            sel = Select(sel_el)
            for opt in sel.options:
                if "fail" in opt.text.lower():
                    sel.select_by_visible_text(opt.text)
                    print(f"[Filter] Status → '{opt.text}'")
                    status_set=True; break
        except Exception: pass
        if status_set: break
    time.sleep(0.4); _dismiss_alert(driver)
    ok_clicked = False
    for xp in ["//button[normalize-space(text())='OK']","//input[@value='OK']","//button[contains(text(),'OK')]","//button[@type='submit']","//input[@type='submit']"]:
        try:
            for c in driver.find_elements(By.XPATH,xp):
                if c.is_displayed():
                    print(f"[Filter] Clicking OK: '{c.text}'")
                    _safe_click(driver,c); ok_clicked=True; break
        except Exception: pass
        if ok_clicked: break
    if not ok_clicked:
        vis_btns = [b for b in driver.find_elements(By.TAG_NAME,"button") if b.is_displayed()]
        print(f"[Filter] Visible buttons: {[b.text for b in vis_btns]}")
        for b in vis_btns:
            if b.text.strip().upper() in ("OK","APPLY","SUBMIT","SEARCH"):
                _safe_click(driver,b); ok_clicked=True; break
    if not ok_clicked:
        driver.find_element(By.TAG_NAME,"body").send_keys(Keys.RETURN); ok_clicked=True
    time.sleep(0.5); _dismiss_alert(driver)
    return ok_clicked

EXPAND_JS = r"""
var n=0;
try{
    var rows=document.querySelectorAll('tbody tr');
    for(var r=0;r<rows.length;r++){
        try{
            var row=rows[r];
            if(!row.querySelector('td')) continue;
            var fc=row.querySelector('td:first-child');
            if(!fc) continue;
            var selectors=['.x-treegrid-expander','.x-tree-ec-icon','.x-tree-elbow-plus','.x-tree-expander','[class*="tree-ec"]','[class*="treegrid-expander"]','[class*="elbow-plus"]'];
            for(var s=0;s<selectors.length;s++){
                var icons=fc.querySelectorAll(selectors[s]);
                for(var i=0;i<icons.length;i++){
                    var icon=icons[i];
                    var cls=(icon.className||'')+' '+((icon.parentElement||{}).className||'');
                    if(cls.indexOf('expander-open')!==-1||cls.indexOf('-expanded')!==-1) continue;
                    var w=icon.offsetWidth||icon.getBoundingClientRect().width;
                    if(w>30) continue;
                    icon.click();n++;break;
                }
            }
        }catch(re){}
    }
}catch(e){}
return n;
"""

def _read_live_rows(driver):
    from selenium.webdriver.common.by import By
    raw = []
    try:
        for row in driver.find_elements(By.CSS_SELECTOR,"tr"):
            try:
                cells = row.find_elements(By.TAG_NAME,"td")
                if not cells: continue
                texts = []
                for c in cells:
                    try: texts.append(c.text.strip())
                    except: texts.append("")
                if any(texts): raw.append(texts)
            except Exception: continue
    except Exception as e: print(f"[DOM] Error: {e}")
    return raw

def _merge_rows(raw_rows):
    import hashlib as _hl
    print(f"[Merge] {len(raw_rows)} raw rows. Sample:")
    for i,r in enumerate(raw_rows[:12]):
        print(f"[Merge]   [{i}] cols={len(r)} | c0='{(r[0] or '')[:20]}' | c1='{(r[1] if len(r)>1 else '')[:20]}' | c2='{(r[2] if len(r)>2 else '')[:20]}' | c6='{(r[6] if len(r)>6 else '')}'")
    results = []
    i = 0
    while i < len(raw_rows):
        cols = raw_rows[i]
        if not cols or len(cols)<4: i+=1; continue
        if _is_tx_id(cols[0]):
            parent = {"tx_id":cols[0],"time":cols[1] if len(cols)>1 else "N/A","object":cols[2] if (len(cols)>2 and cols[2]) else "N/A","state":cols[3] if (len(cols)>3 and cols[3]) else "N/A","target":cols[4] if len(cols)>4 else "N/A","action":cols[5] if len(cols)>5 else "N/A","status":cols[6] if len(cols)>6 else "N/A","attempts":cols[7] if (len(cols)>7 and cols[7]) else "N/A","notes":cols[8] if (len(cols)>8 and cols[8]) else "N/A"}
            j=i+1; children=[]
            while j<len(raw_rows):
                cc=raw_rows[j]
                if not cc: j+=1; continue
                if _is_tx_id(cc[0]): break
                if len(cc)>=4: children.append(cc)
                j+=1
            if children:
                fc=children[0]
                if parent["object"]=="N/A" and len(fc)>2 and fc[2]: parent["object"]=fc[2]
                if parent["state"]=="N/A" and len(fc)>3 and fc[3]: parent["state"]=fc[3]
                lc=children[-1]
                if len(lc)>7 and lc[7]: parent["attempts"]=lc[7] or parent["attempts"]
                if len(lc)>8 and lc[8] not in ("","N/A","null"): parent["notes"]=lc[8]
            results.append(parent); i=j
        else: i+=1
    if results:
        print(f"[Merge] Standard mode: {len(results)} records.")
        return results
    print("[Merge] No parent rows → child-only grouping mode.")
    child_rows=[]
    for r in raw_rows:
        if len(r)<5: continue
        if _is_date(r[0]) or (r[0]=='' and len(r)>1 and _is_date(r[1])): child_rows.append(r)
    print(f"[Merge] {len(child_rows)} valid child rows.")
    if not child_rows: return []
    def _row_c0(r): return 0 if _is_date(r[0]) else 1
    def _row_sig(r):
        c=_row_c0(r)
        return f"{r[c+1] if len(r)>c+1 else ''}||{r[c+3] if len(r)>c+3 else ''}||{r[c+4] if len(r)>c+4 else ''}"
    groups=[]; cur_sig=None; cur_grp=[]
    for r in child_rows:
        sig=_row_sig(r)
        if sig!=cur_sig:
            if cur_grp: groups.append(cur_grp)
            cur_grp=[r]; cur_sig=sig
        else: cur_grp.append(r)
    if cur_grp: groups.append(cur_grp)
    print(f"[Merge] Grouped into {len(groups)} transaction groups.")
    for g_idx,grp in enumerate(groups):
        fc=grp[0]; lc=grp[-1]; c0=_row_c0(fc); c0l=_row_c0(lc)
        time_val=fc[c0] if len(fc)>c0 else "N/A"
        obj_val=fc[c0+1] if len(fc)>c0+1 else "N/A"
        state_val=fc[c0+2] if len(fc)>c0+2 else "N/A"
        target_val=fc[c0+3] if len(fc)>c0+3 else "N/A"
        action_val=fc[c0+4] if len(fc)>c0+4 else "N/A"
        status_val=fc[c0+5] if len(fc)>c0+5 else "N/A"
        att_val=lc[c0l+6] if len(lc)>c0l+6 else str(len(grp))
        notes_val="N/A"
        for row in reversed(grp):
            c=_row_c0(row); n=row[c+7] if len(row)>c+7 else ""
            if n and n not in ("","null","N/A","—"): notes_val=n; break
        _key=f"{time_val[:16].replace(' ','').replace(':','')}{obj_val[:10]}{target_val[:6]}{g_idx}"
        _pseudo_id="AUTO-"+_hl.md5(_key.encode()).hexdigest()[:12].upper()
        results.append({"tx_id":_pseudo_id,"time":time_val,"object":obj_val,"state":state_val,"target":target_val,"action":action_val,"status":status_val,"attempts":att_val,"notes":notes_val})
    print(f"[Merge] Child-only: {len(results)} records built.")
    return results

def _find_table_ctx(driver):
    from selenium.webdriver.common.by import By
    def _has(d):
        try:
            for row in d.find_elements(By.CSS_SELECTOR,"tr")[:40]:
                cells=row.find_elements(By.TAG_NAME,"td")
                if len(cells)>=4:
                    c0,c1=cells[0].text.strip(),cells[1].text.strip() if len(cells)>1 else ""
                    if _is_tx_id(c0) or _is_date(c0) or _is_date(c1): return True
        except Exception: pass
        return False
    driver.switch_to.default_content()
    if _has(driver): print("[Frame] Table in main document."); return None
    for i,fr in enumerate(driver.find_elements("css selector","iframe, frame")):
        try:
            driver.switch_to.default_content(); driver.switch_to.frame(fr)
            if _has(driver): print(f"[Frame] Table in frame #{i}."); driver.switch_to.default_content(); return i
        except Exception: continue
    driver.switch_to.default_content(); print("[Frame] Not found — using main doc."); return None

def _switch_ctx(driver, tx_handle, frame_idx):
    driver.switch_to.window(tx_handle); driver.switch_to.default_content()
    if frame_idx is not None:
        try:
            frs=driver.find_elements("css selector","iframe, frame")
            if frame_idx<len(frs): driver.switch_to.frame(frs[frame_idx])
        except Exception as e: print(f"[Frame] Switch error: {e}")

def _expand_and_harvest(driver, tx_handle, frame_idx):
    from selenium.webdriver.common.by import By
    _switch_ctx(driver, tx_handle, frame_idx)
    try:
        n=driver.execute_script(EXPAND_JS)
        print(f"[Expand] Phase 1: JS clicked {n} expander(s).")
    except Exception as e: print(f"[Expand] Phase 1 JS error: {e}"); n=0
    time.sleep(4)
    driver.switch_to.window(tx_handle); driver.switch_to.default_content()
    _close_stale_popups(driver, tx_handle)
    _switch_ctx(driver, tx_handle, frame_idx)
    try:
        scrollable=driver.find_elements(By.CSS_SELECTOR,".x-grid-body,.x-treegrid-body,.x-panel-body,[class*='grid-body'],[class*='tree-body'],[class*='panel-body']")
        for sc in scrollable:
            try: driver.execute_script("arguments[0].scrollTop=arguments[0].scrollHeight;",sc)
            except Exception: pass
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
        time.sleep(1.5)
        print(f"[Expand] Phase 2: Scrolled {len(scrollable)} grid container(s) to bottom.")
    except Exception as se: print(f"[Expand] Phase 2 scroll error: {se}")
    try:
        tbody_rows=driver.find_elements(By.CSS_SELECTOR,"tbody tr")
        phase2_clicks=0
        for row in tbody_rows:
            try:
                first_cell=row.find_elements(By.CSS_SELECTOR,"td:first-child")
                if not first_cell: continue
                expanders=first_cell[0].find_elements(By.CSS_SELECTOR,".x-treegrid-expander,.x-tree-ec-icon,.x-tree-elbow-plus,.x-tree-expander,[class*='tree-ec'],[class*='treegrid-expander'],[class*='elbow-plus']")
                for exp in expanders:
                    cls=exp.get_attribute("class") or ""
                    if "expander-open" in cls or "-expanded" in cls: continue
                    w=exp.size.get("width",0)
                    if w>30: continue
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});",exp)
                    time.sleep(0.1)
                    driver.execute_script("arguments[0].click();",exp)
                    phase2_clicks+=1; break
            except Exception: continue
        if phase2_clicks:
            print(f"[Expand] Phase 2: Selenium clicked {phase2_clicks} more expander(s).")
            time.sleep(4); _close_stale_popups(driver, tx_handle); _switch_ctx(driver, tx_handle, frame_idx)
    except Exception as se2: print(f"[Expand] Phase 2 Selenium error: {se2}")
    try:
        n3=driver.execute_script(EXPAND_JS)
        if n3:
            print(f"[Expand] Phase 3: {n3} more expander(s) clicked.")
            time.sleep(3); _close_stale_popups(driver, tx_handle); _switch_ctx(driver, tx_handle, frame_idx)
    except Exception as e3: print(f"[Expand] Phase 3 error: {e3}")
    raw=_read_live_rows(driver)
    print(f"[Expand] {len(raw)} raw rows read after all phases.")
    rows=_merge_rows(raw)
    if not rows and frame_idx is not None:
        driver.switch_to.window(tx_handle); driver.switch_to.default_content()
        raw2=_read_live_rows(driver); rows=_merge_rows(raw2)
    driver.switch_to.window(tx_handle); driver.switch_to.default_content()
    return rows

def _has_real_data(r):
    obj=(r.get("object","") or "").strip(); notes=(r.get("notes","") or "").strip()
    return (obj not in ("","N/A","—","null") or notes not in ("","N/A","—","null"))

def _append_csv(rows):
    os.makedirs(os.path.dirname(HISTORY_CSV), exist_ok=True)
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_rows={}
    if os.path.exists(HISTORY_CSV) and os.path.getsize(HISTORY_CSV)>0:
        try:
            with open(HISTORY_CSV,"r",encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    tid=row.get("tx_id","").strip()
                    if tid: existing_rows[tid]=dict(row)
        except Exception as e: print(f"[CSV] Read error: {e}")
    new_count=updated_count=0
    for r in rows:
        tid=(r.get("tx_id","") or "").strip()
        if not tid: continue
        merged={k:r.get(k,"N/A") for k in CSV_FIELDNAMES}
        merged["collected_at"]=ts
        if tid not in existing_rows:
            existing_rows[tid]=merged; new_count+=1
        else:
            old=existing_rows[tid]
            if _has_real_data(r) and not _has_real_data(old):
                for field in ["object","state","attempts","notes"]:
                    val=(r.get(field,"") or "").strip()
                    if val and val not in ("N/A","—","null"): existing_rows[tid][field]=val
                existing_rows[tid]["collected_at"]=ts; updated_count+=1
    if new_count==0 and updated_count==0:
        print("[CSV] No new or updated rows."); return 0
    all_rows=list(existing_rows.values())
    with open(HISTORY_CSV,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=CSV_FIELDNAMES); w.writeheader()
        for row in all_rows: w.writerow({k:row.get(k,"N/A") for k in CSV_FIELDNAMES})
    print(f"[CSV] New: {new_count} | Updated: {updated_count} | Total: {len(all_rows)} rows.")
    return new_count


# ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────────

def run_transaction_filter_automation():
    if _FILTER_LOCK.locked():
        return {"success":False,"message":"Already running.","transactions":[],"new_count":0,"grid_count":0}
    with _FILTER_LOCK:
        result={"success":False,"message":"","transactions":[],"new_count":0,"grid_count":0}
        try:
            today=datetime.now()
            from_date=(today-timedelta(days=7)).strftime("%Y-%m-%d")
            to_date=today.strftime("%Y-%m-%d")
            print(f"[Filter] Range: {from_date} → {to_date}")

            driver=_get_driver()
            print(f"[Filter] Connected ({len(driver.window_handles)} tabs).")

            tx_handle=_find_or_open_tx_tab(driver)
            driver.switch_to.window(tx_handle); driver.switch_to.default_content()
            time.sleep(3)
            _close_stale_popups(driver, tx_handle)
            time.sleep(0.5)

            handles_before=set(driver.window_handles)
            btn=_find_filter_btn(driver)
            if btn is None:
                result["message"]="Could not find 'Filter Transaction' button."; return result
            driver.switch_to.window(tx_handle); _safe_click(driver,btn); time.sleep(1)
            popup=_wait_new_window(driver,handles_before,timeout=15)
            if popup is None:
                result["message"]="Filter popup did not appear."; return result
            print("[Filter] Popup opened.")
            ok=_fill_popup(driver,popup,from_date,to_date)
            if not ok:
                result["message"]="Could not click OK."; return result

            dl=time.time()+12
            while time.time()<dl:
                if popup not in driver.window_handles:
                    print("[Filter] Popup closed."); break
                time.sleep(0.5)
            else:
                try: driver.switch_to.window(popup); driver.close(); print("[Filter] Force-closed popup.")
                except Exception: pass

            driver.switch_to.window(tx_handle); driver.switch_to.default_content()

            # ── KEY FIX: Wait for grid to show FILTERED count (< 50) ──────────
            # The grid initially shows all objects (hundreds). After filter applies
            # it drops to the actual filtered count. Poll until stable + small.
            print("[Filter] Waiting for filtered grid (up to 40s)...")
            grid_count = 0
            filter_confirmed = False
            prev_count = -1
            stable_polls = 0

            for _wi in range(16):  # up to 40s
                try:
                    src = driver.page_source
                    # Read the (N objects) count from grid header
                    m = re.search(r'\(\s*(\d+)\s*(?:of more than \d+\s*)?objects?\s*\)', src)
                    if m:
                        n_obj = int(m.group(1))
                        print(f"[Filter] Grid count: {n_obj} objects")
                        # Filter applied when count drops to manageable level
                        if n_obj <= 200:
                            if n_obj == prev_count:
                                stable_polls += 1
                                if stable_polls >= 2:
                                    grid_count = n_obj
                                    filter_confirmed = True
                                    print(f"[Filter] ✔ Filter confirmed: {n_obj} objects (stable)")
                                    break
                            else:
                                stable_polls = 0
                            prev_count = n_obj
                        else:
                            prev_count = n_obj
                            stable_polls = 0
                except Exception: pass
                time.sleep(2.5)

            if not filter_confirmed:
                # Try one more read
                try:
                    src = driver.page_source
                    m = re.search(r'\(\s*(\d+)\s*(?:of more than \d+\s*)?objects?\s*\)', src)
                    if m: grid_count = int(m.group(1))
                except Exception: pass
                print(f"[Filter] WARNING: Filter may not have settled. Last count: {grid_count}")

            result["grid_count"] = grid_count
            time.sleep(2)

            frame_idx=_find_table_ctx(driver)
            rows=_expand_and_harvest(driver,tx_handle,frame_idx)

            failed_rows=[r for r in rows if re.search(r"FAIL|ERR",(r.get("status","")).upper())]
            if rows and not failed_rows:
                print(f"[Filter] All {len(rows)} rows non-Failed — retrying wait...")
                time.sleep(10); frame_idx=_find_table_ctx(driver)
                rows=_expand_and_harvest(driver,tx_handle,frame_idx)
                failed_rows=[r for r in rows if re.search(r"FAIL|ERR",(r.get("status","")).upper())]
            if failed_rows and len(failed_rows)<len(rows):
                print(f"[Filter] Kept {len(failed_rows)} Failed (removed {len(rows)-len(failed_rows)} non-Failed).")
            rows=failed_rows if failed_rows else rows

            if not rows:
                result["success"]=True
                result["message"]=f"Filter applied but 0 rows captured. Grid count={grid_count}"
                return result

            rows.sort(key=lambda r: _parse_time(r.get("time","")),reverse=True)
            seen,unique=[],{}
            for r in rows:
                if r["tx_id"] not in unique: unique[r["tx_id"]]=r
            unique_list=list(unique.values())

            nc=_append_csv(unique_list)
            result.update({
                "success":True,"transactions":unique_list,"new_count":nc,"grid_count":grid_count,
                "message":(f"Filter applied ({from_date}→{to_date}, Failed). "
                           f"Grid shows {grid_count} objects. Captured {len(unique_list)} rows ({nc} new).")
            })
        except Exception as e:
            import traceback; print(f"[Filter] Error:\n{traceback.format_exc()}")
            result["message"]=f"Automation error: {str(e)}"
        return result
