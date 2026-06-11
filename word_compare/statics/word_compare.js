'use strict';

const $ = id => document.getElementById(id);

(function () {

    let cacheData = null;
    let activeView = 'diff';

    // ─────────────────────────────────────────────
    // File input handlers
    // ─────────────────────────────────────────────
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

    // ─────────────────────────────────────────────
    // Run Compare
    // ─────────────────────────────────────────────
    $('compareBtn').onclick = async () => {
        const form = new FormData();
        form.append('oldFile', $('oldFile').files[0]);
        form.append('newFile', $('newFile').files[0]);

        const status = $('statusMessage');
        if (status) status.innerText = 'Comparing documents...';

        try {
            const res = await fetch('/word_compare/compare', { method: 'POST', body: form });
            const data = await res.json();

            if (!res.ok || data.error) {
                if (status) status.innerText = 'Error: ' + data.error;
                return;
            }

            cacheData = data;
            $('sidebarDownloadBtn').disabled = false;
            if (status) status.innerText = 'Comparison completed.';

            // Update stats
            const stats = data.stats;
            $('statsRow').style.display = 'flex';
            $('statAdded').querySelector('span').innerText    = stats.added;
            $('statRemoved').querySelector('span').innerText  = stats.removed;
            $('statModified').querySelector('span').innerText = stats.modified;

            // Update panel headers
            $('oldDocHeader').innerText = data.file1_name || 'Base Document';
            $('newDocHeader').innerText = data.file2_name || 'Revised Document';
            $('imgOldHeader').innerText = (data.file1_name || 'Base') + ' — Images';
            $('imgNewHeader').innerText = (data.file2_name || 'Revised') + ' — Images';

            // Hide empty state and render active view
            $('emptyState').style.display = 'none';
            showView(activeView);

        } catch (err) {
            if (status) status.innerText = 'Network error.';
            console.error(err);
        }
    };

    // ─────────────────────────────────────────────
    // View switching
    // ─────────────────────────────────────────────
    $('viewDiff').onclick   = () => switchTab('diff');
    $('viewImages').onclick = () => switchTab('images');
    $('viewLog').onclick    = () => switchTab('log');

    function switchTab(name) {
        activeView = name;
        ['viewDiff', 'viewImages', 'viewLog'].forEach(id => $
(id).classList.remove('active'));
        const btnMap = { diff: 'viewDiff', images: 'viewImages', log: 'viewLog' };
        $(btnMap[name]).classList.add('active');
        if (cacheData) showView(name);
    }

    function showView(name) {
        $('diffView').style.display   = 'none';
        $('imagesView').style.display = 'none';
        $('logView').style.display    = 'none';
        $('emptyState').style.display = 'none';

        if (name === 'diff') {
            $('diffView').style.display = 'flex';
            renderDiff();
            bindScrollSync();
        } else if (name === 'images') {
            $('imagesView').style.display = 'flex';
            renderImages();
        } else {
            $('logView').style.display = 'flex';
            renderLog();
        }
    }

    // ─────────────────────────────────────────────
    // Diff renderer
    // ─────────────────────────────────────────────
    function renderDiff() {
        if (!cacheData) return;
        const { old: oldRows, new: newRows } = cacheData.diff;

        $('leftLines').innerHTML  = buildDiffHTML(oldRows);
        $('rightLines').innerHTML = buildDiffHTML(newRows);
    }

    function buildDiffHTML(rows) {
        return rows.map(r => {
            const cls = r.css || 'normal';
            const txt = r.html || '';
            return `<div class="diff-line ${cls}">${escapeHtml(txt)}</div>`;
        }).join('');
    }

    function escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // ─────────────────────────────────────────────
    // Synchronized scrolling
    // ─────────────────────────────────────────────
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

    // ─────────────────────────────────────────────
    // Images renderer
    // ─────────────────────────────────────────────
    function renderImages() {
        if (!cacheData) return;
        renderImagePane($('imagesOld'), cacheData.images_old, 'Base');
        renderImagePane($('imagesNew'), cacheData.images_new, 'Revised');
    }

    function renderImagePane(container, images, label) {
        if (!images || images.length === 0) {
            container.innerHTML = '<div class="images-empty">No images found in this document</div>';
            return;
        }
        container.innerHTML = images.map((img, idx) => `
            <div class="doc-image-card">
                <img src="data:${img.mime};base64,${img.data}" alt="${label} image ${idx + 1}" title="${label} — Image ${idx + 1}">
                <div class="doc-image-label">Image ${idx + 1}</div>
            </div>
        `).join('');
    }

    // ─────────────────────────────────────────────
    // Change log renderer
    // ─────────────────────────────────────────────
    function renderLog() {
        if (!cacheData) return;
        const { old: oldRows, new: newRows } = cacheData.diff;
        const logEntries = [];

        const typeLabels = {
            removed: { label: '<span class="chip removed">Removed</span>', icon: '❌' },
            added:   { label: '<span class="chip added">Added</span>',   icon: '➕' },
            updated: { label: '<span class="chip modified">Modified</span>', icon: '🔄' },
        };

        const maxLen = Math.max(oldRows.length, newRows.length);
        for (let i = 0; i < maxLen; i++) {
            const o = oldRows[i];
            const n = newRows[i];

            const type = o?.css === 'removed' ? 'removed'
                       : n?.css === 'added'   ? 'added'
                       : o?.css === 'updated' || n?.css === 'updated' ? 'updated'
                       : null;

            if (!type) continue;

            logEntries.push({
                idx: logEntries.length + 1,
                type,
                old: o?.text || '',
                new: n?.text || '',
            });
        }

        if (logEntries.length === 0) {
            $('logBody').innerHTML = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:20px">No changes detected.</td></tr>';
            return;
        }

        $('logBody').innerHTML = logEntries.map(e => {
            const meta = typeLabels[e.type];
            const oldTd = e.old ? `<td title="${escapeHtml(e.old)}">${escapeHtml(e.old.substring(0, 120))}${e.old.length > 120 ? '…' : ''}</td>` : '<td style="color:#94a3b8">—</td>';
            const newTd = e.new ? `<td title="${escapeHtml(e.new)}">${escapeHtml(e.new.substring(0, 120))}${e.new.length > 120 ? '…' : ''}</td>` : '<td style="color:#94a3b8">—</td>';
            return `<tr class="wc-log-row">
                <td style="color:#94a3b8;width:40px">${e.idx}</td>
                <td style="width:100px">${meta.label}</td>
                ${oldTd}
                ${newTd}
            </tr>`;
        }).join('');
    }

    // ─────────────────────────────────────────────
    // Page search override (prevent crash on diff lines)
    // ─────────────────────────────────────────────
    window.executePageSearch = function(query) {
        const token = query.trim().toLowerCase();

        if (activeView === 'diff') {
            [$('leftLines'), $('rightLines')].forEach(container => {
                if (!container) return;
                container.querySelectorAll('.diff-line').forEach(line => {
                    if (!token || line.textContent.toLowerCase().includes(token)) {
                        line.style.display = '';
                        if (!token) line.style.outline = '';
                        else line.style.outline = '2px solid #fbbf24';
                    } else {
                        line.style.display = 'none';
                        line.style.outline = '';
                    }
                });
            });
        } else if (activeView === 'log') {
            document.querySelectorAll('.wc-log-row').forEach(row => {
                row.style.display = (!token || row.textContent.toLowerCase().includes(token)) ? '' : 'none';
            });
        }

        if (!token) {
            // Reset all outlines
            document.querySelectorAll('.diff-line').forEach(l => { l.style.display = ''; l.style.outline = ''; });
        }
    };

    // ─────────────────────────────────────────────
    // Clear workspace
    // ─────────────────────────────────────────────
    window.clearWorkspace = function () {
        $('oldFile').value = '';
        $('newFile').value = '';
        $('oldFileName').innerText = 'Select Base Document...';
        $('newFileName').innerText = 'Select Revision Document...';
        $('compareBtn').disabled = true;
        $('sidebarDownloadBtn').disabled = true;

        cacheData = null;
        activeView = 'diff';

        $('diffView').style.display   = 'none';
        $('imagesView').style.display = 'none';
        $('logView').style.display    = 'none';
        $('emptyState').style.display = 'flex';

        $('leftLines').innerHTML  = '';
        $('rightLines').innerHTML = '';
        $('imagesOld').innerHTML  = '<div class="images-empty">No images found</div>';
        $('imagesNew').innerHTML  = '<div class="images-empty">No images found</div>';
        $('logBody').innerHTML    = '';
        $('statsRow').style.display = 'none';

        ['viewDiff', 'viewImages', 'viewLog'].forEach(id => $(id).classList.remove('active'));
        $('viewDiff').classList.add('active');

        const status = $('statusMessage');
        if (status) status.innerText = 'Ready';

        const pw = $('progressWrapper');
        if (pw) pw.classList.add('hidden');
    };

    // ─────────────────────────────────────────────
    // Download
    // ─────────────────────────────────────────────
    window.triggerDownload = function () {
        const status = $('statusMessage');
        if (status) status.innerText = 'Generating highlighted .docx bundle...';
        window.location.href = '/word_compare/download';
    };

    // ─────────────────────────────────────────────
    // Help modal
    // ─────────────────────────────────────────────
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
