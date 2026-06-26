const $ = id => document.getElementById(id);

(function () {
    'use strict';

    let cacheData = null;
    let selectedSheet = null;
    let activeView = 'sbs';

    // Localized Help Center Data Matrix
    const helpTopics = [
        {
            id: "overview",
            title: "📘 Workspace Overview",
            content: "<h3>Workspace Overview</h3><p>The Excel Comparison tool provides an interactive side-by-side operational overview allowing cross-functional verification between baseline workbooks and recent file changes line-by-line.</p><h4>Core Functionalities:</h4><ul><li><b>Automatic Coordinate Mapping:</b> Aligns cells at uniform dimensional indexes across separate files.</li><li><b>KPIMetrics:</b> Calculates complete transaction items automatically upon file execution.</li></ul>"
        },
        {
            id: "actions",
            title: "⚡ Toolbar Actions",
            content: "<h3>Toolbar & Dashboard Controls</h3><p>Manage processing inputs directly using the top workspace configuration buttons:</p><ul><li><b>File Selection Stubs:</b> Click either block to choose a target source spreadsheet from your disk files.</li><li><b>Run Compare:</b> Validates files and initiates calculation passes on the server.</li><li><b>Clear Workspace:</b> Clears loaded datasets and re-initializes empty views.</li></ul>"
        },
        {
            id: "navigation",
            title: "🔄 Layout Navigation",
            content: "<h3>Layout Views & Sheet Sub-Tabs</h3><p>Review variances through separate view modes:</p><ul><li><b>Side by Side:</b> Presents aligned dual-viewports with synchronized scrolling. Moving one panel automatically shifts the opposite viewport.</li><li><b>Change Log:</b> Collects flattened transformation summaries for text filtering tasks.</li><li><b>Sheet Tabs:</b> Dynamically changes active views between separate workbooks sheets.</li></ul>"
        }
    ];

    $('oldFile').onchange = e => $('oldFileName').innerText = e.target.files[0]?.name || "Select Base File...";
    $('newFile').onchange = e => $('newFileName').innerText = e.target.files[0]?.name || "Select Revision File...";

    document.addEventListener('change', () => {
        $('compareBtn').disabled = !($('oldFile').files[0] && $('newFile').files[0]);
    });

    function bindScrollListeners() {
        const left = $('leftScroller');
        const right = $('rightScroller');
        let activeDriver = null;

        function sync(driver, target) {
            if (activeDriver === null || activeDriver === driver) {
                activeDriver = driver;
                target.scrollTop = driver.scrollTop;
                target.scrollLeft = driver.scrollLeft;
                clearTimeout(driver._scrollTimeout);
                driver._scrollTimeout = setTimeout(() => { activeDriver = null; }, 50);
            }
        }
        if (left && right) {
            left.onscroll = () => sync(left, right);
            right.onscroll = () => sync(right, left);
        }
    }

    $('compareBtn').onclick = async () => {
        const form = new FormData();
        form.append('oldFile', $('oldFile').files[0]);
        form.append('newFile', $('newFile').files[0]);

        const statusLabel = $('statusMessage');
        updateProcessingStatus("Processing", "Comparing sheets...", "processing"); document.getElementById("lastAction").innerText = "Comparing...";
        
        try {
            const res = await fetch('/excel_compare/compare', { method: 'POST', body: form });
            const data = await res.json();

            if (!res.ok || data.error) {
                updateProcessingStatus("Error", data.error, "failed"); document.getElementById("lastAction").innerText = "Compare failed";
                return;
            }

            cacheData = data;
            $('sidebarDownloadBtn').disabled = false;
            updateProcessingStatus("Ready", "Comparison completed", "completed"); document.getElementById("lastAction").innerText = "Comparison completed";
            
            // Update sidebar KPI boxes
            $('kpiMod').innerText = data.totals.modified;
            $('kpiAdd').innerText = data.totals.added;
            $('kpiRem').innerText = data.totals.removed;
            $('kpiTot').innerText = data.totals.total;
            $('kpiSidebar').style.display = 'flex';

            // Update panel headers with actual filenames
            const oldH = document.getElementById('oldDocHeader');
            const newH = document.getElementById('newDocHeader');
            if (oldH) oldH.innerText = data.file1_name || 'Base Workbook (Old File)';
            if (newH) newH.innerText = data.file2_name || 'Revised Workbook (New File)';

            renderTabs();
            if (data.sheets.length > 0) switchSheet(data.sheets[0]);

        } catch (err) {
            if (statusLabel) statusLabel.innerText = "Network transmission error.";
        }
    };

    function renderTabs() {
        const container = $('sheetTabs');
        container.innerHTML = '';
        cacheData.sheets.forEach(sheet => {
            const btn = document.createElement('button');
            btn.className = 'tab-btn';
            btn.innerText = sheet;
            btn.onclick = () => switchSheet(sheet);
            container.appendChild(btn);
        });
    }

    function switchSheet(name) {
        selectedSheet = name;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.innerText === name));
        $('emptyState').style.display = 'none';
        renderActiveWorkspaceView();
    }

    function renderActiveWorkspaceView() {
        if (activeView === 'sbs') {
            $('sbsView').style.display = 'flex';
            $('logView').style.display = 'none';
            renderSplitMatrix();
            bindScrollListeners();
        } else {
            $('sbsView').style.display = 'none';
            $('logView').style.display = 'flex';
            renderLogTable();
        }
    }

    function renderSplitMatrix() {
        const sheetInfo = cacheData.sheet_data[selectedSheet];
        const cols = sheetInfo.col_count;

        let headHtml = '<tr><th style="width: 50px;">#</th>';
        for(let i=0; i<cols; i++) {
            headHtml += `<th style="width: 120px;">${String.fromCharCode(65+i)}</th>`;
        }
        headHtml += '</tr>';
        $('leftTableHead').innerHTML = headHtml;
        $('rightTableHead').innerHTML = headHtml;

        let leftBody = '', rightBody = '';
        sheetInfo.sbs.forEach(row => {
            leftBody += `<tr class="data-row-item"><td class="c-cell gt">${row.row_num}</td>`;
            row.left.forEach(c => {
                leftBody += `<td class="c-cell ${c.status}" title="${c.value}">${c.value}</td>`;
            });
            leftBody += '</tr>';

            rightBody += `<tr class="data-row-item"><td class="c-cell gt">${row.row_num}</td>`;
            row.right.forEach(c => {
                rightBody += `<td class="c-cell ${c.status}" title="${c.value}">${c.value}</td>`;
            });
            rightBody += '</tr>';
        });

        $('leftTableBody').innerHTML = leftBody;
        $('rightTableBody').innerHTML = rightBody;
    }

    function renderLogTable() {
        const logData = cacheData.sheet_data[selectedSheet].change_log;
        $('logBody').innerHTML = logData.map(item => `
            <tr class="log-row-item">
                <td>${item.sheet}</td>
                <td><strong>${item.cell}</strong></td>
                <td style="color:#b91c1c">${item.oldValue}</td>
                <td style="color:#15803d">${item.newValue}</td>
                <td><span class="chip ${item.status.toLowerCase()}">${item.status}</span></td>
            </tr>
        `).join('') || '<tr><td colspan="5" style="text-align:center; color:#94a3b8">No logged variations found.</td></tr>';
    }

    $('viewSideBySide').onclick = () => { activeView = 'sbs'; $('viewSideBySide').classList.add('active'); $('viewChangelog').classList.remove('active'); if(cacheData) renderActiveWorkspaceView(); };
    $('viewChangelog').onclick = () => { activeView = 'log'; $('viewChangelog').classList.add('active'); $('viewSideBySide').classList.remove('active'); if(cacheData) renderActiveWorkspaceView(); };

    // STABLE SUB-CELL ROW FILTER: Replaces common.js recursive walk to prevent crashes
    window.executePageSearch = function(query) {
        const token = query.trim().toLowerCase();
        
        if (activeView === 'sbs') {
            document.querySelectorAll('#leftTableBody .data-row-item').forEach((row, idx) => {
                const rightRow = document.querySelectorAll('#rightTableBody .data-row-item')[idx];
                const textContent = (row.textContent + ' ' + (rightRow ? rightRow.textContent : '')).toLowerCase();
                
                if (token === '' || textContent.includes(token)) {
                    row.style.display = '';
                    if (rightRow) rightRow.style.display = '';
                } else {
                    row.style.display = 'none';
                    if (rightRow) rightRow.style.display = 'none';
                }
            });
        } else {
            document.querySelectorAll('#logBody .log-row-item').forEach(row => {
                if (token === '' || row.textContent.toLowerCase().includes(token)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }
    };

    // INTERACTIVE SPLIT-PANE HELP CENTER MODAL OVERRIDE (DCN STYLE)
    window.toggleHelpSystemModal = async function() {
        const modal = document.getElementById('helpSystemModal');
        if (!modal) return;
        
        modal.classList.toggle('hidden');
        if (!modal.classList.contains('hidden')) {
            const indexPane = document.getElementById('helpModalIndexPane');
            const contentPane = document.getElementById('helpModalContentPane');
            indexPane.innerHTML = '<div style="padding:10px; color:#94a3b8; font-size:12px;">Loading documentation...</div>';
            
            try {
                const res = await fetch('/excel_compare/help-data');
                const data = await res.json();
                
                indexPane.innerHTML = '';
                data.topics.forEach(topic => {
                    const btn = document.createElement('button');
                    btn.className = 'help-index-item';
                    btn.innerText = topic.title;
                    btn.onclick = () => {
                        document.querySelectorAll('.help-index-item').forEach(b => b.classList.remove('active-help-topic'));
                        btn.classList.add('active-help-topic');
                        contentPane.innerHTML = topic.content;
                    };
                    indexPane.appendChild(btn);
                });
                
                if (data.topics.length > 0) indexPane.firstChild.click();
            } catch(e) {
                indexPane.innerHTML = '<div style="padding:10px; color:#ef4444; font-size:12px;">Failed loading help data.</div>';
            }
        }
    };

    window.clearWorkspace = function () {
        $('oldFile').value = ''; $('newFile').value = '';
        $('oldFileName').innerText = "Select Base File...";
        $('newFileName').innerText = "Select Revision File...";
        $('compareBtn').disabled = true; $('sidebarDownloadBtn').disabled = true;
        cacheData = null; selectedSheet = null;
        
        $('kpiMod').innerText = '—';
        $('kpiAdd').innerText = '—';
        $('kpiRem').innerText = '—';
        $('kpiTot').innerText = '—';
        $('kpiSidebar').style.display = 'none';
        
        $('sheetTabs').innerHTML = ''; $('leftTableHead').innerHTML = '';
        $('leftTableBody').innerHTML = ''; $('rightTableHead').innerHTML = '';
        $('rightTableBody').innerHTML = ''; $('logBody').innerHTML = '';
        
        $('sbsView').style.display = 'none'; $('logView').style.display = 'none';
        $('emptyState').style.display = 'flex';

        // Reset panel headers back to defaults
        const oldH = document.getElementById('oldDocHeader');
        const newH = document.getElementById('newDocHeader');
        if (oldH) oldH.innerText = 'Base Workbook (Old File)';
        if (newH) newH.innerText = 'Revised Workbook (New File)';
        
        const statusLabel = $('statusMessage');
        updateProcessingStatus("Ready", "", "completed"); document.getElementById("lastAction").innerText = "Workspace cleared";
        
        
        
    };

    window.clearWorkspace = window.clearWorkspace;

    window.triggerDownloadPackage = function() {
        const statusLabel = $('statusMessage');
        updateProcessingStatus("Processing", "Generating ZIP...", "processing"); document.getElementById("lastAction").innerText = "Generating download...";
        window.location.href = '/excel_compare/download';
    };

})();

/* =========================================
   OPS-STYLE PROGRESS BAR CONTROLLER
   Works with main.html IDs:
   statusMessage, progressWrapper,
   progressFill, progressText
========================================= */

function updateProcessingStatus(message, detail, state) {
    const status  = document.getElementById('statusMessage');
    const text    = document.getElementById('progressText');
    const fill    = document.getElementById('progressFill');
    const wrapper = document.getElementById('progressWrapper');

    if (status) status.innerText = message;
    if (text)   text.innerText   = detail || '';

    if (!fill || !wrapper) return;

    fill.classList.remove('ops-bar-processing', 'ops-bar-completed', 'ops-bar-failed');

    if (state === 'processing') {
        wrapper.classList.remove('hidden');
        fill.style.width = '70%';
        fill.classList.add('ops-bar-processing');

    } else if (state === 'completed') {
        wrapper.classList.remove('hidden');
        fill.style.width = '100%';
        fill.classList.add('ops-bar-completed');
        setTimeout(() => {
            wrapper.classList.add('hidden');
            fill.style.width = '0%';
            fill.classList.remove('ops-bar-completed');
        }, 2000);

    } else {
        wrapper.classList.remove('hidden');
        fill.style.width = '100%';
        fill.classList.add('ops-bar-failed');
        setTimeout(() => {
            wrapper.classList.add('hidden');
            fill.style.width = '0%';
            fill.classList.remove('ops-bar-failed');
        }, 3000);
    }
}

/* Track filenames in status rows when files are selected */
document.addEventListener('DOMContentLoaded', function() {
    const oldInput = document.getElementById('oldFile');
    const newInput = document.getElementById('newFile');
    if (oldInput) {
        oldInput.addEventListener('change', function(e) {
            const name = e.target.files[0]?.name || '—';
            const el = document.getElementById('statusOldFile');
            if (el) el.innerText = name.length > 22 ? name.substring(0, 20) + '…' : name;
        });
    }
    if (newInput) {
        newInput.addEventListener('change', function(e) {
            const name = e.target.files[0]?.name || '—';
            const el = document.getElementById('statusNewFile');
            if (el) el.innerText = name.length > 22 ? name.substring(0, 20) + '…' : name;
        });
    }
});
