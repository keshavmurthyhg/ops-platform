import os
import re
import csv
from datetime import datetime

WVS_HISTORY_CSV = os.path.join("data", "history", "wvs_queue_history.csv")
WVS_FIELDNAMES = ["position", "queue", "job", "status", "number", "name",
                  "version", "context", "user", "captured_at"]


def parse_wvs_queue(save_history=True):
    """
    Parses wvs_queue.txt and optionally saves to history CSV.
    File structure (one value per line):
      position → QUEUE_NAME → job_id → status → number → name → version → context → user
    """
    queue_list = []
    wvs_path = "data/wvs_queue.txt"
    if not os.path.exists(wvs_path):
        return queue_list

    try:
        with open(wvs_path, "r", encoding="utf-8") as f:
            raw = f.read()

        lines = [l.strip() for l in raw.splitlines()]
        lines = [l for l in lines if l]
        job_id_pat = re.compile(r'^\d{3},\d{3},\d{3}$|^\d{7,12}$')

        i = 0
        while i < len(lines):
            line = lines[i]
            if job_id_pat.match(line):
                job_id     = line
                queue_name = lines[i - 1] if i > 0 else "UNKNOWN"
                pos_raw    = lines[i - 2] if i > 1 else ""
                position   = pos_raw if pos_raw.isdigit() else ""

                tokens = []
                j = i + 1
                while j < len(lines) and len(tokens) < 7:
                    t = lines[j].strip()
                    if t:
                        tokens.append(t)
                    j += 1

                status  = tokens[0] if len(tokens) > 0 else ""
                number  = tokens[1] if len(tokens) > 1 else ""
                name    = tokens[2] if len(tokens) > 2 else ""
                version = tokens[3] if len(tokens) > 3 else ""
                context = tokens[4] if len(tokens) > 4 else ""
                user    = tokens[5] if len(tokens) > 5 else ""

                if not any(q["job"] == job_id and q["queue"] == queue_name for q in queue_list):
                    queue_list.append({
                        "position": position,
                        "queue":    queue_name,
                        "job":      job_id,
                        "status":   status or "READY",
                        "number":   number,
                        "name":     name,
                        "version":  version,
                        "context":  context,
                        "user":     user,
                    })
                i = j
            else:
                i += 1

    except Exception as e:
        print(f"[QueueScraper] Parse error: {e}")

    if save_history and queue_list:
        _save_wvs_history(queue_list)

    return queue_list


def _save_wvs_history(queue_list):
    """Append WVS queue snapshot to history CSV."""
    try:
        os.makedirs(os.path.dirname(WVS_HISTORY_CSV), exist_ok=True)
        write_header = not os.path.exists(WVS_HISTORY_CSV) or os.path.getsize(WVS_HISTORY_CSV) == 0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(WVS_HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=WVS_FIELDNAMES)
            if write_header:
                writer.writeheader()
            for row in queue_list:
                writer.writerow({k: {**row, "captured_at": ts}.get(k, "") for k in WVS_FIELDNAMES})
        print(f"[QueueScraper] Saved {len(queue_list)} rows to wvs_queue_history.csv")
    except Exception as e:
        print(f"[QueueScraper] History save error: {e}")
