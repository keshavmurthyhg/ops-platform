"""
wvs_job_monitor.py — Windchill WVS Job Monitor Scraper  (v12)
==============================================================
Two-part scraper:
  PART 1 — Active Jobs (Ready + Executing + Failed)
            Filter via 'Pick a View' dropdown, parse, sort, save.

  PART 2 — Job Statistics
            Actions menu → Job Statistics → popup opens at edrpubstatisticsmain.jsp
            Click 'Display Summary Statistics' → wait up to 8 min → parse two tables:
              • Job Summary Statistics  (Authoring App × Worker Type)
              • Worker Name stats       (Worker Name × Total/Failed/Success/%)
            Save both to CSV + combined TXT report.

Requirements:  pip install selenium beautifulsoup4
"""

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Config ─────────────────────────────────────────────────────────────────────

WVS_MONITOR_URL = (
    "https://vcewindchill.got.volvo.net/Windchill/ptc1/wvs/queueMonitorMain"
    "?containerOid=OR:wt.inf.container.OrgContainer:4678&u8=1"
)

DEBUG_PORT        = 9222
OUTPUT_DIR        = Path("wvs_output")

# Part 1
FULL_LOAD_WAIT    = 120
POLL_INTERVAL     = 3
STABLE_POLLS      = 3
FILTER_WAIT       = 30
MAX_FAILED_ROWS   = 30
SCROLL_PAUSE      = 0.5

# Part 2 — Job Statistics
STATS_LOAD_WAIT   = 480   # 8 minutes max for statistics to compute
STATS_POLL        = 10    # poll every 10s while waiting

COLUMNS = [
    "position", "queue", "job", "job_status",
    "number", "name", "version", "context", "user", "post_job",
]
STATUS_WORDS = {
    "READY", "EXECUTING", "JOB SUCCESSFUL", "JOB FAILED",
    "WAITING", "SUSPENDED", "PENDING", "QUEUED", "DELETED",
}
FILTER_CONFIG = [
    ("Ready Jobs",     False),
    ("Executing Jobs", False),
    ("Failed Jobs",    True),
]

# ── Driver ─────────────────────────────────────────────────────────────────────

def build_driver(port: int):
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    opts = Options()
    opts.use_chromium = True
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(60)
    print(f"[Driver] Connected — {len(driver.window_handles)} tab(s) open.")
    return driver


def switch_to_windchill_tab(driver) -> bool:
    for h in driver.window_handles:
        try:
            driver.switch_to.window(h)
            if "vcewindchill.got.volvo.net" in driver.current_url:
                print(f"[Nav] Tab: {driver.current_url[:90]}")
                return True
        except Exception:
            continue
    return False


# ── DOM helpers ────────────────────────────────────────────────────────────────

def get_dom_row_count(driver) -> int:
    try:
        return driver.execute_script(
            "return document.querySelectorAll('div.x-grid3-row').length;"
        )
    except Exception:
        return 0


def wait_stable(driver, timeout: int, min_rows: int = 1,
                label: str = "load") -> int:
    deadline = time.time() + timeout
    elapsed  = 0
    prev     = -1
    stable   = 0
    while time.time() < deadline:
        live = get_dom_row_count(driver)
        print(f"    [{elapsed:>3}s]  DOM rows = {live:,}")
        if live >= min_rows and live == prev:
            stable += 1
            if stable >= STABLE_POLLS:
                print(f"    ✔ {label} stable at {live:,} after {elapsed}s.")
                return live
        else:
            stable = 0
        prev = live
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    live = get_dom_row_count(driver)
    print(f"    ⚠  Timeout. rows={live:,}. Proceeding.")
    return live


# ── Part 1: Filter selection ───────────────────────────────────────────────────

