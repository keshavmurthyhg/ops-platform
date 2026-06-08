import re


def summarize_notes(text):
    if not text:
        return ""

    lines = []

    for line in str(text).split("\n"):
        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        if "attachment:" in lower:
            continue

        if "has been attached" in lower:
            continue

        if re.match(r"^\d{4}-\d{2}-\d{2}", line):
            continue

        if line not in lines:
            lines.append(line)

    return "\n".join(lines[:5])


def generate_rca(data):
    """
    Kept for backward compatibility.
    Main logic now handled in rca_service.py
    """

    problem = data.get("short_description", "")
    analysis = summarize_notes(
        str(data.get("work_notes", "")) +
        "\n" +
        str(data.get("comments", ""))
    )

    resolution_raw = data.get("resolution", "")

    if str(resolution_raw).lower() in ["nan", "nat", "none"]:
        resolution_raw = ""

    resolution = summarize_notes(resolution_raw)

    return {
        "problem": problem,
        "analysis": analysis,
        "resolution": resolution
    }
