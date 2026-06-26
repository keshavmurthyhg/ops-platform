import os
import csv
from datetime import datetime

WORKER_HISTORY_CSV = os.path.join("data", "history", "worker_stats_history.csv")
WORKER_FIELDNAMES = ["name", "total", "failed", "success", "failed_pct", "captured_at"]


def parse_worker_stats(save_history=True):
    """Reads and parses worker_stats.txt, optionally saves to history CSV."""
    stats_list = []
    stats_path = "data/worker_stats.txt"

    if not os.path.exists(stats_path):
        return stats_list

    try:
        with open(stats_path, "r", encoding="utf-8") as f:
            stats_content = f.read()

        lines = stats_content.splitlines()
        for i, line in enumerate(lines):
            cleaned = line.strip()
            if "segot" in cleaned.lower():
                metrics = []
                for offset in range(1, 7):
                    if i + offset < len(lines):
                        val = lines[i + offset].strip()
                        if val and (val.isdigit() or "%" in val or "." in val):
                            metrics.append(val)

                if len(metrics) >= 4:
                    if not any(s["name"] == cleaned for s in stats_list):
                        stats_list.append({
                            "name":       cleaned,
                            "total":      metrics[0],
                            "failed":     metrics[1],
                            "success":    metrics[2],
                            "failed_pct": metrics[3],
                        })

    except Exception as e:
        print(f"[WorkerScraper] Parse error: {e}")

    if save_history and stats_list:
        _save_worker_history(stats_list)

    return stats_list


def _save_worker_history(stats_list):
    """Append worker stats snapshot to history CSV."""
    try:
        os.makedirs(os.path.dirname(WORKER_HISTORY_CSV), exist_ok=True)
        write_header = not os.path.exists(WORKER_HISTORY_CSV) or os.path.getsize(WORKER_HISTORY_CSV) == 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(WORKER_HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=WORKER_FIELDNAMES)
            if write_header:
                writer.writeheader()
            for row in stats_list:
                writer.writerow({k: {**row, "captured_at": ts}.get(k, "") for k in WORKER_FIELDNAMES})
        print(f"[WorkerScraper] Saved {len(stats_list)} rows to worker_stats_history.csv")
    except Exception as e:
        print(f"[WorkerScraper] History save error: {e}")