def select_filter(driver, label: str) -> bool:
    print(f"\n    Selecting filter: '{label}' …")

    # Strategy 1: native <select>
    try:
        from selenium.webdriver.support.ui import Select as SeleniumSelect
        for sel_el in driver.find_elements(By.TAG_NAME, "select"):
            try:
                sel = SeleniumSelect(sel_el)
                opts = [o.text.strip() for o in sel.options]
                if label in opts:
                    sel.select_by_visible_text(label)
                    print(f"    ✔ <select>: '{label}'")
                    return True
            except Exception:
                continue
    except Exception:
        pass

    # Strategy 2: Ext.ComponentQuery
    result = driver.execute_script(f"""
        try {{
            var combos = Ext.ComponentQuery.query('combo');
            for (var i=0;i<combos.length;i++) {{
                var c=combos[i], store=c.getStore?c.getStore():null;
                if (!store) continue;
                var recs=store.getRange();
                for (var j=0;j<recs.length;j++) {{
                    var txt=recs[j].get(c.displayField||'text')||'';
                    if (txt.trim()==='{label}') {{
                        c.setValue(recs[j].get(c.valueField||'field1'));
                        c.fireEvent('select',c,recs[j]);
                        return 'ok:'+txt;
                    }}
                }}
            }}
            return 'no-match';
        }} catch(e) {{ return 'error:'+e.message; }}
    """)
    if result and str(result).startswith("ok:"):
        print(f"    ✔ Ext.ComponentQuery: '{label}'")
        return True

    # Strategy 3: click trigger → click list item
    try:
        triggers = [t for t in driver.find_elements(
            By.CSS_SELECTOR, ".x-form-trigger, .x-combo-trigger")
            if t.is_displayed()]
        for trigger in triggers:
            driver.execute_script("arguments[0].click();", trigger)
            time.sleep(0.8)
            items = driver.find_elements(
                By.CSS_SELECTOR, ".x-combo-list-item, .x-boundlist-item")
            item_texts = [i.text.strip() for i in items]
            if item_texts:
                print(f"    Dropdown items: {item_texts}")
            for item in items:
                if item.text.strip() == label:
                    driver.execute_script("arguments[0].click();", item)
                    print(f"    ✔ Combo click: '{label}'")
                    return True
            try:
                driver.find_element(By.TAG_NAME, "body").click()
            except Exception:
                pass
    except Exception as e:
        print(f"    [combo] {e}")

    print(f"    ✗ Could not select '{label}'.")
    return False


# ── Part 1: Row parsing ────────────────────────────────────────────────────────

def parse_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    records = []
    for row in soup.select("div.x-grid3-row"):
        cells = row.select("div.x-grid3-cell-inner")
        raw   = [c.get_text(strip=True) for c in cells]
        if not any(raw):
            continue
        # Anchor on status word
        status_idx = next(
            (i for i, v in enumerate(raw) if v.strip().upper() in STATUS_WORDS),
            None
        )
        if status_idx is None:
            continue

        def g(i): return raw[i].strip() if 0 <= i < len(raw) else ""

        rec = {
            "position":   g(status_idx - 4),
            "queue":      g(status_idx - 3),
            "job":        g(status_idx - 2),
            "job_status": g(status_idx),
            "number":     g(status_idx + 1),
            "name":       g(status_idx + 2),
            "version":    g(status_idx + 3),
            "context":    g(status_idx + 4),
            "user":       g(status_idx + 5),
            "post_job":   g(status_idx + 6),
        }
        if rec["queue"] and rec["job"]:
            records.append(rec)
    return records


def row_key(r: dict) -> str:
    return f"{r.get('queue','')}|{r.get('job','')}".strip("|")


def job_id_int(r: dict) -> int:
    try:
        return int(r.get("job", "0").replace(",", ""))
    except ValueError:
        return 0


SCROLL_JS = """
var el = document.querySelector('.x-grid3-scroller');
if (!el) return 'no-scroller';
var before = el.scrollTop;
el.scrollTop += arguments[0];
el.dispatchEvent(new Event('scroll', {bubbles:true}));
return el.scrollTop > before ? 'moved' : 'bottom';
"""

