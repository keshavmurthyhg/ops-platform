import time
import streamlit as st

from modules.word_compare.sidebar import render_sidebar
from modules.word_compare.preview import (
    extract_doc_content,
    generate_aligned_diff_rows,
    render_synced_preview
)
from modules.word_compare.generator import generate_output_file


def render():
    # -----------------------------------
    # Header
    # -----------------------------------
    title_col1, title_col2 = st.columns([0.8, 9.2])

    with title_col1:
        st.image(
            "https://cdn-icons-png.flaticon.com/512/281/281760.png",
            width=55
        )

    with title_col2:
        st.markdown(
            """
            <div style="
                font-size:42px;
                font-weight:700;
                color:#2f3342;
                margin-top:4px;
                white-space:nowrap;
                line-height:1;
            ">
                Word Compare Utility
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div style="
            margin-top:-5px;
            margin-bottom:10px;
            font-size:16px;
        ">
            Compare old and new word documents.
        </div>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------------
    # Sidebar
    # -----------------------------------
    controls = render_sidebar()

    old_file = controls["old_file"]
    new_file = controls["new_file"]
    generate_clicked = controls["generate_clicked"]

    if not old_file or not new_file:
        return

    try:
        # -----------------------------------
        # Extract preview content
        # -----------------------------------
        old_file.seek(0)
        old_lines = extract_doc_content(old_file)

        new_file.seek(0)
        new_lines = extract_doc_content(new_file)

        old_html, new_html = generate_aligned_diff_rows(
            old_lines,
            new_lines
        )

        # -----------------------------------
        # Message container
        # -----------------------------------
        message_placeholder = st.empty()
        current_time = time.time()

        # Upload success message
        if (
            old_file and new_file
            and not st.session_state.get("generation_success")
        ):
            if "upload_message_time" not in st.session_state:
                st.session_state["upload_message_time"] = current_time

            upload_elapsed = (
                current_time -
                st.session_state["upload_message_time"]
            )

            if upload_elapsed <= 3:
                message_placeholder.success(
                    "Files loaded successfully."
                )
            else:
                st.session_state.pop(
                    "upload_message_time",
                    None
                )

        # Final generation success message
        if st.session_state.get(
            "generation_success"
        ):
            generation_time = st.session_state.get(
                "generation_success_time",
                current_time
            )

            generation_elapsed = (
                current_time - generation_time
            )

            if generation_elapsed <= 4:
                message_placeholder.success(
                    "Highlighted document generated successfully. File is ready for download."
                )
            else:
                st.session_state.pop(
                    "generation_success",
                    None
                )
                st.session_state.pop(
                    "generation_success_time",
                    None
                )

        # -----------------------------------
        # Generate output file
        # -----------------------------------
        if generate_clicked:
            try:
                old_file.seek(0)
                new_file.seek(0)

                progress_bar = st.progress(0)
                status_box = st.empty()

                def update_progress(
                    percent,
                    message
                ):
                    progress_bar.progress(percent)

                    status_box.info(
                        f"{message} ({percent}%)"
                    )

                output_data = generate_output_file(
                    old_file,
                    new_file,
                    progress_callback=update_progress
                )

                st.session_state[
                    "word_compare_output"
                ] = output_data

                # Remove upload message
                st.session_state.pop(
                    "upload_message_time",
                    None
                )

                progress_bar.progress(100)

                # Remove progress message
                status_box.empty()

                # Final success message
                st.session_state[
                    "generation_success"
                ] = True

                st.session_state[
                    "generation_success_time"
                ] = time.time()

                time.sleep(0.5)
                st.rerun()

            except Exception as e:
                st.error(
                    f"Generation Error: {str(e)}"
                )

        # -----------------------------------
        # Preview section
        # -----------------------------------
        st.markdown(
            """
            <h3 style='margin-bottom:5px;'>
                Difference Preview
            </h3>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"""
                <div style="
                    font-size:18px;
                    font-weight:600;
                    margin-bottom:4px;
                ">
                    {old_file.name}
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div style="
                    font-size:18px;
                    font-weight:600;
                    margin-bottom:4px;
                ">
                    {new_file.name}
                </div>
                """,
                unsafe_allow_html=True
            )

        render_synced_preview(
            old_html,
            new_html
        )

    except Exception as e:
        st.error(
            f"Preview Error: {str(e)}"
        )
