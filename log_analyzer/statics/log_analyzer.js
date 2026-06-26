/* ================================================================
   log_analyzer.js
   Windchill log4j file analyzer — 100% browser-side, no upload.

   Log format (per image):
     2026-06-25 10:58:56,336 ERROR [ajp-nio-127.0.0.1-8011-exec-103]
       wt.servlet.ServletRequestMonitor.request A546072 - <message>
     <continuation lines…>

   Parses into entries:
     { ts, date, time, level, thread, logger, user, message, raw, lineNo }

   Features:
     • Multi-file: drag multiple files → merged & sorted by timestamp
     • Virtual scroll — all entries in memory, ~60 DOM rows rendered
     • Filters: time range, level toggle, thread, logger, user, message
     • Jump to timestamp (binary search)
     • Error summary: KPIs, top error patterns, top loggers
================================================================ */
"use strict";

const $ = id => document.getElementById(id);

/* ── Tunables ─────────────────────────────────────────────────── */
const ROW_CAP       = 500_000;
const VIRT_ROW_H    = 32;         // must match CSS .la-virt-row height
const VIRT_OVERSCAN = 30;
const PROGRESS_EVERY = 10_000;

/* ── State ────────────────────────────────────────────────────── */
const LA = {
    allEntries:     [],    // all parsed LogEntry objects
    visibleEntries: [],    // after filters
    activeLevels:   new Set(['FATAL','ERROR','WARN','INFO','DEBUG','TRACE']),
    abortCtrl:      null,
    sortAsc:        true,
};

/* ── Log entry structure ──────────────────────────────────────── */
// { ts, date, time, level, thread, logger, user, message, lineNo }

/* ── Log line regex ───────────────────────────────────────────── */
// 2026-06-25 10:58:56,336 ERROR [thread] logger user - message
const RE_ENTRY = /^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+(FATAL|ERROR|WARN|WARNING|INFO|DEBUG|TRACE)\s+\[([^\]]+)\]\s+(\S+)\s+(\S+)\s+-\s+(.*)/;

/* ── Headers ──────────────────────────────────────────────────── */
const HEADERS = ['Timestamp','Level','Thread','Logger','User','Message'];

/* ── Dock ─────────────────────────────────────────────────────── */
function switchDock(name) {
    document.querySelectorAll('.la-panel').forEach(p => p.classList.add('hidden'));
    const p = $('panel' + name[0].toUpperCase() + name.slice(1));
    if (p) p.classList.remove('hidden');
    // Activate dock icon
    document.querySelectorAll('.dock-item').forEach(b => b.classList && b.classList.remove('dock-active'));
}

/* ── Drop zone ────────────────────────────────────────────────── */
function onDragOver(e) { e.preventDefault(); $('dropZone').classList.add('drag-over'); }
function onDragLeave()  { $('dropZone').classList.remove('drag-over'); }
function onDrop(e) {
    e.preventDefault(); $('dropZone').classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files);
}
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop',     e => e.preventDefault());

function handleFileSelect(files) {
    if (!files || !files.length) return;
    openFiles(Array.from(files));
}

/* ── Plain file line iterator (4 MB slices) ──────────────────── */
async function* readLines(file, signal) {
    const SLICE = 4 * 1024 * 1024;
    let offset = 0, leftover = '';
    while (offset < file.size) {
        if (signal?.aborted) break;
        const text  = await file.slice(offset, offset + SLICE).text();
        const chunk = leftover + text;
        const lines = chunk.split('\n');
        leftover    = lines.pop();
        for (const l of lines) yield l;
        offset += SLICE;
        await new Promise(r => setTimeout(r, 0));
    }
    if (leftover) yield leftover;
}

