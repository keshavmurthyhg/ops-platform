/* =============================================================
   gz_reader/statics/gz_reader.js

   LOCAL-FIRST approach: .gz files are decompressed entirely in
   the browser using the native DecompressionStream API.
   No file upload, no server round-trip for reading.

   Server is only used for:
     POST /gz-reader/split-stream  — split large file (needs server disk)
     GET  /gz-reader/chunk-preview — preview saved chunk
     GET  /gz-reader/chunk-download — download a chunk

   Pipeline (all in-browser):
     File → ReadableStream → DecompressionStream('gzip')
          → TextDecoderStream → line-by-line async generator
          → JMX parser / raw collector → table render
============================================================= */
"use strict";

const $ = id => document.getElementById(id);

// ── State ──────────────────────────────────────────────────────
const GZ = {
    file:        null,    // File object (kept for server split)
    savedAs:     null,    // server-side safe_name after upload (for split)
    result:      null,    // parsed metadata
    allRows:     [],
    visibleRows: [],
    headers:     [],
    sortCol:     -1,
    sortAsc:     true,
    chunkMb:     25,
    rawWrap:     true,
    chunks:      [],
    activeChunk: null,
    sseSource:   null,
    abortCtrl:   null,    // AbortController for cancel
    // Pagination
    _byteOffset:  0,
    _lineOffset:  0,
    _loadedPages: 0,
    _totalLines:  0,
};

// ── MAX constants (browser-side) ──────────────────────────────
const MAX_PREVIEW_ROWS = 500;
const ROW_CAP = 500_000;
const VIRT_ROW_H = 28;
const VIRT_OVERSCAN = 30;
const MAX_RAW_CHARS    = 80_000;

// JMX detection markers (Windchill namespaces)
const JMX_MARKERS = [
    'wt.queue','wt.folder','wt.fv.','wt.admin',
    'com.ptc.core','com.ptc.windchill',
    'wt.intersr','wt.method','wt.inf.',
    'fv.FileServers','esi.tgt',
];

// ── Regex (compiled once) ─────────────────────────────────────
const RE_MBEAN = /((?:wt|com\.ptc|fv|esi)\.[A-Za-z0-9.$_]+)(?:[^A-Za-z0-9.$_\n]([A-Za-z][A-Za-z0-9_]*))?/g;
const RE_TS    = /(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})|(\d{2}\/\w{3}\/\d{4}:\d{2}:\d{2}:\d{2})/;
const RE_KV    = /([A-Za-z][A-Za-z0-9_]{1,40})\s*[=:]\s*(\S{1,80})/g;
const RE_USER  = /(?:user|principal|subject|login|uid)[=:\s]+([A-Za-z0-9@._-]{3,60})/i;
// Printable ASCII segments ≥6 chars (strip binary framing)
const RE_PRINT = /[ -~\t\r\n\u0080-\u00ff]{6,}/g;

// ── Dock switching ────────────────────────────────────────────
function switchDock(name) {
    document.querySelectorAll('.gz-dock-panel').forEach(p => p.classList.add('hidden'));
    const panel = $('panel' + name.charAt(0).toUpperCase() + name.slice(1));
    if (panel) panel.classList.remove('hidden');
}

// ── Drop zones ────────────────────────────────────────────────
function onDragOver(e)  { e.preventDefault(); $('dropZone').classList.add('drag-over'); }
function onDragLeave()  { $('dropZone').classList.remove('drag-over'); }
function onDrop(e) {
    e.preventDefault(); $('dropZone').classList.remove('drag-over');
    const f = e.dataTransfer.files[0]; if (f) handleFileSelect(f);
}
function onDragOver2(e) { e.preventDefault(); $('dropZoneSplit').classList.add('drag-over'); }
function onDragLeave2() { $('dropZoneSplit').classList.remove('drag-over'); }
function onDrop2(e) {
    e.preventDefault(); $('dropZoneSplit').classList.remove('drag-over');
    const f = e.dataTransfer.files[0]; if (f) handleFileSelect(f);
}

function handleFileSelect(file) {
    if (!file) return;
    if (file.name.toLowerCase().endsWith('.gz')) {
        openLocalGz(file);
    } else {
        openPlainFile(file);
    }
}

async function* streamPlainLines(file, signal, startByte=0) {
    const SLICE = 4 * 1024 * 1024;
    let offset = startByte, leftover = '';
    while (offset < file.size) {
        if (signal?.aborted) break;
        const text = await file.slice(offset, offset + SLICE).text();
        const chunk = leftover + text;
        const lines = chunk.split('\n');
        leftover = lines.pop();
        for (const l of lines) yield l;
        offset += SLICE;
        await new Promise(r => setTimeout(r, 0));
    }
    if (leftover) yield leftover;
}

async function openPlainFile(file) {
    if (GZ.abortCtrl) GZ.abortCtrl.abort();
    GZ.abortCtrl = new AbortController();
    GZ.file = file; GZ.savedAs = null; GZ.allRows = []; GZ.visibleRows = []; GZ.headers = []; GZ.result = null;
    GZ._lineOffset=0; GZ._byteOffset=0; GZ._loadedPages=0; GZ._totalLines=0;
    GZ._estimatedTotalPages=0; GZ._estimatedTotalLines=0;
    GZ._estimatedTotalPages=0; GZ._estimatedTotalLines=0;
    if($('pageIndicator')){$('pageIndicator').style.display='none';}
    if($('btnNextPage')){$('btnNextPage').style.display='none';}
    updateProcessingStatus('Processing', 'Reading ' + file.name + '…', 'processing');
    $('lastAction').innerText = 'Reading…';
    $('statusFilename').innerText = truncate(file.name, 22);
    $('statusFormat').innerText = '…';
    hideError();
    $('emptyState').classList.add('hidden');
    showReadingProgress(file.name, file.size);
    const result = await _parseLineIter(streamPlainLines(file, GZ.abortCtrl.signal), file, GZ.abortCtrl.signal, false);
    if (!result) return;
    GZ.result = result;
    GZ._lineOffset = result.lines_this_page || 0;
    GZ._byteOffset = result.bytes_this_page || 0;
    updateProcessingStatus('Ready', 'Read locally — ' + GZ.allRows.length.toLocaleString() + ' records', 'completed');
    $('lastAction').innerText = 'Opened ' + file.name;
    renderResult(GZ.result);
}

