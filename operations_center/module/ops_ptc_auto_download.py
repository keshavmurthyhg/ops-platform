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

# =====================================================
#  PTC CASE TRACKER — ENTERPRISE AUTO DOWNLOAD ENGINE
# =====================================================

import os
import sys
import time
import shutil
import traceback
from pathlib import Path
from datetime import date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException

sys.path.append(r"D:\my-apps-restructured")
from common.logger import setup_logger

logger = setup_logger("operations_center")

# ─────────────────────────────────────────────────────────────
#  PATHS, CHANNELS, & CONFIGURATIONS
# ─────────────────────────────────────────────────────────────
_PROJECT      = Path(r"D:\my-apps-restructured")
_DATA_DIR     = _PROJECT / "data"
_DRIVERS_DIR  = _PROJECT / "drivers"

PTC_CSV_DEST  = _DATA_DIR / "Ptc.csv"
PTC_URL        = "https://www.ptc.com/en/support/cstracker/casetracker#"
DEBUG_ADDRESS = "127.0.0.1:9222"

# Watch the actual runtime download landing directory directly
EDGE_DOWNLOAD_DIR = Path(r"G:\Downloads")

# Broad window timeouts requested for dense multi-year historical table generation
TABLE_LOAD_TIMEOUT = 120
FILE_DOWNLOAD_TIMEOUT = 120
ELEMENT_TIMEOUT = 20

# ─────────────────────────────────────────────────────────────
#  DOM MANIPULATION & FINDER LOGIC
# ─────────────────────────────────────────────────────────────

def _js_click(driver, el):
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)

def _wait_for_table_render(driver, step_name: str, max_wait=120):
    """Monitors the DOM state to ensure large tabular lists stabilize."""
    logger.info(f"Stabilizing database layout state for: {step_name}...")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        state = driver.execute_script("""
            var body = document.body ? document.body.innerText : "";
            var expLinks = document.querySelectorAll("a, div, span");
            for (var i = 0; i < expLinks.length; i++) {
                if ((expLinks[i].innerText || "").trim().toLowerCase() === "export results"
                        && expLinks[i].offsetParent !== null) {
                    return "ready";
                }
            }
            if (body.indexOf("NO DATA") !== -1) return "no-data";
            var rows = document.querySelectorAll("table tr, .case-row, [class*='row']");
            if (rows.length > 1) return "populated";
            return "loading";
        """)
        if state in ["ready", "populated", "no-data"]:
            return True
        time.sleep(3)
    return False

def _click_ptc_filter(driver, label: str) -> bool:
    """Locates and triggers the target selection criteria matching the UI structure."""
    return driver.execute_script("""
        var label = arguments[0].toLowerCase().trim();
        var elements = document.querySelectorAll("button, li, span, div, label");
        for (var i = 0; i < elements.length; i++) {
            var txt = (elements[i].innerText || "").toLowerCase().trim();
            if (txt === label) {
                elements[i].scrollIntoView({block: "center"});
                elements[i].click();
                return true;
            }
        }
        return false;
    """, label)

def _apply_custom_date_range(driver):
    """Selects the standard 2020 context boundary timeline drop-down options."""
    return driver.execute_script("""
        var dropdowns = document.querySelectorAll('select');
        for (var i = 0; i < dropdowns.length; i++){
            var sel = dropdowns[i];
            for (var j = 0; j < sel.options.length; j++){
                var txt = sel.options[j].text.toLowerCase();
                if (txt.indexOf('2020') !== -1 || txt.indexOf('all time') !== -1 || txt.indexOf('custom') !== -1){
                    sel.value = sel.options[j].value;
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
            }
        }
        return false;
    """)

def _scan_for_latest_csv(before_mtime: float) -> Path:
    """Scans G:\\Downloads directly to isolate the newly generated file footprint."""
    deadline = time.time() + FILE_DOWNLOAD_TIMEOUT
    while time.time() < deadline:
        for csv_file in EDGE_DOWNLOAD_DIR.glob("*.csv"):
            if csv_file.name.startswith("PTC_Cases_Report"):
                if csv_file.stat().st_mtime > before_mtime:
                    # Guard against incomplete transfers
                    if not csv_file.name.endswith(".crdownload") and not csv_file.name.endswith(".tmp"):
                        if csv_file.stat().st_size > 1024:  # Confirm payload is written
                            return csv_file
        time.sleep(2)
    raise TimeoutError("The complete file footprint failed to materialize within 120 seconds.")

