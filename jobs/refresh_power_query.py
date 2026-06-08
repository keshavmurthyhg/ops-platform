import time
import pythoncom
import win32com.client as win32
from pathlib import Path

DATA_FILE = Path(
    r"C:\Users\a447927\Desktop\my-apps\data\Operations_Center.xlsx"
)

def refresh_power_query():

    pythoncom.CoInitialize()

    excel = None
    wb = None

    try:

        print("=" * 50)
        print("STARTING POWER QUERY REFRESH")
        print("=" * 50)

        excel = win32.DispatchEx("Excel.Application")

        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AskToUpdateLinks = False

        wb = excel.Workbooks.Open(str(DATA_FILE))

        print("Workbook opened")

        wb.RefreshAll()

        print("Refresh started")

        timeout = 1800
        waited = 0

        while waited < timeout:

            refreshing = False

            for conn in wb.Connections:

                try:
                    if conn.OLEDBConnection.Refreshing:
                        refreshing = True
                except:
                    pass

                try:
                    if conn.ODBCConnection.Refreshing:
                        refreshing = True
                except:
                    pass

            if not refreshing:
                break

            print(f"Waiting... {waited}s")

            time.sleep(5)
            waited += 5

        print("Saving workbook...")

        wb.Save()

        print("Workbook saved")

    except Exception as e:

        print(f"REFRESH FAILED: {e}")

    finally:

        try:
            wb.Close(True)
        except:
            pass

        try:
            excel.Quit()
        except:
            pass

        pythoncom.CoUninitialize()

        print("Refresh complete")


if __name__ == "__main__":
    refresh_power_query()