// ── Browser-side gzip line iterator ──────────────────────────
async function* streamGzLines(file, signal) {
    /* Yields decoded text lines directly from the local .gz file.
       Uses native DecompressionStream — no upload, no server. */

    if (typeof DecompressionStream === 'undefined') {
        throw new Error('Your browser does not support DecompressionStream. '
            + 'Please use Edge 103+ or Chrome 80+.');
    }

    const ds      = new DecompressionStream('gzip');
    const tds     = new TextDecoderStream('utf-8', { fatal: false });
    const pipe    = file.stream().pipeThrough(ds).pipeThrough(tds);
    const reader  = pipe.getReader();

    let leftover  = '';
    try {
        while (true) {
            if (signal?.aborted) break;
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = leftover + value;
            const lines = chunk.split('\n');
            leftover    = lines.pop();          // incomplete last line
            for (const line of lines) yield line;
        }
        if (leftover) yield leftover;
    } finally {
        reader.cancel().catch(() => {});
    }
}

// ── JMX detection from first N lines ────────────────────────
function detectJmx(sampleLines) {
    const joined = sampleLines.join('\n');
    let hits = 0;
    for (const m of JMX_MARKERS) { if (joined.includes(m)) hits++; }
    return hits >= 3;
}

// ── Extract printable segments from a binary-mixed line ──────
function printableSegments(line) {
    const segs = [];
    let m;
    RE_PRINT.lastIndex = 0;
    while ((m = RE_PRINT.exec(line)) !== null) {
        const s = m[0].trim();
        if (s.length >= 6) segs.push(s);
    }
    return segs;
}

// ── Parse a JMX segment into rows ───────────────────────────
function parseJmxSeg(seg, ts, user) {
    const rows = [];
    RE_MBEAN.lastIndex = 0;
    RE_KV.lastIndex    = 0;
    const mbeans   = [...seg.matchAll(RE_MBEAN)];
    const kvs      = [...seg.matchAll(RE_KV)];

    if (mbeans.length) {
        for (const mhit of mbeans) {
            const mbean = mhit[1];
            const attr  = mhit[2] || '';
            const parts = mbean.split('.');
            const comp  = parts.length >= 2 ? parts[0] + '.' + parts[1] : parts[0];
            if (kvs.length) {
                for (const [, k, v] of kvs)
                    rows.push([ts, user, comp, mbean, attr || k, v, seg.slice(0, 120)]);
            } else {
                rows.push([ts, user, comp, mbean, attr, '', seg.slice(0, 120)]);
            }
        }
    } else if (kvs.length) {
        for (const [, k, v] of kvs)
            rows.push([ts, user, '', '', k, v, seg.slice(0, 120)]);
    }
    return rows;
}

// ── Shared parse loop — supports append mode for pagination ──
async function _parseLineIter(lineIter, file, signal, isGz, appendMode=false) {
    const headers = ['Timestamp','User','Component','MBean / Cache','Attribute','Value','Raw Segment'];
    let decompBytes=0, lineCount=0, segCount=0;
    let isJmx = appendMode ? true : false;   // JMX already known on append
    let formatKnown=appendMode, collecting=true, rawChars=0;
    const rawLines=[], sampleLines=[];
    let currentTs = appendMode ? (GZ.allRows[GZ.allRows.length-1]?.[0]||'') : '';
    let currentUser = '';
    const rowsBefore = appendMode ? GZ.allRows.length : 0;

    let linesConsumed = 0;
    let bytesConsumed = 0;   // raw bytes read (for plain file byte-offset seek)
    try {
        for await (const line of lineIter) {
            if (signal.aborted) break;
            lineCount++; decompBytes += line.length + 1;
            bytesConsumed += line.length + 1;  // +1 for newline
            if (!appendMode && sampleLines.length < 200) sampleLines.push(line);
            if (!formatKnown && sampleLines.length >= 100) {
                isJmx = detectJmx(sampleLines); formatKnown = true;
                $('statusFormat').innerText = isJmx ? 'JMX' : 'TEXT';
                updateProcessingStatus('Processing', (isJmx?'JMX detected — ':'')+'Reading '+file.name+'…','processing');
            }
            if (isJmx) {
                if (collecting) {
                    linesConsumed = lineCount;   // mark progress before each line
                    for (const seg of printableSegments(line)) {
                        segCount++;
                        const tsHit = RE_TS.exec(seg);
                        if (tsHit) currentTs = tsHit[1] || tsHit[2] || currentTs;
                        const uHit = RE_USER.exec(seg);
                        if (uHit) currentUser = uHit[1];
                        const newRows = parseJmxSeg(seg, currentTs, currentUser);
                        GZ.allRows.push(...newRows);
                        if (GZ.allRows.length >= ROW_CAP * (GZ._loadedPages + 1)) {
                            collecting = false;
                            break;   // stop collecting rows
                        }
                    }
                    if (!collecting) break;   // EXIT the outer loop immediately — don't count rest
                }
            } else {
                if (rawChars < MAX_RAW_CHARS) { rawLines.push(line); rawChars += line.length+1; }
            }
            if (lineCount % 50000 === 0) { updateReadingProgress(decompBytes, lineCount); await new Promise(r=>setTimeout(r,0)); }
        }
    } catch(err) {
        if (!signal.aborted) {
            updateProcessingStatus('Error', err.message, 'failed');
            $('lastAction').innerText = 'Read failed';
            showError('Could not read file: ' + err.message);
            hideReadingProgress(); return null;
        }
        return null;
    }
    if (!collecting) linesConsumed = lineCount;  // final position when cap hit
    if (!formatKnown) isJmx = detectJmx(sampleLines);
    const fmt = isJmx ? 'jmx' : 'text';
    // _totalLines = absolute file line position (offset for skip on next page)
    // For page 1:  linesConsumed = lines read until cap
    // For page 2+: linesConsumed = lines read from skipped position until cap
    GZ._totalLines += linesConsumed;
    return {
        filename: file.name, format: fmt,
        compressed_kb: isGz ? Math.round(file.size/1024*10)/10 : 0,
        file_size_kb:  Math.round(decompBytes/1024*10)/10,
        total_rows:    GZ.allRows.length,
        line_count:    GZ._totalLines,   // absolute file position so far
        lines_this_page: linesConsumed,
        bytes_this_page: bytesConsumed,
        decomp_bytes_page: decompBytes,
        segment_count: segCount, truncated: !collecting,
        headers: isJmx ? headers : [],
        raw: isJmx ? '' : rawLines.join('\n').slice(0, MAX_RAW_CHARS),
        newRows: GZ.allRows.length - rowsBefore,
    };
}


