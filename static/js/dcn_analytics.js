let monthlyChartInstance = null;


// ======================================================
// PAGE LOAD
// ======================================================
document.addEventListener(
    "DOMContentLoaded",
    () => {

        initializeDashboard();

    }
);


// ======================================================
// INITIALIZE
// ======================================================
function initializeDashboard() {

    bindEvents();

    showSidebarPanel("kpi");

    handleDateFilterType();

    loadDashboard();

}


// ======================================================
// EVENTS
// ======================================================
function bindEvents() {

    // ==========================================
    // REFRESH
    // ==========================================
    document
        .getElementById("refreshBtn")
        ?.addEventListener(
            "click",
            loadDashboard
        );


    // ==========================================
    // APPLY FILTERS (FIXED EVENT LISTENER MATCHES)
    // ==========================================
    // 1. Check for standard local ID names
    document
        .getElementById("applyFiltersBtn")
        ?.addEventListener("click", applyDashboardFilters);

    // 2. Add structural string match fallback for the top platform layout action header
    const topBarFilterBtn = Array.from(document.querySelectorAll("button")).find(
        btn => btn.textContent.trim() === "Apply Filters"
    );
    if (topBarFilterBtn) {
        topBarFilterBtn.addEventListener("click", applyDashboardFilters);
        console.log("✓ Attached filter interceptor to Platform Header Button");
    }

    // ==========================================
    // DOWNLOAD BUTTONS
    // ==========================================
    document
        .getElementById("downloadMonthlyBtn")
        ?.addEventListener(
            "click",
            downloadMonthlyReport
        );

    document
        .getElementById("downloadDailyBtn")
        ?.addEventListener(
            "click",
            downloadDailyReport
        );

    // ==========================================
    // UPLOAD EXCEL INTERCEPTOR
    // ==========================================
    document
        .getElementById("uploadExcel")
        ?.addEventListener(
            "change",
            handleExcelUpload
        );

    // ==========================================
    // FULL CONSOLIDATED DASHBOARD DOWNLOAD
    // ==========================================
    document
        .getElementById("downloadFullDashboardBtn")
        ?.addEventListener(
            "click",
            () => { window.open("/api/dcn-analytics/download/full-dashboard", "_blank"); }
        );

    // Inside bindEvents() function
    document.getElementById("chartTypeSelector")?.addEventListener("change", (e) => {
        // Grab cached global chart data or reload dashboard to update instantly
        loadDashboard();
    });

    // Clear Workspace Fix
    document.getElementById("clearWorkspaceBtn")?.addEventListener("click", () => {
        // Reset inputs
        if(document.getElementById("dateFilterType")) document.getElementById("dateFilterType").value = "none";
        if(document.getElementById("startDate")) document.getElementById("startDate").value = "";
        if(document.getElementById("endDate")) document.getElementById("endDate").value = "";
        
        // Check all year checkboxes
        document.querySelectorAll('#yearSection .year-checkbox-grid input[type="checkbox"]').forEach(cb => cb.checked = true);
        
        // Uncheck quick radio buttons
        document.querySelectorAll('input[name="quickDate"]').forEach(rb => rb.checked = false);
        
        handleDateFilterType();
        loadDashboard(); // Restores baseline dataset view
    });
}


// ======================================================
// SIDEBAR PANEL SWITCH
// ======================================================
function showSidebarPanel(type) {

    // ==========================================
    // REMOVE ACTIVE
    // ==========================================
    document
        .querySelectorAll(".dock-item")
        .forEach(item => {

            item.classList.remove(
                "active-dock"
            );

        });


    // ==========================================
    // HIDE PANELS
    // ==========================================
    document
        .querySelectorAll(".dock-section")
        .forEach(section => {

            section.classList.remove(
                "active-section"
            );

        });


    // ==========================================
    // KPI
    // ==========================================
    if (type === "kpi") {

        document
            .getElementById("kpi-section")
            ?.classList.add(
                "active-section"
            );

        document
            .getElementById("kpiDockBtn")
            ?.classList.add(
                "active-dock"
            );

    }


    // ==========================================
    // FILTER
    // ==========================================
    else if (type === "filter") {

        document
            .getElementById("filter-section")
            ?.classList.add(
                "active-section"
            );

        document
            .getElementById("filterDockBtn")
            ?.classList.add(
                "active-dock"
            );

    }


    // ==========================================
    // DOWNLOAD
    // ==========================================
    else if (type === "download") {

        document
            .getElementById("download-section")
            ?.classList.add(
                "active-section"
            );

        document
            .getElementById("downloadDockBtn")
            ?.classList.add(
                "active-dock"
            );

    }

}


