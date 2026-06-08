import re


# ---------------- SAFE VALUE ---------------- #
def safe_text(val):
    if val is None:
        return ""

    val = str(val).strip()

    if val.lower() in ["nan", "nat", "none"]:
        return ""

    return val


# ---------------- GET COLUMN SAFELY ---------------- #
def get_value(data, *possible_keys):
    """
    Supports both:
    'resolution notes'
    'resolution_notes'
    """
    for key in possible_keys:
        if key in data:
            return safe_text(data.get(key))
    return ""


# ---------------- CLEAN NOISE ---------------- #
def clean_lines(text):
    if not text:
        return []

    noise_words = [
        "hello",
        "hi team",
        "thanks",
        "thank you",
        "regards",
        "br",
        "please close",
        "closing incident",
        "call scheduled",
        "waiting for response",
        "waiting for update",
        "attached",
        "attachment:",
        "assigned to",
        "priority changed"
    ]

    cleaned = []

    for raw in text.split("\n"):
        line = raw.strip()

        if not line:
            continue

        lower = line.lower()

        # remove timestamps
        if re.match(r"^\d{4}-\d{2}-\d{2}", line):
            continue

        # remove pure names
        if len(line.split()) <= 2 and line.istitle():
            continue

        # remove noise lines
        if any(x in lower for x in noise_words):
            continue

        cleaned.append(line)

    return cleaned


# ---------------- PROBLEM STATEMENT ---------------- #
def build_problem(data):
    short_desc = get_value(
        data,
        "short description",
        "short_description"
    )

    desc = get_value(
        data,
        "description"
    )

    problem_lines = []

    if short_desc:
        problem_lines.append(short_desc)

    if desc:
        short_clean = short_desc.lower().strip()
        desc_clean = desc.lower().strip()

        if (
            desc_clean != short_clean
            and short_clean not in desc_clean
            and desc_clean not in short_clean
        ):
            problem_lines.append(desc)

    problem_lines = list(dict.fromkeys(problem_lines))

    return "\n".join(problem_lines[:2])


# ---------------- ROOT CAUSE ---------------- #
def build_root_cause(data):
    resolution_notes = get_value(
        data,
        "resolution notes",
        "resolution_notes"
    )

    work_notes = get_value(
        data,
        "work notes",
        "work_notes"
    )

    comments = get_value(
        data,
        "additional comments",
        "additional_comments"
    )

    combined = "\n".join([
        resolution_notes,
        work_notes,
        comments
    ])

    lines = clean_lines(combined)

    root_lines = []

    for line in lines:
        lower = line.lower()

        if (
            "cause:" in lower
            or "root cause" in lower
            or "incorrect path" in lower
            or "certificate" in lower
            or "validation issue" in lower
            or "failed due to" in lower
            or "exception" in lower
            or "error" in lower
            or "unable to" in lower
        ):
            root_lines.append(line)

    # fallback if no explicit cause found
    if not root_lines:
        for line in lines:
            lower = line.lower()

            if not any(x in lower for x in [
                "validated",
                "working fine",
                "working now",
                "closed",
                "resolved"
            ]):
                root_lines.append(line)
                break

    root_lines = list(dict.fromkeys(root_lines))

    return "\n".join(root_lines[:4])


# ---------------- RESOLUTION ---------------- #
def build_resolution(data):
    resolution_notes = get_value(
        data,
        "resolution notes",
        "resolution_notes"
    )

    lines = clean_lines(resolution_notes)

    resolution_lines = []

    for line in lines:
        lower = line.lower()

        if any(x in lower for x in [
            "resolution:",
            "resolved",
            "fixed",
            "implemented",
            "modified",
            "restarted",
            "validated",
            "working fine",
            "working now",
            "successful",
            "success",
            "closed"
        ]):
            resolution_lines.append(line)

    # fallback → use resolution notes directly
    if not resolution_lines and lines:
        resolution_lines = lines[:3]

    resolution_lines = list(dict.fromkeys(resolution_lines))

    return "\n".join(resolution_lines[:5])


# ---------------- MAIN ---------------- #
def build_rca(data):
    return {
        "problem_statement": build_problem(data),
        "root_cause": build_root_cause(data),
        "resolution": build_resolution(data)
    }
