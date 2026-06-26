"""
wvs_job_statistics.py — Windchill WVS Job Statistics Scraper  (v14)
===================================================================
Confirmed: data EXISTS for 2026-06-16 (manual click works perfectly).
Selenium click is accepted (no error) but server never processes it.

Root cause analysis:
  The form in frame 'pubstatisticswiz' submits to 'pubstatisticslist'
  via a TARGET attribute. Selenium's btn.click() may not properly
  trigger the form's onsubmit handler or the TARGET frame navigation.

Fix strategy — try ALL of these in sequence until data appears:
  1. Native btn.click()                  ← tried, works visually but not server
  2. form.submit() via Selenium          ← bypasses button, submits form directly  
  3. JS: form.submit()                   ← same but via execute_script
  4. JS: XMLHttpRequest to form action   ← direct AJAX POST
  5. Simulate full form submission via fetch() with correct parameters

After each attempt, check if pubstatisticslist frame grows > 5000b.
Stop at first success.

Requirements:  pip install selenium beautifulsoup4
"""

import argparse
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

DEBUG_PORT = 9222
OUTPUT_DIR = Path("wvs_output")
STATS_WAIT = 300   # 5 min per attempt
STATS_POLL = 5     # poll every 5s
MIN_GROWTH = 5000  # bytes of growth = real data

WVS_MONITOR_URL = (
    "https://vcewindchill.got.volvo.net/Windchill/ptc1/wvs/queueMonitorMain"
    "?containerOid=OR:wt.inf.container.OrgContainer:4678&u8=1"
)

SUMMARY_HEADERS = [
    "Authoring Application", "Worker Type", "Total Jobs",
    "Failed Jobs", "Successful Jobs", "% Failed Jobs", "% Successful Jobs"
]
WORKER_HEADERS = [
    "Worker Name", "Total Jobs", "Failed Jobs",
    "Successful Jobs", "% Failed Jobs", "% Successful Jobs", "Busy Time"
]
PLACEHOLDER_TEXTS = {"( 0 objects )", "0 objects", "no data", ""}

# ── Driver ─────────────────────────────────────────────────────────────────────

def build_driver(port: int):
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    opts = Options()
    opts.use_chromium = True
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(30)
    print(f"[Driver] Connected — {len(driver.window_handles)} tab(s) open.")
    return driver


def get_wvs_monitor_handle(driver) -> str | None:
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "queueMonitorMain" in driver.current_url:
                return h
        except Exception:
            continue
    return None


def close_stale_stats_tabs(driver, keep_handle: str):
    closed = 0
    for h in list(driver.window_handles):
        if h == keep_handle:
            continue
        try:
            driver.switch_to.window(h)
            url   = driver.current_url
            title = driver.title
            if "edrpubstat" in url or "Job Statistics" in title:
                print(f"    Closing stale: '{title}'")
                driver.close()
                closed += 1
        except Exception:
            pass
    driver.switch_to.window(keep_handle)
    print(f"    Closed {closed} stale tab(s)." if closed else "    No stale tabs.")


def click_text(driver, text: str, wait: float = 0.8) -> bool:
    for xpath in [
        f"//a[normalize-space(.)='{text}']",
        f"//button[normalize-space(.)='{text}']",
        f"//*[normalize-space(text())='{text}']",
    ]:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                driver.execute_script("arguments[0].click();", el)
                time.sleep(wait)
                return True
        except Exception:
            continue
    r = driver.execute_script(f"""
        var els=document.querySelectorAll('*');
        for(var i=0;i<els.length;i++){{
            if(els[i].textContent.trim()==='{text}'){{
                els[i].click();return 'ok:'+els[i].tagName;
            }}
        }}return 'not-found';
    """)
    time.sleep(wait)
    return bool(r) and r.startswith("ok:")


# ── Open stats tab ─────────────────────────────────────────────────────────────

def open_stats_tab(driver, monitor_handle: str) -> str | None:
    print("\n[1] Opening Job Statistics tab …")
    driver.switch_to.window(monitor_handle)
    before = set(driver.window_handles)
    ok = click_text(driver, "Actions", 1.0)
    print(f"    Actions: {'✔' if ok else '⚠'}")
    ok = click_text(driver, "Job Statistics", 2.0)
    print(f"    Job Statistics: {'✔' if ok else '⚠'}")
    deadline = time.time() + 20
    while time.time() < deadline:
        new = set(driver.window_handles) - before
        if new:
            h = new.pop()
            driver.switch_to.window(h)
            for _ in range(20):
                url = driver.current_url
                if url and url != "about:blank":
                    print(f"    ✔ Stats tab: {url[:70]}")
                    time.sleep(2)
                    return h
                time.sleep(0.5)
            return h
        time.sleep(0.5)
    print("    ✗ No new tab.")
    return None


