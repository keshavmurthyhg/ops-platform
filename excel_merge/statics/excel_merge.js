'use strict';

let generatedFileName = null;
let updatedCells      = {};
let newRowsList       = [];


/* =========================================
   DOCK SECTION SWITCH
========================================= */

function showExcelSection(sectionName, event) {
    document.querySelectorAll('.dock-item')
            .forEach(i => i.classList.remove('active-dock'));
    document.querySelectorAll('.dock-section')
            .forEach(s => s.classList.remove('active-section'));

    const target = document.getElementById(sectionName + '-section');
    if (target) target.classList.add('active-section');
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active-dock');
    }
}


/* =========================================
   FILE NAMES
========================================= */

function updateFileNames() {
    const f1 = document.getElementById('file1');
    const f2 = document.getElementById('file2');

    const name1 = f1.files.length ? f1.files[0].name : 'Select Old Excel...';
    const name2 = f2.files.length ? f2.files[0].name : 'Select New Excel...';

    document.getElementById('file1Name').innerText = name1;
    document.getElementById('file2Name').innerText = name2;

    // Update sidebar status rows
    const s1 = document.getElementById('statusOldFile');
    const s2 = document.getElementById('statusNewFile');
    if (s1) s1.innerText = f1.files.length
        ? (name1.length > 22 ? name1.substring(0, 20) + '…' : name1)
        : '—';
    if (s2) s2.innerText = f2.files.length
        ? (name2.length > 22 ? name2.substring(0, 20) + '…' : name2)
        : '—';
}


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
    const last    = document.getElementById('lastAction');

    if (status) status.innerText = message;
    if (text)   text.innerText   = detail || '';
    if (last)   last.innerText   = detail || message;

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


/* =========================================
   MERGE
========================================= */

async function mergeExcelFiles() {

    const file1      = document.getElementById('file1').files[0];
    const file2      = document.getElementById('file2').files[0];
    const keyColumn  = document.getElementById('uniqueKeyColumn').value.trim();
    const latestLogic = document.getElementById('mergeMode').value;
    const dateColumn = document.getElementById('dateColumn').value.trim();

    if (!file1 || !file2) {
        updateProcessingStatus('Error', 'Upload both Excel files', 'failed');
        return;
    }

    if (!keyColumn) {
        updateProcessingStatus('Error', 'Enter unique key column', 'failed');
        return;
    }

    try {
        updateProcessingStatus('Processing', 'Preparing merge...', 'processing');

        const formData = new FormData();
        formData.append('file1',         file1);
        formData.append('file2',         file2);
        formData.append('key_column',    keyColumn);
        formData.append('latest_logic',  latestLogic);
        formData.append('date_column',   dateColumn);

        updateProcessingStatus('Processing', 'Merging records...', 'processing');

        const response = await fetch('/excel-merge/process', {
            method: 'POST',
            body:   formData
        });

        const result = await response.json();

        if (!result.success) {
            updateProcessingStatus('Error', result.message, 'failed');
            return;
        }

        generatedFileName = result.download_file;
        updatedCells      = result.updated_cells    || {};
        newRowsList       = result.new_rows_list    || [];

        updateKPI(result);
        renderPreviewTable(result.preview_rows || [], result.preview_columns || []);
        activateDownloadButton();

        updateProcessingStatus('Ready', 'Excel merge completed successfully', 'completed');

    } catch (error) {
        console.error(error);
        updateProcessingStatus('Error', 'Excel merge failed', 'failed');
    }
}


/* =========================================
   KPI — now updates strip in main area
========================================= */

function updateKPI(result) {
    document.getElementById('totalRows').innerText        = result.total_rows        || 0;
    document.getElementById('updatedRows').innerText      = result.updated_rows      || 0;
    document.getElementById('newRows').innerText          = result.new_rows          || 0;
    document.getElementById('duplicatesRemoved').innerText = result.duplicates_removed || 0;

    // Show the KPI strip
    const strip = document.getElementById('kpiStrip');
    if (strip) strip.classList.remove('hidden');
}


/* =========================================
   DOWNLOAD
========================================= */

function activateDownloadButton() {
    document.getElementById('downloadBtn').classList.remove('hidden');
}

function downloadMergedExcel() {
    if (!generatedFileName) {
        alert('No merged output available');
        return;
    }
    updateProcessingStatus('Processing', 'Preparing download...', 'processing');
    window.location.href = `/excel-merge/download/${generatedFileName}`;
    setTimeout(() => {
        updateProcessingStatus('Ready', 'Download started', 'completed');
    }, 1500);
}


/* =========================================
   PREVIEW TABLE
========================================= */

