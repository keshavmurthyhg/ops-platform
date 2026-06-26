import streamlit as st


def render_sidebar():
    st.sidebar.subheader("Word Compare Controls")

    # -----------------------------------
    # Initialize dynamic uploader keys
    # -----------------------------------
    if "old_uploader_key" not in st.session_state:
        st.session_state["old_uploader_key"] = "old_upload_1"

    if "new_uploader_key" not in st.session_state:
        st.session_state["new_uploader_key"] = "new_upload_1"

    # -----------------------------------
    # Upload old file
    # -----------------------------------
    old_file = st.sidebar.file_uploader(
        "Upload Old Document",
        type=["docx"],
        key=st.session_state["old_uploader_key"]
    )

    # -----------------------------------
    # Upload new file
    # -----------------------------------
    new_file = st.sidebar.file_uploader(
        "Upload New Document",
        type=["docx"],
        key=st.session_state["new_uploader_key"]
    )

    # -----------------------------------
    # Clear button
    # -----------------------------------
    clear_clicked = st.sidebar.button(
        "Clear Files",
        use_container_width=True
    )
    
    if clear_clicked:
        # Current uploader keys
        old_key = st.session_state.get(
            "old_uploader_key"
        )
        new_key = st.session_state.get(
            "new_uploader_key"
        )
    
        # Remove uploaded file objects
        if old_key and old_key in st.session_state:
            del st.session_state[old_key]
    
        if new_key and new_key in st.session_state:
            del st.session_state[new_key]
    
        # Remove generated file/output
        keys_to_remove = [
            "word_compare_output",
            "generation_success"
        ]
    
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
        # Create fresh uploader keys
        import uuid
    
        st.session_state["old_uploader_key"] = (
            f"old_upload_{uuid.uuid4().hex}"
        )
    
        st.session_state["new_uploader_key"] = (
            f"new_upload_{uuid.uuid4().hex}"
        )
    
        st.rerun()

    # -----------------------------------
    # Generate button
    # -----------------------------------
    generate_clicked = st.sidebar.button(
        "Generate Highlighted File",
        use_container_width=True
    )

    # -----------------------------------
    # Download button in sidebar
    # -----------------------------------
    if "word_compare_output" in st.session_state:
        output_data = st.session_state["word_compare_output"]

        st.sidebar.download_button(
            label="Download Compared File",
            data=output_data["file_bytes"],
            file_name=output_data["file_name"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    return {
        "old_file": old_file,
        "new_file": new_file,
        "generate_clicked": generate_clicked
    }