/* ── Parse all files ─────────────────────────────────────────── */
async function openFiles(files) {
    if (LA.abortCtrl) LA.abortCtrl.abort();
    LA.abortCtrl = new AbortController();
    const signal = LA.abortCtrl.signal;

    LA.allEntries = []; LA.visibleEntries = [];

    // Sort files by name (log rotation order)
    files.sort((a, b) => a.name.localeCompare(b.name));
    const totalSize = files.reduce((s, f) => s + f.size, 0);

    updateProcessingStatus('Processing', 'Parsing ' + files.length + ' file(s)…', 'processing');
    $('lastAction').innerText     = 'Parsing…';
    $('statusFilename').innerText = files.length > 1
        ? files.length + ' files' : truncate(files[0].name, 22);
    hideError();
    $('emptyState').classList.add('hidden');
    showReadingProgress(files.map(f => f.name).join(', '), totalSize);

    let totalLines = 0, totalBytes = 0, errorCount = 0;

    for (const file of files) {
        if (signal.aborted) break;
        let current = null;
        let lineNo  = 0;

        try {
            for await (const line of readLines(file, signal)) {
                if (signal.aborted) break;
                lineNo++; totalLines++; totalBytes += line.length + 1;

                const m = RE_ENTRY.exec(line);
                if (m) {
                    // Save previous entry
                    if (current) LA.allEntries.push(current);
                    const level = m[3] === 'WARNING' ? 'WARN' : m[3];
                    if (level === 'ERROR' || level === 'FATAL') errorCount++;
                    current = {
                        ts:      m[1] + ' ' + m[2].replace(',','.'),
                        date:    m[1],
                        time:    m[2],
                        level,
                        thread:  m[4],
                        logger:  m[5],
                        user:    m[6],
                        message: m[7],
                        extra:   '',      // continuation lines (stack traces)
                        file:    file.name,
                        lineNo,
                    };
                } else if (current) {
                    // continuation line — append to current entry's extra
                    current.extra += (current.extra ? '\n' : '') + line;
                }

                if (LA.allEntries.length >= ROW_CAP) break;

                if (totalLines % PROGRESS_EVERY === 0) {
                    $('readingBytes').textContent   = fmtKb(totalBytes / 1024);
                    $('readingLines').textContent   = totalLines.toLocaleString();
                    $('readingEntries').textContent = LA.allEntries.length.toLocaleString();
                    $('readingErrors').textContent  = errorCount.toLocaleString();
                    await new Promise(r => setTimeout(r, 0));
                }
            }
            if (current) LA.allEntries.push(current);

        } catch (err) {
            if (!signal.aborted) {
                showError('Error reading ' + file.name + ': ' + err.message);
                hideReadingProgress(); return;
            }
            return;
        }
    }

    // Sort merged entries by timestamp
    if (files.length > 1) {
        LA.allEntries.sort((a, b) => a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0);
    }

    LA.visibleEntries = LA.allEntries.slice();

    // Update meta
    const first = LA.allEntries[0]?.ts  || '—';
    const last  = LA.allEntries[LA.allEntries.length - 1]?.ts || '—';
    const fileNames = files.map(f => f.name);
    $('metaFiles').textContent = fileNames.length > 2
        ? fileNames.length + ' files loaded'
        : fileNames.join('\n');
    $('metaSize').textContent    = fmtKb(totalSize / 1024);
    $('metaEntries').textContent = LA.allEntries.length.toLocaleString()
        + (LA.allEntries.length >= ROW_CAP ? ' (capped)' : '');
    $('metaRange').textContent   = first.slice(0,19) + ' → ' + last.slice(0,19);
    $('fileMetaBox').style.display = '';

    updateProcessingStatus('Ready',
        LA.allEntries.length.toLocaleString() + ' entries loaded', 'completed');
    $('lastAction').innerText     = 'Parsed ' + files.length + ' file(s)';
    $('statusEntries').innerText  = LA.allEntries.length.toLocaleString() + ' entries';

    buildSummary();
    renderResult();
}

