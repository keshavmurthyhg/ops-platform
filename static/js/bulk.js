/* -------------------------
   PROGRESS FUNCTIONS
------------------------- */
function formatBulkDate(dateValue) {
    const date = new Date(dateValue);

    const months = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec"
    ];

    const day = String(date.getDate()).padStart(2, "0");
    const month = months[date.getMonth()];
    const year = date.getFullYear();

    return `${day}-${month}-${year}`;
}

function showProgress(message) {
    document.getElementById("progressWrapper")
        .classList.remove("hidden");

    document.getElementById("progressFill")
        .style.width = "20%";

    document.getElementById("progressText")
        .innerText = message;

    document.getElementById("statusMessage")
        .innerText = "Processing...";
}

function updateProgress(percent, message) {
    document.getElementById("progressFill")
        .style.width = percent + "%";

    document.getElementById("progressText")
        .innerText = message;
}

function completeProgress(message) {
    document.getElementById("progressFill")
        .style.width = "100%";

    document.getElementById("progressText")
        .innerText = "Completed";

    document.getElementById("statusMessage")
        .innerText = message;

    // Hide progress bar after completion
    setTimeout(() => {
        document.getElementById("progressWrapper")
            .classList.add("hidden");
    }, 1200);
}


/* -------------------------
   GENERATE
------------------------- */

function generateBulkReports() {
    const incidents =
        document.getElementById("bulk_incidents")
            .value.trim();

    const outputType =
        document.getElementById("bulk_output_type").value;

    if (!incidents) {
        alert("Enter incident numbers");
        return;
    }

    const incidentList = incidents
        .split(",")
        .map(i => i.trim())
        .filter(i => i !== "");

    showProgress("Starting bulk generation...");

    setTimeout(() => {
        updateProgress(40, "Fetching incident data...");

        setTimeout(() => {
            updateProgress(75, "Publishing reports...");

            setTimeout(() => {

                let rows = "";
                let successCount = 0;
                let failedCount = 0;

                incidentList.forEach((incident, index) => {

                    // Mock failure for every 3rd record
                    let status =
                        (index + 1) % 3 === 0
                            ? "Failed"
                            : "Successful";

                    if (status === "Successful") {
                        successCount++;
                    } else {
                        failedCount++;
                    }

                    rows += `
                        <tr data-status="${status.toLowerCase()}">
                            <td>${formatBulkDate(new Date())}</td>
                            <td>${incident}</td>
                            <td>${outputType.toUpperCase()}</td>
                            <td class="${
                                status === "Successful"
                                    ? "status-success"
                                    : "status-failed"
                            }">
                                ${status}
                            </td>
                        </tr>
                    `;
                });

                document.getElementById("bulkResultsBody").innerHTML = rows;

                document.getElementById("totalJobs").innerText =
                    incidentList.length;

                document.getElementById("successJobs").innerText =
                    successCount;

                document.getElementById("failedJobs").innerText =
                    failedCount;

                completeProgress("Bulk generation completed");

            }, 1200);

        }, 1000);

    }, 1000);
}

function filterResults(type) {
    const rows =
        document.querySelectorAll("#bulkResultsTable tbody tr");

    rows.forEach(row => {
        const status =
            row.cells[3].innerText.toLowerCase();

        if (type === "all") {
            row.style.display = "";
        }
        else if (type === "successful") {
            row.style.display =
                status.includes("successful")
                ? ""
                : "none";
        }
        else if (type === "failed") {
            row.style.display =
                status.includes("failed")
                ? ""
                : "none";
        }
    });
}

/* -------------------------
   DOWNLOAD
------------------------- */

function downloadBulkZip() {
    const incidents =
        document.getElementById("bulk_incidents").value.trim();

    if (!incidents) {
        alert("No incidents available for download");
        return;
    }

    console.log(
        "Sending output type:",
        document.getElementById("bulk_output_type").value
    );

    fetch("/bulk/download-zip", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            incidents: incidents,
            output_type: document.getElementById("bulk_output_type").value
        })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "bulk_reports.zip";

        document.body.appendChild(a);
        a.click();
        a.remove();

        document.getElementById("statusMessage").innerText =
            "ZIP downloaded successfully";
    })
    .catch(error => {
        console.error(error);
    });
}


function downloadFailedReport() {
    const failedRows =
        document.querySelectorAll(
            '.status-failed'
        );

    let failedIncidents = [];

    failedRows.forEach(row => {
        const tr = row.closest("tr");

        if (tr) {
            const incident =
                tr.children[1].innerText.trim();

            failedIncidents.push(incident);
        }
    });

    if (failedIncidents.length === 0) {
        alert("No failed incidents found");
        return;
    }

    fetch("/bulk/download-failed-report", {
        method: "POST",
        headers: {
            "Content-Type":
                "application/json"
        },
        body: JSON.stringify({
            failed_incidents:
                failedIncidents
        })
    })
    .then(response => response.blob())
    .then(blob => {
        const url =
            window.URL.createObjectURL(blob);

        const a =
            document.createElement("a");

        a.href = url;
        a.download =
            "failed_incidents.csv";

        a.click();

        completeProgress(
            "Failed report downloaded"
        );
    })
    .catch(error => {
        console.error(error);

        document.getElementById(
            "statusMessage"
        ).innerText =
            "Failed report download error";
    });
}