# ── Frame size helpers ─────────────────────────────────────────────────────────

def get_frame_src_size(driver, frame_name: str) -> int:
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


def wait_for_growth(driver, baseline: int, timeout: int,
                    label: str = "") -> bool:
    """
    Wait for pubstatisticslist to clear then grow > MIN_GROWTH above baseline.
    Returns True when real data detected.
    """
    deadline = time.time() + timeout
    elapsed  = 0
    cleared  = False

    while time.time() < deadline:
        size   = get_frame_src_size(driver, "pubstatisticslist")
        growth = size - baseline

        if not cleared:
            if size < baseline / 2:
                cleared = True
                print(f"    [{elapsed:>3}s] {size}b ← cleared ✔")
            else:
                print(f"    [{elapsed:>3}s] {size}b (waiting for clear)")
        else:
            print(f"    [{elapsed:>3}s] {size}b  growth={growth:+d}")
            if growth >= MIN_GROWTH:
                print(f"    ✔ Real data! ({size}b, +{growth}b) {label}")
                return True
            if size > 100 and growth < MIN_GROWTH:
                # Frame reloaded but with empty/small content
                print(f"    ⚠  Reloaded with only +{growth}b — no data yet.")
                return False

        time.sleep(STATS_POLL)
        elapsed += STATS_POLL

    print(f"    ⚠  Timeout after {timeout}s.")
    return False


# ── Switch into form frame ─────────────────────────────────────────────────────

def enter_form_frame(driver) -> bool:
    driver.switch_to.default_content()
    try:
        driver.switch_to.frame(driver.find_element(By.NAME, "pubstatisticswiz"))
        return True
    except Exception:
        try:
            driver.switch_to.frame(0)
            return True
        except Exception as e:
            print(f"    ✗ Frame error: {e}")
            return False


def set_dates(driver, from_date: str, to_date: str):
    """Set From/To date inputs in the current frame."""
    try:
        date_inputs = [
            el for el in driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            if "-" in (el.get_attribute("value") or "")
        ]
        for i, (el, val) in enumerate(zip(date_inputs[:2], [from_date, to_date])):
            # Clear completely first
            driver.execute_script("arguments[0].value='';", el)
            driver.execute_script("arguments[0].value=arguments[1];", el, val)
            try:
                el.clear()
                el.send_keys(val)
            except Exception:
                pass
            print(f"    Date[{i}] → {el.get_attribute('value')!r}")
    except Exception as e:
        print(f"    ⚠  Dates: {e}")


# ── Multiple click strategies ──────────────────────────────────────────────────

def attempt_click(driver, from_date: str, to_date: str,
                  baseline: int, strategy: str) -> bool:
    """
    Set dates and click using the given strategy.
    Returns True if pubstatisticslist grows with real data.
    """
    print(f"\n  ── Strategy: {strategy} ──")

    if not enter_form_frame(driver):
        return False

    set_dates(driver, from_date, to_date)

    if strategy == "native_click":
        try:
            btn = driver.find_element(
                By.XPATH, "//input[@value='Display Summary Statistics']")
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.2)
            btn.click()
            print("    btn.click() sent")
        except Exception as e:
            print(f"    ✗ {e}")
            driver.switch_to.default_content()
            return False

    elif strategy == "action_chains":
        try:
            btn = driver.find_element(
                By.XPATH, "//input[@value='Display Summary Statistics']")
            ActionChains(driver).move_to_element(btn).pause(0.2).click().perform()
            print("    ActionChains click sent")
        except Exception as e:
            print(f"    ✗ {e}")
            driver.switch_to.default_content()
            return False

    elif strategy == "selenium_form_submit":
        try:
            btn = driver.find_element(
                By.XPATH, "//input[@value='Display Summary Statistics']")
            form = btn.find_element(By.XPATH, "./ancestor::form")
            action = form.get_attribute("action")
            method = form.get_attribute("method")
            target = form.get_attribute("target")
            print(f"    Form: action={action!r} method={method!r} target={target!r}")
            form.submit()
            print("    form.submit() sent")
        except Exception as e:
            print(f"    ✗ {e}")
            driver.switch_to.default_content()
            return False

    elif strategy == "js_form_submit":
        try:
            result = driver.execute_script("""
                var btn = document.querySelector(
                    'input[value="Display Summary Statistics"]');
                if (!btn) return 'no-button';
                var form = btn.closest('form') || btn.form;
                if (!form) return 'no-form';
                var action = form.action;
                var method = form.method;
                var target = form.target;
                form.submit();
                return 'submitted: action=' + action +
                       ' method=' + method + ' target=' + target;
            """)
            print(f"    JS form.submit(): {result}")
        except Exception as e:
            print(f"    ✗ {e}")
            driver.switch_to.default_content()
            return False

    elif strategy == "keyboard_enter":
        try:
            btn = driver.find_element(
                By.XPATH, "//input[@value='Display Summary Statistics']")
            btn.send_keys(Keys.SPACE)   # space bar triggers button
            time.sleep(0.1)
            btn.send_keys(Keys.RETURN)  # enter key
            print("    SPACE + ENTER sent to button")
        except Exception as e:
            print(f"    ✗ {e}")
            driver.switch_to.default_content()
            return False

    driver.switch_to.default_content()

    # Now wait for results
    new_baseline = get_frame_src_size(driver, "pubstatisticslist")
    print(f"    Frame size after click: {new_baseline}b (was {baseline}b)")
    return wait_for_growth(driver, baseline=baseline,
                           timeout=STATS_WAIT, label=f"[{strategy}]")


