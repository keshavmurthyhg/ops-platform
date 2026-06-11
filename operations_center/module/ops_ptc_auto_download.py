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

# =====================================================
#  PTC CASE TRACKER — ENTERPRISE AUTO DOWNLOAD ENGINE
# =====================================================

# =====================================================
#  PTC CASE TRACKER — ENTERPRISE AUTO DOWNLOAD ENGINE
# =====================================================

# =====================================================
#  PTC CASE TRACKER — ENTERPRISE AUTO DOWNLOAD ENGINE
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

EDGE_DOWNLOAD_DIR = Path(r"G:\Downloads")

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

def _ensure_toggle_active(driver, label_text: str):
    """
    Finds a toggle block by its button text label string. 
    Clicks it ONLY if it lacks active visual indicators to avoid untoggling.
    """
    driver.execute_script("""
        var target = arguments[0].toLowerCase().trim();
        var elements = document.querySelectorAll("button, li, span, div, label");
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            if ((el.innerText || "").toLowerCase().trim() === target) {
                var styles = window.getComputedStyle(el);
                var classes = el.className || "";
                
                // Inspect active states (PTC styles use distinct green fill background properties)
                var isActive = classes.indexOf("active") !== -1 || 
                               classes.indexOf("selected") !== -1 || 
                               styles.backgroundColor.indexOf("rgba(0, 0, 0, 0)") === -1;
                               
                if (!isActive) {
                    el.scrollIntoView({block: "center"});
                    el.click();
                }
                break;
            }
        }
    """, label_text)

def _select_all_time_dropdown(driver):
    """Interacts directly with the Date dropdown element box to select All time data."""
    return driver.execute_script("""
        var selects = document.querySelectorAll("select");
        for (var i = 0; i < selects.length; i++) {
            var sel = selects[i];
            for (var j = 0; j < sel.options.length; j++) {
                var txt = sel.options[j].text.toLowerCase();
                if (txt.indexOf("all") !== -1 || txt.indexOf("history") !== -1 || txt.indexOf("custom") !== -1) {
                    sel.selectedIndex = j;
                    sel.dispatchEvent(new Event("change", { bubbles: true }));
                    return true;
                }
            }
        }
        return false;
    """)

def _scan_for_latest_csv(before_mtime: float) -> Path:
    deadline = time.time() + FILE_DOWNLOAD_TIMEOUT
    while time.time() < deadline:
        for csv_file in EDGE_DOWNLOAD_DIR.glob("*.csv"):
            if csv_file.name.startswith("PTC_Cases_Report"):
                if csv_file.stat().st_mtime > before_mtime:
                    if not csv_file.name.endswith(".crdownload") and not csv_file.name.endswith(".tmp"):
                        if csv_file.stat().st_size > 1024:
                            return csv_file
        time.sleep(2)
    raise TimeoutError("The complete file footprint failed to materialize within 120 seconds.")

# ─────────────────────────────────────────────────────────────
#  MAIN DRIVER METHOD
# ─────────────────────────────────────────────────────────────

def download_latest_ptc_csv() -> dict:
    try:
        logger.info("Initializing background web testing driver wrapper...")
        driver_path = _PROJECT / "drivers" / "msedgedriver.exe"
        if not driver_path.exists():
            driver_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedgedriver.exe")
        
        edge_options = Options()
        edge_options.add_experimental_option("debuggerAddress", DEBUG_ADDRESS)
        
        driver = webdriver.Edge(service=Service(str(driver_path)), options=edge_options)
        wait = WebDriverWait(driver, ELEMENT_TIMEOUT)
        before_mtime = time.time() - 5

        logger.info("Accessing portal workspace view index...")
        driver.get(PTC_URL)
        time.sleep(6)
        _wait_for_table_render(driver, "Initial Portal Load")

        # ── 1. Update the Date range parameter selection box ──
        logger.info("Expanding timeline dropdown constraint views to 'All time' historical context...")
        _select_all_time_dropdown(driver)
        _wait_for_table_render(driver, "All Time Dropdown Adjustment")

        # ── 2. Handle 'Opened By' Group Toggles ──
        logger.info("Merging corporate organizational visibility scopes (Me + My Company)...")
        _ensure_toggle_active(driver, "My Company")
        _ensure_toggle_active(driver, "Me")
        _wait_for_table_render(driver, "Combined Scope View Profiles")

        # ── 3. Handle Status Multiselect Toggles ──
        logger.info("Activating complete lifecycle history lines (Open + Closed rows)...")
        _ensure_toggle_active(driver, "Open")
        _ensure_toggle_active(driver, "Closed")
        _wait_for_table_render(driver, "Merged Production & Archived Queues")

        # ── 4. Verify Severity Settings ──
        logger.info("Confirming global severity selection layer...")
        _ensure_toggle_active(driver, "All")
        
        # Enforce the required wait statement to compile thousands of rows safely
        logger.info("Enforcing mandatory portal compilation hold (Waiting 120s for dataset assembly)...")
        time.sleep(120)
        _wait_for_table_render(driver, "Final Consolidated Analytical Sheet", max_wait=60)

        # ── 5. Trigger Compilation ──
        logger.info("Requesting remote server generation package...")
        export_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnCaseStrackerCSVexport")))
        _js_click(driver, export_btn)
        time.sleep(4)

        # ── 6. Execute Transmission Download ──
        logger.info("Initiating secure browser document transmission download...")
        download_btn = wait.until(EC.element_to_be_clickable((By.ID, "fileExportDownloadbtnId")))
        _js_click(driver, download_btn)

        logger.info("Monitoring download landing path directory (Waiting 120s max for disk output write)...")
        downloaded_file = _scan_for_latest_csv(before_mtime)
        
        # ── 7. Save and Relocate target data cache ──
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