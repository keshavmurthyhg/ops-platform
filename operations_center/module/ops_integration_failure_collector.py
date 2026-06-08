import pythoncom
import win32com.client
import re

from operations_center.module.ops_server_mapping import (
    SERVER_MAP
)


# Environment extraction
def extract_environment(subject):

    subject = subject.upper()

    if "[PROD]" in subject:
        return "PROD"

    if "[TEST]" in subject:
        return "TEST"

    if "[TESTB]" in subject:
        return "TESTB"

    if "[QA]" in subject:
        return "QA"

    if "[DEVA]" in subject:
        return "DEVA"

    if "[DEVB]" in subject:
        return "DEVB"

    return ""


# Server extraction
def extract_server(body):

    match = re.search(
        r"Windchill Server:\s*(.+)",
        body,
        re.IGNORECASE
    )

    if not match:
        return ""

    return match.group(1).strip()

# Environment from Server
def get_environment_from_server(server):

    return SERVER_MAP.get(
        server.lower(),
        "UNKNOWN"
    )

def shorten_server(server):

    return (
        server
        .replace(
            ".got.volvo.net",
            ""
        )
        .strip()
    )

# Object Number extraction
def extract_object_number(body):

    patterns = [

        r"Object Number:\s*(.+)",

        r"Part Number:\s*(.+)",

        r"QSS Object Number:\s*(.+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            body,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

    return ""

# Error extraction
def extract_error_message(body):

    match = re.search(
        r"Error Message:\s*(.+?)(?:Windchill Server:|$)",
        body,
        re.IGNORECASE | re.DOTALL
    )

    if match:

        return (
            match.group(1)
            .replace("\n", " ")
            .strip()
        )

    return ""


def extract_integration_type(subject):

    subject = str(subject)

    match = re.search(
        r"for\s+([A-Z0-9_-]+)",
        subject,
        re.IGNORECASE
    )

    if match:
        return match.group(1).upper()

    return ""

def get_integration_failures(limit=500):

    pythoncom.CoInitialize()

    outlook = (
        win32com.client.Dispatch(
            "Outlook.Application"
        )
        .GetNamespace("MAPI")
    )

    mailbox = outlook.Folders[
        "keshavamurthy.hg@consultant.volvo.com"
    ]

    inbox = mailbox.Folders["Inbox"]

    failure_folder = inbox.Folders[
        "Integration Failure"
    ]

    messages = failure_folder.Items

    messages.Sort(
        "[ReceivedTime]",
        True
    )

    rows = []

    count = 0

    for msg in messages:

        try:

            body = str(msg.Body)

            server = extract_server(body)

            environment = extract_environment(
                msg.Subject
            )

            if not environment:

                environment = (
                    get_environment_from_server(
                        server.lower()
                    )
                )

            rows.append({

                "Failure Time":
                    msg.ReceivedTime.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                "Integration":
                    extract_integration_type(
                        msg.Subject
                    ),
                
                "Subject":
                    str(msg.Subject),

                "Object Number":
                    extract_object_number(body),

                "Error Message":
                    extract_error_message(body),

                "Environment":
                    environment,
                    
                "Windchill Server":
                    shorten_server(server),
            })

            count += 1

            if count >= limit:
                break

        except Exception:
            continue

    return rows