# ── Parse ──────────────────────────────────────────────────────────────────────

def parse_results(driver) -> tuple[list[dict], list[dict]]:
    driver.switch_to.default_content()
    try:
        driver.switch_to.frame(driver.find_element(By.NAME, "pubstatisticslist"))
    except Exception:
        try:
            driver.switch_to.frame(1)
        except Exception:
            driver.switch_to.default_content()
            return [], []

    grids = driver.find_elements(By.CSS_SELECTOR, "div.x-grid3")
    print(f"    ExtJS grids: {len(grids)}")
    s_raw, w_raw = [], []

    for i, grid in enumerate(grids):
        rows_data = []
        for row_el in grid.find_elements(By.CSS_SELECTOR, "div.x-grid3-row"):
            cells = row_el.find_elements(
                By.CSS_SELECTOR, "div.x-grid3-cell-inner")
            texts = [c.text.strip() for c in cells]
            if any(t for t in texts
                   if t and t not in PLACEHOLDER_TEXTS
                   and "objects" not in t.lower()):
                rows_data.append(texts)
        print(f"    Grid[{i}]: {len(rows_data)} rows")
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
                cells = [c for c in cells if c and c not in PLACEHOLDER_TEXTS
                         and "objects" not in c.lower()]
                if cells: rows.append(cells)
            if "Authoring Application" in hdrs and rows: s_raw = rows
            elif any("Worker" in h for h in hdrs) and rows: w_raw = rows

    driver.switch_to.default_content()

    def to_dicts(raw, hdrs):
        result = []
        for row in raw:
            while len(row) < len(hdrs): row.append("")
            result.append(dict(zip(hdrs, row[:len(hdrs)])))
        return result

    return to_dicts(s_raw, SUMMARY_HEADERS), to_dicts(w_raw, WORKER_HEADERS)


# ── Output ─────────────────────────────────────────────────────────────────────

def fmt_table(hdrs, rows) -> str:
    if not rows or not hdrs: return "  (no data)\n"
    widths = {h: len(h) for h in hdrs}
    for r in rows:
        for h in hdrs: widths[h] = max(widths[h], len(str(r.get(h,""))))
    lines = [
        "  |  ".join(h.ljust(widths[h]) for h in hdrs),
        "  |  ".join("-"*widths[h] for h in hdrs),
    ]
    for r in rows:
        lines.append("  |  ".join(str(r.get(h,"")).ljust(widths[h]) for h in hdrs))
    return "\n".join(lines)+"\n"


def save_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"    💾 {path.resolve()}")


