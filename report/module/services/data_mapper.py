from common.utils.parsers import extract_azure_id
from common.utils.formatters import format_description, safe_text


def map_incident(row):
    """
    Maps raw SNOW row → normalized report format
    while preserving original RCA columns required
    by rca_service.py
    """

    work_notes = row.get("work notes") or ""
    additional_comments = row.get("additional comments") or ""
    resolution_notes = row.get("resolution notes") or ""

    # -----------------------------------
    # Azure bug should ONLY come from
    # resolution notes Azure DevOps URL
    # -----------------------------------
    azure_bug = extract_azure_id(
        str(resolution_notes)
    )

    return {
        "number": safe_text(
            row.get("number")
        ),

        # Header fields
        "azure_bug": azure_bug if azure_bug else "-",

        "ptc_case": safe_text(
            row.get("vendor ticket")
        ),

        "created_by": safe_text(
            row.get("opened by")
        ),

        "assigned_to": safe_text(
            row.get("assigned to")
        ),

        "created_date": row.get("created"),

        "resolved_date": row.get("resolved"),

        "priority": safe_text(
            row.get("priority")
        ),

        # Description fields
        "short_description": safe_text(
            row.get("short description")
        ),

        "description": format_description(
            row.get("description")
        ),

        # Preserve original notes
        "work notes": work_notes,
        "additional comments": additional_comments,
        "resolution notes": resolution_notes,

        # Optional underscore aliases
        "work_notes": work_notes,
        "additional_comments": additional_comments,
        "resolution_notes": resolution_notes
    }
