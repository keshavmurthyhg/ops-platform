# =============================================================================
#  OPERATIONS CENTER — DASHBOARD SERVICE
#  operations_center/module/ops_center_service.py
#
#  Aggregates data from all loaders, computes summary KPIs, reads data-file
#  modification timestamps, and returns a single dict consumed by the routes
#  layer and injected into the Jinja2 template.
# =============================================================================

import os
from datetime import datetime
from pathlib import Path

# ── Sub-module loaders ────────────────────────────────────────────────────────
from operations_center.module.ops_center_data_loader import (
    load_support_mails,
    load_integration_failures,
)
from operations_center.module.ops_center_incident_engine import (
    detect_critical_failures,
)
from operations_center.module.ops_center_incident_loader import (
    load_incident_tracker,
)
from operations_center.module.ops_center_azure_loader import (
    load_azure_tracker,
)
from operations_center.module.ops_center_ptc_loader import (
    load_ptc_tracker,
)

# ── Platform logger ───────────────────────────────────────────────────────────
try:
    from common.logger import setup_logger
    log = setup_logger("operations_center")
except Exception:
    import logging
    log = logging.getLogger("operations_center")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — data file last-modified timestamp
# ─────────────────────────────────────────────────────────────────────────────

def _file_last_updated(rel_path: str) -> str:
    """
    Return a human-readable timestamp for when a data file was last modified.
    Example output: '19 Jun 2026, 14:32'
    Returns 'File not found' or 'Unknown' on error.
    """
    try:
        p = Path(rel_path)
        if not p.exists():
            log.warning(f"Data file not found: {rel_path}")
            return "File not found"
        dt = datetime.fromtimestamp(p.stat().st_mtime)
        # Use strftime compatible with Windows (no %-d)
        day = str(dt.day)                          # removes leading zero
        return f"{day} {dt.strftime('%b %Y, %H:%M')}"
    except Exception as exc:
        log.error(f"Could not read mtime for {rel_path}: {exc}")
        return "Unknown"


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN SERVICE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_operations_dashboard_data() -> dict:
    """
    Load all data sources, compute KPI summaries, and return a unified dict.

    Keys returned
    ─────────────
    support_data     list[dict]  – Support e-mail records
    failure_data     list[dict]  – Integration failure records
    incident_data    list[dict]  – ServiceNow incident records
    azure_data       list[dict]  – Azure DevOps bug records
    ptc_data         list[dict]  – PTC Case Tracker records
    summary          dict        – Aggregated KPI counts
    data_ages        dict        – Last-modified labels for each source file
    """
    log.info("Loading Operations Center dashboard data…")

    # ── Load each data source ─────────────────────────────────────────────────
    support_data  = load_support_mails()
    log.info(f"  Support e-mails  : {len(support_data)} rows")

    failure_data  = load_integration_failures()
    log.info(f"  Failures         : {len(failure_data)} rows")

    incident_data = load_incident_tracker()
    log.info(f"  Incidents (SNOW) : {len(incident_data)} rows")

    azure_data    = load_azure_tracker()
    log.info(f"  Azure bugs       : {len(azure_data)} rows")

    ptc_data      = load_ptc_tracker()
    log.info(f"  PTC cases        : {len(ptc_data)} rows")

    # ── Derived KPIs ──────────────────────────────────────────────────────────
    pending_actions  = len([
        r for r in support_data
        if "Action Required" in str(r.get("Categories", ""))
    ])
    critical_servers = detect_critical_failures(failure_data)

    summary = {
        "support_count"   : len(support_data),
        "failure_count"   : len(failure_data),
        "pending_actions" : pending_actions,
        "critical_servers": len(critical_servers),
        "active_incidents": len(incident_data),
        "azure_count"     : len(azure_data),
        "ptc_count"       : len(ptc_data),
    }
    log.info(f"  Summary KPIs     : {summary}")

    # ── Data-file modification timestamps ─────────────────────────────────────
    data_ages = {
        "incident": _file_last_updated("data/Snow.xlsx"),
        "azure"   : _file_last_updated("data/Azure.csv"),
        "ptc"     : _file_last_updated("data/Ptc.csv"),
    }
    log.info(f"  Data ages        : {data_ages}")

    log.info("Operations Center dashboard data loaded successfully.")
    return {
        "support_data" : support_data,
        "failure_data" : failure_data,
        "incident_data": incident_data,
        "azure_data"   : azure_data,
        "ptc_data"     : ptc_data,
        "summary"      : summary,
        "data_ages"    : data_ages,
    }