// ══════════════════════════════════════════════════════════════════
// PAGINATION — Load Next 500k Rows
// Re-reads the file from scratch, skips already-consumed lines,
// appends new rows to GZ.allRows. Memory grows across pages.
// Page indicator: "Page X of Y" where Y = ceil(totalLines / 500k)
// ══════════════════════════════════════════════════════════════════
async function loadNextPage() {
    if (!GZ.file) { showError('No file open.'); return; }
    if (!GZ.result?.truncated) { return; }

    const btn = $('btnNextPage');
    if (btn) { btn.disabled=true; btn.textContent='⏳ Loading…'; }

    if (GZ.abortCtrl) GZ.abortCtrl.abort();
    GZ.abortCtrl = new AbortController();
    const signal  = GZ.abortCtrl.signal;
    const isGz    = GZ.file.name.toLowerCase().endsWith('.gz');
    GZ._loadedPages++;
    const pageNum = GZ._loadedPages + 1;

    updateProcessingStatus('Processing',
        'Loading page ' + pageNum + ' (skipping ' + skipN.toLocaleString() + ' lines)…', 'processing');
    $('lastAction').innerText = 'Loading page ' + pageNum + '…';
    showReadingProgress(GZ.file.name, GZ.file.size);

    let pageIter;
    if (!isGz) {
        // Plain file: seek directly to byte offset — O(1), no skip loop
        pageIter = streamPlainLines(GZ.file, signal, GZ._byteOffset);
    } else {
        // GZ file: must decompress from start, but skip iteratively
        // yield every 10k lines to prevent call-stack overflow
        const skipN = GZ._lineOffset;
        const rawIter = streamGzLines(GZ.file, signal);
        pageIter = (async function* () {
            let n = 0;
            for await (const line of rawIter) {
                if (signal.aborted) break;
                if (n < skipN) {
                    n++;
                    if (n % 10000 === 0) await new Promise(r => setTimeout(r, 0));
                    continue;
                }
                yield line;
            }
        })();
    }

    const result = await _parseLineIter(pageIter, GZ.file, signal, isGz, true);

    if (!result) {
        GZ._loadedPages--;
        if (btn) { btn.disabled=false; btn.textContent='⏩ Load Next 500k Rows'; }
        return;
    }

    GZ._lineOffset += result.lines_this_page || 0;
    GZ._byteOffset += result.bytes_this_page  || 0;
    GZ.result = Object.assign({}, GZ.result, result);
    GZ.visibleRows = GZ.allRows.slice();

    hideReadingProgress();

    const totalPages = GZ._estimatedTotalPages || Math.ceil((GZ.result.line_count||1) / ROW_CAP);
    const hasMore = result.truncated;

    updateProcessingStatus('Ready',
        'Page ' + pageNum + ' of ~' + totalPages + ' loaded — '
        + GZ.allRows.length.toLocaleString() + ' rows total', 'completed');
    $('lastAction').innerText = 'Page ' + pageNum + ' of ~' + totalPages;
    if ($('pageIndicator')) { $('pageIndicator').textContent = 'Page ' + pageNum + ' of ~' + totalPages; }

    // Update meta
    if ($('metaRows')) {
        $('metaRows').textContent = GZ.allRows.length.toLocaleString() + ' records'
            + (hasMore ? ' (more available)' : ' — all loaded')
            + ' · ' + (result.line_count||0).toLocaleString() + ' lines';
    }
    if ($('jmxTruncNote')) {
        $('jmxTruncNote').textContent = hasMore
            ? 'Page ' + pageNum + ' of ~' + totalPages
              + ' — ' + GZ.allRows.length.toLocaleString() + ' rows loaded'
            : '✓ All ' + GZ.allRows.length.toLocaleString() + ' rows loaded (' + totalPages + ' pages)';
    }

    // Rebuild virtual table with new rows
    buildVirtualTable();
    updateRowCount(GZ.visibleRows.length, GZ.allRows.length);

    // Update next-page button
    if (btn) {
        btn.disabled = !hasMore;
        btn.style.display = hasMore ? '' : 'none';
        btn.textContent = hasMore ? '⏩ Load Next 500k Rows' : 'All Loaded';
    }
}

