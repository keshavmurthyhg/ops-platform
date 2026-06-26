/* =========================================
   GLOBAL STATE
========================================= */

let currentResults = [];
let currentPage = 1;
let rowsPerPage = 10;

// UGM modal state
let ugmAllUsers = [];
let ugmGroupMembers = [];

/* =========================================
   PROCESSING STATUS
   Uses common.js IDs + hidden class. Extends progress-bar-fill
   with ops-bar colour classes defined in search.css.
========================================= */

function updateProcessingStatus(message, detail = "", state = "completed") {

    const statusEl  = document.getElementById("statusMessage");
    const textEl    = document.getElementById("progressText");
    const fillEl    = document.getElementById("progressFill");
    const wrapperEl = document.getElementById("progressWrapper");

    if (statusEl) statusEl.innerText = message;
    if (textEl)   textEl.innerText   = detail;

    if (!fillEl || !wrapperEl) return;

    wrapperEl.classList.remove("hidden");
    fillEl.classList.remove("ops-bar-processing", "ops-bar-completed", "ops-bar-failed");

    if (state === "processing") {
        fillEl.style.width = "70%";
        fillEl.classList.add("ops-bar-processing");

    } else if (state === "completed") {
        fillEl.style.width = "100%";
        fillEl.classList.add("ops-bar-completed");
        setTimeout(() => {
            fillEl.style.width = "0%";
            fillEl.classList.remove("ops-bar-completed");
            wrapperEl.classList.add("hidden");
        }, 2000);

    } else {
        // failed
        fillEl.style.width = "100%";
        fillEl.classList.add("ops-bar-failed");
        setTimeout(() => {
            fillEl.style.width = "0%";
            fillEl.classList.remove("ops-bar-failed");
            wrapperEl.classList.add("hidden");
        }, 3000);
    }
}

/* =========================================
   SHOW SEARCH SECTION
========================================= */
function showSearchSection(section, el) {

    document.querySelectorAll(".dock-section")
        .forEach(e => e.classList.remove("active-section"));

    document.querySelectorAll(".dock-item")
        .forEach(e => e.classList.remove("active-dock"));

    const target = document.getElementById(section + "-section");
    if (target) target.classList.add("active-section");

    if (el) el.classList.add("active-dock");
}

/* =========================================
   LOAD FILTER OPTIONS
========================================= */

async function loadFilterOptions() {

    try {

        const response =
            await fetch("/search/filter-options");

        const data =
            await response.json();


        populateDropdown(
            "statusFilter",
            data.status,
            "Status"
        );

        populateDropdown(
            "priorityFilter",
            data.priority,
            "Priority"
        );

        populateDropdown(
            "groupFilter",
            data.groups,
            "Group"
        );

    }

    catch(error) {

        console.error(error);

    }
}


/* =========================================
   POPULATE DROPDOWN
========================================= */

function populateDropdown(id, values, label) {

    const dropdown =
        document.getElementById(id);

    dropdown.innerHTML =
        `<option value="">${label}</option>`;

    values.forEach(value => {

        dropdown.innerHTML += `
            <option value="${value}">
                ${value}
            </option>
        `;
    });
}

/* =========================================
   GET SEARCH-IN FIELDS
========================================= */

function getSearchInFields() {

    return Array.from(
        document.querySelectorAll(".search-in-item:checked")
    ).map(el => el.value);
}

/* =========================================
   SEARCH
========================================= */

