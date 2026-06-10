let generatedFileName = null;
let pptConverted = false;


/* ==========================================
   DOCK SWITCHING
========================================== */
function showConverterSection(sectionName) {

    document.querySelectorAll(".dock-section")
        .forEach(section => {
            section.classList.remove("active-section");
        });

    document.querySelectorAll(".dock-item")
        .forEach(icon => {
            icon.classList.remove("active-dock");
        });

    const target =
        document.getElementById(
            `${sectionName}-section`
        );

    if (target) {
        target.classList.add("active-section");
    }

    const clickedIcon = document.querySelector(
        `.dock-item[onclick="showConverterSection('${sectionName}')"]`
    );

    if (clickedIcon) {
        clickedIcon.classList.add("active-dock");
    }
}


/* ==========================================
   PROCESS STATUS
========================================== */

function showProgress(message) {

    const wrapper =
        document.getElementById("progressWrapper");

    if (wrapper) {
        wrapper.classList.remove("hidden");
    }

    document.getElementById("statusMessage")
        .innerText = "Processing";

    document.getElementById("progressText")
        .innerText = message;

    document.getElementById("progressFill")
        .style.width = "20%";
}


function updateProgress(percent, message) {

    document.getElementById("progressFill")
        .style.width = percent + "%";

    document.getElementById("progressText")
        .innerText = message;
}


function completeProgress(message) {

    document.getElementById("statusMessage")
        .innerText = "Completed";

    document.getElementById("progressText")
        .innerText = message;

    document.getElementById("progressFill")
        .style.width = "100%";
}


function failProgress(message) {

    document.getElementById("statusMessage")
        .innerText = "Failed";

    document.getElementById("progressText")
        .innerText = message;
}


function resetProcessingStatus() {

    document.getElementById("statusMessage")
        .innerText = "Ready";

    document.getElementById("progressText")
        .innerText = "Waiting";

    document.getElementById("progressFill")
        .style.width = "0%";

    document.getElementById("progressWrapper")
        .classList.add("hidden");
}


/* ==========================================
   PREVIEW PPT
========================================== */

