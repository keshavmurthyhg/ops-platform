function getUniqueValues(data, field) {
    if (!Array.isArray(data)) {
        return [];
    }

    const values = data
        .map(item => {
            const value = item[field];

            if (value === null || value === undefined) {
                return "";
            }

            return String(value).trim();
        })
        .filter(value => value !== "")
        .filter((value, index, array) => {
            return array.indexOf(value) === index;
        })
        .sort((a, b) => a.localeCompare(b));

    console.log("UNIQUE VALUES:", field, values);

    return values;
}

function buildOptions(values) {

    let html = '<option value="All">All</option>';

    values.forEach(v => {

        html += `<option value="${v}">${v}</option>`;

    });

    return html;
}


function updateProcessingStatus(
    message,
    detail = "",
    state = "completed"
) {

    const status =
        document.getElementById(
            "statusMessage"
        );

    const text =
        document.getElementById(
            "progressText"
        );

    const fill =
        document.getElementById(
            "progressFill"
        );

    if(status){
        status.innerText = message;
    }

    if(text){
        text.innerText = detail;
    }

    if(!fill) return;

    if(state === "processing"){

        fill.style.width = "70%";
        fill.style.background = "#f59e0b";

        fill.classList.add(
            "active-progress"
        );
    }

    else if(state === "completed"){

        fill.style.width = "100%";
        fill.style.background = "#22c55e";

        fill.classList.remove(
            "active-progress"
        );
    }

    else{

        fill.style.width = "100%";
        fill.style.background = "#ef4444";

        fill.classList.remove(
            "active-progress"
        );
    }
}

function updateStatus(message) {

    const statusElement =
        document.getElementById(
            "statusMessage"
        );

    if (statusElement) {
        statusElement.innerText =
            message;
    }
}


let supportLoaded = false;
let failuresLoaded = false;

async function refreshOperationsData() {

    updateProcessingStatus(
        "Support Emails",
        "Connecting to Outlook...",
        "processing"
    );

    try {

        const response =
            await fetch(
                "/api/operations-center/refresh"
            );

        const result =
            await response.json();

        if (result.success) {

            supportLoaded = false;
            failuresLoaded = false;

            updateProcessingStatus(
                "Completed",
                (result.support_data?.length || 0) +
                " emails loaded",
                "completed"
            );
            
            const refreshEl =
                document.getElementById(
                    "lastRefreshTime"
                );

            if (
                refreshEl &&
                result.refresh_time
            ) {

                refreshEl.textContent =
                    "Last Refresh: " +
                    result.refresh_time;
            }

            setTimeout(() => {

                location.reload();

            }, 1500);
        }

    } catch (error) {

        console.error(error);

        updateStatus(
            "Refresh failed"
        );
    }
}


function populateServerDropdown() {

    const env =
        document.getElementById(
            "failureEnvironmentFilter"
        )?.value || "All";

    const serverDropdown =
        document.getElementById(
            "failureServerFilter"
        );

    if(!serverDropdown) return;

    const servers = new Set();

    document
        .querySelectorAll(
            "#failureTableBody tr"
        )
        .forEach(row => {

            const rowEnv =
                row.cells[4]
                    .innerText
                    .trim();

            const rowServer =
                row.cells[5]
                    .innerText
                    .trim();

            if(
                env === "All" ||
                rowEnv === env
            ){
                servers.add(rowServer);
            }
        });

    serverDropdown.innerHTML =
        '<option value="All">All</option>';

    [...servers]
        .sort()
        .forEach(server => {

            serverDropdown.innerHTML +=
                `<option value="${server}">
                    ${server}
                </option>`;
        });
}

async function refreshPowerQuery() {

    console.log("refreshPowerQuery called");

    updateStatus(
        "Refreshing Power Query... this may take 1-5 minutes."
    );

    try {

        const response =
            await fetch(
                "/api/operations-center/refresh-power-query"
            );

        const result =
            await response.json();

        if (result.success) {

            updateStatus(
                result.message
            );

            setTimeout(() => {

                location.reload();

            }, 2000);
        

        } else {

            updateStatus(
                result.message
            );
        }

    } catch (error) {

        console.error(error);

        updateStatus(
            "Power Query refresh failed"
        );
    }
}

