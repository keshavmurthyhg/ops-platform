from io import BytesIO
import zipfile
from datetime import datetime

from common.utils.links import extract_azure_id
from report.module.doc_generator import (
    generate_pdf,
    generate_word_doc_wrapper
)
from report.module.services.rca_service import build_rca


# -----------------------------------
# SAFE TEXT
# -----------------------------------
def safe_text(val):
    if val is None:
        return ""

    if isinstance(val, list):
        val = "\n".join([str(v) for v in val])

    val = str(val).strip()

    if val.lower() in ["nan", "none", "nat"]:
        return ""

    MAX_LEN = 800
    lines = []

    for raw in val.split("\n"):
        raw = raw.strip()

        if not raw:
            continue

        if len(raw) > MAX_LEN:
            chunks = [
                raw[i:i + MAX_LEN]
                for i in range(0, len(raw), MAX_LEN)
            ]
            lines.extend(chunks)
        else:
            lines.append(raw)

    return "\n".join(lines)


# -----------------------------------
# BUILD BULK REPORTS
# -----------------------------------
def build_bulk_reports(
    df,
    incident_list,
    images_map=None
):
    results = []

    for inc in incident_list:
        try:
            row = df[df["number"] == inc]

            if row.empty:
                print(f"Incident not found: {inc}")
                continue

            r = row.iloc[0]

            # -----------------------------------
            # FIX:
            # Azure bug should ONLY be extracted
            # from resolution notes
            # -----------------------------------
            resolution_notes = str(
                r.get("resolution notes", "")
            )

            azure_bug = extract_azure_id(
                resolution_notes
            )

            # FULL incident payload required by PDF/Word
            data = {
                "number": r.get("number"),

                "short_description": r.get("short description"),
                "description": r.get("description"),

                "priority": r.get("priority"),

                "created_by": r.get("opened by"),
                "created_date": r.get("created"),

                "assigned_to": r.get("assigned to"),
                "resolved_date": r.get("resolved"),

                # Fixed Azure extraction
                "azure_bug": azure_bug,

                "ptc_case": r.get("vendor ticket"),

                # RCA fields
                "work notes": r.get("work notes", ""),
                "additional comments": r.get("additional comments", ""),
                "resolution notes": r.get("resolution notes", ""),

                # aliases
                "work_notes": r.get("work notes", ""),
                "additional_comments": r.get("additional comments", ""),
                "resolution_notes": r.get("resolution notes", "")
            }

            # Build RCA
            rca = build_rca(data)

            images = (
                images_map.get(inc, {})
                if images_map
                else {}
            )

            results.append({
                "data": data,
                "root": safe_text(
                    rca.get("problem_statement", "")
                ),
                "l2": safe_text(
                    rca.get("root_cause", "")
                ),
                "res": safe_text(
                    rca.get("resolution", "")
                ),
                "images": images
            })

        except Exception as e:
            print(f"Error building report for {inc}: {e}")
            continue

    return results


# -----------------------------------
# GENERATE BULK ZIP
# -----------------------------------
def generate_bulk_zip(
    reports,
    output_type="both"
):
    zip_buffer = BytesIO()

    current_date = datetime.now().strftime("%d%b%Y")

    with zipfile.ZipFile(
        zip_buffer,
        "w",
        zipfile.ZIP_DEFLATED
    ) as z:

        for report in reports:
            try:
                data = report["data"]
                number = data.get(
                    "number",
                    "unknown_incident"
                )

                # Generate PDF
                pdf_bytes = generate_pdf(
                    data=data,
                    root=report["root"],
                    l2=report["l2"],
                    res=report["res"],
                    images=report["images"]
                )

                # Generate Word
                word_bytes = generate_word_doc_wrapper(
                    data=data,
                    root=report["root"],
                    l2=report["l2"],
                    res=report["res"],
                    images=report["images"]
                )

                # -----------------------------------
                # INCIDENT FOLDER
                # -----------------------------------
                incident_folder = f"{number}/"

                # File names
                pdf_filename = (
                    f"{incident_folder}"
                    f"{number}_{current_date}.pdf"
                )

                word_filename = (
                    f"{incident_folder}"
                    f"{number}_{current_date}.docx"
                )

                # -----------------------------------
                # WRITE SELECTED OUTPUTS
                # -----------------------------------

                if output_type in ["pdf", "both"]:
                    z.writestr(
                        pdf_filename,
                        pdf_bytes
                    )

                if output_type in ["word", "both"]:
                    z.writestr(
                        word_filename,
                        word_bytes
                    )

                print(
                    f"Generated bulk report for {number}"
                )

            except Exception as e:
                print(f"Failed bulk report: {e}")
                continue

    zip_buffer.seek(0)
    return zip_buffer
