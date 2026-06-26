// =============================================================================
//  UTILS & CORE FILTER ENGINE
// =============================================================================
function getUniqueValues(data, field) {
    if (!Array.isArray(data)) return [];
    const values = data
        .map(item => {
            const value = item[field];
            if (value === null || value === undefined) return "";
            return String(value).trim();
        })
        .filter(value => value !== "")
        .filter((value, index, array) => array.indexOf(value) === index)
        .sort((a, b) => a.localeCompare(b));
    return values;
}

function buildOptions(values) {
    let html = '<option value="All">All</option>';
    values.forEach(v => { html += `<option value="${v}">${v}</option>`; });
    return html;
}

function updateStatus(message) {
    const statusElement = document.getElementById("statusMessage");
    if (statusElement) statusElement.innerText = message;
}

function updateProcessingStatus(message, detail = "", state = "completed") {
    const status  = document.getElementById("statusMessage");
    const text    = document.getElementById("progressText");
    const fill    = document.getElementById("progressFill");
    const wrapper = document.getElementById("progressWrapper");

    if (status) status.innerText = message;
    if (text)   text.innerText   = detail;
    if (!fill || !wrapper) return;

    fill.classList.remove("ops-bar-processing", "ops-bar-completed", "ops-bar-failed");

    if (state === "processing") {
        wrapper.classList.remove("hidden");
        fill.style.width = "70%";
        fill.classList.add("ops-bar-processing");
    } else if (state === "completed") {
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.classList.add("ops-bar-completed");
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.classList.remove("ops-bar-completed");
        }, 2000);
    } else {
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.classList.add("ops-bar-failed");
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.classList.remove("ops-bar-failed");
        }, 3000);
    }
}

// Data mapping pointing directly to your global window data structures
const OPS_DATA_MAP = {
    support: () => window.supportData,
    failure: () => window.failureData,
    incident: () => window.incidentData,
    azure: () => window.azureData,
    ptc: () => window.ptcData,
};