async function performSearch() {

    try {

        const query =
            document.getElementById("searchInput").value.trim();

        updateProcessingStatus("Searching issues…", query || "all records", "processing");

        const selectedSources = Array.from(
            document.querySelectorAll(".source-item:checked")
        ).map(el => el.value);

        const searchInFields = getSearchInFields();

        const selectedStatus =
            document.getElementById("statusFilter").value;

        const selectedPriority =
            document.getElementById("priorityFilter").value;

        const selectedGroup =
            document.getElementById("groupFilter").value;

        const dateField =
            document.getElementById("dateField").value;

        // ── Resolve start/end dates from whichever filter mode is active ──
        let startDate = "";
        let endDate   = "";

        const filterType = document.getElementById("dateFilterType").value;

        if (filterType === "range") {
            // Direct date inputs
            startDate = document.getElementById("startDate").value;
            endDate   = document.getElementById("endDate").value;

        } else if (filterType === "year") {
            const yr = document.getElementById("yearFilter").value;
            if (yr) {
                startDate = `${yr}-01-01`;
                endDate   = `${yr}-12-31`;
            }

        } else if (filterType === "quick") {
            const days = parseInt(document.getElementById("quickDate").value);
            if (days) {
                const now   = new Date();
                const from  = new Date();
                from.setDate(now.getDate() - days);
                const pad   = n => String(n).padStart(2, "0");
                startDate = `${from.getFullYear()}-${pad(from.getMonth()+1)}-${pad(from.getDate())}`;
                endDate   = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`;
            }
        }

        const response = await fetch("/search/issues", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query,
                sources: selectedSources,
                search_in: searchInFields,
                status: selectedStatus,
                priority: selectedPriority,
                group: selectedGroup,
                date_field: dateField,
                start_date: startDate,
                end_date: endDate
            })
        });

        const data = await response.json();

        if (data.error) {
            updateProcessingStatus("Search failed", data.error, "failed");
            return;
        }

        currentResults = data.results;
        currentPage = 1;
        // Apply preference sort only if user has explicitly changed it
        if (_sortKey && _prefSortApplied) {
            applySort();
        }
        renderCurrentPage();
        updateSummary(currentResults);

        updateProcessingStatus(
            "Search completed",
            `${currentResults.length} result${currentResults.length !== 1 ? "s" : ""} found`,
            "completed"
        );

    } catch(error) {

        console.error(error);
        updateProcessingStatus("Search failed", error.message, "failed");
    }
}


/* =========================================
   EVENTS
========================================= */

document
    .getElementById("searchBtn")
    .addEventListener("click", performSearch);


document
    .getElementById("searchInput")
    .addEventListener("keypress", function(e) {

        if (e.key === "Enter") {
            performSearch();
        }
    });


/* =========================================
   CLEAR
========================================= */

function clearSearchWorkspace() {

    document.getElementById("searchInput").value = "";

    document.getElementById("searchResultsBody").innerHTML = `
        <tr>
            <td colspan="15" class="empty-search-message">Workspace cleared</td>
        </tr>
    `;

    updateSummary([]);
    updateProcessingStatus("Workspace cleared", "", "completed");
}


/* =========================================
   SOURCE CHECKBOXES
========================================= */

const allCheckbox =
    document.getElementById("source_all");

const sourceCheckboxes =
    document.querySelectorAll(".source-item");


allCheckbox.addEventListener("change", function () {

    sourceCheckboxes.forEach(cb => {
        cb.checked = allCheckbox.checked;
    });

});


sourceCheckboxes.forEach(cb => {

    cb.addEventListener("change", function () {

        const checkedCount = Array.from(
            sourceCheckboxes
        ).filter(x => x.checked).length;

        allCheckbox.checked =
            checkedCount === sourceCheckboxes.length;

    });

});


/* =========================================
   TABLE
========================================= */

function populateSearchTableRows(results) {

    const tbody = document.getElementById(
        "searchResultsBody"
    );

    tbody.innerHTML = "";


    // -----------------------------------
    // EMPTY
    // -----------------------------------
    if (!results.length) {

        tbody.innerHTML = `
            <tr>
                <td colspan="15"
                    class="empty-search-message">
                    No records found
                </td>
            </tr>
        `;

        return;
    }


    // -----------------------------------
    // BUILD HTML STRING
    // -----------------------------------
    let rowsHtml = "";

    const startIndex = (currentPage - 1) * rowsPerPage;

    results.forEach((item, index) => {

        // ── Vendor Ticket (SNOW only) — PTC case link
        // Values: numeric like 18076027 or C18028229 → support.ptc.com case URL
        function vendorTicketUrl(v) {
            if (!v) return "";
            // Strip leading C if present to get numeric case ID
            const id = v.replace(/^C/i, "");
            return `https://support.ptc.com/appserver/cs/view/case.jsp?n=${id}`;
        }
        const vendorTicketCell = (item.source === "SNOW" && item.vendor_ticket && item.vendor_ticket !== "nan")
            ? item.vendor_ticket.split(",").map(v => v.trim()).filter(Boolean)
                .map(v => `<a href="${vendorTicketUrl(v)}" target="_blank" class="vendor-ticket-badge">${v}</a>`)
                .join(" ")
            : "";

        // ── Azure Bug (VCEWindchill, from Resolution Notes only)
        let azureBugCell = "";
        if (item.source === "SNOW" && item.azure_bug && item.azure_bug !== "nan") {
            azureBugCell = item.azure_bug.split(",").map(s => s.trim()).filter(Boolean)
                .map(id => {
                    const url = `https://dev.azure.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/${id}`;
                    return `<a href="${url}" target="_blank" class="azure-bug-chip">${id}</a>`;
                }).join(", ");
        }

        // ── Azure User Story (VPA, from Work Notes + Additional Comments)
        // Stored as "ID|ENV, ID|ENV, ..."
        const ENV_COLORS = {PROD:"#16a34a", QA:"#d97706", TEST:"#0891b2",
                            UAT:"#7c3aed", DEV:"#64748b", WC13:"#0f766e", STAGE:"#64748b"};
        let azureUserStoryCell = "";
        if (item.source === "SNOW" && item.azure_user_story && item.azure_user_story !== "nan") {
            azureUserStoryCell = item.azure_user_story.split(",").map(s => s.trim()).filter(Boolean)
                .map(entry => {
                    const [id, env] = entry.split("|");
                    if (!id) return "";
                    const url = `https://dev.azure.com/VolvoGroup-DVP/VPA/_workitems/edit/${id}`;
                    const envBadge = env
                        ? `<span class="env-badge" style="background:${ENV_COLORS[env]||"#64748b"}">${env}</span>`
                        : "";
                    return `<a href="${url}" target="_blank" class="azure-vpa-chip">${id}</a>${envBadge}`;
                }).join(", ");
        }

        // ── PTC Articles (from Work Notes + Additional Comments)
        let ptcArticlesCell = "";
        if (item.source === "SNOW" && item.ptc_articles && item.ptc_articles !== "nan") {
            ptcArticlesCell = item.ptc_articles.split(",").map(s => s.trim()).filter(Boolean)
                .map(aid => {
                    const url = `https://www.ptc.com/en/support/article/${aid}`;
                    return `<a href="${url}" target="_blank" class="ptc-article-chip">${aid}</a>`;
                }).join(", ");
        }

        // ── Status colour map
        const STATUS_DOT_COLOR = {
            "open":        "#D97706",
            "in progress": "#2563EB",
            "on hold":     "#DB2777",
            "resolved":    "#059669",
            "closed":      "#059669",
            "cancelled":   "#6B7280",
            "new":         "#7C3AED",
        };
        const STATUS_TEXT_COLOR = {
            "open":        "#92400E",
            "in progress": "#1E40AF",
            "on hold":     "#9D174D",
            "resolved":    "#065F46",
            "closed":      "#065F46",
            "cancelled":   "#374151",
            "new":         "#4C1D95",
        };
        const STATUS_BG_COLOR = {
            "open":        "#FEF3C7",
            "in progress": "#DBEAFE",
            "on hold":     "#FCE7F3",
            "resolved":    "#D1FAE5",
            "closed":      "#D1FAE5",
            "cancelled":   "#F3F4F6",
            "new":         "#EDE9FE",
        };

        const statusKey  = (item.status || "").toLowerCase().trim();
        const dotColor   = STATUS_DOT_COLOR[statusKey]  || "#9CA3AF";
        const textColor  = STATUS_TEXT_COLOR[statusKey] || "#111827";
        const statusBg   = STATUS_BG_COLOR[statusKey]   || "transparent";
        const statusDot  = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${dotColor};margin-right:5px;vertical-align:middle;flex-shrink:0"></span>`;
        const statusCell = `<span style="display:inline-flex;align-items:center;color:${textColor};font-weight:600;font-size:11px;background:${statusBg};padding:2px 7px;border-radius:10px;white-space:nowrap">${statusDot}${item.status}</span>`;
        const numberDot  = `<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${dotColor};margin-right:4px;vertical-align:middle;flex-shrink:0"></span>`;

        // Build the number URL: prefer server-supplied url, fall back to known patterns
        function buildNumberUrl(src, num) {
            if (!num) return "";
            if (src === "SNOW")  return `https://volvoitsm.service-now.com/nav_to.do?uri=incident.do?sysparm_query=number=${num}`;
            if (src === "AZURE") return `https://dev.azure.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/${num}`;
            if (src === "PTC")   return `https://support.ptc.com/appserver/cs/view/case.jsp?n=${num}`;
            if (src === "AOM")   return `https://dev.azure.com/VolvoGroup-DVP/VPA/_workitems/edit/${num}`;
            return "";
        }
        const numberUrl = item.url || buildNumberUrl(item.source, item.number);

        rowsHtml += `
            <tr data-source="${item.source}">

                <td>${startIndex + index + 1}</td>

                <td>

                    ${
                        numberUrl
                            ? `<a href="${numberUrl}"
                                target="_blank"
                                class="number-link number-link--${(item.source || "").toLowerCase()}">
                                    ${numberDot}${item.number}
                               </a>`
                            : `${numberDot}${item.number}`
                    }

                </td>

                <td title="${item.description}">
                    ${truncate(item.description, 45)}
                </td>

                <td>${vendorTicketCell}</td>

                <td>${azureBugCell}</td>

                <td>${azureUserStoryCell}</td>

                <td>${ptcArticlesCell}</td>

                <td>${item.priority}</td>

                <td>${statusCell}</td>

                <td>${item.created_by}</td>

                <td>${item.created_date}</td>

                <td>${item.assigned_to}</td>

                <td>${item.resolved_date}</td>


            </tr>
        `;
    });


    // -----------------------------------
    // SINGLE DOM UPDATE
    // -----------------------------------
    tbody.innerHTML = rowsHtml;

    applyColClasses();
    if (_rowColorsEnabled) applyRowColors();
}

