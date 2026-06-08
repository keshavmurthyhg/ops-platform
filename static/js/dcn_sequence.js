console.log(
    "DCN Sequence Module Loaded"
);


// =====================================================
// ELEMENTS
// =====================================================
const processBtn =
    document.getElementById(
        "processBtn"
    );

const fileInput =
    document.getElementById(
        "excelFile"
    );

const statusMessage =
    document.getElementById(
        "statusMessage"
    );

const previewTableBody =
    document.querySelector(
        "#previewTable tbody"
    );

const missingCount =
    document.getElementById(
        "missingCount"
    );

const dockMissingCount =
    document.getElementById(
        "dockMissingCount"
    );

const downloadBtn =
    document.getElementById(
        "downloadBtn"
    );


// =====================================================
// GLOBAL VARIABLES
// =====================================================
let uploadedFile = null;

let outputFilename = null;


// =====================================================
// FILE UPLOAD CHANGE
// =====================================================
fileInput.addEventListener(
    "change",
    handleFileSelection
);


// =====================================================
// HANDLE FILE SELECTION
// =====================================================
function handleFileSelection(event) {

    const file =
        event.target.files[0];

    // =============================================
    // NO FILE
    // =============================================
    if (!file) {

        uploadedFile = null;

        updateStatus(
            "No file selected"
        );

        return;
    }

    // =============================================
    // VALIDATE EXTENSION
    // =============================================
    const allowedExtensions = [
        ".xlsx",
        ".xls"
    ];

    const lowerName =
        file.name.toLowerCase();

    const isValid =
        allowedExtensions.some(
            ext => lowerName.endsWith(ext)
        );

    if (!isValid) {

        alert(
            "Please upload valid Excel file"
        );

        fileInput.value = "";

        uploadedFile = null;

        updateStatus(
            "Invalid file format"
        );

        return;
    }

    // =============================================
    // SAVE FILE
    // =============================================
    uploadedFile = file;

    updateStatus(
        `Selected: ${file.name}`
    );
}


// =====================================================
// PROCESS BUTTON
// =====================================================
processBtn.addEventListener(
    "click",
    processDCNSequence
);


// =====================================================
// PROCESS FUNCTION
// =====================================================
async function processDCNSequence() {

    try {

        // =========================================
        // VALIDATE FILE
        // =========================================
        if (!uploadedFile) {

            alert(
                "Please upload Excel file"
            );

            updateStatus(
                "Upload Excel file first"
            );

            return;
        }

        // =========================================
        // RESET UI
        // =========================================
        resetPreviewTable();

        // =========================================
        // BUTTON STATE
        // =========================================
        processBtn.disabled = true;

        processBtn.innerText =
            "Processing...";

        // =========================================
        // STATUS
        // =========================================
        updateStatus(
            "Uploading and processing Excel..."
        );

        // =========================================
        // FORM DATA
        // =========================================
        const formData =
            new FormData();

        formData.append(
            "file",
            uploadedFile
        );

        // =========================================
        // API CALL
        // =========================================
        const response = await fetch(

            "/api/dcn-sequence/process",

            {
                method: "POST",
                body: formData
            }

        );

        // =========================================
        // JSON
        // =========================================
        const result =
            await response.json();

        console.log(result);

        // =========================================
        // FAILURE
        // =========================================
        if (!result.success) {

            updateStatus(
                `Error: ${result.message}`
            );

            alert(
                result.message
            );

            processBtn.disabled = false;

            processBtn.innerText =
                "Find Missing Sequence";

            return;
        }

        // =========================================
        // UPDATE KPI
        // =========================================
        missingCount.innerText =
            result.total_missing;

        dockMissingCount.innerText =
            result.total_missing;

        // =========================================
        // TABLE
        // =========================================
        renderPreviewTable(
            result.preview
        );

        // =========================================
        // DOWNLOAD
        // =========================================
        outputFilename =
            result.output_file;

        if (result.total_missing > 0) {

            enableDownloadButton(
                outputFilename
            );

        } else {

            disableDownloadButton();
        }

        // =========================================
        // STATUS
        // =========================================
        updateStatus(

            `Completed. Missing sequences found: ${result.total_missing}`

        );

    } catch (error) {

        console.error(error);

        updateStatus(
            "Unexpected error occurred"
        );

        alert(
            "Unexpected error occurred"
        );

    } finally {

        // =========================================
        // RESET BUTTON
        // =========================================
        processBtn.disabled = false;

        processBtn.innerText =
            "Find Missing Sequence";
    }
}


// =====================================================
// RENDER TABLE
// =====================================================
function renderPreviewTable(data) {

    previewTableBody.innerHTML = "";

    // =============================================
    // EMPTY RESULT
    // =============================================
    if (!data || data.length === 0) {

        previewTableBody.innerHTML = `
            <tr>
                <td colspan="3"
                    class="empty-table">

                    No missing sequences found

                </td>
            </tr>
        `;

        return;
    }

    // =============================================
    // BUILD ROWS
    // =============================================
    data.forEach(row => {

        const tr =
            document.createElement("tr");

        tr.innerHTML = `

            <td>
                ${row["SL NO"]}
            </td>

            <td>
                ${row["Missing DCN Number"]}
            </td>

            <td>
                ${row["Numeric Value"]}
            </td>

        `;

        previewTableBody.appendChild(tr);
    });
}


// =====================================================
// RESET TABLE
// =====================================================
function resetPreviewTable() {

    previewTableBody.innerHTML = `
        <tr>
            <td colspan="3"
                class="empty-table">

                Processing...

            </td>
        </tr>
    `;
}


// =====================================================
// ENABLE DOWNLOAD
// =====================================================
function enableDownloadButton(filename) {

    downloadBtn.classList.remove(
        "disabled-btn"
    );

    downloadBtn.href =
        `/api/dcn-sequence/download/${filename}`;

    downloadBtn.setAttribute(
        "download",
        filename
    );
}


// =====================================================
// DISABLE DOWNLOAD
// =====================================================
function disableDownloadButton() {

    downloadBtn.classList.add(
        "disabled-btn"
    );

    downloadBtn.href = "#";
}


// =====================================================
// CLEAR WORKSPACE
// =====================================================
function clearWorkspace() {

    // =============================================
    // FILE
    // =============================================
    fileInput.value = "";

    uploadedFile = null;

    outputFilename = null;

    // =============================================
    // KPI
    // =============================================
    missingCount.innerText = "0";

    dockMissingCount.innerText = "0";

    // =============================================
    // TABLE
    // =============================================
    previewTableBody.innerHTML = `
        <tr>
            <td colspan="3"
                class="empty-table">

                Upload Excel and click
                Find Missing Sequence

            </td>
        </tr>
    `;

    // =============================================
    // DOWNLOAD
    // =============================================
    disableDownloadButton();

    // =============================================
    // BUTTON
    // =============================================
    processBtn.disabled = false;

    processBtn.innerText =
        "Find Missing Sequence";

    // =============================================
    // STATUS
    // =============================================
    updateStatus(
        "Workspace cleared"
    );
}


// =====================================================
// STATUS
// =====================================================
function updateStatus(message) {

    const currentTime =
        new Date().toLocaleTimeString();

    statusMessage.innerText =
        `[${currentTime}] ${message}`;
}


// =====================================================
// CONNECT GLOBAL SIDEBAR CLEAR BUTTON
// =====================================================
window.clearWorkspace =
    clearWorkspace;