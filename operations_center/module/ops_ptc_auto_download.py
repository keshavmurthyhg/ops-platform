# =====================================================
#  PTC CASE TRACKER — AUTO DOWNLOAD
# =====================================================
#
#  Automates the PTC Case Tracker CSV export using
#  Selenium attached to an existing Edge debug session.
#
#  PRE-REQUISITES
#  ──────────────
#  1. Run start_edge_debug.bat  (closes all Edge,
#     opens Edge on port 9222, navigates to PTC).
#  2. Log in to PTC if prompted (session is saved).
#  3. Click "Refresh PTC Cases" in the dashboard.
#
#  WHAT THE SCRIPT DOES
#  ─────────────────────
#  • Navigates to the Case Tracker page
#  • Applies filters:
#      - Severity  : All
#      - Status    : Open  (both Open + Closed if needed)
#      - Opened By : My Company
#      - Date      : Custom  Jan 1 2020 → today
#  • Clicks "Export results" → CSV already selected → Download
#  • Saves the file as  data/Ptc.csv
# =====================================================

import json
import os
import string
import time
import shutil
import traceback
import subprocess
from pathlib import Path
from datetime import datetime, date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)

# ─────────────────────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────────────────────

_HERE        = Path(__file__).resolve().parent   # operations_center/module/
_PROJECT     = _HERE.parent.parent               # project root
_DATA_DIR    = _PROJECT / "data"
_DRIVERS_DIR = _PROJECT / "drivers"

PTC_CSV_DEST = _DATA_DIR / "Ptc.csv"

# ─────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────

PTC_URL       = "https://www.ptc.com/en/support/cstracker/casetracker#"
DEBUG_ADDRESS = "127.0.0.1:9222"

PAGE_LOAD_WAIT   = 20   # seconds for initial page load after navigation
FILTER_WAIT      = 5    # seconds after clicking each filter
EXPORT_WAIT      = 4    # seconds after clicking Export results
DOWNLOAD_WAIT    = 30   # max seconds to wait for CSV file
POLL_INTERVAL    = 1    # seconds between file-check polls
ELEMENT_TIMEOUT  = 15   # WebDriverWait timeout


# ─────────────────────────────────────────────────────────────
#  DRIVER DISCOVERY
# ─────────────────────────────────────────────────────────────

def _find_edge_driver(log_fn=print) -> str:
    # 1. Project drivers/ folder
    project_driver = _DRIVERS_DIR / "msedgedriver.exe"
    if project_driver.exists():
        log_fn(f"Driver found in project: {project_driver}")
        return str(project_driver)

    # 2. Common Windows locations
    for p in [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedgedriver.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedgedriver.exe"),
        Path(r"C:\Windows\System32\msedgedriver.exe"),
    ]:
        if p.exists():
            log_fn(f"Driver found at: {p}")
            return str(p)

    # 3. webdriver-manager (auto-downloads matching version)
    try:
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        log_fn("Using webdriver-manager to download msedgedriver...")
        path = EdgeChromiumDriverManager().install()
        log_fn(f"webdriver-manager installed: {path}")
        return path
    except ImportError:
        log_fn("webdriver-manager not installed — run: pip install webdriver-manager")
    except Exception as e:
        log_fn(f"webdriver-manager failed: {e}")

    # 4. System PATH
    import shutil as _shutil
    if _shutil.which("msedgedriver"):
        return "msedgedriver"

    raise RuntimeError(
        "msedgedriver not found.\n"
        "Fix: pip install webdriver-manager   (auto-downloads the right version)\n"
        "  OR copy msedgedriver.exe into the project's drivers/ folder."
    )


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────

def _js_click(driver, el):
    """Click element, fall back to JS click if intercepted."""
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)