// ── Open .gz ──────────────────────────────────────────────────
async function openLocalGz(file) {
    if (GZ.abortCtrl) GZ.abortCtrl.abort();
    GZ.abortCtrl = new AbortController();
    GZ.file=file; GZ.savedAs=null; GZ.allRows=[]; GZ.visibleRows=[]; GZ.headers=[]; GZ.result=null;
    GZ._lineOffset=0; GZ._byteOffset=0; GZ._loadedPages=0; GZ._totalLines=0;
    GZ._estimatedTotalPages=0; GZ._estimatedTotalLines=0;
    GZ._estimatedTotalPages=0; GZ._estimatedTotalLines=0;
    if($('pageIndicator')){$('pageIndicator').style.display='none';}
    if($('btnNextPage')){$('btnNextPage').style.display='none';}
    updateProcessingStatus('Processing','Reading '+file.name+' locally…','processing');
    $('lastAction').innerText='Reading…'; $('statusFilename').innerText=truncate(file.name,22);
    $('statusFormat').innerText='…'; hideError();
    $('emptyState').classList.add('hidden');
    showReadingProgress(file.name, file.size);
    const result = await _parseLineIter(streamGzLines(file,GZ.abortCtrl.signal), file, GZ.abortCtrl.signal, true);
    if (!result) return;
    GZ.result = result;
    GZ._lineOffset = result.line_count || 0;
    updateProcessingStatus('Ready','File read locally — no upload needed','completed');
    $('lastAction').innerText = 'Opened '+file.name+' locally';
    renderResult(GZ.result);
    if (result.format === 'jmx') uploadToServerBackground(file);
}

// ── Background server upload (for split endpoint only) ───────
function uploadToServerBackground(file) {
    const fd = new FormData();
    fd.append('file', file);

    // Show subtle indicator
    $('splitUploadStatus').textContent = '⏳ Syncing to server for split…';
    $('splitUploadStatus').style.display = '';

    fetch('/gz-reader/upload', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data._saved_as) {
                GZ.savedAs = data._saved_as;
                $('btnSplit').disabled = false;
                $('splitUploadStatus').textContent = '✓ Ready to split';
                setTimeout(() => { $('splitUploadStatus').style.display = 'none'; }, 3000);
            }
        })
        .catch(() => {
            $('splitUploadStatus').textContent = '⚠ Server sync failed — split unavailable';
        });
}

// ── Reading progress overlay ─────────────────────────────────
function showReadingProgress(name, sizeBytes) {
    $('readingOverlay').style.display = 'flex';
    $('readingFileName').textContent  = name;
    $('readingFileSize').textContent  = fmtKb(sizeBytes / 1024);
    $('readingLines').textContent     = '0 lines';
    $('readingDecomp').textContent    = '0 MB';
}
function updateReadingProgress(decompBytes, lines) {
    $('readingLines').textContent = lines.toLocaleString() + ' lines';
    $('readingDecomp').textContent = fmtKb(decompBytes / 1024);
}
function hideReadingProgress() {
    $('readingOverlay').style.display = 'none';
}

// ── Render result ─────────────────────────────────────────────
function renderResult(data) {
    hideReadingProgress();
    $('emptyState').classList.add('hidden');

    // File panel meta
    $('metaFilename').textContent     = data.filename    || '—';
    $('metaFormat').textContent       = (data.format || '?').toUpperCase();
    $('metaCompressed').textContent   = fmtKb(data.compressed_kb);
    $('metaDecompressed').textContent = fmtKb(data.file_size_kb);
    const estLn = GZ._estimatedTotalLines ? ' · ~'+Math.round(GZ._estimatedTotalLines/1000000)+'M lines' : '';
    $('metaRows').textContent         = data.format === 'jmx'
        ? (data.allRows?.length || GZ.allRows.length).toLocaleString()
          + (data.truncated ? '+ records (preview)' : ' records')
        : (data.line_count || 0).toLocaleString() + ' lines';
    $('fileMetaBox').style.display   = '';
    $('btnDownload').style.display   = '';
    if($('btnSummary')) $('btnSummary').classList.remove('hidden');
    if($('searchInput')) $('searchInput').style.display='';

    // Split panel
    $('splitUploadZone').classList.add('hidden');
    $('splitFileChip').classList.remove('hidden');
    $('splitFileLabel').textContent = truncate(data.filename || '—', 26);
    $('splitNoFileHint').classList.add('hidden');
    // Split button enabled only after server background upload completes
    // (handled in uploadToServerBackground)

    // Toolbar
    $('viewToggleGroup').classList.remove('hidden');
    $('formatPill').textContent        = (data.format || '?').toUpperCase();
    $('formatPill').style.display      = '';

    // JMX info bar
    // Page indicator
    // Estimate total pages:
    // For plain files: linesConsumed is accurate, extrapolate
    // For gz files: use compression ratio × compressed file size
    let totalPgs = 1;
    if (data.format === 'jmx' && data.truncated) {
        const isGz = GZ.file && GZ.file.name.toLowerCase().endsWith('.gz');
        if (isGz && data.decomp_bytes_page && GZ.file.size > 0) {
            // compression ratio = decompressed_page / (compressed_fraction_read)
            // We don't know how much compressed data was read, so use a simpler ratio:
            // estimate total_decomp = file.size * (decomp_bytes_page / bytes_per_row * typical_gz_ratio)
            // Windchill JMX gz typically has 8-12x compression ratio
            // Use: total_lines ≈ (GZ.file.size * GZ_RATIO) / (decomp_bytes_page / lines_this_page)
            const avgBytesPerLine = data.decomp_bytes_page / Math.max(data.lines_this_page, 1);
            const GZ_RATIO = 8;  // conservative Windchill JMX compression ratio
            const estimatedTotalLines = Math.round((GZ.file.size * GZ_RATIO) / avgBytesPerLine);
            totalPgs = Math.max(1, Math.ceil(estimatedTotalLines / ROW_CAP));
            GZ._estimatedTotalLines = estimatedTotalLines;
        } else {
            // Plain file: extrapolate from bytes consumed vs file size
            const fracRead = (data.bytes_this_page||1) / (GZ.file?.size||1);
            totalPgs = Math.max(1, Math.ceil(1 / fracRead));
        }
    }
    GZ._estimatedTotalPages = totalPgs;
    if ($('pageIndicator')) {
        $('pageIndicator').textContent = 'Page 1 of ~' + totalPgs;
        $('pageIndicator').style.display = data.format==='jmx' ? '' : 'none';
    }
    // Pagination button
    if ($('btnNextPage')) {
        $('btnNextPage').style.display = (data.format==='jmx' && data.truncated) ? '' : 'none';
        $('btnNextPage').disabled = false;
        $('btnNextPage').textContent = '⏩ Load Next 500k Rows';
    }
    if (data.format === 'jmx') {
        $('jmxBar').classList.remove('hidden');
        $('jmxBarText').textContent =
            'JMX binary — read locally, no upload. '
            + (data.segment_count || 0).toLocaleString() + ' text segments extracted.';
        $('jmxTruncNote').textContent = data.truncated
            ? 'Page 1 of ~' + (GZ._estimatedTotalPages||'?') + ' — ' + GZ.allRows.length.toLocaleString() + ' rows. Click ⏩ to load more.'
            : '';
    } else {
        $('jmxBar').classList.add('hidden');
    }

    updateSplitEstimate();

    const hasTable = data.headers && data.headers.length && GZ.allRows.length;
    if (hasTable) {
        GZ.headers     = data.headers;
        GZ.visibleRows = GZ.allRows.slice();
        buildVirtualTable();
        updateRowCount(GZ.visibleRows.length, GZ.allRows.length);
        setView('table');
        $('searchInput').style.display = '';
    } else {
        $('rawPre').textContent        = data.raw || '(no readable content)';
        setView('raw');
    }
}