function showSidebarSection(sectionId, element){

    document
        .querySelectorAll(".dock-section")
        .forEach(section => {
            section.classList.remove("active-dock-section");
        });

    document
        .getElementById(sectionId)
        .classList.add("active-dock-section");

    document
        .querySelectorAll(".dock-item")
        .forEach(item => {
            item.classList.remove("active-dock");
        });

    element.classList.add("active-dock");
}

function updateKpis(section) {

    const grid = document.getElementById("summaryGrid");

    if (!grid) return;

    let html = "";

    switch (section) {

        case "support":

            html = `
                <div class="summary-card">
                    <div class="summary-title">
                        Support Emails
                    </div>
                    <div class="summary-value">
                        ${window.supportData ? window.supportData.length : 0}
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-title">
                        Pending Actions
                    </div>
                    <div class="summary-value">
                        ${
                            window.supportData
                            ? window.supportData.filter(
                                x =>
                                String(
                                    x.category || ""
                                ).includes(
                                    "Action Required"
                                )
                            ).length
                            : 0
                        }
                    </div>
                </div>
            `;

            break;

        case "failure":

            html = "";

            break;
            
        case "incident":

            html =
                document.getElementById("incidentKpis").innerHTML;

            break;

        case "azure":

            html =
                document.getElementById("azureKpis").innerHTML;

            break;

        case "ptc":

            html =
                document.getElementById("ptcKpis").innerHTML;

            break;

        case "dashboard":
            // Dashboard uses its own layout — no summaryGrid needed
            html = "";
            break;
    }


    if(section === "failure" && !failuresLoaded) {

        failuresLoaded = true;
        loadIntegrationFailures();
    }
    grid.innerHTML = html;

    const summaryGrid =
        document.getElementById(
            "summaryGrid"
        );

    if (section === "failure" || section === "dashboard") {

        summaryGrid.style.display =
            "none";

    } else {

        summaryGrid.style.display =
            "grid";
    }
}