/* =========================================
   PAGINATION
========================================= */

function renderCurrentPage() {

    rowsPerPage = parseInt(

        document.getElementById(
            "rowsPerPage"
        ).value

    );

    const start =
        (currentPage - 1) * rowsPerPage;

    const end =
        start + rowsPerPage;

    const pagedResults =
        currentResults.slice(start, end);


    populateSearchTableRows(
        pagedResults
    );

    updatePageInfo();
}


/* =========================================
   PAGE INFO
========================================= */

function updatePageInfo() {

    const total =
        currentResults.length;

    const totalPages = Math.max(
        1,
        Math.ceil(total / rowsPerPage)
    );

    const start =
        total === 0
            ? 0
            : ((currentPage - 1) * rowsPerPage) + 1;

    const end =
        Math.min(
            currentPage * rowsPerPage,
            total
        );


    document.getElementById(
        "pageInfo"
    ).innerText =
        `${start} to ${end} of ${total}`;


    // buttons
    document.getElementById(
        "firstPageBtn"
    ).disabled = currentPage === 1;

    document.getElementById(
        "prevPageBtn"
    ).disabled = currentPage === 1;

    document.getElementById(
        "nextPageBtn"
    ).disabled =
        currentPage === totalPages;

    document.getElementById(
        "lastPageBtn"
    ).disabled =
        currentPage === totalPages;
}

/* =========================================
   SUMMARY
========================================= */

function updateSummary(results) {

    document.getElementById("resultCount").innerText =
        results.length;

    document.getElementById("azureCount").innerText =
        results.filter(x => x.source === "AZURE").length;

    document.getElementById("snowCount").innerText =
        results.filter(x => x.source === "SNOW").length;

    document.getElementById("ptcCount").innerText =
        results.filter(x => x.source === "PTC").length;

    const aomEl = document.getElementById("aomCount");
    if (aomEl) aomEl.innerText = results.filter(x => x.source === "AOM").length;
}


/* =========================================
   TRUNCATE
========================================= */

function truncate(text, len) {

    if (!text) return "";

    return text.length > len
        ? text.substring(0, len) + "..."
        : text;
}

/* =========================================
   APPLY FILTERS
========================================= */