/* ── Summary ─────────────────────────────────────────────────── */
function buildSummary() {
    const counts = { FATAL:0, ERROR:0, WARN:0, INFO:0, DEBUG:0 };
    for (const e of LA.allEntries) {
        const lv = e.level || 'INFO';
        if (counts[lv] !== undefined) counts[lv]++;
    }
    $('kpiFatal').textContent = counts.FATAL.toLocaleString();
    $('kpiError').textContent = counts.ERROR.toLocaleString();
    $('kpiWarn').textContent  = counts.WARN.toLocaleString();
    $('kpiInfo').textContent  = counts.INFO.toLocaleString();
    if ($('btnMoreDetails')) $('btnMoreDetails').style.display = '';
}

/* ── Render ───────────────────────────────────────────────────── */
function renderResult() {
    hideReadingProgress();
    $('emptyState').classList.add('hidden');
    $('viewToggleGroup').classList.remove('hidden');
    if ($('btnSummary')) $('btnSummary').classList.remove('hidden');
    $('searchInput').style.display     = '';
    buildVirtualTable();
    updateRowCount(LA.visibleEntries.length, LA.allEntries.length);
    setView('table');
}

/* ── Virtual scroll table ─────────────────────────────────────── */
function buildVirtualTable() {
    const wrapper = $('tableView');
    wrapper.innerHTML = '';

    // Single scroll container — header INSIDE so H-scroll stays in sync
    const scroll = document.createElement('div');
    scroll.className = 'la-virt-scroll';
    scroll.id        = 'virtScroll';
    scroll.style.cssText = 'position:relative; overflow:auto; flex:1;';

    // Header inside scroll — sticky to top, moves with H-scroll
    const hdr = document.createElement('div');
    hdr.className = 'la-virt-header';
    HEADERS.forEach((h, i) => {
        const cell = document.createElement('div');
        cell.className = 'la-vhdr-cell la-vhdr-' + i;
        cell.innerHTML = escHtml(h) + ' <span class="sort-icon">⇅</span>';
        cell.title = 'Click to sort';
        cell.style.cursor = 'pointer';
        cell.addEventListener('click', () => sortByCol(i));
        hdr.appendChild(cell);
    });
    scroll.appendChild(hdr);

    // Spacer sets total scrollable height
    const spacer = document.createElement('div');
    spacer.id = 'virtSpacer';
    spacer.style.cssText = 'position:absolute;top:0;left:0;width:1px;pointer-events:none';

    const rowsEl = document.createElement('div');
    rowsEl.id        = 'virtRows';
    rowsEl.className = 'la-virt-rows';

    scroll.appendChild(spacer);
    scroll.appendChild(rowsEl);
    wrapper.appendChild(scroll);
    scroll.addEventListener('scroll', () => renderVirtWindow(scroll.scrollTop));
    renderVirtWindow(0);
}

function renderVirtWindow(scrollTop) {
    const n      = LA.visibleEntries.length;
    const spacer = $('virtSpacer'), rowsEl = $('virtRows');
    if (!spacer || !rowsEl) return;

    const HDR_H = 36;
    spacer.style.height = (n * VIRT_ROW_H + HDR_H) + 'px';
    spacer.style.top    = HDR_H + 'px';
    const scroll  = $('virtScroll');
    const vpH     = scroll ? scroll.clientHeight - HDR_H : 600;
    const adjTop  = Math.max(0, scrollTop - HDR_H);
    const firstIdx = Math.max(0, Math.floor(adjTop / VIRT_ROW_H) - VIRT_OVERSCAN);
    const lastIdx  = Math.min(n - 1, Math.ceil((adjTop + vpH) / VIRT_ROW_H) + VIRT_OVERSCAN);

    rowsEl.style.transform = `translateY(${HDR_H + firstIdx * VIRT_ROW_H}px)`;
    rowsEl.innerHTML = '';

    const frag = document.createDocumentFragment();
    for (let i = firstIdx; i <= lastIdx; i++) {
        const e  = LA.visibleEntries[i];
        const tr = document.createElement('div');
        tr.className = 'la-virt-row la-level-' + (e.level||'INFO').toLowerCase()
            + (i % 2 ? ' la-row-alt' : '');

        // Expand/collapse for multi-line entries
        const hasExtra = e.extra && e.extra.trim();
        tr.innerHTML =
            `<div class="la-vcell la-vc-ts">${escHtml(e.ts.slice(0,23))}</div>
             <div class="la-vcell la-vc-lv"><span class="la-badge la-badge-${(e.level||'INFO').toLowerCase()}">${escHtml(e.level||'')}</span></div>
             <div class="la-vcell la-vc-th" title="${escHtml(e.thread)}">${escHtml(e.thread)}</div>
             <div class="la-vcell la-vc-lg" title="${escHtml(e.logger)}">${escHtml(e.logger)}</div>
             <div class="la-vcell la-vc-us">${escHtml(e.user)}</div>
             <div class="la-vcell la-vc-ms" title="${escHtml(e.message+(hasExtra?'\n'+e.extra:''))}">
                ${hasExtra ? `<button class="la-expand-btn" onclick="showDetail(${i})">＋</button>` : ''}
                ${escHtml(e.message)}
             </div>`;
        frag.appendChild(tr);
    }
    rowsEl.appendChild(frag);
}