def _wait_for_table(driver, log_fn, max_wait=90):
    """
    Wait until the Case Tracker table has at least one data row,
    or the page shows a recognisable state (NO DATA / Export results).
    Polls every 2 seconds up to max_wait seconds.
    Returns True when table/export is visible, False on timeout.
    """
    log_fn(f"    Waiting up to {max_wait}s for table to load...")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        state = driver.execute_script("""
            var body = document.body ? document.body.innerText : "";
            // Table has loaded if Export results link is visible
            var expLinks = document.querySelectorAll("a, div, span");
            for (var i = 0; i < expLinks.length; i++) {
                if ((expLinks[i].innerText || "").trim().toLowerCase() === "export results"
                        && expLinks[i].offsetParent !== null) {
                    return "export-visible";
                }
            }
            if (body.indexOf("NO DATA") !== -1) return "no-data";
            // Any table row with a case number (7+ digit number)
            var rows = document.querySelectorAll("table tr, .case-row, [class*='row']");
            if (rows.length > 1) return "rows:" + rows.length;
            return "loading";
        """)
        if state != "loading":
            log_fn(f"    Table state: {state}")
            return state
        time.sleep(2)
    log_fn(f"    Timed out waiting for table ({max_wait}s)")
    return "timeout"


def _click_filter_btn(driver, label: str, log_fn=print):
    """
    Click a PTC Case Tracker filter button by its exact visible text.
    Uses CSS class hints (btn, filter, action) to target real buttons
    and avoids navigation links entirely.
    Returns the class of the element clicked, or None.
    """
    log_fn(f"  → Filter: {label}")
    result = driver.execute_script("""
        var label = arguments[0];
        // Pass 1: BUTTON elements only — most reliable
        var buttons = document.querySelectorAll("button");
        for (var i = 0; i < buttons.length; i++) {
            if ((buttons[i].innerText || "").trim() === label) {
                buttons[i].scrollIntoView({block: "center"});
                buttons[i].click();
                return "button:" + (buttons[i].getAttribute("class") || "");
            }
        }
        // Pass 2: elements with filter-like class names (not <a> tags)
        var els = document.querySelectorAll(
            "li, span, div"
        );
        for (var i = 0; i < els.length; i++) {
            var cls = (els[i].getAttribute("class") || "").toLowerCase();
            var looks_like_filter = cls.indexOf("btn") !== -1
                                 || cls.indexOf("filter") !== -1
                                 || cls.indexOf("action") !== -1
                                 || cls.indexOf("tab") !== -1;
            if (looks_like_filter
                    && (els[i].innerText || "").trim() === label) {
                els[i].scrollIntoView({block: "center"});
                els[i].click();
                return "filter-el:" + cls;
            }
        }
        return null;
    """, label)
    if result:
        log_fn(f"    ✓ clicked ({result})")
    else:
        log_fn(f"    ⚠ not found — page may have changed")
    return result