function applySearchFilters() {

    document.getElementById("searchStatusText").innerText =
        "Filters updated";

}

/* =========================================
   INITIAL LOAD
========================================= */

loadFilterOptions();

/* =========================================
   DATE FILTER MODES
========================================= */

function handleDateFilterType() {

    // hide all
    document
        .querySelectorAll(".date-sub-section")
        .forEach(el => {
            el.classList.remove(
                "active-date-section"
            );
        });


    const type =
        document.getElementById(
            "dateFilterType"
        ).value;


    // no filter
    if (type === "none") {
        return;
    }


    // date range
    if (type === "range") {

        document
            .getElementById(
                "dateRangeSection"
            )
            .classList.add(
                "active-date-section"
            );
    }


    // year
    if (type === "year") {

        document
            .getElementById(
                "yearSection"
            )
            .classList.add(
                "active-date-section"
            );
    }


    // quick
    if (type === "quick") {

        document
            .getElementById(
                "quickSection"
            )
            .classList.add(
                "active-date-section"
            );
    }
}


/* =========================================
   INITIALIZE DATE FILTER
========================================= */

handleDateFilterType();


/* =========================================
   ROWS
========================================= */

document
    .getElementById("rowsPerPage")
    .addEventListener("change", function() {

        currentPage = 1;

        renderCurrentPage();
    });


/* =========================================
   PAGINATION BUTTONS
========================================= */

document
    .getElementById("firstPageBtn")
    .addEventListener("click", function() {

        currentPage = 1;

        renderCurrentPage();
    });


document
    .getElementById("prevPageBtn")
    .addEventListener("click", function() {

        if (currentPage > 1) {

            currentPage--;

            renderCurrentPage();
        }
    });


document
    .getElementById("nextPageBtn")
    .addEventListener("click", function() {

        const totalPages = Math.ceil(
            currentResults.length /
            rowsPerPage
        );

        if (currentPage < totalPages) {

            currentPage++;

            renderCurrentPage();
        }
    });


document
    .getElementById("lastPageBtn")
    .addEventListener("click", function() {

        currentPage = Math.ceil(
            currentResults.length /
            rowsPerPage
        );

        renderCurrentPage();
    });

/* =========================================================
   COLUMN RESIZE + SAVE PREFERENCE
========================================================= */

const COLUMN_STORAGE_KEY = "search_table_column_widths";

const defaultColumnWidths = {
    slno: 70,
    number: 150,
    description: 420,
    priority: 150,
    status: 140,
    createdby: 220,
    createddate: 160,
    assignedto: 220,
    resolveddate: 160
};

/* =========================================================
   LOAD SAVED WIDTHS
========================================================= */

function loadColumnWidths() {

    const saved =
        JSON.parse(
            localStorage.getItem(COLUMN_STORAGE_KEY)
        ) || defaultColumnWidths;

    Object.keys(saved).forEach(column => {

        const col = document.getElementById(`col-${column}`);

        if (col) {
            col.style.width = `${saved[column]}px`;
        }
    });
}

/* =========================================================
   SAVE WIDTH
========================================================= */

function saveColumnWidth(column, width) {

    const saved =
        JSON.parse(
            localStorage.getItem(COLUMN_STORAGE_KEY)
        ) || defaultColumnWidths;

    saved[column] = width;

    localStorage.setItem(
        COLUMN_STORAGE_KEY,
        JSON.stringify(saved)
    );
}

/* =========================================================
   ENABLE RESIZE
========================================================= */

function enableColumnResize() {

    const headers =
        document.querySelectorAll(
            "#searchResultsTable th"
        );

    headers.forEach(header => {

        const handle =
            header.querySelector(".resize-handle");

        if (!handle) return;

        handle.addEventListener("mousedown", function (e) {

            e.preventDefault();

            const column =
                header.dataset.column;

            const col =
                document.getElementById(
                    `col-${column}`
                );

            const startX = e.pageX;

            const startWidth =
                col.offsetWidth;

            function mouseMoveHandler(e) {

                const newWidth =
                    startWidth +
                    (e.pageX - startX);

                if (newWidth < 60) return;

                col.style.width =
                    `${newWidth}px`;
            }

            function mouseUpHandler(e) {

                const finalWidth =
                    col.offsetWidth;

                saveColumnWidth(
                    column,
                    finalWidth
                );

                document.removeEventListener(
                    "mousemove",
                    mouseMoveHandler
                );

                document.removeEventListener(
                    "mouseup",
                    mouseUpHandler
                );
            }

            document.addEventListener(
                "mousemove",
                mouseMoveHandler
            );

            document.addEventListener(
                "mouseup",
                mouseUpHandler
            );
        });
    });
}

/* =========================================================
   INITIALIZE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadColumnWidths();

        enableColumnResize();
    }
);


/* =========================================
   EXISTING GROUPS (sidebar)
========================================= */

function toggleExistingGroupsSection() {

    const existing =
        document.getElementById(
            "existingGroupsSection"
        );

    const isVisible =
        existing.classList.contains(
            "active-group-section"
        );

    existing.classList.toggle(
        "active-group-section",
        !isVisible
    );

    if (!isVisible) {

        loadExistingGroups();
    }
}


/* =========================================
   LOAD EXISTING GROUPS (sidebar — individual collapsible)
========================================= */