/* ── Detail popup ─────────────────────────────────────────────── */
function showDetail(idx) {
    const e = LA.visibleEntries[idx];
    if (!e) return;
    const existing = $('la-detail-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'la-detail-modal';
    modal.className = 'la-detail-modal';
    modal.innerHTML =
        `<div class="la-detail-card">
            <div class="la-detail-header">
                <span class="la-badge la-badge-${(e.level||'info').toLowerCase()}">${escHtml(e.level)}</span>
                <span class="la-detail-ts">${escHtml(e.ts)}</span>
                <button class="la-detail-close" onclick="document.getElementById('la-detail-modal').remove()">✕</button>
            </div>
            <div class="la-detail-meta">
                <div><span class="la-dl">Thread:</span> ${escHtml(e.thread)}</div>
                <div><span class="la-dl">Logger:</span> ${escHtml(e.logger)}</div>
                <div><span class="la-dl">User:</span>   ${escHtml(e.user)}</div>
                <div><span class="la-dl">File:</span>   ${escHtml(e.file||'—')} line ${e.lineNo||'—'}</div>
            </div>
            <div class="la-detail-msg">${escHtml(e.message)}</div>
            ${e.extra ? `<pre class="la-detail-stack">${escHtml(e.extra)}</pre>` : ''}
        </div>`;
    modal.onclick = evt => { if (evt.target === modal) modal.remove(); };
    document.body.appendChild(modal);
}


// ── Column sorting ─────────────────────────────────────────────
let _sortCol = -1, _sortAsc = true;

function sortByCol(colIdx) {
    _sortAsc  = _sortCol === colIdx ? !_sortAsc : true;
    _sortCol  = colIdx;

    // Update header icons
    document.querySelectorAll('.la-vhdr-cell').forEach((c, i) => {
        c.classList.remove('sort-asc','sort-desc');
        const ic = c.querySelector('.sort-icon');
        if (ic) ic.textContent = '⇅';
        if (i === colIdx) {
            c.classList.add(_sortAsc ? 'sort-asc' : 'sort-desc');
            if (ic) ic.textContent = _sortAsc ? '↑' : '↓';
        }
    });

    // Sort visibleEntries by the selected column
    const colKeys = ['ts','level','thread','logger','user','message'];
    const key = colKeys[colIdx] || 'ts';
    LA.visibleEntries.sort((a, b) => {
        const av = (a[key] || '').toLowerCase();
        const bv = (b[key] || '').toLowerCase();
        return _sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });

    const sc = $('virtScroll'); if (sc) sc.scrollTop = 0;
    renderVirtWindow(0);
    updateRowCount(LA.visibleEntries.length, LA.allEntries.length);
}

// ── Details popup (error patterns / loggers) ────────────────────
function showSummaryPopup() {
    const existing = $('la-summary-popup');
    if (existing) { existing.remove(); return; }

    const errMap = {}, logMap = {}, userMap = {};
    for (const e of LA.allEntries) {
        const lv = e.level || 'INFO';
        if (lv === 'ERROR' || lv === 'FATAL' || lv === 'WARN') {
            const key = (e.message||'').replace(/\d+/g,'#').replace(/[A-Z]\d+/g,'#ID').slice(0,80);
            errMap[key]    = (errMap[key]||0)+1;
            logMap[e.logger] = (logMap[e.logger]||0)+1;
            userMap[e.user]  = (userMap[e.user]||0)+1;
        }
    }
    const toRows = (m,n) => Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,n)
        .map(([name,cnt]) =>
            `<tr><td class="sp-cnt">${cnt.toLocaleString()}</td>
             <td class="sp-name" title="${escHtml(name)}">${escHtml(name)}</td>
             <td><button class="sp-filter-btn" onclick="filterByMsg(${JSON.stringify(name)});$('la-summary-popup').remove()">🔍</button></td></tr>`
        ).join('');
    const toRowsL = (m,n) => Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,n)
        .map(([name,cnt]) =>
            `<tr><td class="sp-cnt">${cnt.toLocaleString()}</td>
             <td class="sp-name" title="${escHtml(name)}">${escHtml(name)}</td>
             <td><button class="sp-filter-btn" onclick="filterByLogger(${JSON.stringify(name)});$('la-summary-popup').remove()">🔍</button></td></tr>`
        ).join('');

    const popup = document.createElement('div');
    popup.id = 'la-summary-popup';
    popup.className = 'la-summary-popup';
    popup.innerHTML = `
        <div class="la-sp-window">
            <div class="la-sp-header">
                <span>📊 Error Details</span>
                <button class="la-sp-close" onclick="document.getElementById('la-summary-popup').remove()">✕</button>
            </div>
            <div class="la-sp-body">
                <div class="la-sp-section">
                    <div class="la-sp-title">Top Error Patterns</div>
                    <table class="sp-table">${toRows(errMap,20)}</table>
                </div>
                <div class="la-sp-section">
                    <div class="la-sp-title">Top Loggers with Errors</div>
                    <table class="sp-table">${toRowsL(logMap,15)}</table>
                </div>
                <div class="la-sp-section">
                    <div class="la-sp-title">Top Users in Errors</div>
                    <table class="sp-table">${toRowsL(userMap,10)}</table>
                </div>
            </div>
        </div>`;
    popup.onclick = e => { if (e.target === popup) popup.remove(); };
    document.body.appendChild(popup);
}