// ── Virtual scroll table ──────────────────────────────────────
// Header is INSIDE the scroll container so it moves horizontally
// with the data, but sticks vertically via position:sticky top:0.
// Frozen column 0 (Timestamp) uses position:sticky left:0.
function buildVirtualTable() {
    const wrapper = $('tableView');
    wrapper.innerHTML = '';

    // Single scroll container for both header and rows
    const scroll = document.createElement('div');
    scroll.className = 'gz-virt-scroll'; scroll.id = 'virtScroll';
    scroll.style.cssText = 'position:relative; overflow:auto; flex:1;';

    // Header inside scroll — sticks to top
    const hdr = document.createElement('div');
    hdr.className = 'gz-virt-header';
    GZ.headers.forEach((h, i) => {
        const cell = document.createElement('div');
        cell.className = 'gz-vhdr-cell gz-vhdr-' + i;
        cell.innerHTML = escHtml(h) + ' <span class="sort-icon">⇅</span>';
        cell.onclick = () => sortByCol(i);
        hdr.appendChild(cell);
    });
    scroll.appendChild(hdr);

    // Spacer sets total scroll height
    const spacer = document.createElement('div');
    spacer.id = 'virtSpacer';
    spacer.style.cssText = 'position:absolute;top:0;left:0;width:1px;pointer-events:none';

    // Rows container
    const rowsEl = document.createElement('div');
    rowsEl.id = 'virtRows'; rowsEl.className = 'gz-virt-rows';

    scroll.appendChild(spacer);
    scroll.appendChild(rowsEl);
    wrapper.appendChild(scroll);

    scroll.addEventListener('scroll', () => renderVirtWindow(scroll.scrollTop));
    renderVirtWindow(0);
}

function renderVirtWindow(scrollTop) {
    const n = GZ.visibleRows.length;
    const spacer = $('virtSpacer'), rowsEl = $('virtRows');
    if (!spacer || !rowsEl) return;
    const HDR_H = 36; // header height in px
    spacer.style.height = (n * VIRT_ROW_H + HDR_H) + 'px';
    spacer.style.top    = HDR_H + 'px';
    const scroll = $('virtScroll');
    const vpH = scroll ? scroll.clientHeight - HDR_H : 600;
    const adjTop = Math.max(0, scrollTop - HDR_H);
    const firstIdx = Math.max(0, Math.floor(adjTop / VIRT_ROW_H) - VIRT_OVERSCAN);
    const lastIdx  = Math.min(n-1, Math.ceil((adjTop+vpH)/VIRT_ROW_H) + VIRT_OVERSCAN);
    rowsEl.style.transform = `translateY(${HDR_H + firstIdx * VIRT_ROW_H}px)`;
    rowsEl.innerHTML = '';
    const frag = document.createDocumentFragment();
    for (let i = firstIdx; i <= lastIdx; i++) {
        const row = GZ.visibleRows[i];
        const tr = document.createElement('div');
        tr.className = 'gz-virt-row' + (i%2?' gz-virt-row-alt':'');
        GZ.headers.forEach((_, ci) => {
            const td = document.createElement('div');
            td.className = 'gz-vcell gz-vcell-' + ci;
            td.textContent = row[ci] || ''; td.title = row[ci] || '';
            tr.appendChild(td);
        });
        frag.appendChild(tr);
    }
    rowsEl.appendChild(frag);
}

function buildTable(headers, rows) { /* kept for compat */ buildVirtualTable(); }