async function loadExistingGroups() {

    const container = document.getElementById("existingGroupsContainer");
    container.innerHTML = "";

    try {

        const response = await fetch("/search/group-members");
        const data     = await response.json();
        const groups   = data.groups || {};

        if (!Object.keys(groups).length) {
            container.innerHTML =
                `<div style="color:rgba(255,255,255,0.5);font-size:12px;padding:8px 0;">No groups defined yet.</div>`;
            return;
        }

        Object.keys(groups).sort().forEach(groupName => {

            const members = groups[groupName];
            const safeId  = groupName.replace(/\W/g, "_");
            const btnId   = "grp-btn-"   + safeId;
            const panelId = "grp-panel-" + safeId;

            // Group toggle button
            const btn = document.createElement("button");
            btn.className = "sidebar-group-btn";
            btn.id = btnId;
            btn.innerHTML =
                `<span class="sidebar-group-name">${groupName}</span>` +
                `<span class="sidebar-group-count">${members.length}</span>` +
                `<span class="sidebar-group-arrow">▾</span>`;

            btn.addEventListener("click", () => {
                const panel = document.getElementById(panelId);
                const arrow = btn.querySelector(".sidebar-group-arrow");
                const isOpen = panel.classList.contains("sidebar-group-open");

                // Collapse all other panels
                document.querySelectorAll(".sidebar-group-panel").forEach(p => p.classList.remove("sidebar-group-open"));
                document.querySelectorAll(".sidebar-group-btn").forEach(b => {
                    b.classList.remove("sidebar-group-active");
                    b.querySelector(".sidebar-group-arrow").textContent = "▾";
                });

                if (!isOpen) {
                    panel.classList.add("sidebar-group-open");
                    btn.classList.add("sidebar-group-active");
                    arrow.textContent = "▴";
                }
            });

            // Member panel
            const panel = document.createElement("div");
            panel.className = "sidebar-group-panel";
            panel.id = panelId;

            members.forEach(m => {
                const row = document.createElement("div");
                row.className = "sidebar-group-member";
                row.textContent = m;
                panel.appendChild(row);
            });

            container.appendChild(btn);
            container.appendChild(panel);
        });

    } catch(error) {
        console.error(error);
    }
}


/* =========================================
   USER GROUP MODAL — OPEN
========================================= */

async function openUserGroupModal() {

    document.getElementById("userGroupModal").classList.add("ugm-visible");
    document.getElementById("ugmGroupNameInput").value = "";
    ugmGroupMembers = [];
    renderUgmGroupMembers();

    // Always open on Manage tab
    switchUgmTab("manage");
    await loadUgmAllUsers();
}


/* =========================================
   TAB SWITCHING
========================================= */

function switchUgmTab(tab) {

    // Deactivate all tabs + panels
    document.querySelectorAll(".ugm-tab").forEach(t => t.classList.remove("active-ugm-tab"));
    document.querySelectorAll(".ugm-tab-panel").forEach(p => p.classList.add("ugm-tab-hidden"));

    document.getElementById("tab-" + tab).classList.add("active-ugm-tab");
    document.getElementById("panel-" + tab).classList.remove("ugm-tab-hidden");

    if (tab === "existing") {
        loadUgmExistingGroups();
    }
}


/* =========================================
   USER GROUP MODAL — CLOSE
========================================= */

function closeUserGroupModal() {
    document.getElementById("userGroupModal").classList.remove("ugm-visible");
}

function closeUserGroupModalOutside(event) {
    if (event.target === document.getElementById("userGroupModal")) {
        closeUserGroupModal();
    }
}


/* =========================================
   LOAD ALL USERS INTO MODAL
========================================= */

async function loadUgmAllUsers() {

    const container = document.getElementById("ugmAllUsersList");
    container.innerHTML = `<div class="ugm-loading">Loading users...</div>`;

    try {

        const response = await fetch("/search/group-users");
        const data = await response.json();

        ugmAllUsers = (data.users || []).sort();
        renderUgmAllUsers(ugmAllUsers);

    } catch(error) {

        container.innerHTML = `<div class="ugm-loading">Failed to load users</div>`;
        console.error(error);
    }
}


/* =========================================
   RENDER ALL USERS LIST
========================================= */

function renderUgmAllUsers(users) {

    const container = document.getElementById("ugmAllUsersList");
    container.innerHTML = "";

    if (!users.length) {
        container.innerHTML = `<div class="ugm-loading">No users found</div>`;
        return;
    }

    users.forEach(user => {

        // skip already in group
        if (ugmGroupMembers.includes(user)) return;

        const row = document.createElement("div");
        row.className = "ugm-user-row";
        row.dataset.user = user;
        row.textContent = user;

        row.addEventListener("click", function() {
            document.querySelectorAll(".ugm-user-row.ugm-selected")
                .forEach(r => r.classList.remove("ugm-selected"));
            row.classList.toggle("ugm-selected");
        });

        row.addEventListener("dblclick", function() {
            addUserToGroup(user);
        });

        container.appendChild(row);
    });
}


/* =========================================
   FILTER USERS
========================================= */

function filterUgmUsers() {

    const query = document.getElementById("ugmSearchUserInput").value.toLowerCase();
    const filtered = ugmAllUsers.filter(u => u.toLowerCase().includes(query));
    renderUgmAllUsers(filtered);
}

function clearUgmSearch() {
    document.getElementById("ugmSearchUserInput").value = "";
    renderUgmAllUsers(ugmAllUsers);
}


/* =========================================
   ADD SELECTED USERS TO GROUP
========================================= */

function addSelectedToGroup() {

    const selected = Array.from(
        document.querySelectorAll(".ugm-user-row.ugm-selected")
    ).map(el => el.dataset.user);

    if (!selected.length) {
        // try to add all visible if none selected
        return;
    }

    selected.forEach(user => addUserToGroup(user));
}

