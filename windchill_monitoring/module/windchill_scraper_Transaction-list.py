import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options

def get_driver():
    edge_options = Options()
    edge_options.use_chromium = True
    edge_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    return webdriver.Edge(options=edge_options)

def scrape_windchill_data():
    data = {"transactions": [], "wvs_queue": [], "worker_stats": [], "success": False, "message": ""}
    try:
        driver = get_driver()
        original_handle = driver.current_window_handle
        
        # Track which tabs we successfully find in your open browser
        found_wvs = False
        found_tx = False
        found_stats = False

        # Loop through every open tab in your debug Edge window
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            page_title = driver.title.lower()
            current_url = driver.current_url.lower()
            html_source = driver.page_source
            soup = BeautifulSoup(html_source, "html.parser")

            # 1. Match the Active Job Queue tab (queueMonitorMain)
            if "queuemonitormain" in current_url or "job summary" in page_title:
                found_wvs = True
                for row in soup.find_all("tr"):
                    cols = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cols) >= 8 and (cols[0].isdigit() or any(q in cols[1].upper() for q in ["QUEUE", "OFFICE", "CATIA"])):
                        data["wvs_queue"].append({
                            "pos": cols[0], "queue": cols[1], "job": cols[2], "status": cols[3],
                            "number": cols[4], "name": cols[5], "context": cols[6], "user": cols[7]
                        })

            # 2. Match the Job Statistics tab (edrpubstatisticsmain)
            if "edrpubstatisticsmain" in current_url or "job statistics" in page_title:
                found_stats = True
                for row in soup.find_all("tr"):
                    cols = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cols) >= 5 and any(x in cols[0].lower() for x in ["segotn", "segotw", "worker", "proe", "catia", "v5"]):
                        data["worker_stats"].append({
                            "name": cols[0], "total": cols[1], "failed": cols[2], "success": cols[3], "failed_pct": cols[4]
                        })

            # 3. Match the Transactions List tab (TransactionTreeBuilder)
            if "transactiontreebuilder" in current_url or "transaction" in page_title:
                found_tx = True
                for row in soup.find_all("tr"):
                    cols = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cols) >= 7 and (cols[0].startswith("1781") or "SUCCESS" in cols[6].upper()):
                        data["transactions"].append({
                            "id": cols[0], "time": cols[1], "target": cols[4], "action": cols[5], "status": cols[6]
                        })

        # Return to the handle Selenium started with
        driver.switch_to.window(original_handle)

        # Handle helpful messaging if tabs weren't open/visible
        missing_tabs = []
        if not found_wvs: missing_tabs.append("Job Summary (WVS)")
        if not found_tx: missing_tabs.append("Transaction List")
        
        if missing_tabs and not data["wvs_queue"] and not data["transactions"]:
            data["success"] = False
            data["message"] = f"Please ensure these Windchill tabs are open in your debug Edge browser: {', '.join(missing_tabs)}"
            return data

        data["success"] = True
    except Exception as e:
        data["success"] = False
        data["message"] = str(e)
        
    return data