function buildFilters(section){
    console.log(
        "buildFilters",
        section,
        window.supportData?.length
    );
    const container =
        document.getElementById(
            "dynamicFilters"
        );

    if(!container) return;

    let html = "";

    switch(section){

        case "support":

            html = `

                <div class="filter-group">

                    <div class="filter-label">
                        Date Filter
                    </div>

                    <select
                        id="dateFilterType"
                        class="sidebar-filter">

                        <option value="none">
                            No Filter
                        </option>

                        <option value="range">
                            Date Range
                        </option>

                        <option value="quick">
                            Quick Select
                        </option>

                    </select>

                </div>

                <div
                    id="dateRangeSection"
                    class="date-sub-section">

                    <input
                        type="date"
                        id="startDate"
                        class="sidebar-date">

                    <input
                        type="date"
                        id="endDate"
                        class="sidebar-date">

                </div>

                <div
                    id="quickDateSection"
                    class="date-sub-section">

                    <select
                        id="quickDateFilter"
                        class="sidebar-filter">

                        <option value="today">
                            Today
                        </option>

                        <option value="7">
                            Last 7 Days
                        </option>

                        <option value="30">
                            Last 30 Days
                        </option>

                        <option value="90">
                            Last 90 Days
                        </option>

                    </select>

                </div>

                <div class="filter-group">

                    <div class="filter-label">
                        Importance
                    </div>

                    <select
                        id="supportImportanceFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                window.supportData,
                                "importance"
                            )
                        )}

                    </select>

                    <div class="filter-label">
                        Category
                    </div>

                    <select
                        id="supportCategoryFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                window.supportData,
                                "category"
                            )
                        )}

                    </select>

                </div>

            `;
            break;

        case "failure":

            html = `

                <div class="filter-group">

                    <div class="filter-label">
                        Date Filter
                    </div>

                    <select
                        id="dateFilterType"
                        class="sidebar-filter">

                        <option value="none">
                            No Filter
                        </option>

                        <option value="range">
                            Date Range
                        </option>

                        <option value="quick">
                            Quick Select
                        </option>

                    </select>

                </div>

                <div
                    id="dateRangeSection"
                    class="date-sub-section">

                    <input
                        type="date"
                        id="startDate"
                        class="sidebar-date">

                    <input
                        type="date"
                        id="endDate"
                        class="sidebar-date">

                </div>

                <div
                    id="quickDateSection"
                    class="date-sub-section">

                    <select
                        id="quickDateFilter"
                        class="sidebar-filter">

                        <option value="today">
                            Today
                        </option>

                        <option value="7">
                            Last 7 Days
                        </option>

                        <option value="30">
                            Last 30 Days
                        </option>

                        <option value="90">
                            Last 90 Days
                        </option>

                    </select>

                </div>

                <div class="filter-group">

                    <div class="filter-label">
                        Environment
                    </div>

                    <select
                        id="failureEnvironmentFilter"
                        class="sidebar-filter">

                        <option value="All">All</option>
                        <option value="PROD">PROD</option>
                        <option value="TEST">TEST</option>
                        <option value="TESTB">TESTB</option>
                        <option value="QA">QA</option>
                        <option value="QB">QB</option>
                        <option value="DEVA">DEVA</option>
                        <option value="DEVB">DEVB</option>
                        <option value="DEVC">DEVC</option>
                        <option value="MBM">MBM</option>
                        <option value="INT-VCE">INT-VCE</option>

                    </select>

                    <div class="filter-label">
                        Windchill Server
                    </div>

                    <select
                        id="failureServerFilter"
                        class="sidebar-filter">

                        <option value="All">All</option>

                    </select>

                </div>

            `;
            break;

        case "incident":

            html = `

                <div class="filter-group">

                    <div class="filter-label">
                        Date Filter
                    </div>

                    <select
                        id="dateFilterType"
                        class="sidebar-filter">

                        <option value="none">
                            No Filter
                        </option>

                        <option value="range">
                            Date Range
                        </option>

                        <option value="quick">
                            Quick Select
                        </option>

                    </select>

                </div>

                <div
                    id="dateRangeSection"
                    class="date-sub-section">

                    <input
                        type="date"
                        id="startDate"
                        class="sidebar-date">

                    <input
                        type="date"
                        id="endDate"
                        class="sidebar-date">

                </div>

                <div
                    id="quickDateSection"
                    class="date-sub-section">

                    <select
                        id="quickDateFilter"
                        class="sidebar-filter">

                        <option value="today">
                            Today
                        </option>

                        <option value="7">
                            Last 7 Days
                        </option>

                        <option value="30">
                            Last 30 Days
                        </option>

                        <option value="90">
                            Last 90 Days
                        </option>

                    </select>

                </div>

                <div class="filter-group">

                    <div class="filter-label">
                        Status
                    </div>

                    <select
                        id="incidentStatusFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                incidentData,
                                "Status"
                            )
                        )}

                    </select>

                    <div class="filter-label">
                        Priority
                    </div>

                    <select
                        id="incidentPriorityFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                incidentData,
                                "Priority"
                            )
                        )}

                    </select>

                </div>

            `;
            break;

        case "azure":

            html = `

                <div class="filter-group">

                    <div class="filter-label">
                        Date Filter
                    </div>

                    <select
                        id="dateFilterType"
                        class="sidebar-filter">

                        <option value="none">
                            No Filter
                        </option>

                        <option value="range">
                            Date Range
                        </option>

                        <option value="quick">
                            Quick Select
                        </option>

                    </select>

                </div>

                <div
                    id="dateRangeSection"
                    class="date-sub-section">

                    <input
                        type="date"
                        id="startDate"
                        class="sidebar-date">

                    <input
                        type="date"
                        id="endDate"
                        class="sidebar-date">

                </div>

                <div
                    id="quickDateSection"
                    class="date-sub-section">

                    <select
                        id="quickDateFilter"
                        class="sidebar-filter">

                        <option value="today">
                            Today
                        </option>

                        <option value="7">
                            Last 7 Days
                        </option>

                        <option value="30">
                            Last 30 Days
                        </option>

                        <option value="90">
                            Last 90 Days
                        </option>

                    </select>

                </div>

                <div class="filter-group">

                    <div class="filter-label">
                        Status
                    </div>

                    <select
                        id="azureStatusFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                azureData,
                                "Status"
                            )
                        )}

                    </select>

                    <div class="filter-label">
                        Created By
                    </div>

                    <select
                        id="azureCreatedByFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                azureData,
                                "Created By"
                            )
                        )}

                    </select>

                </div>

            `;
            break;

        case "ptc":

            html = `

                <div class="filter-group">

                    <div class="filter-label">
                        Date Filter
                    </div>

                    <select
                        id="dateFilterType"
                        class="sidebar-filter">

                        <option value="none">
                            No Filter
                        </option>

                        <option value="range">
                            Date Range
                        </option>

                        <option value="quick">
                            Quick Select
                        </option>

                    </select>

                </div>

                <div
                    id="dateRangeSection"
                    class="date-sub-section">

                    <input
                        type="date"
                        id="startDate"
                        class="sidebar-date">

                    <input
                        type="date"
                        id="endDate"
                        class="sidebar-date">

                </div>

                <div
                    id="quickDateSection"
                    class="date-sub-section">

                    <select
                        id="quickDateFilter"
                        class="sidebar-filter">

                        <option value="today">
                            Today
                        </option>

                        <option value="7">
                            Last 7 Days
                        </option>

                        <option value="30">
                            Last 30 Days
                        </option>

                        <option value="90">
                            Last 90 Days
                        </option>

                    </select>

                </div>

                <div class="filter-group">

                    <div class="filter-label">
                        Status
                    </div>

                    <select
                        id="ptcStatusFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                ptcData,
                                "Status"
                            )
                        )}

                    </select>

                    <div class="filter-label">
                        Created By
                    </div>

                    <select
                        id="ptcCreatedByFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                ptcData,
                                "Created By"
                            )
                        )}

                    </select>

                </div>

            `;
            break;
    }

    container.innerHTML = html;
    if(section === "failure") {

        populateServerDropdown();

        document
            .getElementById(
                "failureEnvironmentFilter"
            )
            .addEventListener(
                "change",
                () => {

                    populateServerDropdown();
                    applyFilters();

                }
            );
    }
    
    // =========================================
    // DEFAULT FILTER VALUES
    // =========================================

    if(section === "support") {

        const importanceFilter =
            document.getElementById(
                "supportImportanceFilter"
            );

        const categoryFilter =
            document.getElementById(
                "supportCategoryFilter"
            );

        if(importanceFilter) {

            importanceFilter.value = "All";
        }

        if(categoryFilter) {

            const actionOption =
                [...categoryFilter.options]
                    .find(option =>
                        option.value
                            .toLowerCase()
                            .includes("action required")
                    );

            if(actionOption) {

                categoryFilter.value =
                    actionOption.value;
            }
        }

        applyFilters();
    }


    // =========================================

    if(section === "failure") {

        const envFilter =
            document.getElementById(
                "failureEnvironmentFilter"
            );

        const serverFilter =
            document.getElementById(
                "failureServerFilter"
            );

        if(envFilter) {

            envFilter.value = "PROD";
        }

        if(serverFilter) {

            serverFilter.value = "All";
        }

        applyFilters();
    }
    
    container
        .querySelectorAll("select")
        .forEach(select => {

            select.addEventListener(
                "change",
                applyFilters
            );

        });
    }