function sortByCol(idx) {
    GZ.sortAsc = GZ.sortCol === idx ? !GZ.sortAsc : true;
    GZ.sortCol = idx;
    document.querySelectorAll('.gz-vhdr-cell').forEach((c,i) => {
        c.classList.remove('sort-asc','sort-desc');
        const ic = c.querySelector('.sort-icon'); if(ic) ic.textContent='⇅';
        if (i===idx){ c.classList.add(GZ.sortAsc?'sort-asc':'sort-desc'); if(ic)ic.textContent=GZ.sortAsc?'↑':'↓'; }
    });
    GZ.visibleRows.sort((a,b)=>{
        const av=(a[idx]||'').toLowerCase(),bv=(b[idx]||'').toLowerCase();
        const an=parseFloat(av),bn=parseFloat(bv);
        if(!isNaN(an)&&!isNaN(bn)) return GZ.sortAsc?an-bn:bn-an;
        return GZ.sortAsc?av.localeCompare(bv):bv.localeCompare(av);
    });
    const sc=$('virtScroll'); if(sc) sc.scrollTop=0;
    renderVirtWindow(0);
    updateRowCount(GZ.visibleRows.length, GZ.allRows.length);
}

// ── Sidebar filters ───────────────────────────────────────────
function applyFilters() {
    if (!GZ.allRows.length) return;
    const fTs1  = ($('fTs1') ?$('fTs1').value :'').trim();
    const fTs2  = ($('fTs2') ?$('fTs2').value :'').trim();
    const fUser = ($('fUser') ?$('fUser').value :'').toLowerCase().trim();
    const fComp = ($('fComp') ?$('fComp').value :($('fComponent')?$('fComponent').value:'')).toLowerCase().trim();
    const fAttr = ($('fAttr') ?$('fAttr').value :($('fAttribute')?$('fAttribute').value:'')).toLowerCase().trim();
    const fVal  = ($('fVal')  ?$('fVal').value  :($('fValue')    ?$('fValue').value    :'')).toLowerCase().trim();

    GZ.visibleRows = GZ.allRows.filter(row => {
        const ts = row[0]||'';
        if (fTs1 && ts < fTs1) return false;
        if (fTs2 && ts > fTs2) return false;
        if (fUser && !(row[1]||'').toLowerCase().includes(fUser)) return false;
        if (fComp && !((row[2]||'')+(row[3]||'')).toLowerCase().includes(fComp)) return false;
        if (fAttr && !(row[4]||'').toLowerCase().includes(fAttr)) return false;
        if (fVal  && !(row[5]||'').toLowerCase().includes(fVal))  return false;
        return true;
    });
    const sc=$('virtScroll'); if(sc) sc.scrollTop=0;
    renderVirtWindow(0);
    updateRowCount(GZ.visibleRows.length, GZ.allRows.length);
    if($('filterResult')) $('filterResult').textContent = GZ.visibleRows.length===GZ.allRows.length
        ?'' : GZ.visibleRows.length.toLocaleString()+' of '+GZ.allRows.length.toLocaleString()+' match';
}
function clearFilters() {
    ['fTs1','fTs2','fUser','fComp','fAttr','fVal','fTimestamp','fComponent','fAttribute','fValue']
        .forEach(id=>{if($(id))$(id).value='';});
    GZ.visibleRows = GZ.allRows.slice();
    const sc=$('virtScroll'); if(sc) sc.scrollTop=0;
    renderVirtWindow(0);
    updateRowCount(GZ.visibleRows.length, GZ.allRows.length);
    if($('filterResult')) $('filterResult').textContent='';
}

function jumpToTimestamp() {
    const ts = ($('jumpTs')?$('jumpTs').value:'').trim();
    if (!ts||!GZ.visibleRows.length) return;
    let lo=0,hi=GZ.visibleRows.length-1,found=0;
    while(lo<=hi){const mid=(lo+hi)>>1;if((GZ.visibleRows[mid][0]||'')<ts)lo=mid+1;else{found=mid;hi=mid-1;}}
    const sc=$('virtScroll'); if(sc) sc.scrollTop=found*VIRT_ROW_H;
    renderVirtWindow(found*VIRT_ROW_H);
    if($('jumpResult')) $('jumpResult').textContent='Row '+(found+1).toLocaleString()+': '+(GZ.visibleRows[found][0]||'—');
}

// ── Quick search ──────────────────────────────────────────────
function quickSearch(q) {
    if (!GZ.allRows.length) return;
    q = q.trim().toLowerCase();
    GZ.visibleRows = q ? GZ.allRows.filter(r=>r.some(c=>(c||'').toLowerCase().includes(q))) : GZ.allRows.slice();
    const sc=$('virtScroll'); if(sc) sc.scrollTop=0;
    renderVirtWindow(0);
    updateRowCount(GZ.visibleRows.length, GZ.allRows.length);
}

// ── View toggle ───────────────────────────────────────────────
function setView(view) {
    $('tableView').classList.toggle('hidden',  view !== 'table');
    $('rawView').classList.toggle('hidden',    view !== 'raw');
    $('chunksView').classList.toggle('hidden', view !== 'chunks');
    $('btnViewTable').classList.toggle('active',  view === 'table');
    $('btnViewRaw').classList.toggle('active',    view === 'raw');
    $('btnViewChunks').classList.toggle('active', view === 'chunks');
}
function toggleWrap() {
    GZ.rawWrap = !GZ.rawWrap;
    $('rawPre').classList.toggle('no-wrap', !GZ.rawWrap);
    $('rawWrapBtn').textContent = 'Wrap: ' + (GZ.rawWrap ? 'ON' : 'OFF');
}

// ── Split (server-side, after background upload) ──────────────
function setChunk(mb, btn) {
    GZ.chunkMb = mb;
    document.querySelectorAll('.gz-preset').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    $('customMb').value = mb;
    updateSplitEstimate();
}
function setCustomChunk(val) {
    GZ.chunkMb = Math.max(5, Math.min(500, parseInt(val) || 25));
    document.querySelectorAll('.gz-preset').forEach(b => b.classList.remove('active'));
    updateSplitEstimate();
}
function updateSplitEstimate() {
    const el = $('splitEstimate');
    if (!GZ.result || !GZ.result.file_size_kb) { el.textContent = 'Open a file first.'; return; }
    const totalMb = GZ.result.file_size_kb / 1024;
    const chunks  = Math.ceil(totalMb / GZ.chunkMb);
    el.textContent = totalMb.toFixed(0) + ' MB → ~' + chunks
        + ' chunk' + (chunks !== 1 ? 's' : '') + ' of ≤' + GZ.chunkMb + ' MB';
}

