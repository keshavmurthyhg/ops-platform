let generatedFileName = null;
let updatedCells = {};
let newRows = [];


/* =========================================
   DOCK SECTION SWITCH
========================================= */

function showExcelSection(sectionName, event) {

    document.querySelectorAll(".dock-item")
        .forEach(item => {
            item.classList.remove("active-dock");
        });

    document.querySelectorAll(".dock-section")
        .forEach(section => {
            section.classList.remove("active-section");
        });

    document
        .getElementById(sectionName + "-section")
        .classList.add("active-section");

    event.currentTarget.classList.add("active-dock");
}

/* =====================================================
FILE NAMES
===================================================== */

function updateFileNames() {

    const file1 =
        document.getElementById("file1");

    const file2 =
        document.getElementById("file2");

    document.getElementById(
        "file1Name"
    ).innerText =

        file1.files.length
            ? file1.files[0].name
            : "No file selected";

    document.getElementById(
        "file2Name"
    ).innerText =

        file2.files.length
            ? file2.files[0].name
            : "No file selected";
}


/* =====================================================
PROCESSING STATUS
===================================================== */

function showProcessing(message) {

    const statusMessage =
        document.getElementById("statusMessage");

    const progressWrapper =
        document.getElementById("progressWrapper");

    const progressFill =
        document.getElementById("progressFill");

    const progressText =
        document.getElementById("progressText");

    if (statusMessage) {
        statusMessage.innerText = "Processing...";
    }

    if (progressWrapper) {
        progressWrapper.classList.remove("hidden");
    }

    if (progressFill) {

        progressFill.style.background =
            "linear-gradient(90deg,#22c55e,#4ade80)";

        progressFill.style.width = "60%";

        progressFill.classList.add(
            "active-progress"
        );
    }

    if (progressText) {
        progressText.innerText = message;
    }
}


function showCompleted(message) {

    const statusMessage =
        document.getElementById("statusMessage");

    const progressFill =
        document.getElementById("progressFill");

    const progressText =
        document.getElementById("progressText");

    if (statusMessage) {
        statusMessage.innerText = "Completed";
    }

    if (progressFill) {

        progressFill.style.width = "100%";

        progressFill.classList.remove(
            "active-progress"
        );
    }

    if (progressText) {
        progressText.innerText = message;
    }
}

function showFailed(message) {

    const statusMessage =
        document.getElementById("statusMessage");

    const progressWrapper =
        document.getElementById("progressWrapper");

    const progressFill =
        document.getElementById("progressFill");

    const progressText =
        document.getElementById("progressText");

    if (progressWrapper) {
        progressWrapper.classList.remove("hidden");
    }

    if (statusMessage) {
        statusMessage.innerText = "Failed";
    }

    if (progressText) {
        progressText.innerText = message;
    }

    if (progressFill) {

        progressFill.style.width = "100%";

        progressFill.style.background =
            "linear-gradient(90deg,#ef4444,#dc2626)";

        progressFill.classList.remove(
            "active-progress"
        );
    }
}

/* =====================================================
MERGE
===================================================== */

async function mergeExcelFiles() {

    const file1 =
        document.getElementById(
            "file1"
        ).files[0];

    const file2 =
        document.getElementById(
            "file2"
        ).files[0];

    const keyColumn =
        document.getElementById(
            "uniqueKeyColumn"
        ).value.trim();

    const latestLogic =
        document.getElementById(
            "mergeMode"
        ).value;

    const dateColumn =
        document.getElementById(
            "dateColumn"
        ).value.trim();


    if (!file1 || !file2) {

        showFailed(
            "Upload both Excel files"
        );

        return;
    }


    if (!keyColumn) {

        showFailed(
            "Enter unique key column"
        );

        return;
    }

    try {

        showProcessing(
            "Preparing merge..."
        );

        const formData =
            new FormData();

        formData.append(
            "file1",
            file1
        );

        formData.append(
            "file2",
            file2
        );

        formData.append(
            "key_column",
            keyColumn
        );

        formData.append(
            "latest_logic",
            latestLogic
        );

        formData.append(
            "date_column",
            dateColumn
        );


        showProcessing(
            "Merging records..."
        );


        const response =
            await fetch(
                "/excel-merge/process",
                {
                    method: "POST",
                    body: formData
                }
            );

        const result =
            await response.json();


        if (!result.success) {

            showFailed(
                result.message
            );

            return;
        }


        generatedFileName =
            result.download_file;


        /* =========================
        STORE HIGHLIGHT DATA
        ========================= */

        updatedCells =
            result.updated_cells || {};

        newRows =
            result.new_rows_list || [];


        /* =========================
        UPDATE UI
        ========================= */

        updateKPI(result);

        renderPreviewTable(
            result.preview_rows || [],
            result.preview_columns || []
        );

        activateDownloadButton();

        showCompleted(
            "Excel merge completed successfully"
        );

    }

    catch(error) {

        console.error(error);

        showFailed(
            "Excel merge failed"
        );
    }
}


