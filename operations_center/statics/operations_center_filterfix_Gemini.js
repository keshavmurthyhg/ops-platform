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
    // Update sidebar text labels (common main.html IDs)
    const status  = document.getElementById("statusMessage");
    const text    = document.getElementById("progressText");
    const fill    = document.getElementById("progressFill");
    const wrapper = document.getElementById("progressWrapper");

    if (status) status.innerText = message;
    if (text)   text.innerText   = detail;

    if (!fill || !wrapper) return;

    // Remove prior state classes
    fill.classList.remove("ops-bar-processing", "ops-bar-completed", "ops-bar-failed");

    if (state === "processing") {
        wrapper.classList.remove("hidden");
        fill.style.width = "70%";
        fill.style.background = "";
        fill.classList.add("ops-bar-processing");

    } else if (state === "completed") {
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.style.background = "";
        fill.classList.add("ops-bar-completed");
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.classList.remove("ops-bar-completed");
        }, 2000);

    } else {
        // error / failed
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.style.background = "";
        fill.classList.add("ops-bar-failed");
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.classList.remove("ops-bar-failed");
        }, 3000);
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

// =============================================================================
//  OPS CENTER — DETAIL PANEL (slide-over dashboard)
//  opsOpenDetail(section) slides the detail panel over the dashboard.
//  opsCloseDetail() restores the dashboard view.
//  opsShowDashboard() resets to dashboard (toolbar Dashboard button).
// =============================================================================

// KPI bar definitions per section
const OPS_KPI_DEFS = {
    support: (d) => [
        { label: "Total", val: (d||[]).length, color: "#3b82f6" },
        { label: "Pending Actions", val: (d||[]).filter(x=>String(x["Categories"]||x["Category"]||x.category||"").includes("Action Required")).length, color: "#ef4444" },
    ],
    failure: (d) => [
        { label: "Total Failed", val: (d||[]).length, color: "#ef4444" },
        ...Object.entries((d||[]).reduce((a,r)=>{a[r.Target||r.integration||"?"]=(a[r.Target||r.integration||"?"]||0)+1;return a},{}))
              .sort((a,b)=>b[1]-a[1]).slice(0,4)
              .map(([k,v])=>({label:k, val:v, color:"#f97316"}))
    ],
    incident: (d) => [
        { label: "Total", val: (d||[]).length, color: "#f28c38" },
        { label: "On Hold", val: (d||[]).filter(r=>r.Status==="On Hold").length, color: "#ef4444" },
        { label: "In Progress", val: (d||[]).filter(r=>r.Status==="In Progress").length, color: "#f59e0b" },
        { label: "Working", val: (d||[]).filter(r=>r.Status==="Working").length, color: "#22c55e" },
    ],
    azure: (d) => [
        { label: "Total", val: (d||[]).length, color: "#0ea5e9" },
        { label: "New", val: (d||[]).filter(r=>r.Status==="New").length, color: "#3b82f6" },
        { label: "Active", val: (d||[]).filter(r=>r.Status==="Active").length, color: "#f59e0b" },
        { label: "Resolved", val: (d||[]).filter(r=>r.Status==="Resolved").length, color: "#22c55e" },
    ],
    ptc: (d) => [
        { label: "Total", val: (d||[]).length, color: "#8b5cf6" },
        { label: "Info Received", val: (d||[]).filter(r=>r.Status==="Information Received").length, color: "#f59e0b" },
        { label: "SPR Filed", val: (d||[]).filter(r=>r.Status==="SPR Filed").length, color: "#3b82f6" },
        { label: "Closed", val: (d||[]).filter(r=>r.Status==="Closed").length, color: "#22c55e" },
    ],
};

// Data map: section name → window data variable
const OPS_DATA_MAP = {
    support: () => window.supportData,
    failure: () => window.failureData,
    incident: () => window.incidentData,
    azure: () => window.azureData,
    ptc: () => window.ptcData,
};

let _opsCurrentDetail = null;