// ======================================================
// FILTER TYPE HANDLER
// ======================================================
function handleDateFilterType() {

    // ==========================================
    // HIDE ALL
    // ==========================================
    document
        .querySelectorAll(".date-sub-section")
        .forEach(section => {

            section.classList.remove(
                "active-date-section"
            );

        });


    const filterType =
        document.getElementById(
            "dateFilterType"
        )?.value;


    // ==========================================
    // RANGE
    // ==========================================
    if (filterType === "range") {

        document
            .getElementById(
                "dateRangeSection"
            )
            ?.classList.add(
                "active-date-section"
            );

    }


    // ==========================================
    // YEAR
    // ==========================================
    else if (filterType === "year") {

        document
            .getElementById(
                "yearSection"
            )
            ?.classList.add(
                "active-date-section"
            );

    }


    // ==========================================
    // QUICK
    // ==========================================
    else if (filterType === "quick") {

        document
            .getElementById(
                "quickSection"
            )
            ?.classList.add(
                "active-date-section"
            );

    }

}


// ======================================================
// LOAD DASHBOARD
// ======================================================
async function loadDashboard() {

    try {

        updateProcessingStatus(
            "Loading dashboard...",
            "processing"
        );

        const response = await fetch(
            "/api/dcn-analytics/dashboard"
        );

        const data = await response.json();

        console.log(data);

        if (!data.success) {

            updateProcessingStatus(
                data.message || "Failed to load dashboard",
                "failed"
            );

            return;

        }

        renderKPI(
            data.kpi
        );

        renderMonthlyChart(
            data.chart_data
        );

        renderPivotTable(
            data.monthly_pivot
        );

        renderDailySummary(
            data.daily_summary
        );

        updateProcessingStatus(
            "Dashboard loaded successfully",
            "completed"
        );

    }
    catch (error) {

        console.error(error);

        updateProcessingStatus(
            error.message,
            "failed"
        );

    }

}


// ======================================================
// KPI
// ======================================================
function renderKPI(kpi) {

    setText(
        "totalMissingKpi",
        kpi.total_missing
    );

    setText(
        "currentMonthKpi",
        kpi.current_month
    );

    document.getElementById(
        "latestDcnKpi"
    ).innerHTML = `

        <div class="kpi-latest-dcn">
            ${kpi.latest_dcn || "-"}
        </div>

    `;

    setText(
        "lastUpdatedKpi",
        kpi.last_updated
    );

}


// ======================================================
// MONTHLY CHART
// ======================================================
function renderMonthlyChart(chartData) {
    const canvas = document.getElementById("monthlyTrendChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (monthlyChartInstance) { monthlyChartInstance.destroy(); }
    if (!chartData || !chartData.labels || !chartData.datasets) { return; }

    const selectedType = document.getElementById("chartTypeSelector")?.value || "bar";
    const colors = ["#4e79a7", "#f28e2b", "#e15759", "#bab0ac"];

    let datasets = [];
    let processedLabels = chartData.labels;

    if (selectedType === "pie") {
        // Pie charts display aggregate counts for the newest active dataset year (e.g., 2026)
        const latestDataset = chartData.datasets[chartData.datasets.length - 1];
        datasets = [{
            label: latestDataset ? latestDataset.label : "Data",
            data: latestDataset ? latestDataset.data : [],
            backgroundColor: ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#2563eb", "#db2777"]
        }];
    } else {
        // Bar or Line layout structure configurations
        datasets = chartData.datasets.map((dataset, index) => ({
            label: dataset.label,
            data: dataset.data,
            borderColor: colors[index],
            backgroundColor: selectedType === "line" ? "transparent" : colors[index],
            borderWidth: selectedType === "line" ? 2.5 : 1,
            pointRadius: selectedType === "line" ? 4 : 0,
            tension: 0.1
        }));
    }

    monthlyChartInstance = new Chart(ctx, {
        type: selectedType === "pie" ? "pie" : selectedType,
        data: { labels: processedLabels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: "top" }
            },
            scales: selectedType === "pie" ? {} : {
                x: { grid: { display: false } }, // Kills vertical gridlines
                y: { beginAtZero: true, grid: { display: false }, ticks: { precision: 0 } } // Kills horizontal gridlines
            }
        }
    });
    window.dispatchEvent(new Event("resize"));
}