document.addEventListener("change", e => {

    if(e.target.id !== "dateFilterType") {
        return;
    }

    const range =
        document.getElementById(
            "dateRangeSection"
        );

    const quick =
        document.getElementById(
            "quickDateSection"
        );

    if(!range || !quick) {
        return;
    }

    range.style.display = "none";
    quick.style.display = "none";

    if(e.target.value === "range") {

        range.style.display = "block";
    }

    if(e.target.value === "quick") {

        quick.style.display = "block";
    }
});

async function showSection(section) {

    document
        .querySelectorAll(".operations-section")
        .forEach(el =>
            el.classList.remove("active-section")
        );

    document
        .getElementById(section + "Section")
        .classList.add("active-section");

    document
        .querySelectorAll(".tracker-btn")
        .forEach(btn =>
            btn.classList.remove("active")
        );

    document
        .getElementById(section + "ToolbarBtn")
        ?.classList.add("active");

    updateKpis(section);

    if (section === "support") {

        buildFilters("support");

        if (
            !document.querySelector(
                "#supportTableBody tr"
            )
        ) {
            await loadSupportEmails();
        }

    } else if (section === "failure") {

        buildFilters("failure");

        if (
            !document.querySelector(
                "#failureTableBody tr"
            )
        ) {
            await loadIntegrationFailures();
        }

    } else if (section === "dashboard") {

        updateDashboardCounts();

    } else {

        buildFilters(section);
    }
}

