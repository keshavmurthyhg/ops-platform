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
        // Multi-vendor ticket: "18088970, 18095807" → individual PTC links
        const ptcLinks = (tickets) => {
            if (!tickets || !tickets.trim()) return "";
            return tickets.split(/[,;]/).map(t => t.trim()).filter(Boolean).map(t =>
                `<a href="https://support.ptc.com/appserver/cs/view/support.jsp?n=${t}"
                    target="_blank" class="number-link" title="PTC Case ${t}">${t}</a>`
            ).join(" · ");
        };
        tbody.innerHTML = data.map(r => `<tr>
            <td>${link(r.number_url, r.Number)}</td>
            <td>${ptcLinks(r["Vendor Ticket"] || "")}</td>
            <td>${desc(r.Description)}</td>
            <td>${r["Assigned To"] || ""}</td>
            <td>${pill(r.Status)}</td>
            <td>${r.Priority || ""}</td>
            <td>${r["Created Date"] || ""}</td>
        </tr>`).join("");

    } else if (section === "azure") {
        const tbody = document.getElementById("opsAzureTableBody");
        if (!tbody) return;
        const typePill = (t) => {
            const cls = (t||"").toLowerCase().includes("story") ? "pill-story" : "pill-bug";
            return `<span class="ops-type-pill ${cls}">${t||"Bug"}</span>`;
        };
        tbody.innerHTML = data.map(r => `<tr>
            <td>${link(r.number_url, r.Number)}</td>
            <td>${typePill(r.item_type)}</td>
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
// ── KPI System: Total is FIXED (full dataset), others are DYNAMIC (visible rows) ──
// _kpiCountVisible(section, matchFn) = count tbody rows that are shown AND match fn
function _visibleRows(section) {
    const sec = document.querySelector(".operations-section[data-active='true']");
    if (!sec) return [];
    return [...sec.querySelectorAll("tbody tr")].filter(r => r.style.display !== "none");
}

function _cellText(row, idx) {
    return (row.cells[idx] ? row.cells[idx].innerText.trim() : "");
}

// For each section: { total: fn(fullData), chips: [{label,color,col,match}] }
// col = column index in the rendered table for dynamic counting
const OPS_KPI_CONFIG = {
    support: {
        total: () => (window.supportData||[]).length,
        totalLabel: "Total", totalColor: "#3b82f6",
        chips: [
            { label: "Pending Actions", color: "#ef4444",
              match: r => _cellText(r,4).toLowerCase().includes("action required") }
        ]
    },
    failure: {
        total: () => (window.failureData||[]).length,
        totalLabel: "Total Failed", totalColor: "#ef4444",
        chips: [
            { label: "PROD",    color: "#f59e0b", match: r => _cellText(r,4).toUpperCase()==="PROD" },
            { label: "DEVC",    color: "#3b82f6", match: r => ["DEVC","DEVA"].includes(_cellText(r,4).toUpperCase()) },
            { label: "DEVB",    color: "#8b5cf6", match: r => _cellText(r,4).toUpperCase()==="DEVB" },
            { label: "Unknown", color: "#6b7280", match: r => ["UNKNOWN",""].includes(_cellText(r,4).toUpperCase()) }
        ]
    },
    incident: {
        total: () => (window.incidentData||[]).length,
        totalLabel: "Total", totalColor: "#f28c38",
        chips: [
            { label: "On Hold",     color: "#ef4444", match: r => _cellText(r,4)==="On Hold" },
            { label: "In Progress", color: "#3b82f6", match: r => _cellText(r,4)==="In Progress" },
            { label: "Resolved",    color: "#16a34a", match: r => _cellText(r,4)==="Resolved" },
            { label: "Closed",      color: "#6b7280", match: r => _cellText(r,4)==="Closed" },
            { label: "Cancelled",   color: "#9ca3af", match: r => _cellText(r,4)==="Cancelled" }
        ]
    },
    azure: {
        total: () => (window.azureData||[]).length,
        totalLabel: "Total", totalColor: "#0ea5e9",
        chips: [
            { label: "Bugs",         color: "#dc2626", match: r => !_cellText(r,1).toLowerCase().includes("story") },
            { label: "User Stories", color: "#2563eb", match: r => _cellText(r,1).toLowerCase().includes("story") },
            { label: "New",          color: "#8b5cf6", match: r => _cellText(r,4)==="New" },
            { label: "Active",       color: "#22c55e", match: r => _cellText(r,4)==="Active" },
            { label: "Resolved",     color: "#16a34a", match: r => _cellText(r,4)==="Resolved" },
            { label: "Closed",       color: "#6b7280", match: r => _cellText(r,4)==="Closed" }
        ]
    },
    ptc: {
        total: () => (window.ptcData||[]).length,
        totalLabel: "Total", totalColor: "#8b5cf6",
        chips: [
            { label: "On Hold",       color: "#ef4444", match: r => _cellText(r,3)==="On Hold" },
            { label: "Info Received", color: "#f59e0b", match: r => _cellText(r,3)==="Information Received" },
            { label: "In Progress",   color: "#3b82f6", match: r => ["In Progress","Active","Approved","Committed"].includes(_cellText(r,3)) },
            { label: "Closed",        color: "#6b7280", match: r => _cellText(r,3)==="Closed" },
            { label: "Cancelled",     color: "#9ca3af", match: r => _cellText(r,3)==="Cancelled" }
        ]
    }
};

// Legacy OPS_KPIS reference kept to avoid any stale calls
const OPS_KPIS = {
    support:  () => [],
    failure:  () => [],
    incident: () => [],
    azure:    () => [],
    ptc:      () => []
};

// ── Group filter helper ───────────────────────────────────────────────────────
// Reads user_group_mapping from server or localStorage
var _OPS_GROUP_MAP = {};   // { "Pradnya Shinde": "TEAM_A", ... }

async function _loadGroupMap() {
    try {
        const r = await fetch("/api/operations-center/user-groups");
        if (r.ok) {
            const d = await r.json();
            _OPS_GROUP_MAP = d.groups || {};
        }
    } catch(e) {}
}
_loadGroupMap();

function buildGroupOptions(data) {
    // Collect unique groups from current data via group map
    const groups = new Set(["All"]);
    data.forEach(function(r) {
        const cb = r["Created By"] || "";
        const grp = _OPS_GROUP_MAP[cb] || "";
        if (grp) groups.add(grp);
    });
    return [...groups].map(function(g) {
        return `<option value="${g}">${g}</option>`;
    }).join("");
}

function _getGroupFor(name) {
    return _OPS_GROUP_MAP[name] || "";
}

function renderKpiBar(section) {
    const bar = document.getElementById(section + "KpiBar");
    if (!bar) return;
    const cfg = OPS_KPI_CONFIG[section];
    if (!cfg) { bar.innerHTML = ""; return; }

    // Total chip — FIXED, always shows full dataset size
    let html = `<div class="ops-kpi-chip ops-kpi-chip-total" style="color:${cfg.totalColor};border-color:${cfg.totalColor};">
        <span class="ops-kpi-chip-val">${cfg.total()}</span>
        <span class="ops-kpi-chip-lbl">${cfg.totalLabel}</span>
    </div>`;

    // Dynamic chips — count currently VISIBLE table rows matching condition
    const visRows = _visibleRows(section);
    cfg.chips.forEach(function(chip) {
        const count = visRows.filter(chip.match).length;
        html += `<div class="ops-kpi-chip" style="color:${chip.color};border-color:${chip.color};">
            <span class="ops-kpi-chip-val">${count}</span>
            <span class="ops-kpi-chip-lbl">${chip.label}</span>
        </div>`;
    });

    bar.innerHTML = html;
}


async function showSection(section) {
    // WM pattern — synchronous, no animation race conditions
    document.querySelectorAll(".operations-section").forEach(el => {
        el.style.display = "none";
        el.removeAttribute("data-active");
    });
    document.querySelectorAll(".tracker-btn").forEach(b => b.classList.remove("active"));

    const sec = document.getElementById(section + "Section");
    const btn = document.getElementById(section + "ToolbarBtn");
    if (sec) {
        sec.style.display = "flex";
        sec.setAttribute("data-active", "true");
    }
    if (btn) btn.classList.add("active");

    if (section === "dashboard") {
        updateDashboardCounts();
        return;
    }

    // KPI chips in title bar
    renderKpiBar(section);

    // Build sidebar filters with correct defaults, wire onChange
    buildFilters(section);

    // Support and failure: load from API first time (tbody empty)
    // Incident/azure/ptc: already Jinja-rendered in DOM, just apply filters
    if (section === "support") {
        if (!document.querySelector("#supportTableBody tr")) {
            await loadSupportEmails(); // calls buildFilters + applyFilters when done
            return;
        }
    } else if (section === "failure") {
        if (!document.querySelector("#failureTableBody tr")) {
            await loadIntegrationFailures(); // calls buildFilters + applyFilters when done
            return;
        }
        populateServerDropdown();
    }

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
        const activeIncidents = (window.incidentData||[]).filter(function(r) {
            return ["On Hold","New","In Progress","Open"].indexOf(r.Status) >= 0;
        });
        set("dash-incident-count", activeIncidents.length);
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

        const qVal =
            document.getElementById(
                "quickDateFilter"
            )?.value || "7";

        const today = new Date();
        const cutoff = new Date();

        if (qVal === "today") {
            // Today only: same calendar day
            cutoff.setHours(0, 0, 0, 0);
            const todayEnd = new Date();
            todayEnd.setHours(23, 59, 59, 999);
            return recordDate >= cutoff && recordDate <= todayEnd;
        } else if (qVal === "yesterday_today") {
            cutoff.setDate(today.getDate() - 1);
            cutoff.setHours(0, 0, 0, 0);
        } else {
            const days = parseInt(qVal) || 7;
            cutoff.setDate(today.getDate() - days);
            cutoff.setHours(0, 0, 0, 0);
        }

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
                        class="sidebar-filter"
                        onchange="
                            var v=this.value;
                            var rs=document.getElementById('dateRangeSection');
                            var qs=document.getElementById('quickDateSection');
                            if(rs) rs.style.display=(v==='range')?'block':'none';
                            if(qs) qs.style.display=(v==='quick')?'block':'none';
                            applyFilters();
                        ">

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

                        <option value="yesterday_today" selected>
                            Today &amp; Yesterday
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
                        class="sidebar-filter"
                        onchange="
                            var v=this.value;
                            var rs=document.getElementById('dateRangeSection');
                            var qs=document.getElementById('quickDateSection');
                            if(rs) rs.style.display=(v==='range')?'block':'none';
                            if(qs) qs.style.display=(v==='quick')?'block':'none';
                            applyFilters();
                        ">

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

                        <option value="yesterday_today" selected>
                            Today &amp; Yesterday
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
                        class="sidebar-filter"
                        onchange="
                            var v=this.value;
                            var rs=document.getElementById('dateRangeSection');
                            var qs=document.getElementById('quickDateSection');
                            if(rs) rs.style.display=(v==='range')?'block':'none';
                            if(qs) qs.style.display=(v==='quick')?'block':'none';
                            applyFilters();
                        ">

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

                        <option value="yesterday_today" selected>
                            Today &amp; Yesterday
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

                    <div class="filter-label">
                        Assigned To
                    </div>

                    <select
                        id="incidentAssignedFilter"
                        class="sidebar-filter">

                        ${buildOptions(
                            getUniqueValues(
                                incidentData,
                                "Assigned To"
                            )
                        )}

                    </select>

                </div>

            `;
            break;

        case "azure":

            html = `

                <div class="filter-group">
                    <div class="filter-label">Type</div>
                    <select id="azureTypeFilter" class="sidebar-filter"
                            onchange="applyFilters()">
                        <option value="All">All Types</option>
                        <option value="Bug">Bug</option>
                        <option value="User Story">User Story</option>
                    </select>
                </div>

                <div class="filter-group">
                    <div class="filter-label">Group</div>
                    <select id="azureGroupFilter" class="sidebar-filter"
                            onchange="applyFilters()">
                        ${buildGroupOptions(window.azureData||[])}
                    </select>
                </div>

                <div class="filter-group">

                    <div class="filter-label">
                        Date Filter
                    </div>

                    <select
                        id="dateFilterType"
                        class="sidebar-filter"
                        onchange="
                            var v=this.value;
                            var rs=document.getElementById('dateRangeSection');
                            var qs=document.getElementById('quickDateSection');
                            if(rs) rs.style.display=(v==='range')?'block':'none';
                            if(qs) qs.style.display=(v==='quick')?'block':'none';
                            applyFilters();
                        ">

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

                        <option value="yesterday_today" selected>
                            Today &amp; Yesterday
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
                        class="sidebar-filter"
                        onchange="
                            var v=this.value;
                            var rs=document.getElementById('dateRangeSection');
                            var qs=document.getElementById('quickDateSection');
                            if(rs) rs.style.display=(v==='range')?'block':'none';
                            if(qs) qs.style.display=(v==='quick')?'block':'none';
                            applyFilters();
                        ">

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

                        <option value="yesterday_today" selected>
                            Today &amp; Yesterday
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
            console.log("[buildFilters] category options:", [...categoryFilter.options].map(o=>o.value));
            const actionOption =
                [...categoryFilter.options]
                    .find(option =>
                        option.value
                            .toLowerCase()
                            .includes("action required")
                    );

            if(actionOption) {
                categoryFilter.value = actionOption.value;
                console.log("[buildFilters] set category to:", categoryFilter.value);
            } else {
                console.log("[buildFilters] Action Required option NOT FOUND in dropdown");
            }
        }

        console.log("[buildFilters] calling applyFilters after support defaults");
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

    if(section === "incident") {

        const statusFilter =
            document.getElementById(
                "incidentStatusFilter"
            );

        if(statusFilter) {
            // Default to "On Hold" — show active issues
            const onHoldOpt = [...statusFilter.options]
                .find(o => o.value.toLowerCase().includes("on hold"));
            if(onHoldOpt) {
                statusFilter.value = onHoldOpt.value;
            }
        }

        applyFilters();
    }

    if(section === "ptc") {

        // Default: show On Hold + Information Received only
        const ptcStatus =
            document.getElementById("ptcStatusFilter");
        if(ptcStatus) {
            // Pick "On Hold" as the default — user can switch to All or other
            const ohOpt = [...ptcStatus.options]
                .find(o => o.value.toLowerCase().includes("on hold"));
            if(ohOpt) {
                ptcStatus.value = ohOpt.value;
            }
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

    // Use data-active attribute set by showSection — avoids browser style normalization
    // (browser writes "display: flex;" with space, so style*="display:flex" fails)
    const activeSection =
        document.querySelector(
            ".operations-section[data-active='true']"
        );

    console.log("[applyFilters] activeSection:", activeSection?.id || "NONE");
    if (!activeSection) return;

    const sectionId = activeSection.id;
    const rows = activeSection.querySelectorAll("tbody tr");
    console.log("[applyFilters] rows found:", rows.length, "section:", sectionId);

    let visibleCount = 0;

    rows.forEach(row => {

        let visible = true;

        // SUPPORT
        if (sectionId === "supportSection") {

            const rowDate =
                row.cells[0].innerText.trim();

            if(!passesDateFilter(rowDate)){
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

            if (visibleCount === 0) {
                console.log("[applyFilters] support sample - importance:", importance,
                    "| category:", category,
                    "| importanceFilter:", importanceFilter,
                    "| categoryFilter:", categoryFilter);
            }

            if (
                importanceFilter !== "All" &&
                importance !== importanceFilter
            ) {
                visible = false;
            }

            if (categoryFilter !== "All") {
                const categories =
                    category.split(",").map(v => v.trim());
                if (!categories.includes(categoryFilter)) {
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

            // Assigned To filter
            const assignedFilter =
                document.getElementById("incidentAssignedFilter")?.value || "All";
            if (assignedFilter !== "All") {
                const assignedCell = row.cells[3]?.innerText.trim() || "";
                if (assignedCell !== assignedFilter) {
                    visible = false;
                }
            }
        }

        // AZURE
        else if (
            sectionId === "azureSection"
        ) {
            // Columns: 0=Number, 1=Type, 2=Description, 3=AssignedTo, 4=Status, 5=Priority, 6=CreatedBy, 7=Date
            const rowDate =
                row.cells[7]?.innerText.trim() || "";

            if(
                !passesDateFilter(rowDate)
            ){
                visible = false;
            }
            const itemType =
                row.cells[1]?.innerText.trim() || "";

            const status =
                row.cells[4]?.innerText.trim() || "";

            const createdBy =
                row.cells[6]?.innerText.trim() || "";

            const statusFilter =
                document.getElementById(
                    "azureStatusFilter"
                )?.value || "All";

            const typeFilter =
                document.getElementById(
                    "azureTypeFilter"
                )?.value || "All";

            const createdByFilter =
                document.getElementById(
                    "azureCreatedByFilter"
                )?.value || "All";

            if (typeFilter !== "All" && !itemType.includes(typeFilter)) {
                visible = false;
            }

            // Group filter
            const grpFilter = document.getElementById("azureGroupFilter")?.value || "All";
            if (grpFilter !== "All") {
                const rowCB   = row.cells[6]?.innerText.trim() || "";
                const rowGrp  = _getGroupFor(rowCB);
                if (rowGrp !== grpFilter) {
                    visible = false;
                }
            }

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

    // Re-render dynamic KPI chips after filter (Total stays fixed, others count visible rows)
    if (activeSection) {
        const secKey = activeSection.id.replace("Section", "").toLowerCase();
        if (OPS_KPI_CONFIG[secKey]) {
            renderKpiBar(secKey);
        }
    }
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


// updateKpis — replaced by renderKpiBar; kept as stub to avoid ReferenceError
function updateKpis(section) { renderKpiBar(section); }

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
            ".operations-section[data-active='true']"
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
                ".operations-section[data-active='true']"
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
// =============================================================================
//  REPORTS ADDON — Daily Report, Weekly Report, Summary Report,
//                  Date-Range Report, Multi-sheet Excel, PDF, Settings
//  Appended to operations_center.js — zero changes to existing functions
// =============================================================================

// ── Toast (shared, safe to re-declare with guard) ────────────────────────────
if (typeof window._showToast === "undefined") {
    window._showToast = function(msg, type) {
        var t = document.getElementById("opsToast");
        if (!t) {
            t = document.createElement("div");
            t.id = "opsToast";
            t.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:99997;max-width:420px;padding:12px 18px;border-radius:10px;font-size:13px;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,.18);transition:opacity .4s;cursor:pointer;display:none;color:#fff;";
            t.onclick = function(){ t.style.opacity="0"; setTimeout(function(){t.style.display="none";},400); };
            document.body.appendChild(t);
        }
        var bg = {info:"#1e3a5f",success:"#16a34a",warning:"#d97706",error:"#dc2626"};
        t.style.background = bg[type]||bg.info;
        t.style.display="block"; t.style.opacity="1";
        t.textContent = msg;
        clearTimeout(t._t);
        t._t = setTimeout(function(){t.style.opacity="0";setTimeout(function(){t.style.display="none";},400);},6000);
    };
}

// ── Settings store ────────────────────────────────────────────────────────────
var _OPS_SETTINGS = (function() {
    var defaults = {
        theme          : "light",
        defaultDateRange: "today_yesterday",
        alertThresholds: {
            failure_total: 5, failure_prod: 1, support_pending: 3,
            incident_on_hold: 2, azure_new: 3, ptc_open: 3,
            wm_tx_failed: 3, wm_worker_fail_pct: 10
        },
        reportLogoText : "Ops Platform",
        reportFromEmail: "keshavamurthy.hg@consultant.volvo.com",
        reportToEmail  : "keshavamurthy.hg@consultant.volvo.com",
        defaultExportFormat: "excel",
        showBadgesInReport : true,
        rowsPerPageExport  : 500
    };
    try {
        var saved = JSON.parse(localStorage.getItem("ops_settings")||"{}");
        return Object.assign({}, defaults, saved);
    } catch(e) { return defaults; }
})();

function _saveSettings() {
    try { localStorage.setItem("ops_settings", JSON.stringify(_OPS_SETTINGS)); } catch(e) {}
}

// ── Date helpers ──────────────────────────────────────────────────────────────
function _dateRange(preset) {
    var today = new Date();
    var fmt   = function(d){ return d.toISOString().split("T")[0]; };
    switch(preset) {
        case "today":
            return { from: fmt(today), to: fmt(today), label: "Today" };
        case "today_yesterday":
            var y = new Date(today); y.setDate(y.getDate()-1);
            return { from: fmt(y), to: fmt(today), label: "Today & Yesterday" };
        case "this_week":
            var mon = new Date(today); mon.setDate(today.getDate()-today.getDay()+1);
            return { from: fmt(mon), to: fmt(today), label: "This Week (Mon–today)" };
        case "last_7":
            var l7 = new Date(today); l7.setDate(l7.getDate()-6);
            return { from: fmt(l7), to: fmt(today), label: "Last 7 Days" };
        case "last_30":
            var l30 = new Date(today); l30.setDate(l30.getDate()-29);
            return { from: fmt(l30), to: fmt(today), label: "Last 30 Days" };
        case "this_month":
            var m = new Date(today.getFullYear(), today.getMonth(), 1);
            return { from: fmt(m), to: fmt(today), label: "This Month" };
        default:
            return { from: fmt(today), to: fmt(today), label: "Today" };
    }
}

function _filterByDate(rows, dateKeys, fromStr, toStr) {
    if (!fromStr && !toStr) return rows;
    var from = fromStr ? new Date(fromStr) : null;
    var to   = toStr   ? new Date(toStr + "T23:59:59") : null;
    return rows.filter(function(r) {
        var val = "";
        for (var i=0; i<dateKeys.length; i++) {
            val = r[dateKeys[i]] || "";
            if (val) break;
        }
        if (!val) return true; // keep undated rows (open items)
        var d = new Date(String(val).replace(" CEST","").replace(" CET","").trim());
        if (isNaN(d.getTime())) return true;
        if (from && d < from) return false;
        if (to   && d > to)   return false;
        return true;
    });
}

// ── Get all 8 tracker datasets ────────────────────────────────────────────────
function _getAllData() {
    return {
        support  : window.supportData  || [],
        failure  : window.failureData  || [],
        incident : window.incidentData || [],
        azure    : window.azureData    || [],
        ptc      : window.ptcData      || [],
        // WM data comes from server via fetch
    };
}

// ═══════════════════════════════════════════════════════════════════════════════
//  REPORT MODAL — shared UI for all 3 report types + date-range picker
// ═══════════════════════════════════════════════════════════════════════════════

function _openReportModal(reportType) {
    document.getElementById("opsReportModal")?.remove();

    var isSettings = reportType === "settings";
    var modal = document.createElement("div");
    modal.id  = "opsReportModal";
    modal.style.cssText = "position:fixed;inset:0;z-index:99998;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.45);backdrop-filter:blur(2px);";

    var titles = {
        daily  : "📋 Daily Report",
        weekly : "📅 Weekly Report",
        summary: "📊 Summary Report",
        range  : "📆 Date Range Report",
        settings:"⚙ Settings"
    };

    var presets = [
        {v:"today",          l:"Today"},
        {v:"today_yesterday",l:"Today & Yesterday"},
        {v:"this_week",      l:"This Week"},
        {v:"last_7",         l:"Last 7 Days"},
        {v:"last_30",        l:"Last 30 Days"},
        {v:"this_month",     l:"This Month"},
        {v:"custom",         l:"Custom Range"}
    ];

    var defaultPreset = reportType === "daily"   ? "today_yesterday"
                      : reportType === "weekly"  ? "this_week"
                      : reportType === "summary" ? "last_30"
                      : "today_yesterday";

    var presetOptions = presets.map(function(p){
        return '<option value="'+p.v+'"'+(p.v===defaultPreset?" selected":"")+'>'+p.l+'</option>';
    }).join("");

    var today = new Date().toISOString().split("T")[0];
    var aWeekAgo = new Date(); aWeekAgo.setDate(aWeekAgo.getDate()-6);
    var weekAgoStr = aWeekAgo.toISOString().split("T")[0];

    var bodyContent = isSettings ? _settingsForm() : `
      <div class="orm-field-row">
        <label class="orm-label">Date Preset</label>
        <select id="orm-preset" class="orm-select" onchange="_ormPresetChange()">
          ${presetOptions}
        </select>
      </div>
      <div id="orm-custom-range" style="display:none;" class="orm-field-row orm-date-row">
        <div>
          <label class="orm-label">From</label>
          <input type="date" id="orm-from" class="orm-input" value="${weekAgoStr}">
        </div>
        <div>
          <label class="orm-label">To</label>
          <input type="date" id="orm-to" class="orm-input" value="${today}">
        </div>
      </div>
      <div class="orm-field-row">
        <label class="orm-label">Include Trackers</label>
        <div class="orm-checkboxes">
          ${["Integration Failures","Support Emails","Incidents","Azure Bugs","PTC Cases","WM Transactions","WVS Queue","Worker Stats"].map(function(t,i){
              var keys=["failure","support","incident","azure","ptc","wm_tx","wvs","workers"];
              return '<label class="orm-chk"><input type="checkbox" class="orm-tracker-chk" value="'+keys[i]+'" checked> '+t+'</label>';
          }).join("")}
        </div>
      </div>
      <div class="orm-field-row">
        <label class="orm-label">Export Format</label>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <label class="orm-chk"><input type="radio" name="orm-fmt" value="html" checked> HTML (preview)</label>
          <label class="orm-chk"><input type="radio" name="orm-fmt" value="excel"> Excel (multi-sheet)</label>
          <label class="orm-chk"><input type="radio" name="orm-fmt" value="pdf"> PDF (print)</label>
        </div>
      </div>`;

    modal.innerHTML = `
      <div class="orm-panel">
        <div class="orm-header">
          <span>${titles[reportType]||"Report"}</span>
          <button class="orm-close" onclick="document.getElementById('opsReportModal').remove()">✕</button>
        </div>
        <div class="orm-body">${bodyContent}</div>
        <div class="orm-footer">
          ${isSettings
            ? '<button class="orm-btn orm-btn-primary" onclick="_saveSettingsForm()">💾 Save Settings</button>'
            : '<button class="orm-btn orm-btn-secondary" onclick="document.getElementById(\'opsReportModal\').remove()">Cancel</button>'
              + '<button class="orm-btn orm-btn-primary" onclick="_generateReport(\''+reportType+'\')">⚡ Generate</button>'}
        </div>
      </div>`;

    document.body.appendChild(modal);
    modal.addEventListener("click", function(e){ if(e.target===modal) modal.remove(); });
}

function _ormPresetChange() {
    var v = document.getElementById("orm-preset").value;
    document.getElementById("orm-custom-range").style.display = v==="custom" ? "flex" : "none";
}

// ── Settings form ─────────────────────────────────────────────────────────────
function _settingsForm() {
    var s = _OPS_SETTINGS;
    var thr = s.alertThresholds;
    return `
      <div class="orm-section-title">📧 Report Identity</div>
      <div class="orm-field-row">
        <label class="orm-label">Report Title</label>
        <input type="text" id="s-logo" class="orm-input" value="${s.reportLogoText}">
      </div>
      <div class="orm-field-row">
        <label class="orm-label">From Email</label>
        <input type="text" id="s-from" class="orm-input" value="${s.reportFromEmail}">
      </div>
      <div class="orm-field-row">
        <label class="orm-label">To Email</label>
        <input type="text" id="s-to" class="orm-input" value="${s.reportToEmail}">
      </div>
      <div class="orm-section-title" style="margin-top:14px;">⚠ Alert Thresholds</div>
      ${[
          ["failure_total",      "Integration Failures Total",    thr.failure_total],
          ["failure_prod",       "PROD Failures",                 thr.failure_prod],
          ["support_pending",    "Support Action Required",       thr.support_pending],
          ["incident_on_hold",   "Incidents On Hold",             thr.incident_on_hold],
          ["azure_new",          "New Azure Bugs",                thr.azure_new],
          ["ptc_open",           "Open PTC Cases",                thr.ptc_open],
          ["wm_tx_failed",       "WM Transaction Failures",       thr.wm_tx_failed],
          ["wm_worker_fail_pct", "Worker Fail % threshold",       thr.wm_worker_fail_pct],
      ].map(function(r){
          return '<div class="orm-field-row orm-thr-row">'
              + '<label class="orm-label">'+r[1]+'</label>'
              + '<input type="number" id="thr-'+r[0]+'" class="orm-input orm-thr-input" value="'+r[2]+'" min="0">'
              + '</div>';
      }).join("")}
      <div class="orm-section-title" style="margin-top:14px;">🎨 Appearance</div>
      <div class="orm-field-row">
        <label class="orm-label">Default Date Range</label>
        <select id="s-daterange" class="orm-select">
          ${[["today_yesterday","Today & Yesterday"],["this_week","This Week"],["last_7","Last 7 Days"]].map(function(o){
              return '<option value="'+o[0]+'"'+(o[0]===s.defaultDateRange?" selected":"")+'>'+o[1]+'</option>';
          }).join("")}
        </select>
      </div>
      <div class="orm-field-row">
        <label class="orm-label">Show Status Badges</label>
        <input type="checkbox" id="s-badges" ${s.showBadgesInReport?"checked":""} style="width:18px;height:18px;cursor:pointer;">
      </div>`;
}

function _saveSettingsForm() {
    _OPS_SETTINGS.reportLogoText       = document.getElementById("s-logo").value;
    _OPS_SETTINGS.reportFromEmail      = document.getElementById("s-from").value;
    _OPS_SETTINGS.reportToEmail        = document.getElementById("s-to").value;
    _OPS_SETTINGS.defaultDateRange     = document.getElementById("s-daterange").value;
    _OPS_SETTINGS.showBadgesInReport   = document.getElementById("s-badges").checked;
    ["failure_total","failure_prod","support_pending","incident_on_hold",
     "azure_new","ptc_open","wm_tx_failed","wm_worker_fail_pct"].forEach(function(k){
        var el = document.getElementById("thr-"+k);
        if (el) _OPS_SETTINGS.alertThresholds[k] = parseFloat(el.value)||0;
    });
    _saveSettings();
    document.getElementById("opsReportModal").remove();
    _showToast("✅ Settings saved", "success");
}

// ═══════════════════════════════════════════════════════════════════════════════
//  GENERATE REPORT — calls server, handles HTML/Excel/PDF
// ═══════════════════════════════════════════════════════════════════════════════

function _generateReport(reportType) {
    var preset = document.getElementById("orm-preset")?.value || "today_yesterday";
    var dr;
    if (preset === "custom") {
        dr = {
            from : document.getElementById("orm-from")?.value || "",
            to   : document.getElementById("orm-to")?.value   || "",
            label: "Custom"
        };
    } else {
        dr = _dateRange(preset);
    }

    var checkedTrackers = [];
    document.querySelectorAll(".orm-tracker-chk:checked").forEach(function(cb){ checkedTrackers.push(cb.value); });

    var fmt = document.querySelector("input[name='orm-fmt']:checked")?.value || "html";

    document.getElementById("opsReportModal").remove();

    var reportTypeMap = {
        daily  : "daily_report",
        weekly : "weekly_report",
        summary: "summary_report",
        range  : "range_report"
    };

    _showToast("⏳ Generating " + reportType + " report…", "info");

    fetch("/api/operations-center/generate-report", {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify({
            report_type    : reportTypeMap[reportType] || "daily_report",
            from_date      : dr.from,
            to_date        : dr.to,
            date_label     : dr.label,
            trackers       : checkedTrackers,
            format         : fmt,
            settings       : _OPS_SETTINGS,
        })
    })
    .then(function(r) {
        if (fmt === "html") return r.text().then(function(html) {
            var w = window.open("","_blank");
            w.document.write(html);
            w.document.close();
            _showToast("✅ Report opened in new tab", "success");
        });
        if (!r.ok) return r.text().then(function(t){ throw new Error(t); });
        var cd = r.headers.get("Content-Disposition") || "";
        var fn = (cd.match(/filename="?([^";\n]+)"?/)||[])[1] || ("ops_report."+fmt);
        return r.blob().then(function(blob){
            var a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = fn;
            a.click();
            _showToast("✅ " + fn + " downloaded", "success");
        });
    })
    .catch(function(e){ _showToast("❌ " + e.message, "error"); });
}

// ── Public buttons wired to sidebar + dock ────────────────────────────────────
function openDailyReport()   { _openReportModal("daily");    }
function openWeeklyReport()  { _openReportModal("weekly");   }
function openSummaryReport() { _openReportModal("summary");  }
function openRangeReport()   { _openReportModal("range");    }
function openSettings()      { _openReportModal("settings"); }

// ── Prepare digest (unchanged from before) ────────────────────────────────────
var _digestResults = [];
function prepareAllDigests() {
    var btn = document.getElementById("opsDigestBtn");
    if (btn) { btn.disabled=true; btn.textContent="⏳ Preparing…"; }
    _showToast("Preparing daily alert digests…","info");
    fetch("/api/operations-center/prepare-all-digests",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})
    .then(function(r){return r.json();})
    .then(function(data){
        if(btn){btn.disabled=false;btn.textContent="📨 Prepare Digest";}
        if(!data.success){_showToast("❌ "+(data.message||"Failed"),"error");return;}
        _digestResults=data.results||[];
        var alerts=data.alert_types||[];
        if(alerts.length){
            _showToast("🔔 "+data.total+" digests ready — "+alerts.length+" with alerts!","warning");
            if(btn){btn.style.background="#fef9c3";btn.style.borderColor="#f59e0b";}
        } else {
            _showToast("✅ "+data.total+" digests saved","success");
        }
        _openDigestPanel(data);
    })
    .catch(function(e){if(btn){btn.disabled=false;btn.textContent="📨 Prepare Digest";}_showToast("❌ "+e.message,"error");});
}

function _openDigestPanel(data) {
    var panel=document.getElementById("digestPanel"),overlay=document.getElementById("digestOverlay");
    if(!panel)return;
    var results=data.results||_digestResults,alertTypes=data.alert_types||[],folder=data.folder||"data/email_digests/";
    var today=new Date().toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"});
    var rows=results.map(function(r){
        if(!r.success)return'<div class="dp-row"><div class="dp-row-left"><span class="dp-badge dp-badge-alert">❌</span><span class="dp-type">'+(r.digest_type||"?").replace(/_/g," ")+'</span></div><span style="font-size:11px;color:#6b7280;">'+(r.message||"")+'</span></div>';
        var isAlert=!!r.is_alert,label=(r.digest_type||"").replace(/_/g," ").replace(/\b\w/g,function(c){return c.toUpperCase();});
        var viewUrl="/api/operations-center/view-digest?file="+encodeURIComponent(r.html_file||""),subj=(r.subject||"").replace(/\\/g,"\\\\").replace(/'/g,"\\'");
        return'<div class="dp-row'+(isAlert?" dp-row-alert":"")+'"><div class="dp-row-left">'
            +(isAlert?'<span class="dp-badge dp-badge-alert">⚠ Alert</span>':'<span class="dp-badge dp-badge-ok">✓ Ready</span>')
            +'<span class="dp-type">'+label+'</span></div><div class="dp-row-right">'
            +'<button class="dp-btn dp-btn-view" onclick="window.open(\''+viewUrl+'\',\'_blank\')">👁 Open</button>'
            +'<button class="dp-btn dp-btn-copy" onclick="_copySubject(\''+subj+'\',this)">📋 Subject</button>'
            +'</div></div>';
    }).join("");
    var alertBanner=alertTypes.length?'<div class="dp-alert-banner">⚠ <strong>'+alertTypes.length+' tracker'+(alertTypes.length>1?"s":"")+'</strong>: '+alertTypes.map(function(t){return'<span class="dp-tag">'+t.replace(/_/g," ")+'</span>';}).join(" ")+'</div>':"";
    panel.innerHTML='<div class="dp-header"><div class="dp-header-left"><span class="dp-header-icon">'+(alertTypes.length?"🔔":"📋")+'</span><div><div class="dp-header-title">'+(alertTypes.length?"Alert Digests Ready":"Email Digests Ready")+'</div><div class="dp-header-sub">'+today+' · '+results.length+' digests · today & yesterday</div></div></div><button class="dp-close" onclick="closeDigestPanel()">✕</button></div>'+alertBanner+'<div class="dp-instructions"><strong>To send:</strong> 1. <strong>👁 Open</strong> to preview &nbsp;·&nbsp; 2. <strong>📋 Subject</strong> to copy &nbsp;·&nbsp; 3. Paste into Outlook</div><div class="dp-folder">📁 <code>'+folder+'</code></div><div class="dp-list">'+rows+'</div><div class="dp-footer"><button class="dp-btn dp-btn-primary" onclick="prepareAllDigests()">🔄 Refresh</button><button class="dp-btn dp-btn-secondary" onclick="closeDigestPanel()">Close</button></div>';
    panel.style.display="flex"; overlay.style.display="block";
}
function closeDigestPanel(){var p=document.getElementById("digestPanel"),o=document.getElementById("digestOverlay");if(p)p.style.display="none";if(o)o.style.display="none";var btn=document.getElementById("opsDigestBtn");if(btn){btn.style.background="";btn.style.borderColor="";btn.textContent="📨 Prepare Digest";}}
function _copySubject(s,btn){navigator.clipboard.writeText(s).then(function(){var o=btn.textContent;btn.textContent="✅ Copied!";btn.style.background="#dcfce7";setTimeout(function(){btn.textContent=o;btn.style.background="";},2000);}).catch(function(){prompt("Copy subject:",s);});}