def _set_date_range_select(driver, log_fn=print):
    """
    Set Date Created to the widest available range.
    Reads the <select> options, picks the one containing 2020 if it
    exists (PTC sometimes remembers the last range), otherwise looks
    for a 'Custom' option and fills the date inputs.
    Falls back gracefully — the other filters (My Company + Open +
    Closed) already return the right data without the date filter.
    """
    today_str = date.today().strftime("%m/%d/%Y")
    log_fn(f"  Date range: 01/01/2020 -> {today_str}")

    # Inspect select options — use Array.join with a pipe separator
    # to avoid newline-in-string JS syntax errors
    options_info = driver.execute_script(
        "var s = document.querySelectorAll('select');"
        "var out = [];"
        "for (var i=0;i<s.length;i++){"
        "  var opts=[];"
        "  for (var j=0;j<s[i].options.length;j++){"
        "    opts.push(s[i].options[j].value+':'+s[i].options[j].text);"
        "  }"
        "  out.push('sel['+i+']='+opts.join('|'));"
        "}"
        "return out.join(' || ') || 'no-selects';"
    )
    log_fn(f"    Options: {str(options_info)[:300]}")

    # Try to set the best option
    result = driver.execute_script(
        "var today = arguments[0];"
        "var sels = document.querySelectorAll('select');"
        "for (var i=0;i<sels.length;i++){"
        "  var sel = sels[i];"
        # Priority 1: option already contains 2020 (widest range)
        "  for (var j=0;j<sel.options.length;j++){"
        "    var t = sel.options[j].text.toLowerCase();"
        "    if (t.indexOf('2020')!==-1||t.indexOf('all time')!==-1){"
        "      sel.value=sel.options[j].value;"
        "      sel.dispatchEvent(new Event('change',{bubbles:true}));"
        "      return 'found-2020:'+sel.options[j].text;"
        "    }"
        "  }"
        # Priority 2: custom option
        "  for (var j=0;j<sel.options.length;j++){"
        "    var v=sel.options[j].value.toLowerCase();"
        "    var t=sel.options[j].text.toLowerCase();"
        "    if (v==='custom'||t.indexOf('custom')!==-1){"
        "      sel.value=sel.options[j].value;"
        "      sel.dispatchEvent(new Event('change',{bubbles:true}));"
        "      return 'selected-custom:'+sel.options[j].text;"
        "    }"
        "  }"
        "}"
        "return 'no-match';",
        today_str
    )
    log_fn(f"    Select result: {result}")
    time.sleep(2)

    # If custom was selected, fill the date inputs that appear
    if result and "custom" in str(result).lower():
        filled = driver.execute_script(
            "var today = arguments[0];"
            "var inputs = document.querySelectorAll("
            "  'input[type=text],input[type=date],input[placeholder]'"
            ");"
            "var count=0;"
            "for (var i=0;i<inputs.length&&count<2;i++){"
            "  var ph=(inputs[i].placeholder||'').toLowerCase();"
            "  var nm=(inputs[i].name||'').toLowerCase();"
            "  var isStart=ph==='mm/dd/yyyy'||ph.indexOf('from')!==-1"
            "    ||ph.indexOf('start')!==-1||nm.indexOf('start')!==-1"
            "    ||nm.indexOf('from')!==-1;"
            "  var isEnd=ph.indexOf('to')!==-1||ph.indexOf('end')!==-1"
            "    ||nm.indexOf('end')!==-1||nm.indexOf('to')!==-1;"
            "  if (isStart&&count===0){"
            "    inputs[i].value='01/01/2020';"
            "    inputs[i].dispatchEvent(new Event('change',{bubbles:true}));"
            "    count++;"
            "  } else if (isEnd&&count===1){"
            "    inputs[i].value=today;"
            "    inputs[i].dispatchEvent(new Event('change',{bubbles:true}));"
            "    count++;"
            "  }"
            "}"
            # Click Apply/Search if present
            "var btns=document.querySelectorAll('button');"
            "for (var i=0;i<btns.length;i++){"
            "  var t=(btns[i].innerText||'').trim();"
            "  if (t==='Apply'||t==='Search'||t==='OK'||t==='Go'){"
            "    btns[i].click();"
            "    return 'filled '+count+' clicked:'+t;"
            "  }"
            "}"
            "return 'filled '+count;",
            today_str
        )
        log_fn(f"    Date fill: {filled}")
        time.sleep(1)

    return result


def _get_all_download_dirs(primary_dir: Path) -> list:
    """
    Build a comprehensive list of every folder Edge might save to.
    Reads Edge Preferences JSON for the real configured path,
    then checks every drive letter for a Downloads folder.
    """
    dirs = [primary_dir]

    # Read Edge's actual configured download dir from Preferences JSON
    for prefs_file in [
        Path(r"C:\EdgeDebug\Default\Preferences"),
        Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/Preferences",
    ]:
        try:
            data = json.loads(prefs_file.read_text(encoding="utf-8"))
            dl = (data.get("savefile") or {}).get("default_directory", "") or \
                 (data.get("download") or {}).get("default_directory", "")
            if dl:
                p = Path(dl)
                if p not in dirs:
                    dirs.append(p)
        except Exception:
            pass

    # Windows user Downloads
    win_dl = Path.home() / "Downloads"
    if win_dl not in dirs:
        dirs.append(win_dl)

    # All drive-letter Downloads folders (A–Z)
    for letter in string.ascii_uppercase:
        p = Path(f"{letter}:\\Downloads")
        if p not in dirs:
            try:
                if p.exists():
                    dirs.append(p)
            except Exception:
                pass

    return dirs