// ─────────────────────────────────────────────
//  DASHBOARD OVERVIEW — update counts from live data
// ─────────────────────────────────────────────
function updateDashboardCounts() {

    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    if (window.supportData) {
        set("dash-support-count", window.supportData.length);
        const pending = window.supportData.filter(
            x => String(x.category || "").includes("Action Required")
        ).length;
        set("dash-pending-actions",
            pending + " pending action" + (pending !== 1 ? "s" : ""));
    }

    if (window.failureData) {
        set("dash-failure-count", window.failureData.length);
    }

    if (window.incidentData) {
        set("dash-incident-count", window.incidentData.length);
    }

    if (window.azureData) {
        set("dash-azure-count", window.azureData.length);
    }

    if (window.ptcData) {
        set("dash-ptc-count", window.ptcData.length);
    }
}

function passesDateFilter(rowDate) {

    const filterType =
        document.getElementById(
            "dateFilterType"
        )?.value || "none";

    if(filterType === "none"){
        return true;
    }

    const recordDate =
        new Date(
            rowDate.replace(
                " ",
                "T"
            )
        );

    if(isNaN(recordDate)){
        return true;
    }

    if(filterType === "range"){

        const start =
            document.getElementById(
                "startDate"
            )?.value;

        const end =
            document.getElementById(
                "endDate"
            )?.value;

        if(start){

            if(
                recordDate <
                new Date(start)
            ){
                return false;
            }
        }

        if(end){

            const endDate =
                new Date(end);

            endDate.setHours(
                23,59,59,999
            );

            if(
                recordDate >
                endDate
            ){
                return false;
            }
        }

        return true;
    }

    if(filterType === "quick"){

        const days =
            parseInt(
                document.getElementById(
                    "quickDateFilter"
                )?.value || 0
            );

        const today =
            new Date();

        const cutoff =
            new Date();

        cutoff.setDate(
            today.getDate() - days
        );

        return recordDate >= cutoff;
    }

    return true;
}

function applyFilters() {

    
    const activeSection =
        document.querySelector(
            ".operations-section.active-section"
        );

    if (!activeSection) return;

    const sectionId =
        activeSection.id;

    const rows =
        activeSection.querySelectorAll(
            "tbody tr"
        );

    let visibleCount = 0;

    rows.forEach(row => {

        let visible = true;

        // SUPPORT
        if (sectionId === "supportSection") {

            const rowDate =
                row.cells[0].innerText.trim();

            if(
                !passesDateFilter(rowDate)
            ){
                visible = false;
            }
            const importance =
                row.cells[3].innerText.trim();

            const category =
                row.cells[4].innerText.trim();

            const importanceFilter =
                document.getElementById(
                    "supportImportanceFilter"
                )?.value || "All";

            const categoryFilter =
                document.getElementById(
                    "supportCategoryFilter"
                )?.value || "All";

            if (
                importanceFilter !== "All" &&
                importance !== importanceFilter
            ) {
                visible = false;
            }

            if (
                categoryFilter !== "All"
            ) {

                const categories =
                    category
                        .split(",")
                        .map(v => v.trim());

                if (
                    !categories.includes(
                        categoryFilter
                    )
                ) {
                    visible = false;
                }
            }
        }

        // FAILURES
        else if (
            sectionId === "failureSection"
        ) {

            const rowDate =
                row.cells[0].innerText.trim();

            if(
                !passesDateFilter(rowDate)
            ){
                visible = false;
            }
            const environment =
                row.cells[4].innerText.trim();

            const server =
                row.cells[5].innerText.trim();

            const environmentFilter =
                document.getElementById(
                    "failureEnvironmentFilter"
                )?.value || "All";

            const serverFilter =
                document.getElementById(
                    "failureServerFilter"
                )?.value || "All";

            if (
                environmentFilter !== "All" &&
                environment !== environmentFilter
            ) {
                visible = false;
            }

            if (
                serverFilter !== "All" &&
                server !== serverFilter
            ) {
                visible = false;
            }
        }

        // INCIDENTS
        else if (
            sectionId === "incidentSection"
        ) {

            const rowDate =
                row.cells[6].innerText.trim();

            if(
                !passesDateFilter(rowDate)
            ){
                visible = false;
            }

            const status =
                row.cells[4].innerText.trim();

            const priority =
                row.cells[5].innerText.trim();

            const statusFilter =
                document.getElementById(
                    "incidentStatusFilter"
                )?.value || "All";

            const priorityFilter =
                document.getElementById(
                    "incidentPriorityFilter"
                )?.value || "All";

            if (
                statusFilter !== "All" &&
                status !== statusFilter
            ) {
                visible = false;
            }

            if (
                priorityFilter !== "All" &&
                priority !== priorityFilter
            ) {
                visible = false;
            }
        }

        // AZURE
        else if (
            sectionId === "azureSection"
        ) {

            const rowDate =
                row.cells[6].innerText.trim();

            if(
                !passesDateFilter(rowDate)
            ){
                visible = false;
            }
            const status =
                row.cells[3].innerText.trim();

            const createdBy =
                row.cells[5].innerText.trim();

            const statusFilter =
                document.getElementById(
                    "azureStatusFilter"
                )?.value || "All";

            const createdByFilter =
                document.getElementById(
                    "azureCreatedByFilter"
                )?.value || "All";

            if (
                statusFilter !== "All" &&
                status !== statusFilter
            ) {
                visible = false;
            }

            if (
                createdByFilter !== "All" &&
                createdBy !== createdByFilter
            ) {
                visible = false;
            }
        }

        // PTC
        else if (
            sectionId === "ptcSection"
        ) {

            const rowDate =
                row.cells[6].innerText.trim();

            if(
                !passesDateFilter(rowDate)
            ){
                visible = false;
            }

            const status =
                row.cells[3].innerText.trim();

            const createdBy =
                row.cells[5].innerText.trim();

            const statusFilter =
                document.getElementById(
                    "ptcStatusFilter"
                )?.value || "All";

            const createdByFilter =
                document.getElementById(
                    "ptcCreatedByFilter"
                )?.value || "All";

            if (
                statusFilter !== "All" &&
                status !== statusFilter
            ) {
                visible = false;
            }

            if (
                createdByFilter !== "All" &&
                createdBy !== createdByFilter
            ) {
                visible = false;
            }
        }

        row.style.display =
            visible ? "" : "none";

        if (visible) {
            visibleCount++;
        }

    });

    updateStatus(
        visibleCount +
        " records found"
    );
}