/* =====================================================
KPI
===================================================== */

function updateKPI(result) {

    document.getElementById(
        "totalRows"
    ).innerText =
        result.total_rows || 0;

    document.getElementById(
        "updatedRows"
    ).innerText =
        result.updated_rows || 0;

    document.getElementById(
        "newRows"
    ).innerText =
        result.new_rows || 0;

    document.getElementById(
        "duplicatesRemoved"
    ).innerText =
        result.duplicates_removed || 0;
}


/* =====================================================
DOWNLOAD
===================================================== */

function activateDownloadButton() {

    document.getElementById(
        "downloadBtn"
    ).classList.remove(
        "hidden"
    );
}


function downloadMergedExcel() {

    if (!generatedFileName) {

        alert(
            "No merged output available"
        );

        return;
    }

    window.location.href =
        `/excel-merge/download/${generatedFileName}`;
}


/* =====================================================
PREVIEW TABLE
===================================================== */

function renderPreviewTable(rows, columns) {

    const head =
        document.getElementById(
            "mergeTableHead"
        );

    const body =
        document.getElementById(
            "mergeTableBody"
        );

    if (!rows.length) {

        body.innerHTML = `
            <tr>
                <td colspan="20"
                    class="empty-search-message">

                    No preview available

                </td>
            </tr>
        `;

        return;
    }

    /* =========================
       HEADER
    ========================= */

    let headHtml = "<tr>";

    columns.forEach((col, index) => {

        let className = "";

        const lower =
            col.toLowerCase();

        if (index === 0) {

            className = "number-column";
        }

        else if (

            lower.includes("description") ||
            lower.includes("comment") ||
            lower.includes("resolution") ||
            lower.includes("additional")

        ) {

            className = "long-text-column";
        }

        else {

            className = "small-column";
        }

        headHtml += `
            <th class="${className}">
                ${col}
            </th>
        `;
    });

    headHtml += "</tr>";

    head.innerHTML = headHtml;

    /* =========================
       BODY
    ========================= */

    let bodyHtml = "";

    rows.forEach(row => {

        bodyHtml += "<tr>";

        const rowId =
            String(
                row[columns[0]] || ""
            );

        columns.forEach((col, index) => {

            let className = "";

            const lower =
                col.toLowerCase();

            if (index === 0) {

                className = "number-column";
            }

            else if (

                lower.includes("description") ||
                lower.includes("comment") ||
                lower.includes("resolution") ||
                lower.includes("additional")

            ) {

                className = "long-text-column";
            }

            else {

                className = "small-column";
            }

            let extraClass = "";

            if (newRows.includes(rowId)) {

                extraClass = "new-cell";
            }

            else if (

                updatedCells[rowId] &&
                updatedCells[rowId].includes(col)

            ) {

                extraClass = "updated-cell";
            }

            bodyHtml += `
                <td
                    class="${className} ${extraClass}"
                    title="${row[col] ?? ""}">

                    ${row[col] ?? ""}

                </td>
            `;
        });

        bodyHtml += "</tr>";
    });

    body.innerHTML = bodyHtml;
}

/* =====================================================
CLEAR WORKSPACE
===================================================== */

function clearExcelWorkspace() {

    document.getElementById(
        "file1"
    ).value = "";

    document.getElementById(
        "file2"
    ).value = "";

    document.getElementById(
        "file1Name"
    ).innerText =
        "No file selected";

    document.getElementById(
        "file2Name"
    ).innerText =
        "No file selected";

    document.getElementById(
        "uniqueKeyColumn"
    ).value = "";

    document.getElementById(
        "mergeMode"
    ).value = "prefer_new";

    document.getElementById(
        "dateColumn"
    ).value = "";

    generatedFileName = null;

    document.getElementById(
        "downloadBtn"
    ).classList.add(
        "hidden"
    );

    updateKPI({
        total_rows: 0,
        updated_rows: 0,
        new_rows: 0,
        duplicates_removed: 0
    });

    document.getElementById(
        "mergeTableHead"
    ).innerHTML = "";

    document.getElementById(
        "mergeTableBody"
    ).innerHTML = `
        <tr>
            <td colspan="20"
                class="empty-search-message">

                Workspace cleared

            </td>
        </tr>
    `;

    
}


/* =====================================================
EVENTS
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        resetProcessingStatus();

        document
            .getElementById(
                "mergeBtn"
            )
            .addEventListener(
                "click",
                mergeExcelFiles
            );

        document
            .getElementById(
                "downloadBtn"
            )
            .addEventListener(
                "click",
                downloadMergedExcel
            );

        document
            .getElementById(
                "file1"
            )
            .addEventListener(
                "change",
                updateFileNames
            );

        document
            .getElementById(
                "file2"
            )
            .addEventListener(
                "change",
                updateFileNames
            );

        const clearBtn =
            document.querySelector(
                ".sidebar-toolbar button"
            );

        if (clearBtn) {

            clearBtn.addEventListener(
                "click",
                clearExcelWorkspace
            );
        }
    }
);