// ======================================================
// PIVOT TABLE WITH COLUMN TOTALS
// ======================================================
function renderPivotTable(rows) {

    const tbody = document.getElementById("pivotTableBody");
    if (!tbody) return;

    tbody.innerHTML = "";

    if (!rows || rows.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">No pivot data available</td>
            </tr>
        `;
        return;
    }

    // Accumulators for column totals
    let total2023 = 0;
    let total2024 = 0;
    let total2025 = 0;
    let total2026 = 0;

    // Render monthly data rows
    rows.forEach(row => {
        const val2023 = parseInt(row["2023"] || 0, 10);
        const val2024 = parseInt(row["2024"] || 0, 10);
        const val2025 = parseInt(row["2025"] || 0, 10);
        const val2026 = parseInt(row["2026"] || 0, 10);

        total2023 += val2023;
        total2024 += val2024;
        total2025 += val2025;
        total2026 += val2026;

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.Month || "-"}</td>
            <td>${val2023}</td>
            <td>${val2024}</td>
            <td>${val2025}</td>
            <td>${val2026}</td>
        `;
        tbody.appendChild(tr);
    });

    // Append the calculated Totals row at the bottom
    const totalTr = document.createElement("tr");
    totalTr.className = "pivot-total-row";
    totalTr.innerHTML = `
        <td>Total</td>
        <td>${total2023}</td>
        <td>${total2024}</td>
        <td>${total2025}</td>
        <td>${total2026}</td>
    `;
    tbody.appendChild(totalTr);
}


// ======================================================
// DAILY SUMMARY
// ======================================================
function renderDailySummary(rows) {

    const tbody =
        document.getElementById(
            "dailySummaryBody"
        );

    if (!tbody) return;

    tbody.innerHTML = "";

    if (!rows || rows.length === 0) {

        tbody.innerHTML = `

            <tr>
                <td colspan="4">
                    No daily summary data
                </td>
            </tr>

        `;

        return;
    }

    rows.forEach((row, index) => {

        const tr =
            document.createElement("tr");

        tr.innerHTML = `

            <td>${index + 1}</td>
            <td>${row.Date || "-"}</td>
            <td>${row["Sequence Skipped"] || 0}</td>
            <td>${row["Skipped DCN Numbers"] || "-"}</td>

        `;

        tbody.appendChild(tr);

    });

}


// ======================================================
// APPLY FILTERS (FIXED DOM SCANNER & EXPLICIT MAPPINGS)
// ======================================================
async function applyDashboardFilters() {
    try {
        updateProcessingStatus("Applying filters...", "processing");

        // 1. Fetch exact element choices based on your sidebar HTML structure
        const filterType = document.getElementById("dateFilterType")?.value || "none";
        const startDate = document.getElementById("startDate")?.value || "";
        const endDate = document.getElementById("endDate")?.value || "";

        // 2. Extract ALL checked checkboxes from your year-checkbox-grid
        const checkedYearBoxes = document.querySelectorAll('#yearSection .year-checkbox-grid input[type="checkbox"]:checked');
        const selectedYears = Array.from(checkedYearBoxes).map(box => parseInt(box.value, 10));

        // 3. Extract checked quick-select radio button
        const quickOptionEl = document.querySelector('input[name="quickDate"]:checked');
        const quickOption = quickOptionEl ? quickOptionEl.value : "";

        // Assemble precise payload profile matching the new multi-select structure
        const payload = {
            filter_type: filterType,
            start_date: startDate,
            end_date: endDate,
            years: selectedYears, // Transmits as an array, e.g., [2025, 2026]
            quick_option: quickOption
        };

        console.log("SENDING FILTER PAYLOAD:", payload);

        // 4. API Request
        const response = await fetch("/api/dcn-analytics/apply-filters", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!data.success) {
            updateProcessingStatus(data.message || "Filter execution failed", "failed");
            return;
        }

        // 5. Live UI Components Refresh
        renderKPI(data.kpi);
        renderMonthlyChart(data.chart_data);
        renderPivotTable(data.monthly_pivot);
        renderDailySummary(data.daily_summary);

        updateProcessingStatus("Filters applied successfully", "completed");

    } catch (error) {
        console.error("Filter Interception Error:", error);
        updateProcessingStatus(error.message, "failed");
    }
}


