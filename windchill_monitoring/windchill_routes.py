import os
from flask import Blueprint, render_template, jsonify, request
from windchill_monitoring.module.windchill_scraper import scrape_windchill_data
from windchill_monitoring.module.transaction_filter_scraper import run_transaction_filter_automation
from windchill_monitoring.module.wvs_queue_scraper import scrape_wvs_queue_live
from windchill_monitoring.module.wvs_stats_scraper import (
    open_stats_popup, wait_for_data_after_manual_click,
    parse_stats_from_frame, save_worker_history,
    _build_driver, _get_wvs_handle, _close_stale_stats,
    WORKER_HISTORY_CSV, WVS_MONITOR_URL
)

# ── Platform logger ───────────────────────────────────────────────────────────
try:
    from common.logger import setup_logger
    log = setup_logger("windchill_monitoring")
except Exception:
    import logging
    log = logging.getLogger("windchill_monitoring")

_HERE = os.path.dirname(os.path.abspath(__file__))

windchill_monitoring_bp = Blueprint(
    "windchill_monitoring", __name__,
    template_folder=os.path.join(_HERE, "templates"),
    static_folder=os.path.join(_HERE, "statics"),
    static_url_path="/windchill_monitoring/static"
)


def _clean(val):
    return "" if val is None else str(val)


def _clean_row(row):
    return {k: _clean(v) for k, v in (row or {}).items()}


def _clean_list(lst):
    return [_clean_row(r) for r in (lst or [])]


@windchill_monitoring_bp.route("/windchill-monitoring")
def monitoring_dashboard():
    log.info("Windchill monitoring dashboard page loaded.")
    return render_template("windchill_monitoring.html")


# ── Refresh from CSV ──────────────────────────────────────────────────────────
@windchill_monitoring_bp.route("/api/windchill-monitoring/refresh")
def windchill_monitoring_refresh_api():
    try:
        status_mode = request.args.get("status_mode", "FAILED")
        log.info(f"Refresh API called — status_mode={status_mode}")
        payload = scrape_windchill_data(status_mode=status_mode)
        tx  = len(payload.get("transactions", []))
        wvs = len(payload.get("wvs_queue", []))
        wk  = len(payload.get("worker_stats", []))
        log.info(f"Refresh complete — {tx} transactions, {wvs} WVS jobs, {wk} workers")
        return jsonify({
            "success": True,
            "data": {
                "transactions":    _clean_list(payload.get("transactions", [])),
                "wvs_queue":       _clean_list(payload.get("wvs_queue",    [])),
                "worker_stats":    _clean_list(payload.get("worker_stats", [])),
                "wvs_snapshot_ts": payload.get("wvs_snapshot_ts", ""),
            }
        })
    except Exception as e:
        log.error(f"Refresh API error: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


# ── Run full automation ───────────────────────────────────────────────────────
@windchill_monitoring_bp.route("/api/windchill-monitoring/run-automation", methods=["POST"])
def run_automation_api():
    log.info("Full automation triggered.")
    result = {
        "success": True, "transactions": [], "wvs_queue": [],
        "worker_stats": [], "errors": [], "new_count": 0,
        "tx_grid_count": 0, "wvs_grid_counts": {}, "message": ""
    }

    # Step 1: Transactions
    try:
        tx = run_transaction_filter_automation()
        if tx.get("success"):
            result["transactions"]  = _clean_list(tx.get("transactions", []))
            result["new_count"]     = tx.get("new_count", 0)
            result["tx_grid_count"] = tx.get("grid_count", 0)
        else:
            result["errors"].append(f"Transactions: {tx.get('message', 'unknown')}")
    except Exception as e:
        result["errors"].append(f"Transaction scraper failed: {e}")

    # Step 2: WVS Queue
    # IMPORTANT: extract _grid_counts BEFORE cleaning so WVS rows are not corrupted
    try:
        raw_wvs = scrape_wvs_queue_live(save_history=True)
        # Extract grid counts from sentinel on first row (if present)
        grid_counts = {}
        clean_wvs = []
        for i, row in enumerate(raw_wvs or []):
            if i == 0 and "_grid_counts" in row:
                grid_counts = row.pop("_grid_counts", {})
            clean_wvs.append(_clean_row(row))
        result["wvs_queue"]       = clean_wvs
        result["wvs_grid_counts"] = grid_counts
    except Exception as e:
        result["errors"].append(f"WVS queue scraper failed: {e}")

    # Step 3: Worker stats from CSV
    try:
        snap = scrape_windchill_data(status_mode="FAILED")
        result["worker_stats"] = _clean_list(snap.get("worker_stats", []))
    except Exception as e:
        result["errors"].append(f"Worker CSV load failed: {e}")

    parts = []
    if result["transactions"]: parts.append(f"{result['tx_grid_count'] or len(result['transactions'])} failures")
    if result["wvs_queue"]:    parts.append(f"{len(result['wvs_queue'])} WVS jobs")
    result["message"] = "Updated: " + ", ".join(parts) if parts else "No new data found."
    if result["errors"]:
        result["message"] += " | Errors: " + "; ".join(result["errors"])
        result["success"] = len(result["errors"]) < 3
    return jsonify(result)


# ── Filter transactions only ──────────────────────────────────────────────────
@windchill_monitoring_bp.route("/api/windchill-monitoring/filter-transactions", methods=["POST"])
def windchill_filter_transactions_api():
    try:
        result = run_transaction_filter_automation()
        if "transactions" in result:
            result["transactions"] = _clean_list(result["transactions"])
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "transactions": [], "new_count": 0}), 500