function doSplit() {
    if (!GZ.savedAs) {
        $('splitNoFileHint').classList.remove('hidden');
        $('splitNoFileHint').textContent = '⏳ Server is still syncing the file. Please wait a moment.';
        return;
    }
    $('splitNoFileHint').classList.add('hidden');
    if (GZ.sseSource) { GZ.sseSource.close(); GZ.sseSource = null; }

    GZ.chunks = []; GZ.activeChunk = null;
    $('chunkTabs').innerHTML   = '';
    $('chunkViewer').innerHTML =
        '<div class="gz-chunk-progress">'
        + '<div>Splitting — chunks appear here as each is written to outputs/…</div>'
        + '<div class="gz-chunk-progress-bar"><div class="gz-chunk-progress-fill"></div></div>'
        + '</div>';

    $('btnViewChunks').style.display = '';
    setView('chunks');

    const btn = $('btnSplit');
    btn.disabled = true; btn.textContent = '⏳ Splitting…';
    updateProcessingStatus('Processing', 'Splitting into ' + GZ.chunkMb + ' MB chunks…', 'processing');
    $('lastAction').innerText = 'Splitting…';

    const url = '/gz-reader/split-stream?saved_as='
        + encodeURIComponent(GZ.savedAs) + '&split_mb=' + GZ.chunkMb;
    GZ.sseSource = new EventSource(url);

    GZ.sseSource.onmessage = e => {
        let msg; try { msg = JSON.parse(e.data); } catch { return; }
        if (msg.type === 'chunk') {
            addChunkTab(msg);
        } else if (msg.type === 'done') {
            GZ.sseSource.close(); GZ.sseSource = null;
            btn.disabled = false; btn.textContent = '✂ Split & Preview Chunks';
            updateProcessingStatus('Ready', GZ.chunks.length + ' chunks in outputs/', 'completed');
            $('lastAction').innerText = 'Split done — ' + GZ.chunks.length + ' chunks';
            if (!GZ.activeChunk && GZ.chunks.length) loadChunkPreview(GZ.chunks[0].filename);
        } else if (msg.type === 'error') {
            GZ.sseSource.close(); GZ.sseSource = null;
            btn.disabled = false; btn.textContent = '✂ Split & Preview Chunks';
            updateProcessingStatus('Error', msg.message, 'failed');
            showError('Split error: ' + msg.message);
        }
    };
    GZ.sseSource.onerror = () => {
        if (GZ.sseSource) { GZ.sseSource.close(); GZ.sseSource = null; }
        btn.disabled = false; btn.textContent = '✂ Split & Preview Chunks';
    };
}

function addChunkTab(msg) {
    GZ.chunks.push({ filename: msg.filename, size_kb: msg.size_kb });
    const tab = document.createElement('button');
    tab.className = 'gz-chunk-tab';
    tab.id        = 'tab_' + msg.filename;
    tab.innerHTML = 'Part ' + msg.index + ' <span class="chunk-size">' + fmtKb(msg.size_kb) + '</span>';
    tab.onclick   = () => loadChunkPreview(msg.filename);
    $('chunkTabs').appendChild(tab);
    if (GZ.chunks.length === 1) loadChunkPreview(msg.filename);
}

function loadChunkPreview(filename) {
    GZ.activeChunk = filename;
    document.querySelectorAll('.gz-chunk-tab').forEach(t =>
        t.classList.toggle('active', t.id === 'tab_' + filename));
    $('chunkViewer').innerHTML =
        '<div class="gz-chunk-header">'
        + '<span class="gz-chunk-path">outputs/' + escHtml(filename) + '</span>'
        + '<button class="gz-chunk-dl-btn" onclick="downloadChunk(\'' + escAttr(filename) + '\')">⬇ Download</button>'
        + '</div><div class="gz-chunk-content" style="color:#94a3b8;font-style:italic">Loading…</div>';

    fetch('/gz-reader/chunk-preview/' + encodeURIComponent(filename))
        .then(r => r.json())
        .then(data => {
            const trunc = data.size_kb > 80
                ? '<span style="color:#f59e0b;font-size:11px;margin-left:8px">First 80 KB of ' + fmtKb(data.size_kb) + '</span>' : '';
            $('chunkViewer').innerHTML =
                '<div class="gz-chunk-header">'
                + '<span class="gz-chunk-path">outputs/' + escHtml(filename) + ' — ' + fmtKb(data.size_kb) + '</span>'
                + trunc
                + '<button class="gz-chunk-dl-btn" onclick="downloadChunk(\'' + escAttr(filename) + '\')">⬇ Download</button>'
                + '</div><div class="gz-chunk-content">' + escHtml(data.content || data.error || '') + '</div>';
        })
        .catch(err => {
            $('chunkViewer').querySelector('.gz-chunk-content').textContent = 'Preview failed: ' + err.message;
        });
}

function downloadChunk(filename) {
    window.location.href = '/gz-reader/chunk-download/' + encodeURIComponent(filename);
}

function downloadDecompressed() {
    // No server file for local-read mode — trigger browser download directly
    if (!GZ.file) return;
    showError('Decompressed download requires the file to be re-opened via server. Use Split to get readable chunks instead.');
}