// ======================================================
// DOWNLOADS
// ======================================================
function downloadMonthlyReport() {

    window.open(
        "/api/dcn-analytics/download/monthly",
        "_blank"
    );

}


function downloadDailyReport() {

    window.open(
        "/api/dcn-analytics/download/daily",
        "_blank"
    );

}


// ======================================================
// STATUS
// ======================================================
function updateProcessingStatus(
    message,
    type = "processing"
) {

    const wrapper =
        document.getElementById(
            "progressWrapper"
        );

    const statusMessage =
        document.getElementById(
            "statusMessage"
        );

    const progressText =
        document.getElementById(
            "progressText"
        );

    const progressFill =
        document.getElementById(
            "progressFill"
        );

    if (
        !wrapper ||
        !statusMessage ||
        !progressText ||
        !progressFill
    ) {
        return;
    }

    wrapper.classList.remove(
        "hidden"
    );

    const time =
        new Date().toLocaleTimeString();

    progressText.innerHTML =
        `[${time}] ${message}`;

    // ==========================================
    // PROCESSING
    // ==========================================
    if (type === "processing") {

        statusMessage.innerText =
            "Processing...";

        progressFill.style.width =
            "60%";

        progressFill.style.background =
            "linear-gradient(90deg,#22c55e,#4ade80)";

    }

    // ==========================================
    // COMPLETED
    // ==========================================
    else if (type === "completed") {

        statusMessage.innerText =
            "Completed";

        progressFill.style.width =
            "100%";

        progressFill.style.background =
            "linear-gradient(90deg,#22c55e,#16a34a)";

    }

    // ==========================================
    // FAILED
    // ==========================================
    else if (type === "failed") {

        statusMessage.innerText =
            "Failed";

        progressFill.style.width =
            "100%";

        progressFill.style.background =
            "linear-gradient(90deg,#ef4444,#dc2626)";

    }

}


// ======================================================
// HELPERS
// ======================================================
function setText(id, value) {

    const element =
        document.getElementById(id);

    if (element) {

        element.textContent =
            value ?? "-";

    }

}

// ======================================================
// HANDLE EXCEL FILE UPLOAD
// ======================================================
async function handleExcelUpload(event) {
    const fileInput = event.target;
    if (!fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
        updateProcessingStatus(
            "Uploading and parsing new Excel dataset...",
            "processing"
        );

        const response = await fetch("/api/dcn-analytics/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!data.success) {
            updateProcessingStatus(
                data.message || "Upload failed",
                "failed"
            );
            fileInput.value = ""; // Reset file picker input cache
            return;
        }

        updateProcessingStatus(
            "Upload complete! Refreshing metrics...",
            "processing"
        );

        // Clear file input cache and completely reload view components
        fileInput.value = "";
        await loadDashboard();

    } catch (error) {
        console.error(error);
        updateProcessingStatus(
            "Upload Error: " + error.message,
            "failed"
        );
        fileInput.value = "";
    }
}

// Active tracking variable for visual control selections
let selectedChartType = "bar";

// Bind active chart button group toggles
document.querySelectorAll("#chartTypeIconGroup .chart-icon-btn").forEach(btn => {
    btn.addEventListener("click", function() {
        document.querySelectorAll("#chartTypeIconGroup .chart-icon-btn").forEach(b => b.classList.remove("active-chart-view"));
        this.classList.add("active-chart-view");
        selectedChartType = this.getAttribute("data-type");
        loadDashboard(); // Instant redraw
    });
});