def harvest_with_scroll(driver, max_rows: int) -> list[dict]:
    seen: dict[str, dict] = {}
    info = driver.execute_script("""
        var el=document.querySelector('.x-grid3-scroller');
        if(!el) return null;
        return {sh:el.scrollHeight,ch:el.clientHeight};
    """)
    step_px = (info["ch"] if info else 200) or 200
    if info:
        print(f"    Scroller: {info['sh']}px / {info['ch']}px viewport")

    idle = 0
    step = 0
    while True:
        before = len(seen)
        for r in parse_html(driver.page_source):
            k = row_key(r)
            if k and k not in seen:
                seen[k] = r
        gained = len(seen) - before
        idle = 0 if gained else idle + 1
        print(f"    scroll #{step:>3}  {len(seen):>4} rows  +{gained:>2}")

        if len(seen) >= max_rows:
            print(f"    ↩  Cap {max_rows} reached.")
            break
        if idle >= 8:
            print(f"    ✔ 8 idle scrolls — done.")
            break

        result = driver.execute_script(SCROLL_JS, step_px)
        time.sleep(SCROLL_PAUSE)
        step += 1
        if result in ("bottom", "no-scroller"):
            for r in parse_html(driver.page_source):
                k = row_key(r)
                if k and k not in seen:
                    seen[k] = r
            print(f"    ✔ Bottom. {len(seen)} rows.")
            break
    return list(seen.values())


# ── Part 2: Job Statistics ─────────────────────────────────────────────────────

def open_job_statistics(driver) -> str | None:
    """
    Click Actions → Job Statistics. Returns the new popup window handle.
    """
    print("\n    Opening Actions menu …")

    # Record current windows
    before_handles = set(driver.window_handles)

    # Click 'Actions' button/link
    try:
        actions_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//*[normalize-space(text())='Actions' or "
                "contains(@class,'actions')]"
                "[self::button or self::a or self::span or self::div]"
            ))
        )
        driver.execute_script("arguments[0].click();", actions_btn)
        time.sleep(0.8)
        print("    ✔ Actions menu opened.")
    except Exception as e:
        print(f"    ⚠  Actions button not found: {e}")
        return None

    # Click 'Job Statistics' in the dropdown menu
    try:
        stats_item = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH,
                "//*[normalize-space(text())='Job Statistics']"
            ))
        )
        driver.execute_script("arguments[0].click();", stats_item)
        print("    ✔ Clicked 'Job Statistics'.")
    except Exception as e:
        print(f"    ⚠  'Job Statistics' menu item not found: {e}")
        return None

    # Wait for new popup window
    print("    Waiting for Job Statistics popup …")
    deadline = time.time() + 15
    while time.time() < deadline:
        new_handles = set(driver.window_handles) - before_handles
        if new_handles:
            popup = new_handles.pop()
            driver.switch_to.window(popup)
            print(f"    ✔ Popup opened: {driver.current_url[:80]}")
            return popup
        time.sleep(0.5)

    print("    ⚠  No popup window appeared.")
    return None


def click_display_summary_statistics(driver) -> bool:
    """Click the 'Display Summary Statistics' button in the stats popup."""
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//input[@value='Display Summary Statistics'] | "
                "//button[normalize-space(text())='Display Summary Statistics']"
            ))
        )
        btn.click()
        print("    ✔ Clicked 'Display Summary Statistics'.")
        return True
    except Exception as e:
        print(f"    ⚠  Button not found: {e}")
        return False


