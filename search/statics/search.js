/* =========================================
   GLOBAL STATE
========================================= */

let currentResults = [];

let currentPage = 1;

let rowsPerPage = 10;

/* =========================================
   SHOW SEARCH SECTION
========================================= */
function showSearchSection(section) {

    document
        .querySelectorAll(".dock-section")
        .forEach(el => {
            el.classList.remove("active-section");
        });

    document
        .querySelectorAll(".dock-item")
        .forEach(el => {
            el.classList.remove("active-dock");
        });

    document
        .getElementById(section + "-section")
        .classList.add("active-section");

    event.currentTarget.classList.add("active-dock");
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
   SEARCH
========================================= */

async function performSearch() {

    try {

        // -----------------------------------
        // QUERY
        // -----------------------------------
        const query =
            document.getElementById(
                "searchInput"
            ).value.trim();


        // -----------------------------------
        // STATUS UI
        // -----------------------------------
        document.getElementById(
            "searchStatusText"
        ).innerText = "Searching issues...";


        const progressBar =
            document.getElementById(
                "searchProgressFill"
            );

        progressBar.style.width = "70%";

        progressBar.classList.add(
            "active-progress"
        );


        // -----------------------------------
        // SOURCE FILTERS
        // -----------------------------------
        const selectedSources = Array.from(

            document.querySelectorAll(
                ".source-item:checked"
            )

        ).map(el => el.value);


        // -----------------------------------
        // DROPDOWN FILTERS
        // -----------------------------------
        const selectedStatus =
            document.getElementById(
                "statusFilter"
            ).value;

        const selectedPriority =
            document.getElementById(
                "priorityFilter"
            ).value;

        const selectedGroup =
            document.getElementById(
                "groupFilter"
            ).value;


        // -----------------------------------
        // DATE FILTERS
        // -----------------------------------
        const dateField =
            document.getElementById(
                "dateField"
            ).value;

        const startDate =
            document.getElementById(
                "startDate"
            ).value;

        const endDate =
            document.getElementById(
                "endDate"
            ).value;


        // -----------------------------------
        // API CALL
        // -----------------------------------
        const response = await fetch(
            "/search/issues",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    query: query,

                    sources: selectedSources,

                    status: selectedStatus,

                    priority: selectedPriority,

                    group: selectedGroup,

                    date_field: dateField,

                    start_date: startDate,

                    end_date: endDate
                })
            }
        );


        // -----------------------------------
        // RESPONSE
        // -----------------------------------
        const data =
            await response.json();


        // -----------------------------------
        // ERROR
        // -----------------------------------
        if (data.error) {

            document.getElementById(
                "searchStatusText"
            ).innerText = data.error;

            progressBar.style.width = "0%";

            progressBar.classList.remove(
                "active-progress"
            );

            return;
        }


        // -----------------------------------
        // TABLE
        // -----------------------------------
        currentResults = data.results;

        currentPage = 1;

        renderCurrentPage();

        updateSummary(currentResults);

        // -----------------------------------
        // COMPLETE
        // -----------------------------------
        document.getElementById(
            "searchStatusText"
        ).innerText =
            "Search completed successfully";


        progressBar.style.width = "100%";

        progressBar.classList.remove(
            "active-progress"
        );

    }

    catch(error) {

        console.error(error);

        document.getElementById(
            "searchStatusText"
        ).innerText =
            "Search failed";

        document.getElementById(
            "searchProgressFill"
        ).classList.remove(
            "active-progress"
        );
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
            <td colspan="11"
                class="empty-search-message">
                Workspace cleared
            </td>
        </tr>
    `;

    updateSummary([]);

    document.getElementById("searchStatusText").innerText =
        "Workspace cleared";

    const progressBar =
        document.getElementById("searchProgressFill");

    progressBar.style.width = "0%";

    progressBar.classList.remove("active-progress");
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
                <td colspan="11"
                    class="empty-search-message">
                    No records found
                </td>
            </tr>
        `;

        return;
    }


    // -----------------------------------
    // LIMIT LARGE DATASETS
    // -----------------------------------
    const limitedResults = results.slice(0, 500);


    // -----------------------------------
    // BUILD HTML STRING
    // -----------------------------------
    let rowsHtml = "";


    limitedResults.forEach((item, index) => {

        rowsHtml += `
            <tr>

                <td>${index + 1}</td>

                <td>

                    ${
                        item.url
                            ? `
                                <a href="${item.url}"
                                target="_blank"
                                class="number-link">

                                    ${item.number}

                                </a>
                            `
                            : item.number
                    }

                </td>

                <td title="${item.description}">
                    ${truncate(item.description, 45)}
                </td>

                <td>${item.priority}</td>

                <td>${item.status}</td>

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


    // -----------------------------------
    // LARGE RESULT WARNING
    // -----------------------------------
    if (results.length > 500) {

        tbody.innerHTML += `
            <tr>

                <td colspan="9"
                    class="empty-search-message">

                    Showing first 500 records out of
                    ${results.length}

                </td>

            </tr>
        `;
    }
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
   ACTIVATE MANAGE GROUP
========================================= */

function activateManageGroup() {

    const panel =
        document.getElementById(
            "groupManagePanel"
        );

    panel.classList.toggle(
        "active-group-panel"
    );

    loadUsersForGroupMapping();
    loadExistingGroups();
}


/* =========================================
   LOAD USERS
========================================= */

async function loadUsersForGroupMapping() {

    const container =
        document.getElementById(
            "groupUsersContainer"
        );

    container.innerHTML =
        `<div class="loading-users">
            Loading users...
        </div>`;

    try {

        const response = await fetch(
            "/search/group-users"
        );

        const data =
            await response.json();

        const users =
            data.users || [];

        container.innerHTML = "";

        users
            .sort()
            .forEach(user => {

                container.innerHTML += `
                    <label>

                        <input
                            type="checkbox"
                            value="${user}"
                        >

                        <span>${user}</span>

                    </label>
                `;
            });

    }

    catch(error) {

        console.error(error);

        container.innerHTML =
            `<div class="loading-users">
                Failed to load users
            </div>`;
    }
}

/* =========================================
   SAVE GROUP
========================================= */

async function saveGroupMapping() {

    const groupName =
        document.getElementById(
            "groupNameInput"
        ).value.trim();

    const users = Array.from(

        document.querySelectorAll(
            "#groupUsersContainer input:checked"
        )

    ).map(cb => cb.value);


    if (!groupName) {

        alert(
            "Enter group name"
        );

        return;
    }


    const response = await fetch(
        "/search/save-group",
        {

            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify({

                group_name: groupName,

                users: users
            })
        }
    );

    const result =
        await response.json();


    if (result.success) {

        alert(
            "Group saved successfully"
        );

        loadFilterOptions();
        loadExistingGroups();
    }
}

/* =========================================
   LOAD EXISTING GROUPS
========================================= */

async function loadExistingGroups() {

    const container =
        document.getElementById(
            "existingGroupsContainer"
        );

    container.innerHTML = "";

    try {

        const response =
            await fetch(
                "/search/group-members"
            );

        const data =
            await response.json();

        const groups =
            data.groups || {};

        Object.keys(groups)
            .sort()
            .forEach(group => {

                const users =
                    groups[group];

                let usersHtml = "";

                users.forEach(user => {

                    usersHtml += `
                        <div class="group-member-row">
                            ${user}
                        </div>
                    `;
                });

                container.innerHTML += `

                    <div class="group-card">

                        <div class="group-card-title">
                            ${group}
                        </div>

                        <div class="group-card-users">

                            ${usersHtml}

                        </div>

                    </div>
                `;
            });

    }

    catch(error) {

        console.error(error);
    }
}

/* =========================================
   TOGGLE MANAGE GROUP
========================================= */

function toggleManageGroupSection() {

    const manage =
        document.getElementById(
            "manageGroupSection"
        );

    const existing =
        document.getElementById(
            "existingGroupsSection"
        );

    const isVisible =
        manage.classList.contains(
            "active-group-section"
        );

    manage.classList.toggle(
        "active-group-section",
        !isVisible
    );

    existing.classList.remove(
        "active-group-section"
    );

    if (!isVisible) {

        loadUsersForGroupMapping();
    }
}

/* =========================================
   TOGGLE EXISTING GROUPS
========================================= */

function toggleExistingGroupsSection() {

    const manage =
        document.getElementById(
            "manageGroupSection"
        );

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

    manage.classList.remove(
        "active-group-section"
    );

    if (!isVisible) {

        loadExistingGroups();
    }
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

    // -----------------------------------
    // FORMAT DATA
    // -----------------------------------
    const exportData = currentResults.map(row => ({

        "Number": row.number,
        "Description": row.description,
        "Priority": row.priority,
        "Status": row.status,
        "Created By": cleanUserDisplay(row.created_by),
        "Created Date": row.created_date,
        "Assigned To": cleanUserDisplay(row.assigned_to),
        "Resolved Date": row.resolved_date,
        "Source": row.source

    }));


    // -----------------------------------
    // CREATE SHEET
    // -----------------------------------
    const worksheet =
        XLSX.utils.json_to_sheet(exportData);


    // -----------------------------------
    // COLUMN WIDTHS
    // -----------------------------------
    worksheet["!cols"] = [

        { wch: 18 }, // Number
        { wch: 50 }, // Description
        { wch: 14 }, // Priority
        { wch: 16 }, // Status
        { wch: 28 }, // Created By
        { wch: 16 }, // Created Date
        { wch: 28 }, // Assigned To
        { wch: 16 }, // Resolved Date
        { wch: 12 }  // Source

    ];


    // -----------------------------------
    // CREATE WORKBOOK
    // -----------------------------------
    const workbook =
        XLSX.utils.book_new();

    XLSX.utils.book_append_sheet(
        workbook,
        worksheet,
        "Search Results"
    );

    /* =========================================
    CLEAN USER DISPLAY
    ========================================= */

    function cleanUserDisplay(value) {

        if (!value) {
            return "";
        }

        return String(value)
            .replace(/<.*?>/g, "")
            .trim();
    }    

    /* =========================================
    FILE NAME
    ========================================= */

    const today = new Date();

    const day =
        String(today.getDate()).padStart(2, "0");

    const month =
        today.toLocaleString(
            "en-US",
            { month: "short" }
        ).toUpperCase();

    const year =
        today.getFullYear();

    const fileName =
        `Case_Report_${day}${month}${year}.xlsx`;


    /* =========================================
    DOWNLOAD FILE
    ========================================= */

    XLSX.writeFile(
        workbook,
        fileName
    );
}