function opsShowDashboard() {
    const panel = document.getElementById("opsDetailPanel");
    const dash  = document.getElementById("opsDashboard");
    if (panel) { panel.classList.add("ops-detail-hidden"); panel.classList.remove("ops-detail-visible"); }
    if (dash)  { dash.style.opacity = "1"; dash.style.pointerEvents = ""; }
    // Highlight dashboard tab, deactivate others
    document.querySelectorAll(".tracker-btn").forEach(b => b.classList.remove("active"));
    const db = document.getElementById("dashboardToolbarBtn");
    if (db) db.classList.add("active");
    _opsCurrentDetail = null;
}

async function opsOpenDetail(section) {
    _opsCurrentDetail = section;

    // ── 1. Build KPI chip bar ─────────────────────────────────────────────
    const data   = OPS_DATA_MAP[section] ? OPS_DATA_MAP[section]() : null;
    const kpiFn  = OPS_KPI_DEFS[section];
    const kpiBar = document.getElementById("opsDetailKpiBar");
    if (kpiBar && kpiFn) {
        kpiBar.innerHTML = kpiFn(data).map(k =>
            `<div class="ops-dkpi-chip" style="border-color:${k.color};color:${k.color};">
                <span class="ops-dkpi-val">${k.val}</span>
                <span class="ops-dkpi-lbl">${k.label}</span>
             </div>`
        ).join("");
    }

    // ── 2. Hide all table wraps, show the right one ───────────────────────
    document.querySelectorAll(".ops-detail-table-wrap")
            .forEach(el => el.style.display = "none");
    const key       = section.charAt(0).toUpperCase() + section.slice(1);
    const tableWrap = document.getElementById("opsDetail" + key);
    if (tableWrap) tableWrap.style.display = "";

    // ── 3. Render rows directly from window data (always fresh) ──────────
    _opsRenderTable(section, data);

    // ── 4. Slide panel in over dashboard ─────────────────────────────────
    const panel = document.getElementById("opsDetailPanel");
    const dash  = document.getElementById("opsDashboard");
    if (panel) { panel.classList.remove("ops-detail-hidden"); panel.classList.add("ops-detail-visible"); }
    if (dash)  { dash.style.opacity = "0.3"; dash.style.pointerEvents = "none"; }

    // ── 5. Highlight the active tab ───────────────────────────────────────
    document.querySelectorAll(".tracker-btn").forEach(b => b.classList.remove("active"));
    const tabBtn = document.getElementById(section + "ToolbarBtn");
    if (tabBtn) tabBtn.classList.add("active");
}