def wait_for_statistics(driver, timeout: int) -> bool:
    """
    Wait for the statistics tables to populate.
    We know it's done when table cells contain numeric data
    (Total Jobs column has a number > 0).
    Poll every STATS_POLL seconds.
    """
    print(f"\n    Waiting for statistics (up to {timeout//60}min {timeout%60}s) …")
    deadline = time.time() + timeout
    elapsed  = 0
    while time.time() < deadline:
        try:
            # Check if any table cell contains a digit
            cells = driver.find_elements(By.CSS_SELECTOR, "table td")
            numeric_cells = [c for c in cells if c.text.strip().isdigit()
                             and int(c.text.strip()) > 0]
            row_count = len(driver.find_elements(By.CSS_SELECTOR, "table tr"))
            print(f"    [{elapsed:>4}s]  table rows={row_count}  "
                  f"numeric cells={len(numeric_cells)}")
            if len(numeric_cells) >= 2:  # at least 2 data cells populated
                print("    ✔ Statistics data detected.")
                return True
        except Exception:
            pass
        time.sleep(STATS_POLL)
        elapsed += STATS_POLL

    print("    ⚠  Statistics timeout — saving whatever is loaded.")
    return False


def parse_statistics_tables(html: str) -> tuple[list[dict], list[dict]]:
    """
    Parse the two statistics tables from edrpubstatisticsmain.jsp.

    Table 1 — Job Summary Statistics:
      Columns: Authoring Application | Worker Type | Total Jobs |
               Failed Jobs | Successful Jobs | % Failed | % Successful

    Table 2 — Worker Name stats:
      Columns: Worker Name | Total Jobs | Failed Jobs |
               Successful Jobs | % Failed Jobs | % Successful Jobs | Busy Time
    """
    soup   = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")

    def parse_table(tbl) -> list[dict]:
        if not tbl:
            return []
        rows = tbl.find_all("tr")
        if not rows:
            return []
        # First row = headers
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        records = []
        for tr in rows[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if not any(cells):
                continue
            while len(cells) < len(headers):
                cells.append("")
            records.append(dict(zip(headers, cells[:len(headers)])))
        return records

    summary_rows = parse_table(tables[0]) if len(tables) > 0 else []
    worker_rows  = parse_table(tables[1]) if len(tables) > 1 else []

    return summary_rows, worker_rows


# ── Output helpers ─────────────────────────────────────────────────────────────

def save_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"    💾 {path.resolve()}")