def _wait_for_new_csv(downloads_dir: Path, before_mtime: float, timeout: int) -> Path:
    """
    Poll all plausible download folders for a new CSV file.
    Covers G:\\Downloads and any other drive Edge might use.
    """
    search_dirs = _get_all_download_dirs(downloads_dir)
    print(f"  Watching: {[str(d) for d in search_dirs]}")

    deadline = time.time() + timeout
    last_log  = 0
    while time.time() < deadline:
        for folder in search_dirs:
            try:
                for f in folder.glob("*.csv"):
                    try:
                        mtime = f.stat().st_mtime
                        if (mtime > before_mtime
                                and not f.name.endswith(".crdownload")
                                and not f.name.endswith(".tmp")):
                            print(f"  [CSV found in {folder}]: {f.name}")
                            return f
                    except Exception:
                        pass
            except Exception:
                pass

        # Every 10s log what exists for diagnosis
        if time.time() - last_log > 10:
            for folder in search_dirs:
                try:
                    csvs = list(folder.glob("*.csv"))
                    if csvs:
                        newest = max(csvs, key=lambda f: f.stat().st_mtime)
                        age = time.time() - newest.stat().st_mtime
                        print(f"  {folder}: {len(csvs)} csv, newest={newest.name} age={age:.0f}s")
                except Exception:
                    pass
            last_log = time.time()

        time.sleep(POLL_INTERVAL)

    searched = ", ".join(str(d) for d in search_dirs)
    raise TimeoutError(
        f"No new CSV after {timeout}s.\n"
        f"Searched: {searched}\n"
        "Check Edge's download history (Ctrl+J in Edge) to find where the file landed."
    )