// Disabled for Outlook mode
/*
setInterval(() => {

    refreshOperationsData();

}, 300000);
*/

async function loadIncidentTracker() {

    try {

        const response =
            await fetch(
                "/api/operations-center/refresh"
            );

        const result =
            await response.json();

        if (!result.success) {

            updateProcessingStatus(
                "Failed",
                result.message || "Unable to load failures",
                "failed"
            );

            return;
        }

        const incidentData =
            result.incident_data || [];

        const tbody =
            document.querySelector(
                "#incidentSection tbody"
            );

        if (!tbody) {
            return;
        }

        tbody.innerHTML = "";

        incidentData.forEach(row => {

            tbody.innerHTML += `

                <tr>

                    <td>${row["Number"] || ""}</td>

                    <td>${row["Vendor Ticket"] || ""}</td>

                    <td>${row["Description"] || ""}</td>

                    <td>${row["Assigned To"] || ""}</td>

                    <td>${row["Status"] || ""}</td>

                    <td>${row["Priority"] || ""}</td>

                    <td>${row["Created Date"] || ""}</td>

                </tr>

            `;
        });

        updateStatus(
            incidentData.length +
            " incidents found"
        );

    }

    catch(error) {

        console.error(error);

        updateStatus(
            "Incident load failed"
        );
    }
}

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        loadRefreshStatus();

        // Register apply-filters button
        const applyBtn =
            document.querySelector(
                ".btn-apply-filters"
            );

        if (applyBtn) {

            applyBtn.addEventListener(
                "click",
                applyFilters
            );
        }

        // Show Dashboard tab by default — do NOT load support/failures
        // Those are loaded lazily when the user clicks their tab.
        await showSection("dashboard");
    }
);



async function loadRefreshStatus() {

    try {

        const response = await fetch(
            "/api/refresh-status"
        );

        const data = await response.json();

        const el =
            document.getElementById(
                "lastRefreshTime"
            );

        if (el) {

            el.textContent =
                `Last Refresh: ${data.last_refresh}`;
        }

    } catch (err) {

        console.error(err);
    }
}