/* -------------------------
   RESEND FAILED
------------------------- */

function resendFailedJobs() {

    const failedRows =
        document.querySelectorAll(".status-failed");

    if (failedRows.length === 0) {
        alert("No failed jobs found");
        return;
    }

    let failedIncidents = [];

    failedRows.forEach(row => {
        const tr = row.closest("tr");

        if (tr) {
            failedIncidents.push(
                tr.children[1].innerText.trim()
            );
        }
    });

    document.getElementById("bulk_incidents").value =
        failedIncidents.join(", ");

    generateBulkReports();
}


/* -------------------------
   FILTERS
------------------------- */

function applyBulkFilters() {
    const priority =
        document.getElementById("bulk_priority_filter").value;

    const preset =
        document.getElementById("bulk_preset_date_filter").value;

    const year =
        document.getElementById("bulk_year_filter").value;

    const fromDate =
        document.getElementById("bulk_from_date").value;

    const toDate =
        document.getElementById("bulk_to_date").value;

    showProgress("Fetching incidents...");

    fetch("/bulk/filter-incidents", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            priority: priority,
            preset: preset,
            year: year,
            from_date: fromDate,
            to_date: toDate
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const incidentText =
                data.incidents.join(", ");

            // update textarea
            document.getElementById("bulk_incidents").value =
                incidentText;

            // store latest filtered incidents globally
            window.filteredIncidents =
                data.incidents;

            completeProgress(
                `${data.incidents.length} incidents fetched`
            );
        }
        else {
            document.getElementById(
                "statusMessage"
            ).innerText = "Filter failed";
        }
    })
    .catch(err => {
        console.error(err);

        document.getElementById(
            "statusMessage"
        ).innerText = "Error fetching incidents";
    });
}

/* -------------------------
   OUTPUT TYPE
------------------------- */

function setBulkOutputType(type) {
    document.getElementById("bulk_output_type").value = type;

    document.getElementById("statusMessage")
        .innerText = `${type.toUpperCase()} selected`;
}


/* -------------------------
   CLEAR
------------------------- */

function clearBulkWorkspace() {

    /* -------------------------
       Clear incident textarea
    ------------------------- */
    document.getElementById("bulk_incidents").value = "";

    /* -------------------------
       Clear results table
    ------------------------- */
    document.getElementById("bulkResultsBody").innerHTML = `
        <tr>
            <td colspan="4">
                No reports generated yet
            </td>
        </tr>
    `;

    /* -------------------------
       Reset output type
    ------------------------- */
    document.getElementById("bulk_output_type").value = "both";

    /* -------------------------
       Reset priority filter
    ------------------------- */
    document.getElementById("bulk_priority_filter").value = "";

    /* -------------------------
       Reset preset filter
    ------------------------- */
    document.getElementById("bulk_preset_date_filter").value = "";

    /* -------------------------
       Reset year filter
    ------------------------- */
    document.getElementById("bulk_year_filter").value = "";

    /* -------------------------
       Reset custom date filters
    ------------------------- */
    document.getElementById("bulk_from_date").value = "";
    document.getElementById("bulk_to_date").value = "";

    /* -------------------------
       Clear stored incidents
    ------------------------- */
    window.filteredIncidents = [];

    /* -------------------------
       Reset KPI
    ------------------------- */
    document.getElementById("totalJobs").innerText = 0;
    document.getElementById("successJobs").innerText = 0;
    document.getElementById("failedJobs").innerText = 0;

    /* -------------------------
       Reset progress/status
    ------------------------- */
    document.getElementById("statusMessage").innerText = "Ready";

    document.getElementById("progressWrapper")
        .classList.add("hidden");
}


/* -------------------------
   ACCORDION
------------------------- */

function toggleSidebarSection(header) {
    const parent = header.parentElement;
    parent.classList.toggle("active");
}


/* -------------------------
   HOME
------------------------- */

function goHome() {
    window.location.href = "/";
}

/* -------------------------
   OVERRIDE SHARED SIDEBAR BUTTONS
------------------------- */

function clearPreview() {
    clearBulkWorkspace();
}

function applyFilters() {
    applyBulkFilters();
}

/* -------------------------
   DOCK SECTION SWITCHING
------------------------- */

function showSidebarSection(sectionId) {

    // hide all sections
    document.querySelectorAll(".dock-section")
        .forEach(section => {
            section.style.display = "none";
        });

    // remove active state
    document.querySelectorAll(".dock-item")
        .forEach(item => {
            item.classList.remove("active-dock");
        });

    // show selected section
    const activeSection =
        document.getElementById(sectionId);

    if (activeSection) {
        activeSection.style.display = "block";
    }

    // highlight clicked dock
    event.currentTarget.classList.add("active-dock");
}


/* -------------------------
   DEFAULT LOAD STATE
------------------------- */

document.addEventListener("DOMContentLoaded", function () {

    const downloadSection =
        document.getElementById("download-section");

    const filterSection =
        document.getElementById("filters-section");

    const kpiSection =
        document.getElementById("kpi-section");

    if (downloadSection) downloadSection.style.display = "block";
    if (filterSection) filterSection.style.display = "none";
    if (kpiSection) kpiSection.style.display = "none";

    const downloadsSection =
        document.getElementById("downloads-section");

    if (downloadsSection)
        downloadsSection.style.display = "none";
});