# ─────────────────────────────────────────────────────────────
#  MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def download_latest_ptc_csv() -> dict:
    """
    Download PTC Case Tracker CSV and save as data/Ptc.csv.

    Returns
    -------
    dict  { success: bool, message: str, file: str | None }
    """

    log_lines = []

    def log(msg: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        print(line)

    def make_result(success, file=None):
        return {"success": success, "message": "\n".join(log_lines), "file": file}

    # ── Locate driver before touching Selenium ────────────────
    try:
        edge_driver_path = _find_edge_driver(log)
    except RuntimeError as e:
        log(f"DRIVER ERROR: {e}")
        return make_result(False)

    try:
        log("=" * 52)
        log("PTC AUTO DOWNLOAD — START")
        log("=" * 52)

        # ── Edge options ──────────────────────────────────────
        # Force the debug session to download into a known folder.
        # We use a subfolder in the project so it works regardless of
        # which Windows user profile Edge's debug session uses.
        downloads_dir = _PROJECT / "ptc_downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        prefs = {
            "download.default_directory":   str(downloads_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade":   True,
            "savefile.default_directory":   str(downloads_dir),
        }
        edge_options = Options()
        edge_options.add_experimental_option("prefs", prefs)
        edge_options.add_experimental_option("debuggerAddress", DEBUG_ADDRESS)

        # ── Connect ───────────────────────────────────────────
        log(f"Connecting to Edge debug session at {DEBUG_ADDRESS} ...")
        service = Service(edge_driver_path)
        try:
            driver = webdriver.Edge(service=service, options=edge_options)
        except Exception as conn_err:
            msg = str(conn_err)
            if any(k in msg.lower() for k in ["9222", "connect", "refused", "cannot"]):
                log(
                    "Edge debug session not found.\n"
                    "Run start_edge_debug.bat, wait for Edge to open, then try again."
                )
            else:
                log(f"Failed to connect to Edge: {conn_err}")
            return make_result(False)

        wait = WebDriverWait(driver, ELEMENT_TIMEOUT)
        log("Connected to Edge debug session")

        # Note time before download for file detection
        before_mtime = time.time() - 2

        # ── Navigate to Case Tracker ──────────────────────────
        log("Opening PTC Case Tracker...")

        try:
            driver.get(PTC_URL)
        except Exception as nav_err:
            raise RuntimeError(
                f"Unable to open PTC Case Tracker: {nav_err}"
            )

        log(f"Waiting {PAGE_LOAD_WAIT}s for page to load...")
        time.sleep(PAGE_LOAD_WAIT)

        try:
            final_url = driver.current_url
        except Exception:
            final_url = "Unknown"

        log(f"Loaded URL: {final_url}")
        log(f"Page: {driver.title}")

        # ── Apply filters ──────────────────────────────────────
        # Each filter reloads the table (10-90s).
        # We click a filter, then wait for the table to finish
        # loading before moving to the next filter.
        log("Applying filters...")

        # ── 1. My Company (Opened By) ──────────────────────────
        log("  Step 1: My Company")
        _click_filter_btn(driver, "My Company", log)
        state = _wait_for_table(driver, log, max_wait=90)
        log(f"  Table after My Company: {state}")
        if state == "timeout":
            raise RuntimeError("Table did not load after 'My Company' filter.")

        # ── 2. Open (Status) ───────────────────────────────────
        log("  Step 2: Open")
        _click_filter_btn(driver, "Open", log)
        state = _wait_for_table(driver, log, max_wait=90)
        log(f"  Table after Open: {state}")

        # ── 3. Closed (Status — adds to Open) ─────────────────
        log("  Step 3: Closed")
        _click_filter_btn(driver, "Closed", log)
        state = _wait_for_table(driver, log, max_wait=90)
        log(f"  Table after Closed: {state}")

        # ── 4. Date range via <select> ─────────────────────────
        log("  Step 4: Date range")
        try:
            date_result = _set_date_range_select(driver, log)
            if date_result and "no-match" not in str(date_result):
                state = _wait_for_table(driver, log, max_wait=90)
                log(f"  Table after date range: {state}")
            else:
                log("  No matching date option — proceeding with current results")
        except Exception as date_err:
            log(f"  Date range step skipped (non-fatal): {date_err}")

        log(f"Page after all filters: {driver.title}")

        # ── Click Export results ───────────────────────────────
        log("Clicking 'Export results'...")
        export_clicked = False

        export_xpaths = [
            "//*[normalize-space(text())='Export results']",
            "//*[normalize-space(text())='Export Results']",
            "//*[contains(normalize-space(text()),'Export result')]",
            "//*[contains(normalize-space(text()),'export result')]",
        ]
        for xp in export_xpaths:
            try:
                els = driver.find_elements(By.XPATH, xp)
                visible = [e for e in els if e.is_displayed()]
                if visible:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", visible[0]
                    )
                    time.sleep(0.3)
                    _js_click(driver, visible[0])
                    log(f"  ✓ Clicked Export results")
                    export_clicked = True
                    break
            except Exception:
                pass

        if not export_clicked:
            # JS fallback
            js_result = driver.execute_script("""
                for (const el of document.querySelectorAll('a,button,span,div')) {
                    const txt = (el.innerText || '').trim().toLowerCase();
                    if (el.offsetParent && txt === 'export results') {
                        el.click(); return 'clicked: ' + el.tagName;
                    }
                }
                return 'not found';
            """)
            log(f"  Export JS result: {js_result}")
            if js_result == "not found":
                raise RuntimeError(
                    "'Export results' link not found. "
                    "Check that the page loaded data with the selected filters."
                )
            export_clicked = True

        # Wait for the export dialog to fully appear
        # Poll for up to 10s for the Download button to appear in DOM
        log("Waiting for Export dialog...")
        dialog_appeared = False
        for _ in range(10):
            chk = driver.find_elements(
                By.XPATH,
                "//button[normalize-space(.)='Download'] | "
                "//button[contains(normalize-space(.),'Download')] | "
                "//*[normalize-space(text())='Download']"
            )
            if chk:
                dialog_appeared = True
                break
            time.sleep(1)

        if not dialog_appeared:
            snap = driver.execute_script(
                "return document.body ? document.body.innerText.slice(0,400) : 'no body';"
            )
            log(f"Page snapshot: {snap}")
            raise RuntimeError(
                "Export dialog did not appear — Download button not found after 10s."
            )

        # CSV is pre-selected by default — click Download directly
        log("CSV pre-selected — clicking Download...")

        # JS scan: exact text match, no offsetParent check (modals break it)
        js_dl = driver.execute_script("""
            var tags = document.querySelectorAll('button, a, input[type=button]');
            // exact match
            for (var i=0; i<tags.length; i++) {
                var t = (tags[i].innerText || tags[i].value || '').trim();
                if (t === 'Download') {
                    tags[i].scrollIntoView({block:'center'});
                    tags[i].click();
                    return 'exact:' + tags[i].tagName;
                }
            }
            // contains match
            for (var i=0; i<tags.length; i++) {
                var t = (tags[i].innerText || tags[i].value || '').trim().toLowerCase();
                if (t.indexOf('download') !== -1) {
                    tags[i].scrollIntoView({block:'center'});
                    tags[i].click();
                    return 'contains:' + tags[i].tagName;
                }
            }
            // diagnostic: list all button texts
            var btns = [];
            var all = document.querySelectorAll('button, a');
            for (var i=0; i<all.length && btns.length<20; i++) {
                var t = (all[i].innerText||'').trim();
                if (t && t.length < 30) btns.push(t);
            }
            return 'not found | buttons: ' + btns.join(' || ');
        """)
        log(f"  Download JS: {js_dl}")

        download_clicked = js_dl.startswith("exact:") or js_dl.startswith("contains:")

        if not download_clicked:
            # Selenium fallback — no visibility filter
            for xp in [
                "//button[normalize-space(.)='Download']",
                "//button[contains(normalize-space(.),'Download')]",
                "//*[normalize-space(text())='Download']",
            ]:
                els = driver.find_elements(By.XPATH, xp)
                if els:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", els[0]
                    )
                    time.sleep(0.3)
                    _js_click(driver, els[0])
                    log(f"  ✓ Download via XPATH")
                    download_clicked = True
                    break

        if not download_clicked:
            raise RuntimeError(
                f"Download button not clickable. JS scan: {js_dl}"
            )

        # ── Wait for CSV file ──────────────────────────────────
        log(f"Waiting up to {DOWNLOAD_WAIT}s for CSV to download...")
        downloaded = _wait_for_new_csv(downloads_dir, before_mtime, DOWNLOAD_WAIT)
        log(f"Downloaded: {downloaded.name}  ({downloaded.stat().st_size:,} bytes)")

        # ── Save to data/Ptc.csv ───────────────────────────────
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(downloaded, PTC_CSV_DEST)
        log(f"Saved → {PTC_CSV_DEST}")

        log("=" * 52)
        log("PTC AUTO DOWNLOAD — COMPLETE ✓")
        log("=" * 52)

        return make_result(True, str(PTC_CSV_DEST))

    except Exception as exc:
        log(f"ERROR: {type(exc).__name__}: {exc}")
        log(traceback.format_exc())
        return make_result(False)


# ─────────────────────────────────────────────────────────────
#  STANDALONE  (python ops_ptc_auto_download.py)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    res = download_latest_ptc_csv()
    if res["success"]:
        print(f"\n✅ SUCCESS — file: {res['file']}")
    else:
        print(f"\n❌ FAILED\n{res['message']}")