/* ── Filters ──────────────────────────────────────────────────── */
function applyFilters() {
    if (!LA.allEntries.length) return;
    const fTs1    = ($('fTs1')?.value    || '').trim();
    const fTs2    = ($('fTs2')?.value    || '').trim();
    const fThread = ($('fThread')?.value || '').toLowerCase().trim();
    const fLogger = ($('fLogger')?.value || '').toLowerCase().trim();
    const fUser   = ($('fUser')?.value   || '').toLowerCase().trim();
    const fMsg    = ($('fMsg')?.value    || '').toLowerCase().trim();

    LA.visibleEntries = LA.allEntries.filter(e => {
        const ts = e.ts || '';
        if (fTs1 && ts < fTs1) return false;
        if (fTs2 && ts > fTs2) return false;
        if (!LA.activeLevels.has(e.level || 'INFO')) return false;
        if (fThread && !(e.thread||'').toLowerCase().includes(fThread)) return false;
        if (fLogger && !(e.logger||'').toLowerCase().includes(fLogger)) return false;
        if (fUser   && !(e.user  ||'').toLowerCase().includes(fUser))   return false;
        if (fMsg    && !((e.message||'')+(e.extra||'')).toLowerCase().includes(fMsg)) return false;
        return true;
    });

    const sc = $('virtScroll'); if (sc) sc.scrollTop = 0;
    renderVirtWindow(0);
    updateRowCount(LA.visibleEntries.length, LA.allEntries.length);
    if ($('filterResult'))
        $('filterResult').textContent = LA.visibleEntries.length === LA.allEntries.length
            ? '' : LA.visibleEntries.length.toLocaleString()
                   + ' of ' + LA.allEntries.length.toLocaleString() + ' entries';
}