window.clearWorkspace = function () {

    // reset dropdowns
    document
        .querySelectorAll(".sidebar-filter")
        .forEach(filter => {
            filter.value = "All";
        });

    document
        .querySelectorAll(
            '.sidebar-date'
        )
        .forEach(input => {

            input.value = '';

        });

    const type =
        document.getElementById(
            "dateFilterType"
        );

    if(type){
        type.value = "none";
    }
    
    const range =
        document.getElementById(
            "dateRangeSection"
        );

    const quick =
        document.getElementById(
            "quickDateSection"
        );

    if(range){
        range.style.display = "none";
    }

    if(quick){
        quick.style.display = "none";
    }    
    

    // show all rows in current tracker
    document
        .querySelectorAll(
            ".operations-section tbody tr"
        )
        .forEach(row => {
            row.style.display = "";
        });

    updateProcessingStatus(
        "Ready",
        "",
        "completed"
    );

    console.log(
        "Operations Center workspace cleared"
    );
};


async function loadSupportEmails() {

    try {

        updateProcessingStatus(
            "Support Emails",
            "Connecting to Outlook...",
            "processing"
        );

        const response =
            await fetch(
                "/api/operations-center/support-emails"
            );

        const result =
            await response.json();
        
        console.log("SUPPORT EMAIL SAMPLE:", result.data[0]);
        console.log("SUPPORT EMAIL COUNT:", result.data.length);

        if (!result.success) {

            updateStatus(
                result.message
            );

            return;
        }

        const tbody =
            document.getElementById(
                "supportTableBody"
            );

        if (!tbody) return;

        tbody.innerHTML = "";

        let pendingCount = 0;

        result.data.forEach(row => {

            if (
                row.category &&
                row.category.includes(
                    "Action Required"
                )
            ) {
                pendingCount++;
            }

            tbody.innerHTML += `

                <tr>

                    <td>${row.date_received || ""}</td>

                    <td>${row.name || ""}</td>

                    <td>${row.subject || ""}</td>

                    <td>${row.importance || ""}</td>

                    <td>${row.category || ""}</td>

                </tr>

            `;
        });

        const supportCard =
            document.getElementById(
                "supportCountCard"
            );

        if (supportCard) {

            supportCard.innerText =
                result.data.length;
        }

        const pendingCard =
            document.getElementById(
                "pendingActionCard"
            );

        if (pendingCard) {

            pendingCard.innerText =
                pendingCount;
        }

        updateProcessingStatus(
            "Completed",
            result.data.length +
            " support emails loaded",
            "completed"
        );

        window.supportData = result.data || [];
        
        console.log(
            "WINDOW SUPPORT DATA:",
            window.supportData
        );
        
        if (
            document
                .getElementById("supportSection")
                .classList.contains("active-section")
        ) {

            buildFilters("support");
        }
        updateKpis("support");

        if (
            document
                .getElementById("supportSection")
                .classList.contains("active-section")
        ) {
            buildFilters("support");
        }
    }

    catch(error) {

        console.error(error);

        updateProcessingStatus(
            "Failed",
            "Support email load failed",
            "failed"
        );
    }
}



async function loadIntegrationFailures() {

    try {

        updateProcessingStatus(
            "Integration Failures",
            "Loading RAPID / ODC failures...",
            "processing"
        );

        const response =
            await fetch(
                "/api/operations-center/integration-failures"
            );

        const result =
            await response.json();

        if (!result.success) {

            updateProcessingStatus(
                "Failed",
                result.message ||
                "Unable to load failures",
                "failed"
            );
            
            return;
        }

        const tbody =
            document.getElementById(
                "failureTableBody"
            );

        if (!tbody) return;

        tbody.innerHTML = "";

        result.data.forEach(row => {

            tbody.innerHTML += `

                <tr>

                    <td>${row["Failure Time"] || ""}</td>

                    <td>${row["Integration"] || ""}</td>

                    <td>${row["Object Number"] || ""}</td>

                    <td>${row["Error Message"] || ""}</td>

                    <td>${row["Environment"] || ""}</td>

                    <td>${row["Windchill Server"] || ""}</td>

                </tr>

            `;

        });

        updateProcessingStatus(
            "Completed",
            result.data.length +
            " integration failures loaded",
            "completed"
        );


        populateFailureFiltersFromTable();

        if (
            document
                .getElementById("failureSection")
                .classList.contains("active-section")
        ) {

            buildFilters("failure");

            populateFailureFiltersFromTable();
        }
    }

    catch(error) {

        console.error(error);

        updateProcessingStatus(
            "Failed",
            "Integration failure load failed",
            "failed"
        );
    }
}