// ─────────────────────────────────────────────────────────────────────────────
//  _opsRenderTable — renders window.*Data into the correct tbody.
//  All 5 sections use window data set by Jinja tojson in page_js block.
//  Called every time a tab is clicked so data stays fresh after Refresh Data.
// ─────────────────────────────────────────────────────────────────────────────
function _opsRenderTable(section, data) {
    if (!data || data.length === 0) return;

    // Helper: escape quotes in title attributes
    const esc = s => (s || "").toString().replace(/"/g, "&quot;");
    const pill = s => `<span class="ops-status-pill ops-status-${(s||"").toLowerCase().replace(/ /g,"-")}">${s||""}</span>`;
    const link = (url, txt) => url ? `<a href="${url}" target="_blank" class="number-link">${txt||""}</a>` : (txt||"");
    const desc = s => `<div class="desc-cell" title="${esc(s)}">${s||""}</div>`;

    if (section === "support") {
        const tbody = document.getElementById("supportTableBody");
        if (!tbody) return;
        // window.supportData from Jinja has Excel column names: "Date Received", "Name", etc.
        // Outlook API data uses lowercase: date_received, name, subject, importance, category
        tbody.innerHTML = data.map(r => `<tr>
            <td>${r["Date Received"] || r.date_received || ""}</td>
            <td>${r["Name"]          || r.name          || ""}</td>
            <td>${desc(r["Subject"]  || r.subject       || "")}</td>
            <td>${r["Importance"]    || r.importance     || ""}</td>
            <td>${r["Categories"]    || r["Category"]   || r.category || ""}</td>
        </tr>`).join("");

    } else if (section === "failure") {
        const tbody = document.getElementById("failureTableBody");
        if (!tbody) return;
        tbody.innerHTML = data.map(r => `<tr>
            <td>${r["Failure Time"] || r.failure_time || ""}</td>
            <td>${r["Integration"]  || r.integration  || r["Target"] || ""}</td>
            <td>${r["Object Number"]|| r.object_number|| r["Object"] || ""}</td>
            <td>${desc(r["Error Message"] || r.error_message || r["Notes"] || "")}</td>
            <td>${r["Environment"]  || r.environment  || ""}</td>
            <td>${r["Windchill Server"] || r.wc_server || r["Status"] || ""}</td>
        </tr>`).join("");

    } else if (section === "incident") {
        const tbody = document.getElementById("opsIncidentTableBody");
        if (!tbody) return;
        tbody.innerHTML = data.map(r => `<tr>
            <td>${link(r.number_url, r.Number)}</td>
            <td>${link(r.vendor_ticket_url, r["Vendor Ticket"])}</td>
            <td>${desc(r.Description)}</td>
            <td>${r["Assigned To"] || ""}</td>
            <td>${pill(r.Status)}</td>
            <td>${r.Priority || ""}</td>
            <td>${r["Created Date"] || ""}</td>
        </tr>`).join("");

    } else if (section === "azure") {
        const tbody = document.getElementById("opsAzureTableBody");
        if (!tbody) return;
        tbody.innerHTML = data.map(r => `<tr>
            <td>${link(r.number_url, r.Number)}</td>
            <td>${desc(r.Description)}</td>
            <td>${r["Assigned To"] || ""}</td>
            <td>${pill(r.Status)}</td>
            <td>${r.Priority || ""}</td>
            <td>${r["Created By"] || ""}</td>
            <td>${r["Created Date"] || ""}</td>
        </tr>`).join("");

    } else if (section === "ptc") {
        const tbody = document.getElementById("opsPtcTableBody");
        if (!tbody) return;
        tbody.innerHTML = data.map(r => `<tr>
            <td>${link(r.number_url, r.Number)}</td>
            <td>${desc(r.Description)}</td>
            <td>${r["Assigned To"] || ""}</td>
            <td>${pill(r.Status)}</td>
            <td>${r.Priority || ""}</td>
            <td>${r["Created By"] || ""}</td>
            <td>${r["Created Date"] || ""}</td>
        </tr>`).join("");
    }
}

function opsCloseDetail() { opsShowDashboard(); }

// Legacy showSection alias — used by remaining code references
// ── KPI chip definitions injected above each table ───────────────────────────
const OPS_KPIS = {
    support:  () => [
        { val: (window.supportData||[]).length, label: "Total", color: "#3b82f6" },
        { val: (window.supportData||[]).filter(x=>String(x["Categories"]||x["Category"]||x.category||"").includes("Action Required")).length, label: "Pending Actions", color: "#ef4444" }
    ],
    failure:  () => [
        { val: (window.failureData||[]).length, label: "Total Failed", color: "#ef4444" },
        { val: (window.failureData||[]).filter(x=>(x["Environment"]||x.environment||"").toUpperCase()==="PROD").length, label: "PROD", color: "#f59e0b" }
    ],
    incident: () => [
        { val: (window.incidentData||[]).length, label: "Total", color: "#f28c38" },
        { val: (window.incidentData||[]).filter(x=>x.Status==="On Hold").length, label: "On Hold", color: "#ef4444" },
        { val: (window.incidentData||[]).filter(x=>x.Status==="In Progress").length, label: "In Progress", color: "#3b82f6" }
    ],
    azure:    () => [
        { val: (window.azureData||[]).length, label: "Total", color: "#0ea5e9" },
        { val: (window.azureData||[]).filter(x=>x.Status==="New").length, label: "New", color: "#8b5cf6" },
        { val: (window.azureData||[]).filter(x=>x.Status==="Active").length, label: "Active", color: "#22c55e" },
        { val: (window.azureData||[]).filter(x=>x.Status==="Resolved").length, label: "Resolved", color: "#6b7280" }
    ],
    ptc:      () => [
        { val: (window.ptcData||[]).length, label: "Total", color: "#8b5cf6" },
        { val: (window.ptcData||[]).filter(x=>x.Status==="Information Received").length, label: "Info Received", color: "#f59e0b" },
        { val: (window.ptcData||[]).filter(x=>x.Status==="Closed").length, label: "Closed", color: "#6b7280" }
    ]
};

function renderKpiBar(section) {
    const bar = document.getElementById(section + "KpiBar");
    if (!bar) return;
    const fn = OPS_KPIS[section];
    if (!fn) { bar.innerHTML = ""; return; }
    bar.innerHTML = fn().map(k =>
        `<div class="ops-kpi-chip" style="color:${k.color};border-color:${k.color};">
            <span class="ops-kpi-chip-val">${k.val}</span>
            <span class="ops-kpi-chip-lbl">${k.label}</span>
         </div>`
    ).join("");
}


async function showSection(section) {
    // ── 1. Hide ALL sections (with slide-out animation) ───────────────────
    document.querySelectorAll(".operations-section").forEach(el => {
        if (el.style.display === "flex") {
            el.classList.add("ops-section-hiding");
            setTimeout(() => {
                el.style.display = "none";
                el.classList.remove("ops-section-hiding", "ops-section-visible");
            }, 260);
        } else {
            el.style.display = "none";
            el.classList.remove("ops-section-hiding", "ops-section-visible");
        }
    });

    // ── 2. Highlight toolbar tab ──────────────────────────────────────────
    document.querySelectorAll(".tracker-btn").forEach(b => b.classList.remove("active"));
    const btn = document.getElementById(section + "ToolbarBtn");
    if (btn) btn.classList.add("active");

    // ── 3. Show target section with slide-in ─────────────────────────────
    const sec = document.getElementById(section + "Section");
    if (sec) {
        sec.style.display = "flex";
        // Force reflow then add visible class for transition
        requestAnimationFrame(() => {
            requestAnimationFrame(() => sec.classList.add("ops-section-visible"));
        });
    }

    if (section === "dashboard") {
        updateDashboardCounts();
        return;
    }

    // ── 4. KPI chips ──────────────────────────────────────────────────────
    renderKpiBar(section);

    // ── 5. Build sidebar filters ──────────────────────────────────────────
    buildFilters(section);

    // ── 6. Load data (lazy for support/failure) ───────────────────────────
    if (section === "support") {
        if (!document.querySelector("#supportTableBody tr")) {
            await loadSupportEmails();
            return;   // loadSupportEmails calls buildFilters + applyFilters internally
        }
    } else if (section === "failure") {
        if (!document.querySelector("#failureTableBody tr")) {
            await loadIntegrationFailures();
            buildFilters("failure");
            applyFilters();
            return;
        }
        populateServerDropdown();
    }

    // ── 7. Apply sidebar filters ──────────────────────────────────────────
    applyFilters();
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
                            getUniqueValues((window.supportData||[]).map(r=>({importance:r.importance||r["Importance"]||""})),"importance")
                        )}

                    </select>

                    <div class="filter-label">
                        Category
                    </div>

                    <select
                        id="supportCategoryFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues((window.supportData||[]).map(r=>({category:r.category||r["Category"]||r["Categories"]||""})),"category")
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

function applyFilters() {

    
    const activeSection =
        document.querySelector(
            ".operations-section[style*=\"display:flex\"]:not(#dashboardSection)"
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
                .style.display === "flex"
        ) {
            buildFilters("support");
            applyFilters();
        }
        updateKpis("support");
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
                .style.display === "flex"
        ) {
            buildFilters("failure");
            populateFailureFiltersFromTable();
            applyFilters();
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
            ".operations-section[style*=\"display:flex\"]:not(#dashboardSection)"
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
                ".operations-section[style*=\"display:flex\"]:not(#dashboardSection)"
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