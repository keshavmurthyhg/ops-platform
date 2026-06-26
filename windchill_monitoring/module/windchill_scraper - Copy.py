import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def scrape_windchill_data():
    data = {"transactions": [], "wvs_queue": [], "worker_stats": []}
    
    os.makedirs("data", exist_ok=True)
    wvs_path = "data/wvs_queue.txt"
    stats_path = "data/worker_stats.txt"

    if not os.path.exists(wvs_path):
        with open(wvs_path, "w", encoding="utf-8") as f: f.write("\n")
    if not os.path.exists(stats_path):
        with open(stats_path, "w", encoding="utf-8") as f: f.write("\n")

    # -------------------------------------------------------------
    # 1. LIVE TRANSACTION SYNC
    # -------------------------------------------------------------
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        
        edge_options = Options()
        edge_options.use_chromium = True
        edge_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Edge(options=edge_options)
        original_handle = driver.current_window_handle
        
        seven_days_ago = datetime.now() - timedelta(days=7)

        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                if "transaction" in driver.current_url.lower() or "transaction" in driver.title.lower():
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    for row in soup.find_all("tr"):
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        
                        if len(cols) >= 7:
                            try:
                                tx_time_str = cols[1].split(" ")[0]
                                tx_date = datetime.strptime(tx_time_str, "%Y-%m-%d")
                            except:
                                tx_date = datetime.now()

                            if tx_date >= seven_days_ago:
                                if not any(t["target"] == cols[4] and t["time"] == cols[1] for t in data["transactions"]):
                                    data["transactions"].append({
                                        "time": cols[1],
                                        "target": cols[4], 
                                        "status": cols[6]  
                                    })
            except Exception:
                continue
        driver.switch_to.window(original_handle)
    except Exception as err:
        print(f"[Warning] Selenium loop transaction step bypassed: {err}")

    # -------------------------------------------------------------
    # 2. FILE SCANNER: WVS TEXT REGEX INTERCEPTOR (Fixed Typo)
    # -------------------------------------------------------------
    try:
        with open(wvs_path, "r", encoding="utf-8") as f:
            wvs_content = f.read()
        
        lines = wvs_content.splitlines()
        for i, line in enumerate(lines):
            cleaned = line.strip()
            if "QUEUE" in cleaned.upper() and any(x in cleaned.upper() for x in ["CREO", "OFFICE", "CATIA"]):
                job_id = "Unknown"
                # Scan nearby vertical lines for clean numeric comma job boundaries
                for offset in range(-2, 3):
                    if 0 <= i + offset < len(lines):
                        nxt = lines[i + offset].strip()
                        # Fixed Pattern matching layout
                        if re.match(r'^\d{3},\d{3},\d{3}$|^\d{8,10}$', nxt):
                            job_id = nxt
                            break
                
                if not any(j["job"] == job_id and j["queue"] == cleaned for j in data["wvs_queue"]):
                    data["wvs_queue"].append({
                        "queue": cleaned,
                        "job": job_id,
                        "status": "READY"
                    })
    except Exception as e:
        print(f"Error compiling wvs_queue text block rows: {e}")

    # -------------------------------------------------------------
    # 3. FILE SCANNER: WORKER STATISTICS SNAPSHOT PARSER
    # -------------------------------------------------------------
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
                    if not any(s["name"] == cleaned for s in data["worker_stats"]):
                        data["worker_stats"].append({
                            "name": cleaned,
                            "total": metrics[0],
                            "failed": metrics[1],
                            "success": metrics[2],
                            "failed_pct": metrics[3]
                        })
    except Exception as e:
        print(f"Error compiling worker snapshot data metrics: {e}")

    try:
        from windchill_monitoring.module.data_logger import append_to_historical_log
        for key in ["transactions", "wvs_queue", "worker_stats"]:
            if data[key]: append_to_historical_log(key, data[key])
    except Exception as log_err:
        print(f"Archival database logger execution exception: {log_err}")

    return data