function toggleLevel(btn) {
    const lv = btn.dataset.level;
    if (LA.activeLevels.has(lv)) {
        LA.activeLevels.delete(lv);
        btn.classList.remove('active');
    } else {
        LA.activeLevels.add(lv);
        btn.classList.add('active');
    }
    applyFilters();
}

function clearFilters() {
    ['fTs1','fTs2','fThread','fLogger','fUser','fMsg'].forEach(id => { if ($(id)) $(id).value = ''; });
    LA.activeLevels = new Set(['FATAL','ERROR','WARN','INFO','DEBUG','TRACE','WARNING']);
    document.querySelectorAll('.la-level-pill').forEach(b => b.classList.add('active'));
    LA.visibleEntries = LA.allEntries.slice();
    const sc = $('virtScroll'); if (sc) sc.scrollTop = 0;
    renderVirtWindow(0);
    updateRowCount(LA.visibleEntries.length, LA.allEntries.length);
    if ($('filterResult')) $('filterResult').textContent = '';
}

/* ── Quick filters from summary panel ──────────────────────────── */
function quickFilter(what) {
    clearFilters();
    if (what === 'ERROR')        { LA.activeLevels = new Set(['ERROR']); }
    else if (what === 'WARN')    { LA.activeLevels = new Set(['WARN','WARNING']); }
    else if (what === 'FATAL')   { LA.activeLevels = new Set(['FATAL']); }
    else if (what === 'errors_warns') { LA.activeLevels = new Set(['FATAL','ERROR','WARN','WARNING']); }
    document.querySelectorAll('.la-level-pill').forEach(b =>
        b.classList.toggle('active', LA.activeLevels.has(b.dataset.level)));
    applyFilters();
    setView('table');
    switchDock('filter');
}

function filterByMsg(msg) {
    clearFilters();
    const key = msg.replace(/#ID/g,'').replace(/#/g,'').slice(0, 40).trim();
    if ($('fMsg')) $('fMsg').value = key;
    applyFilters();
    setView('table');
    switchDock('filter');
}
function filterByLogger(lg) {
    clearFilters();
    if ($('fLogger')) $('fLogger').value = lg;
    applyFilters();
    setView('table');
    switchDock('filter');
}

/* ── Quick search (toolbar) ─────────────────────────────────────── */
function quickSearch(q) {
    if (!LA.allEntries.length) return;
    q = q.trim().toLowerCase();
    LA.visibleEntries = q
        ? LA.allEntries.filter(e =>
            (e.ts+e.level+e.thread+e.logger+e.user+e.message+(e.extra||''))
            .toLowerCase().includes(q))
        : LA.allEntries.slice();
    const sc = $('virtScroll'); if (sc) sc.scrollTop = 0;
    renderVirtWindow(0);
    updateRowCount(LA.visibleEntries.length, LA.allEntries.length);
}

/* ── Jump to timestamp ───────────────────────────────────────────── */
function jumpToTimestamp() {
    const ts = ($('jumpTs')?.value || '').trim();
    if (!ts || !LA.visibleEntries.length) return;
    let lo = 0, hi = LA.visibleEntries.length - 1, found = 0;
    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if ((LA.visibleEntries[mid].ts || '') < ts) lo = mid + 1;
        else { found = mid; hi = mid - 1; }
    }
    const sc = $('virtScroll');
    if (sc) sc.scrollTop = found * VIRT_ROW_H;
    renderVirtWindow(found * VIRT_ROW_H);
    if ($('jumpResult'))
        $('jumpResult').textContent = 'Row ' + (found+1).toLocaleString()
            + ': ' + (LA.visibleEntries[found].ts || '—');
}