// =============================================================================
//  UNIFIED TABLE RENDERER
// =============================================================================
function _opsRenderTable(section, data) {
    const tbody = document.getElementById(`${section}TableBody`);
    if (!tbody) {
        console.error(`Target tbody element not found: #${section}TableBody`);
        return;
    }

    if (!data || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:#9ca3af;padding:20px;">No records found</td></tr>`;
        return;
    }

    const esc = s => (s || "").toString().replace(/"/g, "&quot;");
    const pill = s => `<span class="ops-status-pill ops-status-${(s||"").toLowerCase().replace(/ /g,"-")}">${s||""}</span>`;
    const link = (url, txt) => url ? `<a href="${url}" target="_blank" class="number-link">${txt||""}</a>` : (txt||"");
    const desc = s => `<div class="desc-cell" title="${esc(s)}">${s||""}</div>`;

    if (section === "support") {
        tbody.innerHTML = data.map(r => `<tr>
            <td>${r["Date Received"] || r.date_received || ""}</td>
            <td>${r["Name"]          || r.name          || ""}</td>
            <td>${desc(r["Subject"]  || r.subject       || "")}</td>
            <td>${r["Importance"]    || r.importance    || ""}</td>
            <td>${r["Categories"]    || r["Category"]   || r.category || ""}</td>
        </tr>`).join("");
    } 
    else if (section === "failure") {
        tbody.innerHTML = data.map(r => `<tr>
            <td>${r["Failure Time"] || r.failure_time || ""}</td>
            <td>${r["Integration"]  || r.integration  || r["Target"] || ""}</td>
            <td>${r["Object Number"]|| r.object_number|| r["Object"] || ""}</td>
            <td>${desc(r["Error Message"] || r.error_message || r["Notes"] || "")}</td>
            <td>${r["Environment"]  || r.environment  || ""}</td>
            <td>${r["Windchill Server"] || r.wc_server || ""}</td>
        </tr>`).join("");
    } 
    else if (section === "incident") {
        tbody.innerHTML = data.map(r => `<tr>
            <td>${link(r.number_url, r.Number)}</td>
            <td>${link(r.vendor_ticket_url, r["Vendor Ticket"])}</td>
            <td>${desc(r.Description)}</td>
            <td>${r["Assigned To"] || ""}</td>
            <td>${pill(r.Status)}</td>
            <td>${r.Priority || ""}</td>
            <td>${r["Created Date"] || ""}</td>
        </tr>`).join("");
    } 
    else if (section === "azure") {
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
    else if (section === "ptc") {
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

// =============================================================================
//  SECTION LIFE CYCLE
// =============================================================================
const OPS_KPIS = {
    support:  () => [{ val: (window.supportData||[]).length, label: "Total", color: "#3b82f6" }],
    failure:  () => [{ val: (window.failureData||[]).length, label: "Total Failed", color: "#ef4444" }],
    incident: () => [{ val: (window.incidentData||[]).length, label: "Total", color: "#f28c38" }],
    azure:    () => [{ val: (window.azureData||[]).length, label: "Total", color: "#0ea5e9" }],
    ptc:      () => [{ val: (window.ptcData||[]).length, label: "Total", color: "#8b5cf6" }]
};

function renderKpiBar(section) {
    const bar = document.getElementById(section + "KpiBar");
    if (!bar) return;
    const fn = OPS_KPIS[section];
    if (!fn) return;
    bar.innerHTML = fn().map(k =>
        `<div class="ops-kpi-chip" style="color:${k.color};border-color:${k.color};">
            <span class="ops-kpi-chip-val">${k.val}</span>
            <span class="ops-kpi-chip-lbl">${k.label}</span>
         </div>`
    ).join("");
}

async function showSection(section) {
    // ── 1. Hide out existing components ──
    document.querySelectorAll(".operations-section").forEach(el => {
        el.style.display = "none";
        el.classList.remove("ops-section-hiding", "ops-section-visible");
    });

    // ── 2. Highlight active navbar configurations ──
    document.querySelectorAll(".tracker-btn").forEach(b => b.classList.remove("active"));
    const btn = document.getElementById(section + "ToolbarBtn");
    if (btn) btn.classList.add("active");

    // ── 3. Open selected window grid ──
    const sec = document.getElementById(section + "Section");
    if (sec) {
        sec.style.display = "flex";
        sec.classList.add("ops-section-visible");
    }

    if (section === "dashboard") {
        updateDashboardCounts();
        return;
    }

    // ── 4. Generate UI Context Elements ──
    renderKpiBar(section);
    buildFilters(section);

    // ── 5. Lazy loaders or global array fallback ──
    if (section === "support" && (!window.supportData || window.supportData.length === 0)) {
        await loadSupportEmails();
        return;
    } else if (section === "failure" && (!window.failureData || window.failureData.length === 0)) {
        await loadIntegrationFailures();
        return;
    }

    // Force table layout updates directly on structural active lists
    const targetData = OPS_DATA_MAP[section] ? OPS_DATA_MAP[section]() : null;
    _opsRenderTable(section, targetData);
    
    if (section === "failure") populateServerDropdown();
    applyFilters();
}

// =============================================================================
//  LAZY ASYNC DATA FETCHING (Outlook & Integration Logs)
// =============================================================================
async function loadSupportEmails() {
    try {
        updateProcessingStatus("Support Emails", "Connecting to Outlook...", "processing");
        const response = await fetch("/api/operations-center/support-emails");
        const result = await response.json();

        if (result.success) {
            window.supportData = result.data || [];
            _opsRenderTable("support", window.supportData);
            buildFilters("support");
            renderKpiBar("support");
            applyFilters();
            updateProcessingStatus("Completed", window.supportData.length + " emails loaded", "completed");
        }
    } catch (e) {
        console.error(e);
        updateProcessingStatus("Failed", "Load failed", "failed");
    }
}

async function loadIntegrationFailures() {
    try {
        updateProcessingStatus("Integration Failures", "Loading server logs...", "processing");
        const response = await fetch("/api/operations-center/integration-failures");
        const result = await response.json();

        if (result.success) {
            window.failureData = result.data || [];
            _opsRenderTable("failure", window.failureData);
            buildFilters("failure");
            populateFailureFiltersFromTable();
            renderKpiBar("failure");
            applyFilters();
            updateProcessingStatus("Completed", window.failureData.length + " logs loaded", "completed");
        }
    } catch (e) {
        console.error(e);
        updateProcessingStatus("Failed", "Load failed", "failed");
    }
}

function populateFailureFiltersFromTable() {
    const envSet = new Set();
    const serverSet = new Set();
    (window.failureData || []).forEach(row => {
        if (row.Environment || row.environment) envSet.add(row.Environment || row.environment);
        if (row["Windchill Server"] || row.wc_server) serverSet.add(row["Windchill Server"] || row.wc_server);
    });

    const envDropdown = document.getElementById("failureEnvironmentFilter");
    const serverDropdown = document.getElementById("failureServerFilter");

    if (envDropdown) envDropdown.innerHTML = '<option value="All">All</option>' + [...envSet].sort().map(e => `<option value="${e}">${e}</option>`).join("");
    if (serverDropdown) serverDropdown.innerHTML = '<option value="All">All</option>' + [...serverSet].sort().map(s => `<option value="${s}">${s}</option>`).join("");
}

function populateServerDropdown() {
    // Dynamic dependent filter matching
    const env = document.getElementById("failureEnvironmentFilter")?.value || "All";
    const serverDropdown = document.getElementById("failureServerFilter");
    if (!serverDropdown) return;

    const currentServer = serverDropdown.value;
    const servers = new Set();

    (window.failureData || []).forEach(row => {
        const rEnv = row.Environment || row.environment || "";
        const rSrv = row["Windchill Server"] || row.wc_server || "";
        if (env === "All" || rEnv === env) {
            if (rSrv) servers.add(rSrv);
        }
    });

    serverDropdown.innerHTML = '<option value="All">All</option>' + [...servers].sort().map(s => `<option value="${s}">${s}</option>`).join("");
    if (servers.has(currentServer)) serverDropdown.value = currentServer;
}

// =============================================================================
//  FILTER APPLICATOR
// =============================================================================
function applyFilters() {
    const activeSection = [...document.querySelectorAll(".operations-section")].find(
        sec => sec.id !== "dashboardSection" && window.getComputedStyle(sec).display === "flex"
    );
    if (!activeSection) return;

    const sectionId = activeSection.id;
    const rows = activeSection.querySelectorAll("tbody tr");
    let visibleCount = 0;

    rows.forEach(row => {
        // Prevent matching empty array messages
        if (row.cells.length <= 1) return;
        let visible = true;

        if (sectionId === "supportSection") {
            const rowDate = row.cells[0].innerText.trim();
            const importance = row.cells[3].innerText.trim();
            const category = row.cells[4].innerText.trim();

            const impF = document.getElementById("supportImportanceFilter")?.value || "All";
            const catF = document.getElementById("supportCategoryFilter")?.value || "All";

            if (!passesDateFilter(rowDate)) visible = false;
            if (impF !== "All" && importance !== impF) visible = false;
            if (catF !== "All" && !category.split(",").map(v => v.trim()).includes(catF)) visible = false;
        } 
        else if (sectionId === "failureSection") {
            const rowDate = row.cells[0].innerText.trim();
            const environment = row.cells[4].innerText.trim();
            const server = row.cells[5].innerText.trim();

            const envF = document.getElementById("failureEnvironmentFilter")?.value || "All";
            const srvF = document.getElementById("failureServerFilter")?.value || "All";

            if (!passesDateFilter(rowDate)) visible = false;
            if (envF !== "All" && environment !== envF) visible = false;
            if (srvF !== "All" && server !== srvF) visible = false;
        } 
        else if (sectionId === "incidentSection") {
            const rowDate = row.cells[6].innerText.trim();
            const status = row.cells[4].innerText.trim();
            const priority = row.cells[5].innerText.trim();

            const statF = document.getElementById("incidentStatusFilter")?.value || "All";
            const priF = document.getElementById("incidentPriorityFilter")?.value || "All";

            if (!passesDateFilter(rowDate)) visible = false;
            if (statF !== "All" && status !== statF) visible = false;
            if (priF !== "All" && priority !== priF) visible = false;
        } 
        else if (sectionId === "azureSection") {
            const rowDate = row.cells[6].innerText.trim();
            const status = row.cells[3].innerText.trim();
            const createdBy = row.cells[5].innerText.trim();

            const statF = document.getElementById("azureStatusFilter")?.value || "All";
            const cbF = document.getElementById("azureCreatedByFilter")?.value || "All";

            if (!passesDateFilter(rowDate)) visible = false;
            if (statF !== "All" && status !== statF) visible = false;
            if (cbF !== "All" && createdBy !== cbF) visible = false;
        } 
        else if (sectionId === "ptcSection") {
            const rowDate = row.cells[6].innerText.trim();
            const status = row.cells[3].innerText.trim();
            const createdBy = row.cells[5].innerText.trim();

            const statF = document.getElementById("ptcStatusFilter")?.value || "All";
            const cbF = document.getElementById("ptcCreatedByFilter")?.value || "All";

            if (!passesDateFilter(rowDate)) visible = false;
            if (statF !== "All" && status !== statF) visible = false;
            if (cbF !== "All" && createdBy !== cbF) visible = false;
        }

        row.style.display = visible ? "" : "none";
        if (visible) visibleCount++;
    });

    updateStatus(`${visibleCount} records found`);
}

function passesDateFilter(rowDate) {
    const filterType = document.getElementById("dateFilterType")?.value || "none";
    if (filterType === "none" || !rowDate) return true;

    const recordDate = new Date(rowDate.replace(" ", "T"));
    if (isNaN(recordDate)) return true;

    if (filterType === "range") {
        const start = document.getElementById("startDate")?.value;
        const end = document.getElementById("endDate")?.value;
        if (start && recordDate < new Date(start)) return false;
        if (end) {
            const endDate = new Date(end);
            endDate.setHours(23, 59, 59, 999);
            if (recordDate > endDate) return false;
        }
        return true;
    }

    if (filterType === "quick") {
        const val = document.getElementById("quickDateFilter")?.value;
        if (val === "today") {
            const today = new Date();
            return recordDate.toDateString() === today.toDateString();
        }
        const days = parseInt(val || 0);
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - days);
        return recordDate >= cutoff;
    }
    return true;
}

// =============================================================================
//  SIDEBAR FILTERS INJECTION
// =============================================================================
function buildFilters(section) {
    const container = document.getElementById("dynamicFilters");
    if (!container) return;

    let html = `
        <div class="filter-group">
            <div class="filter-label">Date Filter</div>
            <select id="dateFilterType" class="sidebar-filter">
                <option value="none">No Filter</option>
                <option value="range">Date Range</option>
                <option value="quick">Quick Select</option>
            </select>
        </div>
        <div id="dateRangeSection" class="date-sub-section">
            <input type="date" id="startDate" class="sidebar-date">
            <input type="date" id="endDate" class="sidebar-date">
        </div>
        <div id="quickDateSection" class="date-sub-section">
            <select id="quickDateFilter" class="sidebar-filter">
                <option value="today">Today</option>
                <option value="7">Last 7 Days</option>
                <option value="30">Last 30 Days</option>
                <option value="90">Last 90 Days</option>
            </select>
        </div>
    `;

    if (section === "support") {
        html += `
            <div class="filter-group">
                <div class="filter-label">Importance</div>
                <select id="supportImportanceFilter" class="sidebar-filter">
                    ${buildOptions(getUniqueValues((window.supportData || []).map(r => ({ imp: r.importance || r["Importance"] || "" })), "imp"))}
                </select>
                <div class="filter-label">Category</div>
                <select id="supportCategoryFilter" class="sidebar-filter">
                    ${buildOptions(getUniqueValues((window.supportData || []).map(r => ({ cat: r.category || r["Category"] || r["Categories"] || "" })), "cat"))}
                </select>
            </div>`;
    } 
    else if (section === "failure") {
        html += `
            <div class="filter-group">
                <div class="filter-label">Environment</div>
                <select id="failureEnvironmentFilter" class="sidebar-filter"></select>
                <div class="filter-label">Windchill Server</div>
                <select id="failureServerFilter" class="sidebar-filter"></select>
            </div>`;
    } 
    else if (section === "incident") {
        html += `
            <div class="filter-group">
                <div class="filter-label">Status</div>
                <select id="incidentStatusFilter" class="sidebar-filter">${buildOptions(getUniqueValues(window.incidentData, "Status"))}</select>
                <div class="filter-label">Priority</div>
                <select id="incidentPriorityFilter" class="sidebar-filter">${buildOptions(getUniqueValues(window.incidentData, "Priority"))}</select>
            </div>`;
    } 
    else if (section === "azure") {
        html += `
            <div class="filter-group">
                <div class="filter-label">Status</div>
                <select id="azureStatusFilter" class="sidebar-filter">${buildOptions(getUniqueValues(window.azureData, "Status"))}</select>
                <div class="filter-label">Created By</div>
                <select id="azureCreatedByFilter" class="sidebar-filter">${buildOptions(getUniqueValues(window.azureData, "Created By"))}</select>
            </div>`;
    } 
    else if (section === "ptc") {
        html += `
            <div class="filter-group">
                <div class="filter-label">Status</div>
                <select id="ptcStatusFilter" class="sidebar-filter">${buildOptions(getUniqueValues(window.ptcData, "Status"))}</select>
                <div class="filter-label">Created By</div>
                <select id="ptcCreatedByFilter" class="sidebar-filter">${buildOptions(getUniqueValues(window.ptcData, "Created By"))}</select>
            </div>`;
    }

    container.innerHTML = html;

    // Visibility mapping for date selections
    const typeSelect = document.getElementById("dateFilterType");
    const rSection = document.getElementById("dateRangeSection");
    const qSection = document.getElementById("quickDateSection");

    if (typeSelect && rSection && qSection) {
        typeSelect.addEventListener("change", () => {
            rSection.style.display = typeSelect.value === "range" ? "block" : "none";
            qSection.style.display = typeSelect.value === "quick" ? "block" : "none";
            applyFilters();
        });
    }

    // Attach filters calculation hooks to everything inside the sidebar container
    container.querySelectorAll("select, input").forEach(el => {
        el.addEventListener("change", () => {
            if (el.id === "failureEnvironmentFilter") populateServerDropdown();
            applyFilters();
        });
        el.addEventListener("input", applyFilters);
    });
}

function updateDashboardCounts() {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    if (window.supportData) set("dash-support-count", window.supportData.length);
    if (window.failureData) set("dash-failure-count", window.failureData.length);
    if (window.incidentData) set("dash-incident-count", window.incidentData.length);
    if (window.azureData) set("dash-azure-count", window.azureData.length);
    if (window.ptcData) set("dash-ptc-count", window.ptcData.length);
}

// Initialize Document
document.addEventListener("DOMContentLoaded", () => {
    loadRefreshStatus();
    showSection("dashboard");
});

async function loadRefreshStatus() {
    try {
        const response = await fetch("/api/refresh-status");
        const data = await response.json();
        const el = document.getElementById("lastRefreshTime");
        if (el) el.textContent = `Last Refresh: ${data.last_refresh}`;
    } catch (err) { console.error(err); }
}

// Clean up references to old unimplemented metrics
async function refreshOperationsData() { location.reload(); }
function populateServerDropdownLegacy() {}
function refreshPowerQuery() {}
function showSidebarSection(sectionId, element) {
    document.querySelectorAll(".dock-section").forEach(s => s.classList.remove("active-dock-section"));
    const target = document.getElementById(sectionId);
    if (target) target.classList.add("active-dock-section");
    document.querySelectorAll(".dock-item").forEach(i => i.classList.remove("active-dock"));
    if (element) element.classList.add("active-dock");
}
function exportCurrentViewCSV() {}
function exportCurrentViewXLSX() {}