function addUserToGroup(user) {

    if (!ugmGroupMembers.includes(user)) {
        ugmGroupMembers.push(user);
        ugmGroupMembers.sort();
    }

    renderUgmGroupMembers();

    // refresh left list
    const query = document.getElementById("ugmSearchUserInput").value.toLowerCase();
    const filtered = ugmAllUsers.filter(u => u.toLowerCase().includes(query));
    renderUgmAllUsers(filtered);
}


/* =========================================
   RENDER GROUP MEMBERS (right panel)
========================================= */

function renderUgmGroupMembers() {

    const container = document.getElementById("ugmGroupMembersList");
    container.innerHTML = "";

    ugmGroupMembers.forEach(user => {

        const row = document.createElement("div");
        row.className = "ugm-member-row";
        row.dataset.user = user;
        row.textContent = user;

        row.addEventListener("click", function() {
            document.querySelectorAll(".ugm-member-row.ugm-selected")
                .forEach(r => r.classList.remove("ugm-selected"));
            row.classList.toggle("ugm-selected");
        });

        container.appendChild(row);
    });
}


/* =========================================
   REMOVE SELECTED FROM GROUP
========================================= */

function removeSelectedFromGroup() {

    const selected = Array.from(
        document.querySelectorAll(".ugm-member-row.ugm-selected")
    ).map(el => el.dataset.user);

    ugmGroupMembers = ugmGroupMembers.filter(u => !selected.includes(u));

    renderUgmGroupMembers();

    const query = document.getElementById("ugmSearchUserInput").value.toLowerCase();
    const filtered = ugmAllUsers.filter(u => u.toLowerCase().includes(query));
    renderUgmAllUsers(filtered);
}


/* =========================================
   SAVE GROUP FROM MODAL
========================================= */

async function saveGroupMappingFromModal() {

    const groupName = document.getElementById("ugmGroupNameInput").value.trim();

    if (!groupName) {
        alert("Please enter a group name.");
        return;
    }

    if (!ugmGroupMembers.length) {
        alert("Please add at least one member to the group.");
        return;
    }

    try {

        const response = await fetch("/search/save-group", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                group_name: groupName,
                users: ugmGroupMembers
            })
        });

        const result = await response.json();

        if (result.success) {
            alert(`Group "${groupName}" saved successfully.`);
            loadFilterOptions();
            loadExistingGroups();
        } else {
            alert("Save failed: " + (result.message || "Unknown error"));
        }

    } catch(error) {

        console.error(error);
        alert("Save failed.");
    }
}

async function saveAndCloseGroupModal() {
    await saveGroupMappingFromModal();
    closeUserGroupModal();
}


/* =========================================
   DOWNLOAD RESULTS EXCEL
========================================= */

document
    .getElementById("downloadBtn")
    .addEventListener("click", downloadResults);


/* =========================================
   DOWNLOAD FUNCTION
========================================= */

function downloadResults() {

    if (!currentResults.length) {
        alert("No results available");
        return;
    }

    // Sort by number descending before sending
    const sorted = [...currentResults].sort((a, b) => {
        const na = parseInt(String(a.number || "").replace(/\D/g, "")) || 0;
        const nb = parseInt(String(b.number || "").replace(/\D/g, "")) || 0;
        return nb - na;
    });

    const btn = document.getElementById("downloadBtn");
    const origText = btn ? btn.textContent : "";
    if (btn) { btn.textContent = "Building…"; btn.disabled = true; }

    fetch("/search/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows: sorted })
    })
    .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.error || res.statusText); });
        // Extract filename from Content-Disposition header
        const cd  = res.headers.get("Content-Disposition") || "";
        const m   = cd.match(/filename[^;=\n]*=(['"]?)([^\n;]+)\1/);
        const fn  = m ? m[2].trim() : "search-report.xlsx";
        return res.blob().then(blob => ({ blob, fn }));
    })
    .then(({ blob, fn }) => {
        const url = URL.createObjectURL(blob);
        const a   = document.createElement("a");
        a.href    = url;
        a.download = fn;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    })
    .catch(err => {
        console.error("Download error:", err);
        alert("Download failed: " + err.message);
    })
    .finally(() => {
        if (btn) { btn.textContent = origText; btn.disabled = false; }
    });
}


function cleanUserDisplay(value) {
    if (!value) return "";
    return String(value).replace(/<.*?>/g, "").trim();
}

/* =========================================
   REFRESH USERS FROM DATA FILES
========================================= */