def save_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None):
    if not rows:
        print(f"    ⚠  No data to save: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"    💾 {path.resolve()}")


def format_active_jobs_report(rows: list[dict], stamp: str,
                               counts: dict) -> str:
    widths = {col: len(col) for col in COLUMNS}
    for r in rows:
        for col in COLUMNS:
            widths[col] = max(widths[col], len(r.get(col, "")))
    header = "  |  ".join(c.upper().ljust(widths[c]) for c in COLUMNS)
    sep    = "  |  ".join("-" * widths[c] for c in COLUMNS)
    lines  = [
        "Windchill WVS Job Monitor — Active Jobs Snapshot",
        f"Captured  : {stamp}",
        f"URL       : {WVS_MONITOR_URL}",
        f"Total rows: {len(rows):,}", "",
    ]
    for label, count in counts.items():
        lines.append(f"  {label:<22} {count:>4} rows")
    lines += ["", header, sep]
    STATUS_ORDER = {"READY": 0, "EXECUTING": 1, "JOB FAILED": 2}
    for status in ["READY", "EXECUTING", "JOB FAILED"]:
        group = sorted(
            [r for r in rows if r.get("job_status", "").upper() == status],
            key=job_id_int, reverse=True
        )
        if not group:
            continue
        lines.append(f"\n── {status} ({len(group)}) " + "─" * 40)
        for r in group:
            lines.append(
                "  |  ".join(r.get(c, "").ljust(widths[c]) for c in COLUMNS))
    return "\n".join(lines) + "\n"


def format_stats_report(summary: list[dict], workers: list[dict],
                         stamp: str) -> str:
    def table_txt(rows: list[dict]) -> str:
        if not rows:
            return "  (no data)\n"
        cols = list(rows[0].keys())
        widths = {c: len(c) for c in cols}
        for r in rows:
            for c in cols:
                widths[c] = max(widths[c], len(r.get(c, "")))
        header = "  |  ".join(c.ljust(widths[c]) for c in cols)
        sep    = "  |  ".join("-" * widths[c] for c in cols)
        lines  = [header, sep]
        for r in rows:
            lines.append("  |  ".join(r.get(c, "").ljust(widths[c]) for c in cols))
        return "\n".join(lines) + "\n"

    lines = [
        "Windchill WVS — Job Statistics",
        f"Captured  : {stamp}",
        f"URL       : {WVS_MONITOR_URL}",
        "",
        "═" * 65,
        "  JOB SUMMARY STATISTICS  (by Authoring Application)",
        "═" * 65,
        table_txt(summary),
        "═" * 65,
        "  WORKER STATISTICS  (by Worker Name)",
        "═" * 65,
        table_txt(workers),
    ]
    return "\n".join(lines) + "\n"


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Main ───────────────────────────────────────────────────────────────────────

def run(port: int, output_dir: Path, full_load_wait: int,
        max_failed: int, skip_stats: bool, stats_wait: int):

    stamp = ts()
    print(f"\n{'='*65}")
    print(f"  WVS Job Monitor Scraper v12  —  "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*65}\n")

    driver = build_driver(port)
    all_rows: dict[str, dict] = {}
    counts: dict[str, int] = {}

    try:
        # ══ PART 1: Active Jobs ═══════════════════════════════════════════

        print("━" * 65)
        print("  PART 1 — Active Jobs (Ready / Executing / Failed)")
        print("━" * 65)

        print("\n[1/4] Navigating to WVS Job Monitor …")
        switch_to_windchill_tab(driver)
        driver.get(WVS_MONITOR_URL)
        print(f"    Title: {driver.title!r}")
        wait_stable(driver, timeout=full_load_wait, min_rows=50,
                    label="initial table")

        print(f"\n[2/4] Harvesting {len(FILTER_CONFIG)} filters …")
        for i, (label, needs_scroll) in enumerate(FILTER_CONFIG, 1):
            print(f"\n  ── Filter {i}/{len(FILTER_CONFIG)}: '{label}' ──")
            ok = select_filter(driver, label)
            if not ok:
                counts[label] = 0
                continue
            time.sleep(1)
            n = wait_stable(driver, timeout=FILTER_WAIT, min_rows=1,
                            label=f"'{label}'")
            records = (harvest_with_scroll(driver, max_rows=max_failed)
                       if needs_scroll and n > 0
                       else parse_html(driver.page_source))
            added = 0
            for r in records:
                k = row_key(r)
                if k and k not in all_rows:
                    all_rows[k] = r
                    added += 1
            counts[label] = added
            print(f"    → {len(records)} rows parsed, {added} new unique jobs")

        STATUS_ORDER = {"READY": 0, "EXECUTING": 1, "JOB FAILED": 2}
        p1_rows = sorted(
            all_rows.values(),
            key=lambda r: (
                STATUS_ORDER.get(r.get("job_status", "").upper(), 9),
                -job_id_int(r)
            )
        )

        print(f"\n[3/4] Saving Part 1 …")
        output_dir.mkdir(parents=True, exist_ok=True)
        save_text(
            output_dir / f"job_active_{stamp}.txt",
            format_active_jobs_report(p1_rows, stamp, counts)
        )
        save_csv(output_dir / f"job_active_{stamp}.csv", p1_rows, COLUMNS)
        driver.save_screenshot(str(output_dir / f"job_active_{stamp}.png"))
        print(f"    📸 job_active_{stamp}.png")

        print(f"\n  Part 1 complete: {len(p1_rows)} active jobs")
        for label, c in counts.items():
            print(f"    {label:<22} {c:>4}")

        # ══ PART 2: Job Statistics ════════════════════════════════════════

        if skip_stats:
            print("\n  --skip-stats set. Skipping Part 2.")
        else:
            print(f"\n{'━'*65}")
            print("  PART 2 — Job Statistics")
            print(f"{'━'*65}")

            print("\n[4/4] Opening Job Statistics …")

            # Make sure we're on the WVS monitor tab
            switch_to_windchill_tab(driver)

            # Switch back to 'All' view first so Actions menu is available
            select_filter(driver, "All")
            time.sleep(1)

            popup_handle = open_job_statistics(driver)

            if popup_handle:
                print(f"\n    Popup ready. Clicking Display Summary Statistics …")
                time.sleep(1)
                clicked = click_display_summary_statistics(driver)

                if clicked:
                    wait_for_statistics(driver, timeout=stats_wait)

                    # Parse the statistics tables
                    html = driver.page_source
                    summary_rows, worker_rows = parse_statistics_tables(html)

                    print(f"\n    Summary table rows : {len(summary_rows)}")
                    print(f"    Worker table rows  : {len(worker_rows)}")

                    # Save statistics
                    driver.save_screenshot(
                        str(output_dir / f"job_stats_{stamp}.png"))
                    print(f"    📸 job_stats_{stamp}.png")

                    save_text(
                        output_dir / f"job_stats_{stamp}.txt",
                        format_stats_report(summary_rows, worker_rows, stamp)
                    )
                    if summary_rows:
                        save_csv(output_dir / f"job_stats_summary_{stamp}.csv",
                                 summary_rows)
                    if worker_rows:
                        save_csv(output_dir / f"job_stats_workers_{stamp}.csv",
                                 worker_rows)

                    print(f"\n  Part 2 complete.")
                else:
                    print("  ⚠  Could not click Display Summary Statistics.")
            else:
                print("  ⚠  Could not open Job Statistics popup.")

        # ══ Final summary ════════════════════════════════════════════════
        print(f"\n{'='*65}")
        print("  ✅  All done!")
        print(f"  Active jobs   : {len(p1_rows)}")
        for label, c in counts.items():
            print(f"    {label:<22} {c:>4}")
        print(f"  Output folder : {output_dir.resolve()}")
        print(f"{'='*65}\n")

    except Exception as e:
        import traceback
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            driver.save_screenshot(str(output_dir / f"error_{stamp}.png"))
            print(f"    📸 error_{stamp}.png")
        except Exception:
            pass
        print(f"\n❌  {e}")
        traceback.print_exc()
        raise

    finally:
        print("[Driver] Session released (Edge left open).")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Windchill WVS Job Monitor + Job Statistics Scraper v12",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Part 1: Ready + Executing + Failed jobs from filtered grid views.
Part 2: Actions → Job Statistics → Display Summary Statistics → parse tables.

Launch Edge first:
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" ^
      --remote-debugging-port=9222 --new-window ^
      "https://vcewindchill.got.volvo.net/Windchill/app/"

Run:
  python wvs_job_monitor.py                    # both parts
  python wvs_job_monitor.py --skip-stats       # Part 1 only (active jobs)
  python wvs_job_monitor.py --stats-wait 600   # allow 10 min for statistics
  python wvs_job_monitor.py --max-failed 50
        """
    )
    p.add_argument("--port",           type=int,  default=DEBUG_PORT)
    p.add_argument("--output",         default=str(OUTPUT_DIR))
    p.add_argument("--full-load-wait", type=int,  default=FULL_LOAD_WAIT)
    p.add_argument("--max-failed",     type=int,  default=MAX_FAILED_ROWS)
    p.add_argument("--skip-stats",     action="store_true",
                   help="Skip Part 2 (Job Statistics)")
    p.add_argument("--stats-wait",     type=int,  default=STATS_LOAD_WAIT,
                   help=f"Max seconds for statistics to load (default {STATS_LOAD_WAIT})")
    args = p.parse_args()

    run(
        port           = args.port,
        output_dir     = Path(args.output),
        full_load_wait = args.full_load_wait,
        max_failed     = args.max_failed,
        skip_stats     = args.skip_stats,
        stats_wait     = args.stats_wait,
    )
