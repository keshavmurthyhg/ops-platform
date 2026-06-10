let uploadedFiles = {
    problem: [],
    root: [],
    resolution: []
};


/* ==========================================
   LOAD PREVIEW
========================================== */
async function loadPreview() {
    const incidentNumber = document
        .getElementById("incident_number")
        .value
        .trim();

    if (!incidentNumber) {
        alert("Enter Incident Number");
        return;
    }

    showProgress("Loading incident data...");

    try {
        updateProgress(40, "Fetching RCA details...");

        const response = await fetch("/get-rca-data", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                incident_number: incidentNumber
            })
        });

        const data = await response.json();

        if (data.error) {
            failProgress(data.error);
            alert(data.error);
            return;
        }

        /* Update preview */
        document.getElementById("previewContainer").innerHTML =
            data.preview_html || "No preview available";
        document.getElementById("activeIncident").innerText = incidentNumber;
        document.getElementById("lastAction").innerText = "Preview Generated";
        document.getElementById("downloadStatus").innerText = "Available";
        
        /* Populate RCA editor */
        document.getElementById("problem_statement").value =
            data.problem_statement || "";

        document.getElementById("root_cause").value =
            data.root_cause || "";

        document.getElementById("resolution_text").value =
            data.resolution || "";

        /* Hide helper text ONLY */
        const downloadMessage =
            document.getElementById("downloadMessage");

        if (downloadMessage) {
            downloadMessage.style.display = "none";
        }

        /* Auto switch to downloads tab */
        showReportSection("downloads");

        /* KPI update */
        const reportsCount =
            document.getElementById("reportsCount");

        if (reportsCount) {
            reportsCount.innerText =
                parseInt(reportsCount.innerText || 0) + 1;
        }

        completeProgress("Preview generated successfully");

    } catch (error) {
        console.error(error);
        failProgress("Preview generation failed");
        alert("Failed to load preview");
    }
}


/* ==========================================
   FILE UPLOAD SETUP
========================================== */
function setupFileUpload(inputId, type, previewId) {
    const input = document.getElementById(inputId);

    if (!input) return;

    input.addEventListener("change", function () {
        const files = Array.from(input.files);

        files.forEach(file => {
            uploadedFiles[type].push(file);
        });

        renderFilePreview(type, previewId);

        input.value = "";
    });
}


/* ==========================================
   FILE PREVIEW
========================================== */
function renderFilePreview(type, previewId) {
    const container =
        document.getElementById(previewId);

    if (!container) return;

    container.innerHTML = "";

    uploadedFiles[type].forEach((file, index) => {
        const chip = document.createElement("div");

        chip.className = "file-chip";

        chip.innerHTML = `
            ${file.name}
            <span class="remove-file"
                  onclick="removeFile('${type}', ${index}, '${previewId}')">
                  ×
            </span>
        `;

        container.appendChild(chip);
    });
}


/* ==========================================
   REMOVE FILE
========================================== */
function removeFile(type, index, previewId) {
    uploadedFiles[type].splice(index, 1);
    renderFilePreview(type, previewId);
}


/* ==========================================
   UPDATE PREVIEW
========================================== */
async function updatePreview() {
    const incidentNumber = document
        .getElementById("incident_number")
        .value
        .trim();

    if (!incidentNumber) {
        alert("Load incident first");
        return;
    }

    showProgress("Updating preview...");

    const formData = new FormData();

    formData.append("incident_number", incidentNumber);
    formData.append(
        "problem",
        document.getElementById("problem_statement").value
    );

    formData.append(
        "analysis",
        document.getElementById("root_cause").value
    );

    formData.append(
        "resolution",
        document.getElementById("resolution_text").value
    );

    uploadedFiles.problem.forEach(file => {
        formData.append("problem_images", file);
    });

    uploadedFiles.root.forEach(file => {
        formData.append("root_images", file);
    });

    uploadedFiles.resolution.forEach(file => {
        formData.append("resolution_images", file);
    });

    try {
        updateProgress(60, "Refreshing preview...");

        const response = await fetch("/update-preview", {
            method: "POST",
            body: formData
        });

        const html = await response.text();

        document.getElementById("previewContainer").innerHTML = html;
        document.getElementById("lastAction").innerText =
            "Preview Updated";
        completeProgress("Preview updated successfully");

    } catch (error) {
        console.error(error);
        failProgress("Preview update failed");
        alert("Preview update failed");
    }
}