async function runCollectUsers() {

    const btn = document.getElementById("ugmRefreshBtn");
    const status = document.getElementById("ugmRefreshStatus");
    const preview = document.getElementById("ugmRefreshPreview");
    const countBadge = document.getElementById("ugmRefreshCount");
    const userList = document.getElementById("ugmRefreshUserList");

    btn.disabled = true;
    btn.textContent = "⏳ Collecting...";
    status.className = "ugm-refresh-status ugm-status-info";
    status.textContent = "Reading data files and parsing user names...";
    preview.classList.add("ugm-tab-hidden");

    try {

        const response = await fetch("/search/collect-users", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        // Guard against HTML error pages (404, 500, server not restarted)
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            const html = await response.text();
            status.className = "ugm-refresh-status ugm-status-error";
            if (response.status === 404) {
                status.innerHTML = `
                    ❌ <strong>Route not found (404)</strong> — the server needs to be restarted
                    to load the new <code>/search/collect-users</code> endpoint.<br><br>
                    <strong>Fix:</strong> Stop the server and run <code>python search/app.py</code> again,
                    then click Refresh Users.
                `;
            } else {
                status.innerHTML = `❌ Server error (HTTP ${response.status}). Please restart the server and try again.`;
            }
            return;
        }

        const data = await response.json();

        if (!data.success) {
            status.className = "ugm-refresh-status ugm-status-error";
            status.textContent = "❌ Error: " + (data.error || "Unknown error");
            return;
        }

        // Success
        status.className = "ugm-refresh-status ugm-status-success";
        status.textContent = `✅ Successfully collected ${data.count} unique users and saved to user_group_mapping.csv`;

        countBadge.textContent = data.count;

        // Render preview list
        userList.innerHTML = "";
        (data.users || []).forEach(u => {
            const row = document.createElement("div");
            row.className = "ugm-refresh-user-row";
            row.textContent = u;
            userList.appendChild(row);
        });

        preview.classList.remove("ugm-tab-hidden");

        // Also refresh the main user list so new users appear immediately
        ugmAllUsers = data.users || [];

    } catch(error) {

        status.className = "ugm-refresh-status ugm-status-error";
        status.textContent = "❌ Network error: " + error.message;
        console.error(error);

    } finally {

        btn.disabled = false;
        btn.textContent = "🔄 Refresh Users from Data Files";
    }
}


/* =========================================
   LOAD EXISTING GROUPS (modal tab)
========================================= */

async function loadUgmExistingGroups() {

    const container = document.getElementById("ugmExistingGroupsContainer");
    container.innerHTML = `<div class="ugm-loading">Loading groups...</div>`;

    try {

        const response = await fetch("/search/group-members");
        const data = await response.json();
        const groups = data.groups || {};

        if (!Object.keys(groups).length) {
            container.innerHTML = `<div class="ugm-loading">No groups defined yet. Use "Manage Group" to create one.</div>`;
            return;
        }

        container.innerHTML = "";

        Object.keys(groups).sort().forEach(groupName => {

            const members = groups[groupName];

            const card = document.createElement("div");
            card.className = "ugm-existing-card";

            const header = document.createElement("div");
            header.className = "ugm-existing-card-header";

            const title = document.createElement("div");
            title.className = "ugm-existing-card-title";
            title.textContent = groupName;

            const editBtn = document.createElement("button");
            editBtn.className = "ugm-edit-group-btn";
            editBtn.textContent = "✏ Edit";
            editBtn.onclick = () => loadGroupForEditing(groupName, members);

            const countPill = document.createElement("span");
            countPill.className = "ugm-member-count";
            countPill.textContent = members.length + " member" + (members.length !== 1 ? "s" : "");

            header.appendChild(title);
            header.appendChild(countPill);
            header.appendChild(editBtn);

            const memberDiv = document.createElement("div");
            memberDiv.className = "ugm-existing-members";

            members.forEach(m => {
                const row = document.createElement("div");
                row.className = "ugm-existing-member-row";
                row.textContent = m;
                memberDiv.appendChild(row);
            });

            card.appendChild(header);
            card.appendChild(memberDiv);
            container.appendChild(card);
        });

    } catch(error) {

        container.innerHTML = `<div class="ugm-loading">Failed to load groups.</div>`;
        console.error(error);
    }
}


/* =========================================
   LOAD GROUP FOR EDITING
========================================= */

async function loadGroupForEditing(groupName, members) {

    // Switch to Manage tab
    switchUgmTab("manage");

    // Pre-fill group name
    document.getElementById("ugmGroupNameInput").value = groupName;

    // Pre-fill members
    ugmGroupMembers = [...members];
    renderUgmGroupMembers();

    // Refresh user list if empty
    if (!ugmAllUsers.length) {
        await loadUgmAllUsers();
    } else {
        renderUgmAllUsers(ugmAllUsers);
    }
}

/* =========================================
   SEARCH HELP MODAL
   Integrates with common.js toggleHelpSystemModal() via
   loadModuleHelpData() callback — called automatically when
   the top-nav ? button is clicked.
========================================= */

let helpSections = [];

// Called by common.js toggleHelpSystemModal() when modal opens
async function loadModuleHelpData() {

    if (helpSections.length) {
        // Already loaded — just make sure first item is selected
        if (!document.querySelector(".help-index-item.active-help-topic")) {
            if (helpSections.length) showHelpSection(helpSections[0].id);
        }
        return;
    }

    try {
        const response = await fetch("/search/help-data");
        const data = await response.json();
        helpSections = data.sections || [];
        renderHelpNav();
        if (helpSections.length) showHelpSection(helpSections[0].id);
    } catch(e) {
        const nav = document.getElementById("helpNav");
        if (nav) nav.innerHTML = `<div class="help-empty-state">Failed to load help.</div>`;
    }
}

// Close when clicking backdrop
function handleHelpBackdropClick(event) {
    if (event.target === document.getElementById("helpSystemModal")) {
        toggleHelpSystemModal();
    }
}

function renderHelpNav() {

    const nav = document.getElementById("helpNav");
    if (!nav) return;
    nav.innerHTML = "";

    helpSections.forEach(section => {

        const btn = document.createElement("button");
        btn.className = "help-index-item";    // common.css class
        btn.id = "help-nav-" + section.id;
        btn.innerHTML = `<span style="margin-right:8px">${section.icon}</span>${section.title}`;
        btn.addEventListener("click", () => showHelpSection(section.id));
        nav.appendChild(btn);
    });
}

