import pythoncom
import win32com.client


def get_support_emails(limit=500):
    """
    Read emails directly from:
    Support vce.windchill.2nd -> Inbox
    """

    pythoncom.CoInitialize()

    outlook = win32com.client.Dispatch(
        "Outlook.Application"
    ).GetNamespace("MAPI")

    mailbox = outlook.Folders[
        "Support vce.windchill.2nd"
    ]

    inbox = mailbox.Folders["Inbox"]

    messages = inbox.Items

    messages.Sort(
        "[ReceivedTime]",
        True
    )

    rows = []

    count = 0

    for msg in messages:

        try:

            importance = {
                0: "Low",
                1: "Normal",
                2: "High"
            }.get(
                msg.Importance,
                "Normal"
            )

            rows.append({
                "date_received":
                    msg.ReceivedTime.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                "name":
                    str(msg.SenderName),

                "subject":
                    str(msg.Subject),

                "importance":
                    importance,

                "category":
                    str(msg.Categories or "")
            })

            count += 1

            if count >= limit:
                break

        except Exception:
            continue

    return rows