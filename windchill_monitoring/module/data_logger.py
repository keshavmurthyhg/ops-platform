import os
import csv
from datetime import datetime

HISTORY_DIR = "data/history"
os.makedirs(HISTORY_DIR, exist_ok=True)

def append_to_historical_log(tracker_name, data_list):
    """
    Appends data snapshots to a local historical archive cleanly.
    Fails gracefully if a file lock is present to prevent breaking live UI panels.
    """
    if not data_list:
        return True
        
    file_path = os.path.join(HISTORY_DIR, f"{tracker_name}_history.csv")
    file_exists = os.path.exists(file_path)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(file_path, "a", newline="", encoding="utf-8") as csvfile:
            flattened_rows = []
            for item in data_list:
                row_copy = item.copy()
                row_copy["capture_timestamp"] = current_time
                flattened_rows.append(row_copy)
                
            headers = list(flattened_rows[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            
            if not file_exists:
                writer.writeheader()
                
            writer.writerows(flattened_rows)
        return True
    except PermissionError:
        # File is open in Excel; skip appending silently so the dashboard can still load data
        print(f"[Warning] '{tracker_name}_history.csv' is locked by Excel. Skipping historical append.")
        return True
    except Exception as e:
        print(f"[Logger Error] Failed to write history log for {tracker_name}: {e}")
        return False