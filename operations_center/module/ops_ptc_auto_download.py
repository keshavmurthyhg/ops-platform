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
#  • Clicks "All Filters" button to open the filter panel
#  • Sets:
#      - Opened By     : Both
#      - Case Status   : Both
#      - Date Created  : Custom Date Range
#                        From 01-Jan-2020  →  To today
#  • Clicks "Apply Filters"
#  • Waits up to 120 s for the full 5000+ row table to load
#  • Clicks "Export results" → ensures CSV tab → clicks Download
#  • Waits up to 60 s for file in C:\Users\a447927\Downloads\
#  • Picks the newest PTC_Cases_Report*.csv (e.g. (2).csv)
#  • Renames/copies it to:
#      C:\Users\a447927\Desktop\ops-platform\data\Ptc.csv
# =====================================================

import json
import os
import re
import string
import time
import shutil
import traceback
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
#  PATHS  — hardcoded to user a447927
# ─────────────────────────────────────────────────────────────

_HERE        = Path(__file__).resolve().parent   # operations_center/module/
_PROJECT     = _HERE.parent.parent               # project root
_DRIVERS_DIR = _PROJECT / "drivers"

# Destination for the final CSV
PTC_CSV_DEST = Path(r"C:\Users\a447927\Desktop\ops-platform\data\Ptc.csv")

# Primary download folder to watch (Edge default for this user)
USER_DOWNLOADS = Path(r"C:\Users\a447927\Downloads")

# ─────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────

PTC_URL          = "https://www.ptc.com/en/support/cstracker/casetracker#"
DEBUG_ADDRESS    = "127.0.0.1:9222"

PAGE_LOAD_WAIT   = 20    # seconds to wait after navigating to PTC
PANEL_OPEN_WAIT  = 4     # seconds after clicking "All Filters" for panel to open
RADIO_WAIT       = 1     # seconds between each radio/input change
DATE_INPUT_WAIT  = 2     # seconds after clicking Custom Date Range for inputs to appear
TABLE_LOAD_WAIT  = 120   # seconds to wait for 5000+ row table after Apply Filters
EXPORT_MODAL_WAIT= 20    # seconds max to wait for the export modal Download button
DOWNLOAD_WAIT    = 60    # seconds max to wait for CSV file to appear in Downloads
POLL_INTERVAL    = 1     # seconds between file-check polls
ELEMENT_TIMEOUT  = 15    # WebDriverWait timeout


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
    if shutil.which("msedgedriver"):
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


def _wait_for_table(driver, log_fn, max_wait=TABLE_LOAD_WAIT):
    """
    Poll until 'Export results' link is visible (table has loaded).
    Also captures the row count from 'Showing X to Y of Z rows' text.
    Returns state string or 'timeout'.
    """
    log_fn(f"    Waiting up to {max_wait}s for table to load...")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        state = driver.execute_script("""
            var all = document.querySelectorAll("a, div, span, button");
            for (var i = 0; i < all.length; i++) {
                var txt = (all[i].innerText || "").trim().toLowerCase();
                if (txt === "export results" && all[i].offsetParent !== null) {
                    var body = document.body ? document.body.innerText : "";
                    var m = body.match(/Showing\\s+\\d+\\s+to\\s+\\d+\\s+of\\s+([\\d,]+)\\s+rows/i);
                    return m ? "ready:rows=" + m[1] : "ready";
                }
            }
            var body2 = document.body ? document.body.innerText : "";
            if (body2.indexOf("NO DATA") !== -1) return "no-data";
            return "loading";
        """)
        if state != "loading":
            log_fn(f"    Table state: {state}")
            return state
        time.sleep(2)
    log_fn(f"    Timed out after {max_wait}s")
    return "timeout"