def save_csv(path: Path, rows, hdrs):
    if not rows:
        print(f"    ⚠  No rows — skipping {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdrs, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"    💾 {path.resolve()}")


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Main ───────────────────────────────────────────────────────────────────────

def run(port: int, output_dir: Path, from_date: str, to_date: str):
    stamp = ts()
    print(f"\n{'='*65}")
    print(f"  WVS Job Statistics Scraper v14  —  "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Period: {from_date} → {to_date}")
    print(f"{'='*65}\n")

    driver       = build_driver(port)
    stats_handle = None

    try:
        monitor_handle = get_wvs_monitor_handle(driver)
        if not monitor_handle:
            print("[Nav] Loading WVS Job Monitor …")
            driver.switch_to.window(driver.window_handles[0])
            driver.get(WVS_MONITOR_URL)
            time.sleep(5)
            monitor_handle = driver.current_window_handle
        print("[Nav] Monitor tab ready.")

        print("\n[0] Cleaning up …")
        close_stale_stats_tabs(driver, monitor_handle)

        stats_handle = open_stats_tab(driver, monitor_handle)
        if not stats_handle:
            print("❌  Could not open Job Statistics tab.")
            return

        baseline = get_frame_src_size(driver, "pubstatisticslist")
        print(f"\n    Baseline pubstatisticslist = {baseline}b")

        # Try each strategy in order until one works
        strategies = [
            "native_click",
            "action_chains",
            "selenium_form_submit",
            "js_form_submit",
            "keyboard_enter",
        ]

        found = False
        for strategy in strategies:
            found = attempt_click(driver, from_date, to_date,
                                  baseline, strategy)
            if found:
                print(f"\n    ✔ Strategy '{strategy}' succeeded!")
                break
            else:
                print(f"    ✗ Strategy '{strategy}' — no data. Trying next …")
                # Reset baseline for next attempt
                baseline = get_frame_src_size(driver, "pubstatisticslist")
                time.sleep(2)

        if not found:
            print("\n  ⚠  All strategies failed to retrieve data.")
            print(f"     Confirm manually that {from_date} → {to_date} has data.")

        # Screenshot + parse whatever we have
        output_dir.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(str(output_dir / f"job_stats_{stamp}.png"))
        print(f"    📸 job_stats_{stamp}.png")

        print("\n[Parsing] …")
        s_rows, w_rows = parse_results(driver)
        print(f"    Summary: {len(s_rows)} rows  Workers: {len(w_rows)} rows")

        report = "\n".join([
            "Windchill WVS — Job Statistics Report",
            f"Captured  : {stamp}",
            f"Period    : {from_date} → {to_date}",
            f"Source    : {WVS_MONITOR_URL}",
            "",
            "═"*70,
            "  TABLE 1 — JOB SUMMARY STATISTICS (by Authoring Application)",
            "═"*70,
            fmt_table(SUMMARY_HEADERS, s_rows),
            "",
            "═"*70,
            "  TABLE 2 — WORKER STATISTICS (by Worker Name)",
            "═"*70,
            fmt_table(WORKER_HEADERS, w_rows),
        ]) + "\n"

        save_text(output_dir / f"job_stats_{stamp}.txt", report)
        save_csv(output_dir / f"job_stats_summary_{stamp}.csv",
                 s_rows, SUMMARY_HEADERS)
        save_csv(output_dir / f"job_stats_workers_{stamp}.csv",
                 w_rows, WORKER_HEADERS)

        print(f"\n{'='*65}")
        print("  ✅  Complete!")
        print(f"  Period       : {from_date} → {to_date}")
        print(f"  Summary rows : {len(s_rows)}")
        print(f"  Worker rows  : {len(w_rows)}")
        if w_rows:
            h = WORKER_HEADERS
            print(f"\n  Workers (first 5):")
            for w in w_rows[:5]:
                print(f"    {str(w.get(h[0],''))[:40]:<40} "
                      f"Total={w.get(h[1],'')}  "
                      f"Failed={w.get(h[2],'')}  "
                      f"OK={w.get(h[3],'')}")
        print(f"\n  Output: {output_dir.resolve()}")
        print(f"{'='*65}\n")

    except Exception as e:
        import traceback
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            driver.save_screenshot(str(output_dir / f"stats_error_{stamp}.png"))
        except Exception:
            pass
        print(f"\n❌  {e}")
        traceback.print_exc()
        raise

    finally:
        if stats_handle:
            try:
                driver.switch_to.window(stats_handle)
                driver.close()
                print("[Nav] Stats tab closed.")
            except Exception:
                pass
        try:
            m = get_wvs_monitor_handle(driver)
            if m:
                driver.switch_to.window(m)
            elif driver.window_handles:
                driver.switch_to.window(driver.window_handles[0])
            print("[Nav] Returned to monitor.")
        except Exception:
            pass
        print("[Driver] Session released (Edge left open).")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cet_now       = datetime.utcnow() + timedelta(hours=2)
    cet_today     = cet_now.strftime("%Y-%m-%d")
    cet_yesterday = (cet_now - timedelta(days=1)).strftime("%Y-%m-%d")

    p = argparse.ArgumentParser(
        description="Windchill WVS Job Statistics Scraper v14")
    p.add_argument("--port",   type=int, default=DEBUG_PORT)
    p.add_argument("--output", default=str(OUTPUT_DIR))
    p.add_argument("--days",   type=int, default=None)
    p.add_argument("--from",   dest="from_date", default=None)
    p.add_argument("--to",     dest="to_date",   default=None)
    args = p.parse_args()

    if args.days:
        from_date = (cet_now - timedelta(days=args.days)).strftime("%Y-%m-%d")
        to_date   = cet_today
    else:
        from_date = args.from_date or cet_today
        to_date   = args.to_date   or cet_today

    run(port=args.port, output_dir=Path(args.output),
        from_date=from_date, to_date=to_date)