/* ── View toggle ─────────────────────────────────────────────────── */
function setView(view) {
    $('tableView').classList.toggle('hidden', view !== 'table');
    $('rawView').classList.toggle('hidden',   view !== 'raw');
    $('btnViewTable').classList.toggle('active', view === 'table');
    $('btnViewRaw').classList.toggle('active',   view === 'raw');
    if (view === 'raw') {
        $('rawPre').textContent = LA.visibleEntries.slice(0, 2000)
            .map(e => e.ts + ' ' + e.level + ' [' + e.thread + '] '
                + e.logger + ' ' + e.user + ' - ' + e.message
                + (e.extra ? '\n' + e.extra : ''))
            .join('\n');
    }
}

/* ── Reading progress ────────────────────────────────────────────── */
function showReadingProgress(name, sizeBytes) {
    $('readingOverlay').style.display = 'flex';
    $('readingFileName').textContent  = truncate(name, 60);
    $('readingBytes').textContent     = fmtKb(sizeBytes / 1024);
    $('readingLines').textContent     = '0';
    $('readingEntries').textContent   = '0';
    $('readingErrors').textContent    = '0';
}
function hideReadingProgress() { $('readingOverlay').style.display = 'none'; }

/* ── Clear ────────────────────────────────────────────────────────── */
function clearWorkspace() {
    if (LA.abortCtrl) { LA.abortCtrl.abort(); LA.abortCtrl = null; }
    LA.allEntries = []; LA.visibleEntries = [];
    LA.activeLevels = new Set(['FATAL','ERROR','WARN','INFO','DEBUG','TRACE']);

    $('emptyState').classList.remove('hidden');
    hideReadingProgress();
    ['tableView','rawView','errorBanner'].forEach(id => $(id).classList.add('hidden'));
    $('viewToggleGroup').classList.add('hidden');
    $('searchInput').style.display     = 'none';
    $('searchInput').value             = '';
    $('fileMetaBox').style.display     = 'none';
    $('fileInput').value               = '';
    if($('btnSummary')) $('btnSummary').classList.add('hidden');
    if($('searchInput')) { $('searchInput').style.display='none'; $('searchInput').value=''; }
    $('rowCountBadge').style.display   = 'none';
    $('statusFilename').innerText      = '—';
    $('statusEntries').innerText       = '—';
    $('lastAction').innerText          = 'Workspace cleared';
    ['fTs1','fTs2','fThread','fLogger','fUser','fMsg','jumpTs'].forEach(id => { if($(id)) $(id).value=''; });
    if ($('filterResult')) $('filterResult').textContent = '';
    if ($('jumpResult'))   $('jumpResult').textContent   = '';
    if ($('kpiFatal'))     $('kpiFatal').textContent     = '—';
    if ($('kpiError'))     $('kpiError').textContent     = '—';
    if ($('kpiWarn'))      $('kpiWarn').textContent      = '—';
    if ($('kpiInfo'))      $('kpiInfo').textContent      = '—';
    if ($('topErrors'))    $('topErrors').innerHTML  = '<div class="la-summary-empty">Load a log file to see patterns.</div>';
    if ($('topLoggers'))   $('topLoggers').innerHTML = '<div class="la-summary-empty">Load a log file to see patterns.</div>';
    document.querySelectorAll('.la-level-pill').forEach(b => b.classList.add('active'));
    hideError();
    updateProcessingStatus('Ready', '', 'completed');
    switchDock('file');
}