// ── Download Summary Report ───────────────────────────────────
function downloadSummary() {
    if (!GZ.allRows.length) { showError('No data loaded.'); return; }
    updateProcessingStatus('Processing','Building summary report…','processing');

    // Count top items
    const mbean_map={}, comp_map={}, attr_map={}, user_map={};
    for (const row of GZ.allRows) {
        const [ts,user,comp,mbean,attr,val] = row;
        if(mbean) mbean_map[mbean]=(mbean_map[mbean]||0)+1;
        if(comp)  comp_map[comp] =(comp_map[comp] ||0)+1;
        if(attr)  attr_map[attr] =(attr_map[attr] ||0)+1;
        if(user)  user_map[user] =(user_map[user] ||0)+1;
    }
    const toList = (m,n) => Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,n)
        .map(([name,count])=>({name,count}));

    const body = {
        filename: `gz_summary_${(GZ.result?.filename||'jmx').replace(/[^a-z0-9_]/gi,'_')}`,
        metadata: {
            'Source file':        GZ.result?.filename||'—',
            'Compressed size':    fmtKb(GZ.result?.compressed_kb),
            'Decompressed size':  fmtKb(GZ.result?.file_size_kb),
            'Total records':      GZ.allRows.length.toLocaleString() + ' (all loaded pages)',
            'Filtered records':   GZ.visibleRows.length.toLocaleString(),
            'Line count':         (GZ.result?.line_count||0).toLocaleString(),
            'Pages loaded':       (GZ._loadedPages+1) + ' of ~' + Math.ceil((GZ.result?.line_count||1)/ROW_CAP),
        },
        top_mbeans:     toList(mbean_map, 20),
        top_components: toList(comp_map,  10),
        top_attrs:      toList(attr_map,  10),
        top_users:      toList(user_map,  10),
        headers:        GZ.headers,
        filtered_rows:  GZ.visibleRows.slice(0, 10000),
    };

    fetch('/gz-reader/save-summary', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
    })
    .then(r => {
        if (!r.ok) return r.json().then(d=>{throw new Error(d.error||r.statusText);});
        return r.blob();
    })
    .then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = body.filename + '.txt';
        a.click(); URL.revokeObjectURL(a.href);
        updateProcessingStatus('Ready','Summary saved to outputs/gz_summary/','completed');
        $('lastAction').innerText = 'Summary downloaded';
    })
    .catch(err => {
        updateProcessingStatus('Error', err.message, 'failed');
        showError('Summary failed: ' + err.message);
    });
}

// ── Clear ─────────────────────────────────────────────────────
function clearWorkspace() {
    if (GZ.abortCtrl) { GZ.abortCtrl.abort(); GZ.abortCtrl = null; }
    if (GZ.sseSource) { GZ.sseSource.close(); GZ.sseSource = null; }

    GZ.file = null; GZ.savedAs = null; GZ.result = null;
    GZ.allRows = []; GZ.visibleRows = []; GZ.headers = [];
    GZ.sortCol = -1; GZ.sortAsc = true; GZ.chunks = []; GZ.activeChunk = null;

    $('emptyState').classList.remove('hidden');
    hideReadingProgress();
    ['tableView','rawView','chunksView','jmxBar','errorBanner']
        .forEach(id => $(id).classList.add('hidden'));
    $('viewToggleGroup').style.display   = 'none';
    $('formatPill').style.display        = 'none';
    $('rowCountBadge').style.display     = 'none';
    $('btnViewChunks').style.display     = 'none';
    $('searchInput').style.display       = 'none';
    $('searchInput').value               = '';
    $('fileMetaBox').style.display       = 'none';
    $('btnDownload').style.display       = 'none';
    $('fileInput').value                 = '';
    $('splitUploadZone').classList.remove('hidden');
    $('splitFileChip').classList.add('hidden');
    $('splitNoFileHint').classList.add('hidden');
    $('splitUploadStatus').style.display = 'none';
    $('btnSplit').disabled               = true;
    $('btnSplit').textContent            = '✂ Split & Preview Chunks';
    $('splitEstimate').textContent       = 'Open a file first.';
    $('chunkTabs').innerHTML             = '';
    $('rawPre').textContent              = '';
    $('filterResult').textContent        = '';
    ['fTimestamp','fUser','fComponent','fAttribute','fValue'].forEach(id => $(id).value = '');
    $('statusFilename').innerText        = '—';
    $('statusFormat').innerText          = '—';
    $('lastAction').innerText            = 'Workspace cleared';
    hideError();
    updateProcessingStatus('Ready','','completed');
    switchDock('file');
}

// ── Helpers ───────────────────────────────────────────────────
function fmtKb(kb) {
    if (kb == null) return '—';
    if (kb >= 1024) return (kb/1024).toFixed(1) + ' MB';
    return kb.toFixed(1) + ' KB';
}
function truncate(s, n) { return s && s.length > n ? s.slice(0,n-1)+'…' : (s||''); }
function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) { return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }
function updateRowCount(visible, total) {
    const b = $('rowCountBadge'); if(!b) return;
    if (visible == null) { b.style.display='none'; return; }
    b.style.display = '';
    b.textContent = (total && visible!==total)
        ? visible.toLocaleString()+' / '+total.toLocaleString()+' rows'
        : visible.toLocaleString()+' rows';
}
function showError(msg) {
    $('errorBanner').textContent = msg;
    $('errorBanner').classList.remove('hidden');
    $('emptyState').classList.add('hidden');
}
function hideError() { $('errorBanner').classList.add('hidden'); }

function updateProcessingStatus(message, detail, state) {
    const status = $('statusMessage'), text = $('progressText'),
          fill   = $('progressFill'),  wrap = $('progressWrapper');
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
        setTimeout(() => { wrap.classList.add('hidden'); fill.style.width='0%';
            fill.classList.remove('ops-bar-completed'); }, 2000);
    } else {
        wrap.classList.remove('hidden'); fill.style.width = '100%';
        fill.classList.add('ops-bar-failed');
        setTimeout(() => { wrap.classList.add('hidden'); fill.style.width='0%';
            fill.classList.remove('ops-bar-failed'); }, 3000);
    }
}