// OVERRIDE CORE MODULE WORKSPACE CLEANING MECHANIC
window.clearWorkspace = function() {
    console.log("Utilizing standard main framework workspace reset...");
    
    // Reset filters
    if(document.getElementById("dateFilterType")) document.getElementById("dateFilterType").value = "none";
    if(document.getElementById("startDate")) document.getElementById("startDate").value = "";
    if(document.getElementById("endDate")) document.getElementById("endDate").value = "";
    
    document.querySelectorAll('#yearSection .year-checkbox-grid input[type="checkbox"]').forEach(cb => cb.checked = true);
    document.querySelectorAll('input[name="quickDate"]').forEach(rb => rb.checked = false);
    
    if(typeof handleDateFilterType === "function") handleDateFilterType();
    
    // Clear status fill bars
    const progressWrapper = document.getElementById("progressWrapper");
    if (progressWrapper) progressWrapper.classList.add("hidden");
    
    loadDashboard(); // Force baseline metric restore
};

// FIX PIE CHART RENDER LOGIC
function renderMonthlyChart(chartData) {
    const canvas = document.getElementById("monthlyTrendChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (monthlyChartInstance) { monthlyChartInstance.destroy(); }
    if (!chartData || !chartData.labels || !chartData.datasets) { return; }

    const colors = ["#4e79a7", "#f28e2b", "#e15759", "#bab0ac"];
    let datasets = [];
    let processedLabels = chartData.labels;

    if (selectedChartType === "pie") {
        // FIXED: Sum rows to present a pure yearly count dataset responsive to filter slices
        processedLabels = chartData.datasets.map(d => d.label);
        const yearlySums = chartData.datasets.map(d => d.data.reduce((a, b) => a + b, 0));
        
        datasets = [{
            data: yearlySums,
            backgroundColor: colors.slice(0, yearlySums.length)
        }];
    } else {
        datasets = chartData.datasets.map((dataset, index) => ({
            label: dataset.label,
            data: dataset.data,
            borderColor: colors[index],
            backgroundColor: selectedChartType === "line" ? "transparent" : colors[index],
            borderWidth: selectedChartType === "line" ? 2.5 : 1,
            pointRadius: selectedChartType === "line" ? 4 : 0,
            tension: 0.1
        }));
    }

    monthlyChartInstance = new Chart(ctx, {
        type: selectedChartType,
        data: { labels: processedLabels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: "top" }
            },
            scales: selectedChartType === "pie" ? {} : {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { display: false }, ticks: { precision: 0 } }
            }
        }
    });
}

// Local cache placeholder for runtime topic indices
let cachedHelpTopics = [];

async function loadModuleHelpData() {
    const indexPane = document.getElementById("helpModalIndexPane");
    const contentPane = document.getElementById("helpModalContentPane");
    if (!indexPane || !contentPane) return;

    try {
        indexPane.innerHTML = "<div style='font-size:12px;color:#64748b;padding:10px;'>Loading topics...</div>";
        
        const response = await fetch("/api/help/dcn-analytics");
        const data = await response.json();
        
        document.getElementById("helpModuleTitle").innerText = data.module_title || "Help Center";
        cachedHelpTopics = data.topics || [];
        
        indexPane.innerHTML = "";
        
        if (cachedHelpTopics.length === 0) {
            indexPane.innerHTML = "<div style='font-size:12px;color:#64748b;padding:10px;'>No help documentation found.</div>";
            return;
        }

        // Generate left index buttons smoothly
        cachedHelpTopics.forEach((topic, idx) => {
            const btn = document.createElement("button");
            btn.className = "help-index-item";
            btn.innerText = topic.title;
            btn.setAttribute("data-topic-id", topic.id);
            btn.addEventListener("click", () => switchHelpTopic(topic.id));
            indexPane.appendChild(btn);
        });

        // Auto-select the first documentation folder entry by default
        switchHelpTopic(cachedHelpTopics[0].id);

    } catch (err) {
        console.error("Help System Fault:", err);
        indexPane.innerHTML = "<div style='font-size:12px;color:#ef4444;padding:10px;'>Error fetching guides.</div>";
    }
}

function switchHelpTopic(topicId) {
    // Sync graphical active toggles
    document.querySelectorAll("#helpModalIndexPane .help-index-item").forEach(btn => {
        if (btn.getAttribute("data-topic-id") === topicId) {
            btn.classList.add("active-help-topic");
        } else {
            btn.classList.remove("active-help-topic");
        }
    });

    // Inject targeted raw html document package safely into the preview viewport
    const contentPane = document.getElementById("helpModalContentPane");
    const targetTopic = cachedHelpTopics.find(t => t.id === topicId);
    
    if (contentPane && targetTopic) {
        contentPane.innerHTML = targetTopic.content;
    }
}