function showHelpSection(id) {

    const section = helpSections.find(s => s.id === id);
    if (!section) return;

    // Highlight active nav item using common.css class
    document.querySelectorAll(".help-index-item")
        .forEach(b => b.classList.remove("active-help-topic"));
    const navBtn = document.getElementById("help-nav-" + id);
    if (navBtn) navBtn.classList.add("active-help-topic");

    // Render content into right pane
    const pane = document.getElementById("helpContent");
    if (pane) {
        pane.innerHTML =
            `<h3>${section.icon} ${section.title}</h3>` +
            section.content;
    }
}


/* =========================================
   TABLE COLUMN SORTING
========================================= */

// ── Sort state ──────────────────────────────────────────────────────────────
let _sortKey          = "";     // empty = no sort applied yet
let _sortDir          = "asc";
let _prefSortApplied  = false;  // true only after user sets a preference sort

function sortResults(key) {
    // Toggle direction if same key, else new key ascending
    if (_sortKey === key) {
        _sortDir = (_sortDir === "asc") ? "desc" : "asc";
    } else {
        _sortKey = key;
        _sortDir = "asc";
    }
    _prefSortApplied = false;   // manual column click, not preference

    // Update header arrow indicators
    document.querySelectorAll("th[data-sort]").forEach(th => {
        th.classList.remove("sort-asc","sort-desc");
        if (th.dataset.sort === key) {
            th.classList.add(_sortDir === "asc" ? "sort-asc" : "sort-desc");
        }
    });

    applySort();
    currentPage = 1;
    renderCurrentPage();
}

function applySort() {
    if (!_sortKey || !currentResults.length) return;
    const key = _sortKey;
    const dir = _sortDir;
    currentResults.sort((a, b) => {
        let va = a[key] || "";
        let vb = b[key] || "";

        // Numeric sort for Number column (strip non-digits)
        if (key === "number") {
            const na = parseInt(String(va).replace(/\D/g, "")) || 0;
            const nb = parseInt(String(vb).replace(/\D/g, "")) || 0;
            return dir === "asc" ? na - nb : nb - na;
        }
        // Date sort
        if (key === "created_date" || key === "resolved_date") {
            const da = va ? new Date(va) : new Date(0);
            const db = vb ? new Date(vb) : new Date(0);
            return dir === "asc" ? da - db : db - da;
        }
        // String sort (case-insensitive)
        va = String(va).toLowerCase();
        vb = String(vb).toLowerCase();
        if (va < vb) return dir === "asc" ? -1 : 1;
        if (va > vb) return dir === "asc" ?  1 : -1;
        return 0;
    });
}

function applyPreferenceSort() {
    const byEl  = document.getElementById("pref-sort-by");
    const dirEl = document.getElementById("pref-sort-dir");
    if (!byEl || !dirEl || !currentResults.length) return;
    _sortKey         = byEl.value;
    _sortDir         = dirEl.value;
    _prefSortApplied = true;

    // Clear column header arrows (preference overrides manual click)
    document.querySelectorAll("th[data-sort]").forEach(th => {
        th.classList.remove("sort-asc","sort-desc");
    });

    applySort();
    currentPage = 1;
    renderCurrentPage();
}

/* =========================================
   SETTINGS / PREFERENCES
========================================= */

// --- Column visibility ---
const _hiddenCols = new Set();

function toggleColumn(colKey, visible) {
    const col = document.getElementById(`col-${colKey}`);
    const ths = document.querySelectorAll(`th[data-column="${colKey}"]`);
    const tds = document.querySelectorAll(`td.col-${colKey}`);

    if (visible) {
        _hiddenCols.delete(colKey);
        if (col) col.style.display = "";
        ths.forEach(el => el.style.display = "");
        tds.forEach(el => el.style.display = "");
    } else {
        _hiddenCols.add(colKey);
        if (col) col.style.display = "none";
        ths.forEach(el => el.style.display = "none");
        tds.forEach(el => el.style.display = "none");
    }

    // Re-render so new rows get the right class
    renderCurrentPage();
}

// Attach col class to each <td> so toggleColumn can target them
// Called after populateSearchTableRows builds innerHTML
function applyColClasses() {
    const table = document.querySelector("#searchResultsBody");
    if (!table) return;
    const colOrder = [
        "slno","number","description",
        "vendorticket","azurebug","azureuserstory","ptcarticles",
        "priority","status","createdby","createddate","assignedto","resolveddate"
    ];
    table.querySelectorAll("tr").forEach(tr => {
        Array.from(tr.cells).forEach((td, i) => {
            if (colOrder[i]) td.classList.add(`col-${colOrder[i]}`);
            // Apply hidden state
            if (colOrder[i] && _hiddenCols.has(colOrder[i])) {
                td.style.display = "none";
            }
        });
    });
}

// --- Row source colouring ---
let _rowColorsEnabled = true;

function toggleRowColors(enabled) {
    _rowColorsEnabled = enabled;
    renderCurrentPage();
}

function applyRowColors() {
    if (!_rowColorsEnabled) return;
    document.querySelectorAll("#searchResultsBody tr").forEach(tr => {
        const src = tr.dataset.source || "";
        tr.classList.remove("row-snow","row-azure","row-ptc","row-aom");
        if (src === "SNOW")  tr.classList.add("row-snow");
        if (src === "AZURE") tr.classList.add("row-azure");
        if (src === "PTC")   tr.classList.add("row-ptc");
        if (src === "AOM")   tr.classList.add("row-aom");
    });
}
