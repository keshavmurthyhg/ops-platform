"""
windchill_scraper.py — reads history CSVs, returns combined data dict.
No browser interaction. Live scraping done by dedicated scrapers.

v2 fixes:
  - Transaction filter: load ALL rows from CSV (not filtered by ID format)
    The CSV already contains only valid transactions written by the filter scraper.
    The old is_valid_transaction_id() was rejecting rows like 'wt.part.WTPart'.
  - None sanitization: _clean_row() on every row before returning.
  - Falls back to old worker/queue scrapers if history CSV empty.
"""
import os
import csv

from windchill_monitoring.module.worker_scraper import parse_worker_stats
from windchill_monitoring.module.queue_scraper  import parse_wvs_queue


def _clean(val):
    """Replace None with empty string — prevents JSON serialization errors."""
    return "" if val is None else str(val)


def _clean_row(row):
    return {k: _clean(v) for k, v in (row or {}).items()}


def _load_worker_stats_from_history():
    """Read latest snapshot from worker_stats_history.csv. Returns None if unavailable."""
    path = "data/history/worker_stats_history.csv"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    try:
        rows_by_name = {}
        with open(path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                name = _clean(r.get("name", "")).strip()
                if name:
                    rows_by_name[name] = _clean_row(dict(r))
        result = list(rows_by_name.values())
        if result:
            print(f"[Scraper] Loaded {len(result)} workers from worker_stats_history.csv")
            return result
        return None
    except Exception as e:
        print(f"[Scraper] worker_stats_history.csv error: {e}")
        return None


def _load_wvs_queue_from_history():
    """
    Read the LATEST snapshot from wvs_queue_history.csv.
    Handles both field name variants:
      - New format: captured_at, position
      - Actual CSV: capture_timestamp, pos
    Returns None if no data available.
    """
    from datetime import datetime as _dt
    path = "data/history/wvs_queue_history.csv"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    try:
        # Read header first to detect field names
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

        # Support both naming conventions
        ts_field  = "captured_at"   if "captured_at"   in fieldnames else "capture_timestamp"
        pos_field = "position"      if "position"       in fieldnames else "pos"

        best_ts  = None
        best_str = ""

        with open(path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ts_raw = (r.get(ts_field, "") or "").strip()
                if not ts_raw:
                    continue
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                            "%d-%m-%y %H:%M", "%d-%m-%Y %H:%M", "%Y-%m-%d"):
                    try:
                        ts_dt = _dt.strptime(ts_raw, fmt)
                        break
                    except ValueError:
                        ts_dt = None
                if ts_dt is None:
                    continue
                if best_ts is None or ts_dt > best_ts:
                    best_ts  = ts_dt
                    best_str = ts_raw

        if not best_str:
            return None

        result = []
        with open(path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get(ts_field, "") or "").strip() == best_str:
                    result.append(_clean_row({
                        "position": r.get(pos_field,  r.get("position", "")),
                        "queue":    r.get("queue",    ""),
                        "job":      r.get("job",      ""),
                        "status":   r.get("status",   ""),
                        "number":   r.get("number",   ""),
                        "name":     r.get("name",     ""),
                        "version":  r.get("version",  ""),
                        "context":  r.get("context",  ""),
                        "user":     r.get("user",     ""),
                        "captured_at": best_str,
                    }))
        print(f"[Scraper] Loaded {len(result)} WVS jobs from history (snapshot: {best_str})")
        return result

    except Exception as e:
        print(f"[Scraper] wvs_queue_history.csv error: {e}")

    # Fallback: parse wvs_queue.txt directly
    try:
        from windchill_monitoring.module.queue_scraper import parse_wvs_queue
        rows = parse_wvs_queue(save_history=False)
        if rows:
            print(f"[Scraper] Loaded {len(rows)} WVS jobs from wvs_queue.txt (fallback)")
            return [_clean_row(r) for r in rows]
    except Exception as e2:
        print(f"[Scraper] wvs_queue.txt fallback error: {e2}")

    return None


def scrape_windchill_data(status_mode="FAILED"):
    data = {"transactions": [], "wvs_queue": [], "worker_stats": []}

    # ── Worker stats ──────────────────────────────────────────────────────────
    worker_from_history = _load_worker_stats_from_history()
    if worker_from_history is not None:
        data["worker_stats"] = worker_from_history
    else:
        raw = parse_worker_stats(save_history=False)
        data["worker_stats"] = [_clean_row(r) for r in (raw or [])]

    # ── WVS queue ─────────────────────────────────────────────────────────────
    wvs_from_history = _load_wvs_queue_from_history()
    if wvs_from_history is not None:
        data["wvs_queue"] = wvs_from_history
    else:
        raw = parse_wvs_queue(save_history=False)
        data["wvs_queue"] = [_clean_row(r) for r in (raw or [])]

    # ── Transactions — load ALL rows from history CSV ─────────────────────────
    # The CSV is already pre-filtered by the transaction_filter_scraper.
    # We do NOT re-filter by tx_id format — that was rejecting valid rows
    # like 'wt.part.WTPart' and other non-numeric transaction IDs.
    history_csv = "data/history/transactions_history.csv"
    try:
        if os.path.exists(history_csv):
            seen = set()
            with open(history_csv, "r", encoding="utf-8") as f:
                reader     = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                new_schema = "attempts" in fieldnames

                for r in reader:
                    t_id = _clean(r.get("tx_id", "")).strip()
                    # Skip completely empty/header rows only
                    if not t_id or t_id in ("tx_id", "Transaction Id", ""):
                        continue
                    # Deduplicate by tx_id
                    if t_id in seen:
                        continue
                    seen.add(t_id)

                    # Apply status_mode filter if requested
                    status = _clean(r.get("status", "")).upper()
                    if status_mode and status_mode.upper() != "ALL":
                        if status_mode.upper() not in status:
                            continue

                    data["transactions"].append(_clean_row({
                        "tx_id":    t_id,
                        "time":     r.get("time",     "N/A"),
                        "target":   r.get("target",   "N/A"),
                        "action":   r.get("action",   "N/A"),
                        "status":   r.get("status",   "N/A"),
                        "object":   r.get("object",   "N/A"),
                        "state":    r.get("state",    "N/A"),
                        "attempts": r.get("attempts", "N/A") if new_schema else "N/A",
                        "notes":    r.get("notes",    "N/A") if new_schema else "N/A",
                    }))
            print(f"[Scraper] Loaded {len(data['transactions'])} transactions from history CSV.")
    except Exception as e:
        print(f"[Scraper] Transaction history error: {e}")

    return data