function populateFailureFiltersFromTable() {

    const envSet = new Set();
    const serverSet = new Set();

    document
        .querySelectorAll(
            "#failureTableBody tr"
        )
        .forEach(row => {

            envSet.add(
                row.cells[4].innerText.trim()
            );

            serverSet.add(
                row.cells[5].innerText.trim()
            );
        });

    const envDropdown =
        document.getElementById(
            "failureEnvironmentFilter"
        );

    const serverDropdown =
        document.getElementById(
            "failureServerFilter"
        );

    if(envDropdown){

        envDropdown.innerHTML =
            '<option value="All">All</option>';

        [...envSet]
            .sort()
            .forEach(env => {

                envDropdown.innerHTML +=
                    `<option value="${env}">
                        ${env}
                    </option>`;
            });
    }

    if(serverDropdown){

        serverDropdown.innerHTML =
            '<option value="All">All</option>';

        [...serverSet]
            .sort()
            .forEach(server => {

                serverDropdown.innerHTML +=
                    `<option value="${server}">
                        ${server}
                    </option>`;
            });
    }
}

function exportCurrentViewCSV() {

    const activeSection =
        document.querySelector(
            ".operations-section.active-section"
        );

    if(!activeSection) {
        return;
    }

    const table =
        activeSection.querySelector(
            "table"
        );

    if(!table) {
        return;
    }

    let csv = [];

    table.querySelectorAll("tr")
        .forEach(row => {

            let rowData = [];

            row.querySelectorAll("th,td")
                .forEach(cell => {

                    rowData.push(
                        '"' +
                        cell.innerText
                            .replace(/"/g,'""') +
                        '"'
                    );

                });

            csv.push(
                rowData.join(",")
            );
        });

    const blob =
        new Blob(
            [csv.join("\n")],
            {type:"text/csv"}
        );

    const url =
        URL.createObjectURL(blob);

    const a =
        document.createElement("a");

    a.href = url;

    a.download =
        "operations_export.csv";

    document.body.appendChild(a);

    a.click();

    document.body.removeChild(a);
}

async function exportCurrentViewXLSX() {

    try {

        const activeSection =
            document.querySelector(
                ".operations-section.active-section"
            );

        if (!activeSection) {

            alert(
                "No active tracker found."
            );

            return;
        }

        const tracker =
            activeSection.id
                .replace("Section", "");

        const table =
            activeSection.querySelector(
                "table"
            );

        const headers = [];

        table.querySelectorAll(
            "thead th"
        ).forEach(th => {

            headers.push(
                th.innerText.trim()
            );

        });

        const rows = [];

        table.querySelectorAll(
            "tbody tr"
        ).forEach(tr => {

            if (
                tr.style.display === "none"
            ) {
                return;
            }

            const row = {};

            tr.querySelectorAll("td")
                .forEach(
                    (td, index) => {

                        row[
                            headers[index]
                        ] =
                            td.innerText.trim();

                    }
                );

            rows.push(row);

        });

        if (rows.length === 0) {

            alert(
                "No records to export."
            );

            return;
        }

        updateStatus(
            "Creating Excel export..."
        );

        const response =
            await fetch(
                "/api/operations-center/export",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                        "application/json"
                    },

                    body: JSON.stringify({

                        tracker: tracker,

                        rows: rows

                    })
                }
            );

        if (!response.ok) {

            const msg = await response.text();

            throw new Error(msg);
        }

        const blob = await response.blob();

        const url =
            window.URL.createObjectURL(
                blob
            );

        const a =
            document.createElement("a");

        a.href = url;

        a.download =
            `${tracker}.xlsx`;

        document.body.appendChild(a);

        a.click();

        a.remove();

        window.URL.revokeObjectURL(
            url
        );

        updateStatus(
            rows.length +
            " rows exported"
        );

    }

    catch(error) {

        console.error(error);

        updateStatus(
            "Export failed"
        );
    }
}