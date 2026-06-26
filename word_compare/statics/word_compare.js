'use strict';

const $ = id => document.getElementById(id);

(function () {

    /* ─────────────────────────────────────────
       State
    ───────────────────────────────────────── */
    let cacheData     = null;
    let activeView    = 'diff';
    let activeSection = null;       // currently displayed section key
    let sectionKeys   = [];         // ordered list of all section keys
    let pageSize      = 10;         // tabs visible per page
    let currentPage   = 0;          // 0-based page index

    /* ─────────────────────────────────────────
       File input handlers
    ───────────────────────────────────────── */
    $('oldFile').onchange = e => {
        $('oldFileName').innerText = e.target.files[0]?.name || 'Select Base Document...';
        checkEnableCompare();
    };
    $('newFile').onchange = e => {
        $('newFileName').innerText = e.target.files[0]?.name || 'Select Revision Document...';
        checkEnableCompare();
    };

    function checkEnableCompare() {
        $('compareBtn').disabled = !($('oldFile').files[0] && $('newFile').files[0]);
    }

    /* ─────────────────────────────────────────
       Run Compare
    ───────────────────────────────────────── */
    $('compareBtn').onclick = async () => {
        const form = new FormData();
        form.append('oldFile', $('oldFile').files[0]);
        form.append('newFile', $('newFile').files[0]);

        const status = $('statusMessage');
        updateProcessingStatus('Processing', 'Comparing documents...', 'processing'); if (status) status.innerText = 'Processing';

        try {
            const res  = await fetch('/word_compare/compare', { method: 'POST', body: form });
            const data = await res.json();

            if (!res.ok || data.error) {
                updateProcessingStatus('Error', data.error, 'failed'); document.getElementById('lastAction').innerText = 'Compare failed';
                return;
            }

            cacheData    = data;
            sectionKeys  = data.sections || [];
            currentPage  = 0;
            activeSection = sectionKeys[0] || null;

            $('sidebarDownloadBtn').disabled = false;
            updateProcessingStatus('Ready', 'Comparison completed', 'completed'); document.getElementById('lastAction').innerText = 'Comparison completed';

            // Sidebar KPI (totals)
            const t = data.totals;
            $('kpiAdded').innerText    = t.added;
            $('kpiRemoved').innerText  = t.removed;
            $('kpiModified').innerText = t.modified;
            $('kpiTotal').innerText    = t.total;
            $('kpiSidebar').style.display = 'flex';

            // Panel headers
            $('oldDocHeader').innerText  = data.file1_name || 'Base Document';
            $('newDocHeader').innerText  = data.file2_name || 'Revised Document';
            $('imgOldHeader').innerText  = (data.file1_name || 'Base') + ' — Images';
            $('imgNewHeader').innerText  = (data.file2_name || 'Revised') + ' — Images';

            $('emptyState').style.display = 'none';
            showView(activeView);

        } catch (err) {
            updateProcessingStatus('Error', 'Network error', 'failed'); document.getElementById('lastAction').innerText = 'Network error';
            console.error(err);
        }
    };

    /* ─────────────────────────────────────────
       View switching
    ───────────────────────────────────────── */
    $('viewDiff').onclick   = () => switchTab('diff');
    $('viewImages').onclick = () => switchTab('images');
    $('viewLog').onclick    = () => switchTab('log');

    function switchTab(name) {
        activeView = name;
        ['viewDiff', 'viewImages', 'viewLog'].forEach(id => $(id).classList.remove('active'));
        const map = { diff: 'viewDiff', images: 'viewImages', log: 'viewLog' };
        $(map[name]).classList.add('active');
        if (cacheData) showView(name);
    }

    function showView(name) {
        $('diffView').style.display   = 'none';
        $('imagesView').style.display = 'none';
        $('logView').style.display    = 'none';
        $('emptyState').style.display = 'none';

        if (name === 'diff') {
            $('diffView').style.display = 'flex';
            renderSectionTabs();
            renderDiff(activeSection);
            bindScrollSync();
        } else if (name === 'images') {
            $('imagesView').style.display = 'flex';
            renderImages();
        } else {
            $('logView').style.display = 'flex';
            renderLog();
        }
    }

    /* ─────────────────────────────────────────
       Tabs-per-page selector
    ───────────────────────────────────────── */
    window.setTabsPerPage = function(val) {
        pageSize    = parseInt(val, 10) || 10;
        currentPage = 0;
        // Jump to page containing active section
        if (activeSection) {
            const idx = sectionKeys.indexOf(activeSection);
            if (idx >= 0) currentPage = Math.floor(idx / pageSize);
        }
        renderSectionTabs();
    };

    /* ─────────────────────────────────────────
       Section tabs + pagination
    ───────────────────────────────────────── */
    function totalPages() {
        return Math.ceil(sectionKeys.length / pageSize);
    }

    function renderSectionTabs() {
        const container = $('sectionTabs');
        container.innerHTML = '';

        const showAll = pageSize >= 9999;
        const tp      = showAll ? 1 : totalPages();
        const start   = showAll ? 0 : currentPage * pageSize;
        const end     = showAll ? sectionKeys.length : Math.min(start + pageSize, sectionKeys.length);
        const page    = sectionKeys.slice(start, end);

        page.forEach(key => {
            const sd  = cacheData.section_data[key];
            const tot = (sd.added || 0) + (sd.removed || 0) + (sd.modified || 0);
            const btn = document.createElement('button');
            btn.className = 'wc-section-tab' + (key === activeSection ? ' active' : '');
            const label = key.length > 26 ? key.substring(0, 24) + '…' : key;
            btn.title = key;
            btn.innerHTML = `<span class="tab-label">${escHtml(label)}</span>`
                          + (tot > 0 ? `<span class="tab-badge">${tot}</span>` : '');
            btn.onclick = () => switchSection(key);
            container.appendChild(btn);
        });

        // Pagination label
        const displayStart = showAll ? 1 : start + 1;
        const displayEnd   = showAll ? sectionKeys.length : end;
        $('pgLabel').innerText = `${displayStart} to ${displayEnd} of ${sectionKeys.length}`;

        // Show/hide pagination controls
        const showPagination = !showAll && sectionKeys.length > pageSize;
        $('wcPagination').style.display = showPagination ? 'flex' : 'none';

        if (showPagination) {
            $('pgFirst').disabled = currentPage === 0;
            $('pgPrev').disabled  = currentPage === 0;
            $('pgNext').disabled  = currentPage >= tp - 1;
            $('pgLast').disabled  = currentPage >= tp - 1;
        }
    }

    window.goPage = function(dir) {
        const tp = totalPages();
        if (dir === 'first') currentPage = 0;
        else if (dir === 'prev')  currentPage = Math.max(0, currentPage - 1);
        else if (dir === 'next')  currentPage = Math.min(tp - 1, currentPage + 1);
        else if (dir === 'last')  currentPage = tp - 1;
        renderSectionTabs();
    };

    function switchSection(key) {
        activeSection = key;
        // If section is not on current page, jump to its page
        if (pageSize < 9999) {
            const idx = sectionKeys.indexOf(key);
            if (idx >= 0) {
                const targetPage = Math.floor(idx / pageSize);
                if (targetPage !== currentPage) currentPage = targetPage;
            }
        }
        renderSectionTabs();
        renderDiff(key);
        bindScrollSync();
    }

    /* ─────────────────────────────────────────
       Diff renderer
    ───────────────────────────────────────── */
    function renderDiff(key) {
        if (!cacheData || !key) return;
        const sd = cacheData.section_data[key];
        if (!sd) return;

        // Update per-section KPIs in the strip
        $('secKpiAdd').innerText = sd.added    || 0;
        $('secKpiRem').innerText = sd.removed  || 0;
        $('secKpiMod').innerText = sd.modified || 0;

        $('leftLines').innerHTML  = buildDiffHTML(sd.old_rows);
        $('rightLines').innerHTML = buildDiffHTML(sd.new_rows);
    }

    function buildDiffHTML(rows) {
        if (!rows || !rows.length) return '<div class="diff-line blank"></div>';
        return rows.map(r => {
            const cls = r.css || 'normal';
            const prefix = cls === 'removed' ? '❌ '
                         : cls === 'added'   ? '➕ '
                         : cls === 'updated' ? '🔄 '
                         : '';
            return `<div class="diff-line ${cls}">${prefix}${escHtml(r.text || '')}</div>`;
        }).join('');
    }

    function escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /* ─────────────────────────────────────────
       Synchronized scrolling
    ───────────────────────────────────────── */
    function bindScrollSync() {
        const left  = $('leftScroller');
        const right = $('rightScroller');
        if (!left || !right) return;
        let active = null;
        function sync(driver, target) {
            if (active === null || active === driver) {
                active = driver;
                target.scrollTop  = driver.scrollTop;
                target.scrollLeft = driver.scrollLeft;
                clearTimeout(driver._st);
                driver._st = setTimeout(() => { active = null; }, 60);
            }
        }
        left.onscroll  = () => sync(left, right);
        right.onscroll = () => sync(right, left);
    }

    /* ─────────────────────────────────────────
       Images renderer
    ───────────────────────────────────────── */
    function renderImages() {
        if (!cacheData) return;
        renderImagePane($('imagesOld'), cacheData.images_old, 'Base');
        renderImagePane($('imagesNew'), cacheData.images_new, 'Revised');
    }

    function renderImagePane(container, images, label) {
        if (!images || !images.length) {
            container.innerHTML = '<div class="images-empty">No images found in this document</div>';
            return;
        }
        container.innerHTML = images.map((img, idx) => `
            <div class="doc-image-card">
                <img src="data:${img.mime};base64,${img.data}"
                     alt="${label} image ${idx + 1}"
                     title="${label} — Image ${idx + 1}">
                <div class="doc-image-label">Image ${idx + 1}</div>
            </div>
        `).join('');
    }

    /* ─────────────────────────────────────────
       Change log renderer (all sections)
    ───────────────────────────────────────── */
    function renderLog() {
        if (!cacheData) return;
        const typeLabel = {
            added:   '<span class="chip added">Added</span>',
            removed: '<span class="chip removed">Removed</span>',
            updated: '<span class="chip modified">Modified</span>',
        };

        let allLog = [];
        sectionKeys.forEach(key => {
            const sd = cacheData.section_data[key];
            if (sd && sd.change_log) allLog = allLog.concat(sd.change_log);
        });

        if (!allLog.length) {
            $('logBody').innerHTML = '<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:20px">No changes detected.</td></tr>';
            return;
        }

        $('logBody').innerHTML = allLog.map((e, i) => {
            const secShort = e.section.length > 30 ? e.section.substring(0, 28) + '…' : e.section;
            const oldTd = e.old ? `<td title="${escHtml(e.old)}">${escHtml(e.old.substring(0, 100))}${e.old.length > 100 ? '…' : ''}</td>` : '<td style="color:#94a3b8">—</td>';
            const newTd = e.new ? `<td title="${escHtml(e.new)}">${escHtml(e.new.substring(0, 100))}${e.new.length > 100 ? '…' : ''}</td>` : '<td style="color:#94a3b8">—</td>';
            return `<tr class="wc-log-row">
                <td style="color:#94a3b8;width:36px">${i + 1}</td>
                <td title="${escHtml(e.section)}" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(secShort)}</td>
                <td style="width:90px">${typeLabel[e.type] || e.type}</td>
                ${oldTd}
                ${newTd}
            </tr>`;
        }).join('');
    }

    /* ─────────────────────────────────────────
       Page search override
    ───────────────────────────────────────── */
    window.executePageSearch = function(query) {
        const token = query.trim().toLowerCase();

        if (activeView === 'diff') {
            [$('leftLines'), $('rightLines')].forEach(c => {
                if (!c) return;
                c.querySelectorAll('.diff-line').forEach(line => {
                    const match = !token || line.textContent.toLowerCase().includes(token);
                    line.style.display = match ? '' : 'none';
                    line.style.outline = (match && token) ? '2px solid #fbbf24' : '';
                });
            });
            if (!token) {
                document.querySelectorAll('.diff-line').forEach(l => {
                    l.style.display = ''; l.style.outline = '';
                });
            }
        } else if (activeView === 'log') {
            document.querySelectorAll('.wc-log-row').forEach(row => {
                row.style.display = (!token || row.textContent.toLowerCase().includes(token)) ? '' : 'none';
            });
        }
    };

    /* ─────────────────────────────────────────
       Clear workspace
    ───────────────────────────────────────── */
    window.clearWorkspace = function () {
        $('oldFile').value = '';
        $('newFile').value = '';
        $('oldFileName').innerText = 'Select Base Document...';
        $('newFileName').innerText = 'Select Revision Document...';
        $('compareBtn').disabled = true;
        $('sidebarDownloadBtn').disabled = true;

        cacheData = null; sectionKeys = []; activeSection = null; currentPage = 0;
        activeView = 'diff'; pageSize = 10;
        const tppSel = $('tabsPerPage');
        if (tppSel) tppSel.value = '10';

        $('diffView').style.display   = 'none';
        $('imagesView').style.display = 'none';
        $('logView').style.display    = 'none';
        $('emptyState').style.display = 'flex';
        $('kpiSidebar').style.display = 'none';

        $('leftLines').innerHTML  = '';
        $('rightLines').innerHTML = '';
        $('sectionTabs').innerHTML = '';
        $('imagesOld').innerHTML  = '<div class="images-empty">No images found</div>';
        $('imagesNew').innerHTML  = '<div class="images-empty">No images found</div>';
        $('logBody').innerHTML    = '';

        ['viewDiff', 'viewImages', 'viewLog'].forEach(id => $(id).classList.remove('active'));
        $('viewDiff').classList.add('active');

        const status = $('statusMessage');
        updateProcessingStatus('Ready', '', 'completed'); document.getElementById('lastAction').innerText = 'Workspace cleared';
        const pw = $('progressWrapper');
        if (pw) pw.classList.add('hidden');
    };

    /* ─────────────────────────────────────────
       Download
    ───────────────────────────────────────── */
    window.triggerDownload = function () {
        const status = $('statusMessage');
        updateProcessingStatus('Processing', 'Generating .docx bundle...', 'processing'); document.getElementById('lastAction').innerText = 'Generating download...';
        window.location.href = '/word_compare/download';
    };

    /* ─────────────────────────────────────────
       Help modal
    ───────────────────────────────────────── */
    window.toggleHelpSystemModal = async function () {
        const modal = $('helpSystemModal');
        if (!modal) return;
        modal.classList.toggle('hidden');

        if (!modal.classList.contains('hidden')) {
            const indexPane   = $('helpModalIndexPane');
            const contentPane = $('helpModalContentPane');
            indexPane.innerHTML = '<div style="padding:10px;color:#94a3b8;font-size:12px">Loading...</div>';

            try {
                const res  = await fetch('/word_compare/help-data');
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
            } catch (e) {
                indexPane.innerHTML = '<div style="padding:10px;color:#ef4444;font-size:12px">Failed to load help data.</div>';
            }
        }
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