# ── Open Job Statistics popup ─────────────────────────────────────────────────
@windchill_monitoring_bp.route("/api/windchill-monitoring/open-stats-popup", methods=["POST"])
def open_stats_popup_api():
    try:
        driver = _build_driver()
        monitor_handle = _get_wvs_handle(driver)
        if not monitor_handle:
            driver.switch_to.window(driver.window_handles[0])
            driver.get(WVS_MONITOR_URL)
            import time; time.sleep(4)
            monitor_handle = driver.current_window_handle
        _close_stale_stats(driver, monitor_handle)
        stats_handle = open_stats_popup(driver, monitor_handle)
        if stats_handle:
            return jsonify({"success": True, "message": "Job Statistics popup opened in Edge."})
        return jsonify({"success": False, "message": "Could not open stats popup. Is Edge running on port 9222?"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Collect stats (long-poll) ─────────────────────────────────────────────────
@windchill_monitoring_bp.route("/api/windchill-monitoring/collect-stats", methods=["POST"])
def collect_stats_api():
    try:
        driver = _build_driver()
        stats_handle = None
        for h in driver.window_handles:
            try:
                driver.switch_to.window(h)
                if "edrpubstat" in driver.current_url or "Job Statistics" in driver.title:
                    stats_handle = h; break
            except Exception: continue

        if not stats_handle:
            return jsonify({"success": False,
                            "message": "Job Statistics popup not found. Open it in Edge manually (Actions → Job Statistics), then click Collect Stats."})

        wait_for_data_after_manual_click(driver, stats_handle, timeout=60)  # 60s timeout
        summary, workers = parse_stats_from_frame(driver, stats_handle)

        if workers:
            save_worker_history(workers)
            return jsonify({
                "success": True,
                "worker_stats": _clean_list(workers),
                "summary_stats": _clean_list(summary),
                "message": f"Collected {len(workers)} worker stat rows."
            })
        return jsonify({"success": False,
                        "message": "No worker data found. Did you click 'Display Summary Statistics' and wait ~2 min?"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Launch Edge ───────────────────────────────────────────────────────────────
@windchill_monitoring_bp.route("/api/windchill-monitoring/launch-edge", methods=["POST"])
def windchill_launch_edge_api():
    import subprocess
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    url = (
        "https://vcewindchill.got.volvo.net/Windchill/app/#ptc1/comp/"
        "ext.vce.integration.core.transaction.ui.TransactionTreeBuilder"
        "?oid=OR%3Awt.org.WTUser%3A9643933264&u8=1"
    )
    try:
        edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)
        if not edge_exe:
            return jsonify({"success": False, "message": "Edge not found."}), 404
        subprocess.Popen([edge_exe, "--remote-debugging-port=9222", "--new-window", url])
        return jsonify({"success": True, "message": "Edge launched in debug mode on port 9222."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