/* ==========================================
   DOWNLOAD REPORT
========================================== */
async function downloadReport(type) {
    const incidentNumber = document
        .getElementById("incident_number")
        .value
        .trim();

    if (!incidentNumber) {
        alert("Load incident first");
        return;
    }

    showProgress(`Generating ${type.toUpperCase()} report...`);

    const formData = new FormData();

    formData.append("incident_number", incidentNumber);

    formData.append(
        "problem_statement",
        document.getElementById("problem_statement").value
    );

    formData.append(
        "root_cause",
        document.getElementById("root_cause").value
    );

    formData.append(
        "resolution",
        document.getElementById("resolution_text").value
    );

    uploadedFiles.problem.forEach(file => {
        formData.append("problem_images", file);
    });

    uploadedFiles.root.forEach(file => {
        formData.append("root_images", file);
    });

    uploadedFiles.resolution.forEach(file => {
        formData.append("resolution_images", file);
    });

    try {
        updateProgress(75, "Preparing file...");

        const response = await fetch(`/download/${type}`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Download failed");
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;

        if (type === "word") {
            a.download = `${incidentNumber}.docx`;
        } else if (type === "pdf") {
            a.download = `${incidentNumber}.pdf`;
        } else {
            a.download = `${incidentNumber}.zip`;
        }

        document.body.appendChild(a);
        a.click();
        a.remove();

        document.getElementById("lastAction").innerText =
            `${type.toUpperCase()} Download`;

        document.getElementById("downloadStatus").innerText =
            `${type.toUpperCase()} Generated`;

        completeProgress(
            `${type.toUpperCase()} download completed successfully`
        );

    } catch (error) {
        console.error(error);
        failProgress("Download failed");
        alert("Download failed");
    }
}


/* ==========================================
   CLEAR WORKSPACE
========================================== */
function clearPreview() {
    document.getElementById("incident_number").value = "";

    document.getElementById("previewContainer").innerHTML =
        "Preview will appear here";

    document.getElementById("problem_statement").value = "";
    document.getElementById("root_cause").value = "";
    document.getElementById("resolution_text").value = "";

    uploadedFiles = {
        problem: [],
        root: [],
        resolution: []
    };

    document.getElementById("problem_preview_files").innerHTML = "";
    document.getElementById("root_preview_files").innerHTML = "";
    document.getElementById("resolution_preview_files").innerHTML = "";

    /* Restore helper message */
    const downloadMessage =
        document.getElementById("downloadMessage");

    if (downloadMessage) {
        downloadMessage.style.display = "block";
    }

    showReportSection("downloads");

    document.getElementById("activeIncident").innerText = "-";
    document.getElementById("lastAction").innerText =
        "Waiting for input";
    document.getElementById("downloadStatus").innerText =
        "Not generated";

    resetProcessingStatus();
}

/* ==========================================
   APPLY FILTERS
========================================== */
function applyFilters() {
    console.log("Filters feature not implemented yet");
}

/* ==========================================
   DOCK SWITCHING
========================================== */
function showReportSection(sectionName) {

    document.querySelectorAll(".dock-section").forEach(section => {
        section.classList.remove("active-section");
    });

    document.querySelectorAll(".dock-item").forEach(icon => {
        icon.classList.remove("active-dock");
    });

    const target =
        document.getElementById(`${sectionName}-section`);

    if (target) {
        target.classList.add("active-section");
    }

    const clickedIcon = document.querySelector(
        `.dock-item[onclick="showReportSection('${sectionName}')"]`
    );

    if (clickedIcon) {
        clickedIcon.classList.add("active-dock");
    }
}

/* ==========================================
   PROCESS STATUS HELPERS
========================================== */

function showProgress(message) {
    const status = document.getElementById("processingStatusText");

    if (status) {
        status.innerText = message;
    }
}

function updateProgress(percent, message) {
    const status = document.getElementById("processingStatusText");

    if (status) {
        status.innerText = message;
    }
}

function completeProgress(message) {
    const status = document.getElementById("processingStatusText");

    if (status) {
        status.innerText = message;
    }
}

function failProgress(message) {
    const status = document.getElementById("processingStatusText");

    if (status) {
        status.innerText = message;
    }
}

function resetProcessingStatus() {
    const status = document.getElementById("processingStatusText");

    if (status) {
        status.innerText = "Ready";
    }
}

/* ==========================================
   INIT
========================================== */
document.addEventListener("DOMContentLoaded", function () {

    setupFileUpload(
        "problem_images",
        "problem",
        "problem_preview_files"
    );

    setupFileUpload(
        "root_images",
        "root",
        "root_preview_files"
    );

    setupFileUpload(
        "resolution_images",
        "resolution",
        "resolution_preview_files"
    );

    /* Default tab */
    showReportSection("downloads");
});