/* ── Helpers ──────────────────────────────────────────────────────── */
function fmtKb(kb) {
    if (kb == null) return '—';
    if (kb >= 1024) return (kb / 1024).toFixed(1) + ' MB';
    return kb.toFixed(1) + ' KB';
}
function truncate(s, n) { return s && s.length > n ? s.slice(0, n - 1) + '…' : (s || ''); }
function escHtml(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function updateRowCount(visible, total) {
    const b = $('rowCountBadge'); if (!b) return;
    b.style.display = '';
    b.textContent = (total && visible !== total)
        ? visible.toLocaleString() + ' / ' + total.toLocaleString() + ' entries'
        : visible.toLocaleString() + ' entries';
}
function showError(msg) {
    $('errorBanner').textContent = msg;
    $('errorBanner').classList.remove('hidden');
    $('emptyState').classList.add('hidden');
}
function hideError() { $('errorBanner').classList.add('hidden'); }

function updateProcessingStatus(message, detail, state) {
    const status = $('statusMessage'), text = $('progressText'),
          fill = $('progressFill'), wrap = $('progressWrapper');
    if (status) status.innerText = message;
    if (text)   text.innerText   = detail || '';
    if (!fill || !wrap) return;
    fill.classList.remove('ops-bar-processing','ops-bar-completed','ops-bar-failed');
    if (state === 'processing') {
        wrap.classList.remove('hidden'); fill.style.width = '70%';
        fill.classList.add('ops-bar-processing');
    } else if (state === 'completed') {
        wrap.classList.remove('hidden'); fill.style.width = '100%';
        fill.classList.add('ops-bar-completed');
        setTimeout(() => { wrap.classList.add('hidden'); fill.style.width = '0%';
            fill.classList.remove('ops-bar-completed'); }, 2000);
    } else {
        wrap.classList.remove('hidden'); fill.style.width = '100%';
        fill.classList.add('ops-bar-failed');
        setTimeout(() => { wrap.classList.add('hidden'); fill.style.width = '0%';
            fill.classList.remove('ops-bar-failed'); }, 3000);
    }
}

// ── Download Summary Report ────────────────────────────────────
function downloadSummary() {
    if (!LA.allEntries.length) { showError('No log data loaded.'); return; }
    updateProcessingStatus('Processing', 'Building summary report…', 'processing');

    const counts = {FATAL:0,ERROR:0,WARN:0,INFO:0,DEBUG:0};
    const errMap={}, logMap={}, userMap={};
    const errorEntries=[];

    for (const e of LA.allEntries) {
        const lv = e.level||'INFO';
        if (counts[lv]!==undefined) counts[lv]++;
        if (lv==='ERROR'||lv==='FATAL'||lv==='WARN') {
            const key = (e.message||'').replace(/\d+/g,'#').slice(0,80);
            errMap[key]  = (errMap[key]  ||0)+1;
            logMap[e.logger] = (logMap[e.logger]||0)+1;
            userMap[e.user]  = (userMap[e.user]  ||0)+1;
        }
        if (lv==='ERROR'||lv==='FATAL') errorEntries.push(e);
    }

    const toList = (m,n) => Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,n)
        .map(([name,count])=>({name,count}));

    const first = LA.allEntries[0]?.ts||'—';
    const last  = LA.allEntries[LA.allEntries.length-1]?.ts||'—';

    const body = {
        metadata: {
            'Log file(s)':      $('metaFiles')?.textContent||'—',
            'Total size':       $('metaSize')?.textContent||'—',
            'Total entries':    LA.allEntries.length.toLocaleString(),
            'Filtered entries': LA.visibleEntries.length.toLocaleString(),
            'Time range from':  first,
            'Time range to':    last,
        },
        level_counts: counts,
        top_errors:   toList(errMap,  20),
        top_loggers:  toList(logMap,  10),
        top_users:    toList(userMap, 10),
        error_entries: errorEntries.slice(0,5000).map(e=>({
            ts: e.ts, level: e.level, logger: e.logger,
            user: e.user, message: e.message, extra: e.extra||'',
        })),
    };

    fetch('/log-analyzer/save-summary', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
    })
    .then(r=>{
        if(!r.ok) return r.json().then(d=>{throw new Error(d.error||r.statusText);});
        return r.blob();
    })
    .then(blob=>{
        const a=document.createElement('a');
        a.href=URL.createObjectURL(blob);
        a.download='log_summary.txt';
        a.click(); URL.revokeObjectURL(a.href);
        updateProcessingStatus('Ready','Summary saved to outputs/log_analyzer/','completed');
        $('lastAction').innerText='Summary downloaded';
    })
    .catch(err=>{
        updateProcessingStatus('Error',err.message,'failed');
        showError('Summary failed: '+err.message);
    });
}