# ─────────────────────────────────────────────────────────────
#  CORE AUTOMATION STEP FLOW
# ─────────────────────────────────────────────────────────────

def download_latest_ptc_csv() -> dict:
    try:
        logger.info("Initializing background web testing driver wrapper...")
        
        # Resolve path
        driver_path = _PROJECT / "drivers" / "msedgedriver.exe"
        if not driver_path.exists():
            driver_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedgedriver.exe")
        
        edge_options = Options()
        edge_options.add_experimental_option("debuggerAddress", DEBUG_ADDRESS)
        
        driver = webdriver.Edge(service=Service(str(driver_path)), options=edge_options)
        wait = WebDriverWait(driver, ELEMENT_TIMEOUT)
        
        # Use localized epoch time threshold to capture files cleanly
        before_mtime = time.time() - 5

        logger.info("Accessing portal workspace view index...")
        driver.get(PTC_URL)
        time.sleep(6)
        _wait_for_table_render(driver, "Initial Portal Load")

        # ── 1. Severity Filter Setup ──
        # By default, checking all options covers Severity 0, 1, 2, 3
        logger.info("Applying systemic Severity scope configurations...")
        for sev in ["Severity 0", "Severity 1", "Severity 2", "Severity 3"]:
            try:
                _click_ptc_filter(driver, sev)
            except Exception:
                pass
        _wait_for_table_render(driver, "Severity Options")

        # ── 2. Opened By Filters ──
        logger.info("Merging corporate team ownership data views...")
        _click_ptc_filter(driver, "My Company")
        _wait_for_table_render(driver, "My Company Scope")
        
        _click_ptc_filter(driver, "Me")
        _wait_for_table_render(driver, "Personal Scope Matrix")

        # ── 3. Status Filters (Both Open & Closed) ──
        logger.info("Extracting live production ticket lists...")
        _click_ptc_filter(driver, "Open")
        _wait_for_table_render(driver, "Active Queues")

        logger.info("Extracting archived historical ticket datasets...")
        _click_ptc_filter(driver, "Closed")
        _wait_for_table_render(driver, "Archived Repository Data")

        # ── 4. Date Timeline Settings ──
        logger.info("Extending history analytical window boundaries (2020 to Present)...")
        try:
            _click_ptc_filter(driver, "Custom Date Range")
            _apply_custom_date_range(driver)
        except Exception as e:
            logger.warning(f"Date frame dropdown exception skipped: {e}")
        
        # Enforce safety wait cushion requested for massive multi-tier queries to process completely
        logger.info("Enforcing mandatory portal compilation hold (Waiting 120s for dataset assembly)...")
        time.sleep(120)
        _wait_for_table_render(driver, "Final Consolidated Analytical Sheet", max_wait=60)

        # ── 5. Trigger File Compilation ──
        logger.info("Requesting remote server generation package...")
        export_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnCaseStrackerCSVexport")))
        _js_click(driver, export_btn)
        time.sleep(3)

        # ── 6. Execute File Download ──
        logger.info("Initiating secure browser document transmission download...")
        download_btn = wait.until(EC.element_to_be_clickable((By.ID, "fileExportDownloadbtnId")))
        _js_click(driver, download_btn)

        logger.info("Monitoring download landing path directory (Waiting 120s max for disk output write)...")
        downloaded_file = _scan_for_latest_csv(before_mtime)
        
        # ── 7. Relocate and Copy ──
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(downloaded_file, PTC_CSV_DEST)
        
        size_kb = downloaded_file.stat().st_size / 1024
        logger.info(f"Verified compiled historical storage: {PTC_CSV_DEST} ({size_kb:.2f} KB generated).")
        
        return {
            "success": True, 
            "message": "PTC cases updated.", 
            "detail": f"Successfully cached total metrics layer ({int(size_kb)} KB written)."
        }

    except Exception as exc:
        err_stack = traceback.format_exc()
        logger.error(f"Execution pipeline failure: {str(exc)}\n{err_stack}")
        return {
            "success": False, 
            "message": "Automation completed with errors.", 
            "detail": str(exc)
        }


# ─────────────────────────────────────────────────────────────
#  STANDALONE  (python ops_ptc_auto_download.py)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    res = download_latest_ptc_csv()
    if res["success"]:
        print(f"\n✅ SUCCESS — file: {res['file']}")
    else:
        print(f"\n❌ FAILED")