def _click_by_text(driver, text: str, tags="button,a,span,div,label", exact=True):
    """
    Click the first visible element matching text.
    Returns the click result string or None.
    """
    return driver.execute_script("""
        var text = arguments[0];
        var exact = arguments[1];
        var els = document.querySelectorAll(arguments[2]);
        for (var i = 0; i < els.length; i++) {
            var t = (els[i].innerText || els[i].value || "").trim();
            var match = exact ? (t === text) : (t.toLowerCase().indexOf(text.toLowerCase()) !== -1);
            if (match && els[i].offsetParent !== null) {
                els[i].scrollIntoView({block: "center"});
                els[i].click();
                return "clicked:" + els[i].tagName + ":" + t.substring(0, 50);
            }
        }
        return null;
    """, text, exact, tags)


def _fill_date_input_by_index(driver, index: int, value: str, log_fn=print):
    """
    Fill the Nth date input (0=From, 1=To) inside the All Filters panel.
    The PTC date inputs have placeholder 'dd-----yyyy'.
    Uses native value setter for React/Angular compatibility.
    Tries both typing via ActionChains and native setter.
    """
    result = driver.execute_script("""
        var idx   = arguments[0];
        var value = arguments[1];

        // Collect all visible date-like inputs
        var all = document.querySelectorAll("input");
        var dateInputs = [];
        for (var i = 0; i < all.length; i++) {
            var ph = (all[i].placeholder || "").toLowerCase();
            var tp = (all[i].type || "").toLowerCase();
            if (ph.indexOf("dd") !== -1 || ph.indexOf("yyyy") !== -1
                    || ph.indexOf("mon") !== -1 || tp === "date"
                    || ph === "dd-----yyyy") {
                if (all[i].offsetParent !== null) {   // visible only
                    dateInputs.push(all[i]);
                }
            }
        }

        if (dateInputs.length <= idx) {
            return "not-found: only " + dateInputs.length + " date inputs visible";
        }

        var el = dateInputs[idx];
        // Use native setter so React controlled inputs pick up the change
        var nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, "value"
        ).set;
        nativeSetter.call(el, value);
        el.dispatchEvent(new Event("input",  {bubbles: true}));
        el.dispatchEvent(new Event("change", {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent("keyup",  {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent("keydown",{bubbles: true}));
        return "filled[" + idx + "]: ph=" + (el.placeholder || "?") + " val=" + value;
    """, index, value)
    log_fn(f"    Date input[{index}]: {result}")
    return result


def _find_newest_ptc_csv(downloads_dir: Path, before_mtime: float, timeout: int, log_fn=print) -> Path:
    """
    Wait for a new CSV file matching PTC_Cases_Report*.csv (or any *.csv newer
    than before_mtime) to appear in downloads_dir.
    Also checks all drive-letter Downloads folders as fallback.
    Returns the Path of the newest matching file.
    """
    # Build list of folders to watch
    watch_dirs = [downloads_dir]
    for letter in string.ascii_uppercase:
        p = Path(f"{letter}:\\Downloads")
        if p not in watch_dirs:
            try:
                if p.exists():
                    watch_dirs.append(p)
            except Exception:
                pass
    log_fn(f"  Watching folders: {[str(d) for d in watch_dirs]}")

    deadline  = time.time() + timeout
    last_log  = 0
    while time.time() < deadline:
        best = None
        best_mtime = before_mtime
        for folder in watch_dirs:
            try:
                for f in folder.glob("*.csv"):
                    try:
                        if f.name.endswith(".crdownload") or f.name.endswith(".tmp"):
                            continue
                        mtime = f.stat().st_mtime
                        if mtime > best_mtime:
                            best_mtime = mtime
                            best = f
                    except Exception:
                        pass
            except Exception:
                pass

        if best:
            log_fn(f"  [CSV found]: {best}  ({best.stat().st_size:,} bytes)")
            return best

        # Every 10 s log status
        if time.time() - last_log > 10:
            for folder in watch_dirs:
                try:
                    csvs = list(folder.glob("*.csv"))
                    if csvs:
                        newest = max(csvs, key=lambda f: f.stat().st_mtime)
                        age    = time.time() - newest.stat().st_mtime
                        log_fn(f"  {folder}: {len(csvs)} csv, newest={newest.name} age={age:.0f}s")
                except Exception:
                    pass
            last_log = time.time()

        time.sleep(POLL_INTERVAL)

    searched = ", ".join(str(d) for d in watch_dirs)
    raise TimeoutError(
        f"No new CSV appeared after {timeout}s.\n"
        f"Searched: {searched}\n"
        "Tip: open Edge → Ctrl+J to see where the file was saved."
    )