async function loadPPTPreview() {

    const fileInput =
        document.getElementById("pptUpload");

    if (!fileInput.files.length) {
        alert("Upload PPT first");
        return;
    }

    const formData = new FormData();

    formData.append(
        "ppt_file",
        fileInput.files[0]
    );

    showProgress("Reading PPT...");

    try {

        updateProgress(
            40,
            "Extracting incident details..."
        );

        const response = await fetch(
            "/converter/preview",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (data.error) {
            failProgress(data.error);
            alert(data.error);
            return;
        }

        document.getElementById(
            "previewContainer"
        ).innerHTML =
            data.preview_html;

        renderSlidePreview(
            data.slide_images
        );

        completeProgress(
            "Preview generated successfully"
        );

        document.getElementById("convertBtn")
            .classList.remove("hidden");

    } catch (error) {

        console.error(error);

        failProgress(
            "Preview generation failed"
        );

        alert("Preview failed");
    }
}


/* ==========================================
   CONVERT PPT
========================================== */

async function convertPPTSlides() {

    const fileInput =
        document.getElementById("pptUpload");

    if (!fileInput.files.length) {
        alert("Upload PPT first");
        return;
    }

    const formData = new FormData();

    formData.append(
        "ppt_file",
        fileInput.files[0]
    );

    showProgress("Converting PPT...");

    try {

        updateProgress(
            60,
            "Extracting slide images..."
        );

        const response = await fetch(
            "/converter/convert",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (data.error) {
            failProgress(data.error);
            alert(data.error);
            return;
        }

        pptConverted = true;

        renderSlidePreview(
            data.slide_images
        );

        document.getElementById("generateBtn")
            .classList.remove("hidden");

        completeProgress(
            "PPT conversion completed"
        );

    } catch (error) {

        console.error(error);

        failProgress(
            "PPT conversion failed"
        );

        alert("Conversion failed");
    }
}


/* ==========================================
   GENERATE DOCUMENT
========================================== */

async function generateDocument() {

    if (!pptConverted) {
        alert("Convert PPT first");
        return;
    }

    const fileInput =
        document.getElementById("pptUpload");

    const formData = new FormData();

    formData.append(
        "ppt_file",
        fileInput.files[0]
    );

    showProgress("Generating report...");

    try {

        updateProgress(
            80,
            "Creating DOC file..."
        );

        const response = await fetch(
            "/converter/generate",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (data.error) {
            failProgress(data.error);
            alert(data.error);
            return;
        }

        generatedFileName =
            data.filename;

        document.getElementById("downloadBtn")
            .classList.remove("hidden");

        completeProgress(
            "Document generated successfully"
        );

    } catch (error) {

        console.error(error);

        failProgress(
            "Document generation failed"
        );

        alert("Generation failed");
    }
}


/* ==========================================
   DOWNLOAD
========================================== */

function downloadConvertedDoc() {

    if (!generatedFileName) {
        alert("Generate document first");
        return;
    }

    window.location.href =
        `/converter/download/${generatedFileName}`;
}


/* ==========================================
   RENDER SLIDE PREVIEW
========================================== */

function renderSlidePreview(images) {

    const container =
        document.getElementById(
            "slidePreviewContainer"
        );

    if (!images || images.length === 0) {

        container.innerHTML = `
            <p class="preview-placeholder">
                No slide images found
            </p>
        `;

        return;
    }

    let html = "";

    images.forEach(img => {

        html += `
            <div class="ppt-preview-card">

                <img
                    src="/converter/slide-preview/${img.filename}"
                    class="slide-preview-image">

            </div>
        `;
    });

    container.innerHTML = html;
}


/* ==========================================
   CLEAR WORKSPACE
========================================== */
function clearWorkspace() {

    // =====================================
    // RESET FILE INPUT
    // =====================================

    const pptInput =
        document.getElementById("pptUpload");

    if (pptInput) {
        pptInput.value = "";
    }

    // =====================================
    // RESET FILE NAME LABEL
    // =====================================

    const pptFileName =
        document.getElementById("pptFileName");

    if (pptFileName) {
        pptFileName.innerText =
            "No file selected";
    }

    // =====================================
    // CLEAR PREVIEW
    // =====================================

    const previewContainer =
        document.getElementById(
            "previewContainer"
        );

    if (previewContainer) {

        previewContainer.innerHTML = `
            <p class="preview-placeholder">
                Preview will appear here
            </p>
        `;
    }

    // =====================================
    // CLEAR SLIDES PREVIEW
    // =====================================

    const slidePreviewContainer =
        document.getElementById(
            "slidePreviewContainer"
        );

    if (slidePreviewContainer) {

        slidePreviewContainer.innerHTML = `
            <p class="preview-placeholder">
                Converted slide images will appear here after conversion
            </p>
        `;
    }

    // =====================================
    // RESET DOWNLOAD BUTTON
    // =====================================

    const downloadBtn =
        document.getElementById(
            "downloadBtn"
        );

    if (downloadBtn) {
        downloadBtn.style.display =
            "none";
    }

    /* =====================================
    HIDE ACTION BUTTONS
    ===================================== */

    const convertBtn =
        document.getElementById(
            "convertBtn"
        );

    if (convertBtn) {
        convertBtn.classList.add(
            "hidden"
        );
    }

    const generateBtn =
        document.getElementById(
            "generateBtn"
        );

    if (generateBtn) {
        generateBtn.classList.add(
            "hidden"
        );
    }

    if (downloadBtn) {
        downloadBtn.classList.add(
            "hidden"
        );
    }


    generatedFileName = null;
    pptConverted = false;
    
    // =====================================
    // RESET STATUS
    // =====================================

    resetProcessingStatus();
}


/* ==========================================
   INIT
========================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        showConverterSection(
            "converter"
        );

        document.getElementById("convertBtn")
            .classList.add("hidden");

        document.getElementById("generateBtn")
            .classList.add("hidden");

        document.getElementById("downloadBtn")
            .classList.add("hidden");
    }
);

/* ==========================================
   FILE NAME DISPLAY
========================================== */
function updatePPTFileName() {

    const input =
        document.getElementById("pptUpload");

    const label =
        document.getElementById("pptFileName");

    if (
        input.files &&
        input.files.length > 0
    ) {

        label.innerText =
            input.files[0].name;

    } else {

        label.innerText =
            "No file selected";
    }
}