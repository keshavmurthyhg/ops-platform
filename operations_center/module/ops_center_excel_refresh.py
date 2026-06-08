import os
import time

from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client as win32


DATA_FILE = os.path.join(
    "data",
    "operations_tracker.xlsx"
)


def refresh_power_query():

    excel = None
    workbook = None

    try:

        pythoncom.CoInitialize()

        workbook_path = os.path.abspath(
            DATA_FILE
        )

        if not os.path.exists(workbook_path):

            return {
                "success": False,
                "message": f"Workbook not found: {workbook_path}"
            }

        excel = win32.DispatchEx(
            "Excel.Application"
        )

        excel.Visible = False
        excel.DisplayAlerts = False

        workbook = excel.Workbooks.Open(
            workbook_path,
            UpdateLinks=0,
            ReadOnly=False
        )

        workbook.RefreshAll()

        # Allow Power Query refresh to finish
        time.sleep(60)

        workbook.Save()

        refresh_time = datetime.now().strftime(
            "%d-%b-%Y %H:%M:%S"
        )

        Path(
            "data/refresh_status.txt"
        ).write_text(
            refresh_time,
            encoding="utf-8"
        )

        return {
            "success": True,
            "message": "Power Query refreshed successfully",
            "refresh_time": refresh_time
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        try:

            if workbook is not None:
                workbook.Close(
                    SaveChanges=True
                )
        except Exception:
            pass

        try:

            if excel is not None:
                excel.Quit()
        except Exception:
            pass

        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass