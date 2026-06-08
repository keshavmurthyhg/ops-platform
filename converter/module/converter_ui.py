import streamlit as st
import tempfile
import os
import re

from converter.module.converter import convert_ppt
from converter.module.ppt_metadata import extract_slide1_metadata

from common.data.snow_loader import load_snow_data
from report.module.doc_generator import generate_word_doc_wrapper

from common.utils.formatters import format_date
from common.ui.preview import render_preview


# -----------------------------
# HELPERS
# -----------------------------
def clean_incident(value):
    if not value:
        return None

    match = re.search(r"INC\d{7,}", str(value))
    return match.group(0) if match else None


def extract_azure(text):
    if not text:
        return None

    match = re.search(
        r"dev\.azure\.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/(\d+)",
        str(text),
        re.IGNORECASE
    )

    return match.group(1) if match else None


def normalize_snow_data(data):
    def get(*keys):
        for k in keys:
            if k in data:
                value = data[k]

                if value is not None and str(value).strip() not in [
                    "",
                    "nan",
                    "NaT",
                    "None"
                ]:
                    return value

        return None

    resolution_notes = get(
        "resolution notes"
    )

    work_notes = get(
        "work notes"
    )

    additional_comments = get(
        "additional comments"
    )

    return {
        "number": get("number"),

        "created_by": get(
            "opened by",
            "created by"
        ),

        "created_date": get(
            "created",
            "created date",
            "opened at"
        ),

        "assigned_to": get(
            "assigned to",
            "assigned_to"
        ),

        "priority": get("priority"),

        "resolved_date": get(
            "closed",
            "resolved date",
            "closed at",
            "vendor closed"
        ),

        "short_description": get(
            "short description"
        ),

        "description": get(
            "description"
        ),

        # --------------------------
        # RCA fields
        # --------------------------
        "work_notes": work_notes,
        "work notes": work_notes,

        "comments": additional_comments,
        "additional_comments": additional_comments,
        "additional comments": additional_comments,

        # FIX → pass all aliases
        "resolution": resolution_notes,
        "resolution_notes": resolution_notes,
        "resolution notes": resolution_notes,

        # --------------------------
        # Azure extraction
        # --------------------------
        "azure_bug": extract_azure(
            resolution_notes
        ),

        "ptc_case": get(
            "vendor ticket",
            "ptc case"
        )
    }


# -----------------------------
# MAIN UI
# -----------------------------
def render():
    st.subheader("📊 PPT Converter")

    uploaded_ppt = st.file_uploader(
        "Upload PPT",
        type=["pptx"]
    )

    if not uploaded_ppt:
        return

    with tempfile.TemporaryDirectory() as tmpdir:

        ppt_path = os.path.join(
            tmpdir,
            uploaded_ppt.name
        )

        with open(ppt_path, "wb") as f:
            f.write(uploaded_ppt.read())

        # -------------------------
        # Extract metadata
        # -------------------------
        metadata = extract_slide1_metadata(ppt_path)

        incident = clean_incident(
            metadata.get("incident")
        )

        if incident:
            st.info(f"🔍 Detected Incident: {incident}")
        else:
            st.warning(
                "Could not detect incident number from slide 1"
            )

        # -------------------------
        # Load SNOW data
        # -------------------------
        snow_data = None

        if incident:
            try:
                snow_df = load_snow_data()

                matched_row = None

                if snow_df is not None and not snow_df.empty:
                    filtered = snow_df[
                        snow_df["number"].astype(str).str.strip() == incident
                    ]

                    if not filtered.empty:
                        matched_row = filtered.iloc[0].to_dict()

                if matched_row:
                    snow_data = normalize_snow_data(
                        matched_row
                    )
                    st.success("✅ SNOW data loaded")
                else:
                    st.warning(
                        "No matching SNOW incident found. PPT conversion still works."
                    )

            except Exception as e:
                st.error(
                    f"SNOW loading failed: {str(e)}"
                )

        # -------------------------
        # Shared Preview
        # -------------------------
        if snow_data:
            render_preview(
                snow_data,
                show_rca=False
            )
        else:
            st.info(
                "Preview unavailable because SNOW data not found."
            )

        # -------------------------
        # Convert PPT ONLY
        # -------------------------
        if st.button("Convert PPT"):
            with st.spinner(
                "Converting PPT to Word..."
            ):
                try:
                    docx_path = convert_ppt(
                        ppt_path,
                        tmpdir
                    )

                    st.success(
                        "PPT converted successfully"
                    )

                    if os.path.exists(docx_path):
                        with open(docx_path, "rb") as f:
                            st.download_button(
                                "📄 Download Word",
                                f.read(),
                                file_name=os.path.basename(
                                    docx_path
                                )
                            )

                except Exception as e:
                    st.error(
                        f"PPT conversion failed: {str(e)}"
                    )

        # -------------------------
        # Combined Report
        # -------------------------
        if st.button("Generate Combined Report"):

            if not snow_data:
                st.error(
                    "SNOW data required for combined report generation."
                )
                return

            with st.spinner(
                "Generating combined report..."
            ):
                try:
                    combined_doc = generate_word_doc_wrapper(
                        data=snow_data,
                        ppt_data=ppt_path
                    )

                    st.success(
                        "Combined report generated successfully"
                    )

                    st.download_button(
                        "📥 Download Combined Report",
                        combined_doc,
                        file_name=f"{incident}_combined_report.docx"
                    )

                except Exception as e:
                    st.error(
                        f"Combined report failed: {str(e)}"
                    )