function renderPreviewTable(rows, columns) {
    const head = document.getElementById('mergeTableHead');
    const body = document.getElementById('mergeTableBody');

    if (!rows.length) {
        body.innerHTML = `<tr><td colspan="20" class="empty-search-message">No preview available</td></tr>`;
        return;
    }

    // Header
    let headHtml = '<tr>';
    columns.forEach((col, index) => {
        const cls = getColumnClass(col, index);
        headHtml += `<th class="${cls}">${escHtml(col)}</th>`;
    });
    headHtml += '</tr>';
    head.innerHTML = headHtml;

    // Body
    let bodyHtml = '';
    rows.forEach(row => {
        bodyHtml += '<tr>';
        const rowId = String(row[columns[0]] || '');
        const isNew = newRowsList.includes(rowId);

        columns.forEach((col, index) => {
            const cls      = getColumnClass(col, index);
            const isUpdated = !isNew && updatedCells[rowId] && updatedCells[rowId].includes(col);
            const extraCls = isNew ? 'new-cell' : (isUpdated ? 'updated-cell' : '');
            const val      = escHtml(String(row[col] ?? ''));

            bodyHtml += `<td class="${cls} ${extraCls}" title="${String(row[col] ?? '')}">${val}</td>`;
        });

        bodyHtml += '</tr>';
    });
    body.innerHTML = bodyHtml;
}

function getColumnClass(col, index) {
    if (index === 0) return 'number-column';
    const lower = col.toLowerCase();
    if (lower.includes('description') || lower.includes('comment') ||
        lower.includes('resolution')  || lower.includes('additional')) {
        return 'long-text-column';
    }
    return 'small-column';
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}


/* =========================================
   CLEAR WORKSPACE
========================================= */

function clearExcelWorkspace() {
    document.getElementById('file1').value         = '';
    document.getElementById('file2').value         = '';
    document.getElementById('file1Name').innerText = 'Select Old Excel...';
    document.getElementById('file2Name').innerText = 'Select New Excel...';
    document.getElementById('uniqueKeyColumn').value = '';
    document.getElementById('mergeMode').value     = 'prefer_new';
    document.getElementById('dateColumn').value    = '';

    generatedFileName = null;
    updatedCells      = {};
    newRowsList       = [];

    document.getElementById('downloadBtn').classList.add('hidden');

    const strip = document.getElementById('kpiStrip');
    if (strip) strip.classList.add('hidden');

    updateKPI({ total_rows: 0, updated_rows: 0, new_rows: 0, duplicates_removed: 0 });

    document.getElementById('mergeTableHead').innerHTML = '';
    document.getElementById('mergeTableBody').innerHTML =
        `<tr><td colspan="20" class="empty-search-message">Workspace cleared</td></tr>`;

    const s1 = document.getElementById('statusOldFile');
    const s2 = document.getElementById('statusNewFile');
    if (s1) s1.innerText = '—';
    if (s2) s2.innerText = '—';

    updateProcessingStatus('Ready', 'Workspace cleared', 'completed');
    document.getElementById('lastAction').innerText = 'Workspace cleared';
}


/* =========================================
   HELP MODAL
   Fetches from /api/help/excel-merge
   Called by common.js toggleHelpSystemModal()
========================================= */

function loadModuleHelpData() {
    fetch('/api/help/excel-merge')
        .then(r => r.json())
        .then(data => {
            const titleEl = document.getElementById('helpModuleTitle');
            if (titleEl) titleEl.textContent = '💡 ' + (data.module_title || 'Help');

            const indexPane   = document.getElementById('helpModalIndexPane');
            const contentPane = document.getElementById('helpModalContentPane');
            if (!indexPane || !contentPane) return;

            indexPane.innerHTML   = '';
            contentPane.innerHTML = '';

            const topics = data.topics || [];
            if (!topics.length) {
                contentPane.innerHTML = '<p>No help topics available.</p>';
                return;
            }

            topics.forEach((topic, i) => {
                const btn = document.createElement('button');
                btn.className   = 'help-topic-btn' + (i === 0 ? ' active-help-topic' : '');
                btn.textContent = topic.title;
                btn.onclick     = () => {
                    document.querySelectorAll('.help-topic-btn')
                            .forEach(b => b.classList.remove('active-help-topic'));
                    btn.classList.add('active-help-topic');
                    contentPane.innerHTML = topic.content;
                };
                indexPane.appendChild(btn);
            });

            contentPane.innerHTML = topics[0].content;
        })
        .catch(err => {
            console.error('Help load failed:', err);
            const pane = document.getElementById('helpModalContentPane');
            if (pane) pane.innerHTML = '<p>Help content could not be loaded.</p>';
        });
}


/* =========================================
   INIT
========================================= */

document.addEventListener('DOMContentLoaded', function () {

    resetProcessingStatus();

    document.getElementById('mergeBtn')
            .addEventListener('click', mergeExcelFiles);

    document.getElementById('downloadBtn')
            .addEventListener('click', downloadMergedExcel);

    document.getElementById('file1')
            .addEventListener('change', updateFileNames);

    document.getElementById('file2')
            .addEventListener('change', updateFileNames);
});