# ─────────────────────────────────────────────────────────────
#  MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def download_latest_ptc_csv() -> dict:
    """
    Full automation:
      1. Navigate to PTC Case Tracker
      2. Open All Filters panel
      3. Set Opened By = Both, Case Status = Both,
         Date Created = Custom (01-Jan-2020 → today)
      4. Apply Filters — wait for 5000+ row table
      5. Export results → CSV → Download
      6. Move downloaded file → C:\\Users\\a447927\\Desktop\\ops-platform\\data\\Ptc.csv

    Returns  { success: bool, message: str, file: str | None }
    """
    log_lines = []

    def log(msg: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        print(line)

    def make_result(success, file=None):
        return {"success": success, "message": "\n".join(log_lines), "file": file}

    # ── Locate driver ─────────────────────────────────────────
    try:
        edge_driver_path = _find_edge_driver(log)
    except RuntimeError as e:
        log(f"DRIVER ERROR: {e}")
        return make_result(False)

    try:
        log("=" * 56)
        log("PTC AUTO DOWNLOAD — START")
        log("=" * 56)

        # ── Connect to existing Edge debug session ────────────
        edge_options = Options()
        edge_options.add_experimental_option("debuggerAddress", DEBUG_ADDRESS)

        log(f"Connecting to Edge debug session at {DEBUG_ADDRESS} ...")
        service = Service(edge_driver_path)
        try:
            driver = webdriver.Edge(service=service, options=edge_options)
        except Exception as conn_err:
            msg = str(conn_err)
            if any(k in msg.lower() for k in ["9222", "connect", "refused", "cannot"]):
                log("Edge debug session not found. Run start_edge_debug.bat first.")
            else:
                log(f"Failed to connect to Edge: {conn_err}")
            return make_result(False)

        log("Connected to Edge debug session")

        # Snapshot mtime so we can detect the new download
        before_mtime = time.time() - 2

        # ── Navigate ─────────────────────────────────────────
        log(f"Opening PTC Case Tracker: {PTC_URL}")
        driver.get(PTC_URL)
        log(f"Waiting {PAGE_LOAD_WAIT}s for page to load...")
        time.sleep(PAGE_LOAD_WAIT)
        log(f"Page title: {driver.title}")
        log(f"URL: {driver.current_url}")

        # ════════════════════════════════════════════════════════
        #  STEP 1 — Click "All Filters" to open the filter panel
        # ════════════════════════════════════════════════════════
        log("STEP 1: Opening 'All Filters' panel...")
        result = driver.execute_script("""
            var els = document.querySelectorAll("button, a, span, div, li");
            for (var i = 0; i < els.length; i++) {
                var t = (els[i].innerText || "").trim();
                // Match "All Filters" or "▼All Filters" (with triangle prefix)
                if (t === "All Filters" || t.replace(/^[^A-Za-z]+/, "") === "All Filters") {
                    els[i].scrollIntoView({block: "center"});
                    els[i].click();
                    return "clicked: " + els[i].tagName + " text='" + t + "'";
                }
            }
            return null;
        """)
        if not result:
            raise RuntimeError("'All Filters' button not found on page.")
        log(f"  {result}")
        time.sleep(PANEL_OPEN_WAIT)   # let panel animate open

        # ════════════════════════════════════════════════════════
        #  STEP 2 — Opened By → Both
        # ════════════════════════════════════════════════════════
        log("STEP 2: Opened By → Both...")
        # The panel has two "Both" radios; "Opened By" is always first
        r = driver.execute_script("""
            // Strategy: find the "Opened By" heading, then look within its
            // section container for a "Both" radio/label.
            function clickBothIn(sectionText) {
                var all = document.querySelectorAll("*");
                for (var i = 0; i < all.length; i++) {
                    var own = (all[i].childNodes.length === 1 &&
                               all[i].childNodes[0].nodeType === 3)
                              ? all[i].innerText.trim()
                              : "";
                    if (own === sectionText) {
                        // walk up to find a container that also has "Both"
                        var node = all[i];
                        for (var d = 0; d < 5; d++) {
                            node = node.parentElement;
                            if (!node) break;
                            var labels = node.querySelectorAll("label, input[type='radio']");
                            for (var j = 0; j < labels.length; j++) {
                                var lt = (labels[j].innerText || labels[j].value || "").trim();
                                if (lt === "Both") {
                                    labels[j].scrollIntoView({block:"center"});
                                    labels[j].click();
                                    return "in-section:clicked Both under " + sectionText;
                                }
                            }
                        }
                    }
                }
                return null;
            }
            var res = clickBothIn("Opened By");
            if (res) return res;

            // Fallback: first "Both" radio/label on the page
            var all = document.querySelectorAll("label, input[type='radio']");
            for (var i = 0; i < all.length; i++) {
                var t = (all[i].innerText || all[i].value || "").trim();
                if (t === "Both") {
                    all[i].scrollIntoView({block:"center"});
                    all[i].click();
                    return "fallback: clicked first Both";
                }
            }
            return "Both-not-found";
        """)
        log(f"  Opened By Both: {r}")
        time.sleep(RADIO_WAIT)

        # ════════════════════════════════════════════════════════
        #  STEP 3 — Case Status → Both
        # ════════════════════════════════════════════════════════
        log("STEP 3: Case Status → Both...")
        r = driver.execute_script("""
            function clickBothIn(sectionText) {
                var all = document.querySelectorAll("*");
                for (var i = 0; i < all.length; i++) {
                    var own = (all[i].childNodes.length === 1 &&
                               all[i].childNodes[0].nodeType === 3)
                              ? all[i].innerText.trim()
                              : "";
                    if (own === sectionText) {
                        var node = all[i];
                        for (var d = 0; d < 5; d++) {
                            node = node.parentElement;
                            if (!node) break;
                            var labels = node.querySelectorAll("label, input[type='radio']");
                            for (var j = 0; j < labels.length; j++) {
                                var lt = (labels[j].innerText || labels[j].value || "").trim();
                                if (lt === "Both") {
                                    labels[j].scrollIntoView({block:"center"});
                                    labels[j].click();
                                    return "in-section:clicked Both under " + sectionText;
                                }
                            }
                        }
                    }
                }
                return null;
            }
            var res = clickBothIn("Case Status");
            if (res) return res;

            // Fallback: second "Both" occurrence
            var all = document.querySelectorAll("label, input[type='radio']");
            var count = 0;
            for (var i = 0; i < all.length; i++) {
                var t = (all[i].innerText || all[i].value || "").trim();
                if (t === "Both") {
                    count++;
                    if (count === 2) {
                        all[i].scrollIntoView({block:"center"});
                        all[i].click();
                        return "fallback: clicked 2nd Both";
                    }
                }
            }
            return "Case-Status-Both-not-found (found " + count + " Both elements)";
        """)
        log(f"  Case Status Both: {r}")
        time.sleep(RADIO_WAIT)

        # ════════════════════════════════════════════════════════
        #  STEP 4 — Date Created → Custom Date Range
        # ════════════════════════════════════════════════════════
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        today_str = date.today().strftime("%d-%b-%Y")   # e.g. 19-Jun-2026
        from_str  = "01-Jan-2020"
        log(f"STEP 4: Date Created → Custom Date Range ({from_str} to {today_str})...")

        # --- First: dump ALL radio buttons on page so we can see exactly what's there ---
        all_radios_info = driver.execute_script("""
            var radios = document.querySelectorAll("input[type='radio']");
            var out = [];
            for (var i = 0; i < radios.length; i++) {
                var lbl = "";
                // Try <label for="id">
                if (radios[i].id) {
                    var f = document.querySelector("label[for='" + radios[i].id + "']");
                    if (f) lbl = (f.innerText || "").trim();
                }
                // Try parent element text
                if (!lbl && radios[i].parentElement) {
                    lbl = (radios[i].parentElement.innerText || "").trim();
                }
                // Try next sibling
                if (!lbl && radios[i].nextSibling) {
                    lbl = (radios[i].nextSibling.textContent || "").trim();
                }
                out.push({
                    idx:     i,
                    id:      radios[i].id || "",
                    value:   radios[i].value || "",
                    name:    radios[i].name || "",
                    checked: radios[i].checked,
                    label:   lbl.substring(0, 60),
                    visible: radios[i].offsetParent !== null
                });
            }
            return out;
        """)
        log(f"  All radio buttons found ({len(all_radios_info)}):")
        for ri in all_radios_info:
            log(f"    [{ri['idx']}] id='{ri['id']}' name='{ri['name']}' "
                f"val='{ri['value']}' checked={ri['checked']} "
                f"visible={ri['visible']} label='{ri['label']}'")

        # 4a. Click "Custom Date Range" radio — target by label text "Custom Date Range"
        #     Use Selenium find_element with XPath for precision
        custom_radio_clicked = False
        custom_radio_el = None

        # Try XPath: <label> whose text is "Custom Date Range" → click associated radio
        try:
            # XPath to find input[type=radio] that is a sibling of or preceded by
            # a text node / label containing "Custom Date Range"
            xpaths_to_try = [
                # label element whose text equals Custom Date Range
                "//label[normalize-space(text())='Custom Date Range']",
                # label containing the text
                "//label[contains(normalize-space(.),'Custom Date Range')]",
                # span/div containing the text next to a radio
                "//*[normalize-space(text())='Custom Date Range']",
            ]
            for xp in xpaths_to_try:
                try:
                    el = driver.find_element(By.XPATH, xp)
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.3)
                    el.click()
                    log(f"  Custom Date Range: clicked via XPath '{xp}' "
                        f"tag={el.tag_name} text='{el.text}'")
                    custom_radio_clicked = True
                    break
                except NoSuchElementException:
                    continue
        except Exception as xe:
            log(f"  XPath attempt exception: {xe}")

        if not custom_radio_clicked:
            # Fallback: click the radio whose label contains "custom" (case-insensitive)
            # by iterating the dumped radios list
            for ri in all_radios_info:
                if "custom" in ri["label"].lower() or "custom" in ri["value"].lower():
                    try:
                        el = driver.find_element(
                            By.CSS_SELECTOR, f"input[type='radio']:nth-of-type({ri['idx']+1})"
                        )
                    except Exception:
                        el = driver.execute_script(
                            "return document.querySelectorAll(\"input[type='radio']\")[arguments[0]];",
                            ri["idx"]
                        )
                    if el:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        driver.execute_script("arguments[0].click();", el)
                        log(f"  Custom Date Range: JS-clicked radio idx={ri['idx']} label='{ri['label']}'")
                        custom_radio_clicked = True
                        break

        if not custom_radio_clicked:
            raise RuntimeError(
                "Could not find 'Custom Date Range' radio. "
                "Check the radio dump above to see what labels are available."
            )

        # Wait for From/To date inputs to become visible
        time.sleep(DATE_INPUT_WAIT)

        # Verify the radio is actually checked
        checked_state = driver.execute_script("""
            var radios = document.querySelectorAll("input[type='radio']");
            var out = [];
            for (var i = 0; i < radios.length; i++) {
                if (radios[i].checked) {
                    var lbl = "";
                    if (radios[i].id) {
                        var f = document.querySelector("label[for='" + radios[i].id + "']");
                        if (f) lbl = f.innerText.trim();
                    }
                    if (!lbl && radios[i].parentElement)
                        lbl = radios[i].parentElement.innerText.trim();
                    out.push("idx=" + i + " val=" + radios[i].value + " lbl=" + lbl.substring(0,40));
                }
            }
            return out.join(" | ") || "none-checked";
        """)
        log(f"  Currently checked radios: {checked_state}")

        # 4b. Fill date inputs using Selenium send_keys on the actual elements
        #     Find the two date inputs that appeared after selecting Custom Date Range
        log("  Looking for date inputs...")
        date_input_els = []
        try:
            # XPath: inputs near the "From" and "To" labels inside Date Created section
            # PTC uses placeholder "dd-----yyyy"
            date_input_els = driver.find_elements(
                By.XPATH,
                "//input[contains(@placeholder,'dd') or contains(@placeholder,'yyyy') "
                "or contains(@placeholder,'Mon') or contains(@placeholder,'----')]"
            )
            log(f"  Found {len(date_input_els)} date inputs by placeholder XPath")
        except Exception as de:
            log(f"  Date input XPath failed: {de}")

        if len(date_input_els) < 2:
            # Broader search: all visible text inputs in the page
            all_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type])")
            visible_inputs = [e for e in all_inputs if e.is_displayed()]
            log(f"  Fallback: {len(visible_inputs)} visible text inputs")
            for vi in visible_inputs:
                log(f"    ph='{vi.get_attribute('placeholder')}' "
                    f"id='{vi.get_attribute('id')}' "
                    f"cls='{vi.get_attribute('class')}'")
            # Take the last 2 (From/To are at the bottom of the filter panel)
            date_input_els = visible_inputs[-2:] if len(visible_inputs) >= 2 else visible_inputs

        def _selenium_fill_date(el, value, label, log_fn):
            """Fill a date input using Selenium ActionChains (click → select all → type)."""
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)
                el.click()
                time.sleep(0.3)
                el.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                el.send_keys(Keys.DELETE)
                time.sleep(0.2)
                el.send_keys(value)
                time.sleep(0.3)
                el.send_keys(Keys.TAB)
                time.sleep(0.3)
                got = el.get_attribute("value") or ""
                log_fn(f"  {label} input: typed '{value}' → got '{got}'")
                return True
            except Exception as e:
                log_fn(f"  {label} input failed: {e}")
                return False

        if len(date_input_els) >= 1:
            _selenium_fill_date(date_input_els[0], from_str, "FROM", log)
            time.sleep(0.5)
        else:
            log("  WARNING: No FROM date input found!")

        if len(date_input_els) >= 2:
            _selenium_fill_date(date_input_els[1], today_str, "TO", log)
            time.sleep(0.5)
        else:
            log("  WARNING: No TO date input found!")

        # ════════════════════════════════════════════════════════
        #  STEP 5 — Click "Apply Filters" button
        #  CRITICAL: use Selenium find_element scoped to <button> only,
        #  never search <a> or <div> to avoid hitting nav links.
        # ════════════════════════════════════════════════════════
        log("STEP 5: Clicking 'Apply Filters'...")
        time.sleep(1)

        apply_clicked = False

        # Strategy 1: XPath for a <button> whose text is exactly "Apply Filters"
        for xp in [
            "//button[normalize-space(text())='Apply Filters']",
            "//button[normalize-space(.)='Apply Filters']",
            "//input[@type='submit' and @value='Apply Filters']",
        ]:
            try:
                btn = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.3)
                btn.click()
                log(f"  Apply Filters: clicked via XPath '{xp}'")
                apply_clicked = True
                break
            except NoSuchElementException:
                continue
            except Exception as e:
                log(f"  XPath '{xp}' error: {e}")

        if not apply_clicked:
            # Strategy 2: find ALL <button> elements, log them, pick the one matching
            all_btns = driver.find_elements(By.TAG_NAME, "button")
            log(f"  All buttons on page ({len(all_btns)}):")
            for b in all_btns:
                try:
                    log(f"    text='{b.text}' displayed={b.is_displayed()} enabled={b.is_enabled()}")
                except Exception:
                    pass
            for b in all_btns:
                try:
                    t = (b.text or "").strip()
                    if t in ("Apply Filters", "Apply") and b.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", b)
                        log(f"  Apply Filters: JS-clicked button text='{t}'")
                        apply_clicked = True
                        break
                except Exception:
                    pass

        if not apply_clicked:
            raise RuntimeError(
                "Could not find 'Apply Filters' button. "
                "Check the button list logged above."
            )

        # ════════════════════════════════════════════════════════
        #  STEP 7 — Click "Export results"
        # ════════════════════════════════════════════════════════
        log("STEP 7: Clicking 'Export results'...")
        time.sleep(2)
        r = driver.execute_script("""
            var els = document.querySelectorAll("a, button, span, div, [role='button']");
            for (var i = 0; i < els.length; i++) {
                var t = (els[i].innerText || "").trim();
                if (t === "Export results" && els[i].offsetParent !== null) {
                    els[i].scrollIntoView({block:"center"});
                    els[i].click();
                    return "clicked:" + els[i].tagName;
                }
            }
            return null;
        """)
        log(f"  Export results: {r}")
        if not r:
            raise RuntimeError("'Export results' link not found — table may not have loaded.")

        # ════════════════════════════════════════════════════════
        #  STEP 8 — Wait for export modal; ensure CSV; click Download
        # ════════════════════════════════════════════════════════
        log(f"STEP 8: Waiting up to {EXPORT_MODAL_WAIT}s for export modal...")
        modal_ready = False
        for attempt in range(EXPORT_MODAL_WAIT):
            time.sleep(1)
            state = driver.execute_script("""
                // Modal is ready when a visible "Download" button exists
                var all = document.querySelectorAll("button, a, span, div");
                for (var i = 0; i < all.length; i++) {
                    var t = (all[i].innerText || "").trim().toLowerCase();
                    if (t === "download" && all[i].offsetParent !== null) {
                        return "modal-ready";
                    }
                }
                return "waiting";
            """)
            if state == "modal-ready":
                log(f"  Export modal ready after {attempt+1}s")
                modal_ready = True
                break

        if not modal_ready:
            log("  ⚠ Modal slow to appear — attempting click anyway")

        # Confirm CSV tab is selected (it's the default, but click to be sure)
        driver.execute_script("""
            var all = document.querySelectorAll("button, a, li, span");
            for (var i = 0; i < all.length; i++) {
                var t = (all[i].innerText || "").trim().toUpperCase();
                if (t === "CSV") {
                    all[i].click();
                    return;
                }
            }
        """)
        time.sleep(1)
        log("  CSV tab confirmed")

        # Click Download button
        log("  Clicking Download button...")
        downloaded_clicked = False
        for attempt in range(15):
            downloaded_clicked = driver.execute_script("""
                // Search whole document — modal may not have a standard role
                var all = document.querySelectorAll("button, a, span, div, input[type='button']");
                for (var i = 0; i < all.length; i++) {
                    var t = (all[i].innerText || all[i].value || "").trim().toLowerCase();
                    if (t === "download" && all[i].offsetParent !== null) {
                        all[i].scrollIntoView({block:"center"});
                        all[i].click();
                        return true;
                    }
                }
                return false;
            """)
            if downloaded_clicked:
                log(f"  ✓ Download button clicked on attempt {attempt+1}")
                break
            time.sleep(1)

        if not downloaded_clicked:
            raise RuntimeError(
                "Download button inside export modal not found.\n"
                "Check if the modal opened correctly in the browser."
            )

        # ════════════════════════════════════════════════════════
        #  STEP 9 — Wait for CSV to land in Downloads
        # ════════════════════════════════════════════════════════
        log(f"STEP 9: Waiting up to {DOWNLOAD_WAIT}s for CSV to appear in Downloads...")
        downloaded_file = _find_newest_ptc_csv(USER_DOWNLOADS, before_mtime, DOWNLOAD_WAIT, log)
        log(f"  Downloaded: {downloaded_file}  ({downloaded_file.stat().st_size:,} bytes)")

        # ════════════════════════════════════════════════════════
        #  STEP 10 — Rename / copy to destination Ptc.csv
        # ════════════════════════════════════════════════════════
        log(f"STEP 10: Saving to {PTC_CSV_DEST} ...")
        PTC_CSV_DEST.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(downloaded_file, PTC_CSV_DEST)
        log(f"  ✓ Saved → {PTC_CSV_DEST}  ({PTC_CSV_DEST.stat().st_size:,} bytes)")

        log("=" * 56)
        log("PTC AUTO DOWNLOAD — COMPLETE ✓")
        log("=" * 56)

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
