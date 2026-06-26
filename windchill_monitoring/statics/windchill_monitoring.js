/**
 * windchill_monitoring.js — v14 CLEAN
 * No override chains. Single authoritative implementation.
 *
 * Toolbar: nav tabs + Refresh Data + OPS switcher
 * Sidebar: Run Now, Launch Edge, Collect Stats, Export
 *
 * Auto-refresh: Tx + WVS every 30 min · Worker CSV every 60 min
 * Alerts: Worker >40% · WVS Ready >750 growing · Executing stuck 3x
 * Footer timestamps: show automation run time (not CSV load time)
 */

// ── State ─────────────────────────────────────────────────────────────────────
let cachedTransactions = [];
let cachedWvsQueue     = [];
let cachedWorkers      = [];

// WVS alert state
let prevReadyCount     = 0;
let readyRisingCount   = 0;
let stuckExecutingHits = {};
let autoRefreshCount   = 0;

const WORKER_FAIL_THRESHOLD = 40.0;
const WVS_READY_THRESHOLD   = 750;
const WVS_STUCK_REFRESHES   = 3;
const AUTO_INTERVAL_MS      = 30 * 60 * 1000;
const WORKER_INTERVAL_MS    = 60 * 60 * 1000;

// ── Processing status bar ─────────────────────────────────────────────────────
// Wires to the common main.html IDs: statusMessage, progressWrapper,
// progressFill, progressText — same elements used by common.js.
// States:
//   "processing" → orange bar, blinking animation, shows wrapper
//   "completed"  → green bar, stable, auto-hides after 2 s
//   "failed"     → red bar, blinking animation, auto-hides after 3 s
//   "warning"    → orange bar, stable, auto-hides after 3 s
//   (other/reset)→ hides wrapper, resets bar
function updateLocalStatus(msg, detail, state) {
    const statusEl  = document.getElementById("statusMessage");
    const wrapper   = document.getElementById("progressWrapper");
    const fill      = document.getElementById("progressFill");
    const textEl    = document.getElementById("progressText");

    // Always update status text
    if (statusEl) statusEl.innerText = msg || "";
    if (textEl)   textEl.innerText   = detail || "";

    if (!fill || !wrapper) return;

    // Remove any existing state classes
    fill.classList.remove("wm-bar-processing", "wm-bar-completed", "wm-bar-failed");

    if (state === "processing") {
        wrapper.classList.remove("hidden");
        fill.style.width = "70%";
        fill.style.background = "";        // let CSS class set colour
        fill.classList.add("wm-bar-processing");

    } else if (state === "completed") {
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.style.background = "";
        fill.classList.add("wm-bar-completed");
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.classList.remove("wm-bar-completed");
        }, 2000);

    } else if (state === "failed") {
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.style.background = "";
        fill.classList.add("wm-bar-failed");
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.classList.remove("wm-bar-failed");
        }, 3000);

    } else if (state === "warning") {
        wrapper.classList.remove("hidden");
        fill.style.width = "100%";
        fill.style.background = "#f97316";
        setTimeout(() => {
            wrapper.classList.add("hidden");
            fill.style.width = "0%";
            fill.style.background = "";
        }, 3000);

    } else {
        // idle / reset
        wrapper.classList.add("hidden");
        fill.style.width = "0%";
        fill.style.background = "";
    }
}

// ── Sidebar + section nav ─────────────────────────────────────────────────────
function showSidebarSection(id, el) {
    document.querySelectorAll(".dock-section").forEach(s => s.style.display = "none");
    const t = document.getElementById(id);
    if (t) t.style.display = "block";
    document.querySelectorAll(".dock-item").forEach(i => i.classList.remove("active-dock"));
    if (el) el.classList.add("active-dock");
}

function showSection(name) {
    document.querySelectorAll(".operations-section").forEach(el => el.style.display = "none");
    document.querySelectorAll(".tracker-btn").forEach(b => b.classList.remove("active"));
    const sec = document.getElementById(name + "Section");
    const btn = document.getElementById(name + "ToolbarBtn");
    if (sec) sec.style.display = "flex";
    if (btn) btn.classList.add("active");
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function fmtDate(raw) {
    if (!raw || raw === "N/A") return raw || "N/A";
    const dt = new Date(raw.replace(/ (CEST|CET|UTC|EST|PST|BST)$/, "").replace(" ", "T"));
    if (isNaN(dt)) return raw;
    const M = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return `${String(dt.getDate()).padStart(2,"0")}-${M[dt.getMonth()]}-${dt.getFullYear()} `
         + `${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}`;
}

function setBtn(id, text, disabled) {
    const b = document.getElementById(id);
    if (b) { b.textContent = text; b.disabled = disabled; }
}

function setEl(id, val) { const e = document.getElementById(id); if (e) e.textContent = val; }
function nowTime() { return new Date().toLocaleTimeString(); }

function showSidebarStatus(html, cls) {
    const box = document.getElementById("automationStatus");
    if (!box) return;
    box.style.display = "block";
    box.className = "filter-status-box " + (cls || "filter-status-running");
    box.innerHTML = html;
}

// ── Alert popup ───────────────────────────────────────────────────────────────
function showAlert(icon, title, bodyHtml, headerBg) {
    setEl("alertIcon",  icon);
    setEl("alertTitle", title);
    const b = document.getElementById("alertBody");
    if (b) b.innerHTML = bodyHtml;
    const h = document.getElementById("alertHeader");
    if (h) h.style.background = headerBg || "#fef2f2";
    const o = document.getElementById("alertOverlay");
    if (o) o.style.display = "flex";
}
function closeAlert() { const o = document.getElementById("alertOverlay"); if (o) o.style.display = "none"; }

// ── Worker alerts ─────────────────────────────────────────────────────────────
function checkWorkerAlerts(workers) {
    const high = workers.filter(w => parseFloat(w.failed_pct || w["% Failed Jobs"] || "0") > WORKER_FAIL_THRESHOLD);
    const badge = document.getElementById("workerAlertBadge");
    if (badge) badge.style.display = high.length > 0 ? "inline" : "none";
    if (high.length === 0) return;
    const list = high.map(w => {
        const fp   = parseFloat(w.failed_pct || w["% Failed Jobs"] || "0");
        const name = w.name || w["Worker Name"] || "Unknown";
        return `<div class="wm-alert-worker-row">
            <span class="wm-alert-worker-name">${name}</span>
            <span class="wm-alert-worker-pct">⚠ ${fp.toFixed(2)}% failed</span>
            <span class="wm-alert-worker-detail">Total: ${w.total||"—"} · Failed: ${w.failed||"—"}</span>
        </div>`;
    }).join("");
    showAlert("🚨", "High Worker Failure Rate Detected",
        `<p class="wm-alert-intro">${high.length} worker node${high.length>1?"s":""} exceed the
         <strong>${WORKER_FAIL_THRESHOLD}% failure threshold</strong>:</p>
         <div class="wm-alert-worker-list">${list}</div>
         <p class="wm-alert-action">Check the <strong>Workers</strong> tab for full details.</p>`,
        "#fef2f2");
}

// ── WVS alerts ────────────────────────────────────────────────────────────────
function checkWvsAlerts(queue) {
    const readyJobs     = queue.filter(q => (q.status || "").toUpperCase() === "READY");
    const executingJobs = queue.filter(q => (q.status || "").toUpperCase() === "EXECUTING");
    const readyCount    = readyJobs.length;
    const wvsBadge      = document.getElementById("wvsAlertBadge");

    if (readyCount > WVS_READY_THRESHOLD) {
        if (readyCount > prevReadyCount) readyRisingCount++;
        if (wvsBadge) wvsBadge.style.display = "inline";
        if (readyRisingCount >= 2) {
            showAlert("⚡", "WVS Ready Queue Overload",
                `<p class="wm-alert-intro">The WVS <strong>Ready</strong> queue has exceeded
                 <strong>${WVS_READY_THRESHOLD} jobs</strong> and is growing after
                 ${readyRisingCount} consecutive auto-refreshes.</p>
                 <div class="wm-alert-stat-row">
                     <span class="wm-alert-stat-num">${readyCount}</span>
                     <span class="wm-alert-stat-lbl">Ready jobs currently queued</span>
                 </div>
                 <p class="wm-alert-action">Check worker capacity — queue may be backing up.</p>`,
                "#fef9c3");
        }
    } else {
        readyRisingCount = 0;
        if (wvsBadge) wvsBadge.style.display = "none";
    }
    prevReadyCount = readyCount;

    if (autoRefreshCount > 0) {
        const newStuck = {};
        executingJobs.forEach(j => {
            const key = `${j.queue}|${j.job}`;
            newStuck[key] = (stuckExecutingHits[key] || 0) + 1;
        });
        stuckExecutingHits = newStuck;
        const stuck = executingJobs.filter(j => {
            const key = `${j.queue}|${j.job}`;
            return (stuckExecutingHits[key] || 0) >= WVS_STUCK_REFRESHES;
        });
        if (stuck.length > 0) {
            const stuckList = stuck.map(j =>
                `<div class="wm-alert-worker-row">
                    <span class="wm-alert-worker-name">${j.queue}</span>
                    <span class="wm-alert-worker-pct">Job: ${j.job}</span>
                    <span class="wm-alert-worker-detail">${(j.name||"").substring(0,40)} · ${j.user||""}</span>
                </div>`
            ).join("");
            showAlert("⏱️", "Stuck Executing Jobs Detected",
                `<p class="wm-alert-intro">${stuck.length} job${stuck.length>1?"s":""} ha${stuck.length>1?"ve":"s"} been
                 <strong>Executing</strong> unchanged for <strong>${WVS_STUCK_REFRESHES}+ auto-refreshes</strong>:</p>
                 <div class="wm-alert-worker-list">${stuckList}</div>
                 <p class="wm-alert-action">These jobs may be stalled. Consider checking the worker or resubmitting.</p>`,
                "#f0fdf4");
        }
    }
}

// ── Stale worker stats check ──────────────────────────────────────────────────
function checkWorkerStatsAge(workers) {
    if (!workers || workers.length === 0) return;
    let latestTs = null;
    workers.forEach(w => {
        const ts = w.captured_at || w.capture_timestamp || "";
        if (ts && (!latestTs || ts > latestTs)) latestTs = ts;
    });
    if (!latestTs) return;
    const lastUpdate = new Date(latestTs.replace(" ", "T"));
    if (isNaN(lastUpdate)) return;
    const ageMs  = Date.now() - lastUpdate.getTime();
    const ageMin = Math.round(ageMs / 60000);
    if (ageMs > 60 * 60 * 1000) {
        const ageHrs    = Math.floor(ageMin / 60);
        const ageMinRem = ageMin % 60;
        const ageStr    = ageHrs > 0 ? `${ageHrs}h ${ageMinRem}m` : `${ageMin} minutes`;
        const dash = document.getElementById("dashWorkerContainer");
        if (dash) {
            const old = dash.querySelector(".wm-stale-banner");
            if (old) old.remove();
            const banner = document.createElement("div");
            banner.className = "wm-stale-banner";
            banner.innerHTML = `⚠️ Worker stats are <strong>${ageStr} old</strong> (last: ${latestTs}).
                Click <strong>Collect Stats</strong> in sidebar to refresh.`;
            dash.insertBefore(banner, dash.firstChild);
        }
        const badge = document.getElementById("workerAlertBadge");
        if (badge && badge.style.display === "none") {
            badge.style.display = "inline";
            badge.textContent   = `⏰ Stats ${ageStr} old`;
            badge.style.background = "#fef9c3";
            badge.style.color      = "#92400e";
        }
    }
}

// ── Render: Worker Stats ──────────────────────────────────────────────────────

// Worker queue name classification
// Based on production worker table:
//   vm1480, vm1481             → CATIATXQUEUE
//   vm1482-1485                → CATIAQUEUE
//   vm1486-1488                → CATIAHUGEASM
//   vm1602, vm1603, vm1604     → CATIAQUEUE
//   vm1605                     → CATIAHUGEASM
//   13403-x, 13404-x           → CREOQUEUE
//   15670 (OFFICE suffix)      → OFFICEQUEUE
//   15670-1-THUMBNAIL          → THUMBNAIL
//   15669/15666 (ILLUSTRATE)   → CREOILLUSTRATE
//   18415-x, 19368-x           → CATIAATB
function _workerQueue(name) {
    const n = (name || "").toLowerCase();
    // Exact number matches first (most specific)
    if (/wvm1(480|481)/.test(n)) return "CATIATWXQUEUE";
    if (/wvm1(486|487|488|605)/.test(n)) return "CATIAHUGEASM";
    if (/wvm1(482|483|484|485|602|603|604)/.test(n)) return "CATIAQUEUE";
    // segotwvm catch-all
    if (n.includes("wvm")) return "CATIAQUEUE";
    // Production workers
    if (n.includes("13403") || n.includes("13404")) return "CREOQUEUE";
    if (n.includes("18415") || n.includes("19368")) return "CATIAATB";
    if (n.includes("thumbnail")) return "THUMBNAIL";
    if (n.includes("15669") || n.includes("15666") || n.includes("illustrat")) return "CREOILLUSTRATE";
    if (n.includes("15670") || n.includes("office")) return "OFFICEQUEUE";
    return "OTHER";
}

const QUEUE_COLORS = {
    CREOQUEUE      : "#3b82f6",
    CATIAATB       : "#8b5cf6",
    CATIAQUEUE     : "#f59e0b",
    CATIAHUGEASM   : "#ef4444",
    OFFICEQUEUE    : "#16a34a",
    THUMBNAIL      : "#6b7280",
    CREOILLUSTRATE : "#0ea5e9",
    OTHER          : "#9ca3af",
};

function renderWorkerStats(workers) {
    cachedWorkers = workers;
    // Remove non-worker rows (e.g. "Worker Utilization" header row from scraper)
    workers = (workers || []).filter(function(w) {
        const n = (w.name || w["Worker Name"] || "").toLowerCase();
        return n.includes("segot") || n.includes("segow");
    });

    const body  = document.getElementById("workerStatsBody");
    const dash  = document.getElementById("dashWorkerContainer");
    if (body) body.innerHTML = "";
    if (dash) dash.innerHTML = "";
    let unstable = 0;

    const queueCounts = {};  // { queueName: { total: n, failed: n, workers: [] } }

    workers.forEach(w => {
        const name       = w.name        || w["Worker Name"]      || "—";
        const total      = parseInt(w.total   || w["Total Jobs"]   || "0") || 0;
        const failed     = parseInt(w.failed  || w["Failed Jobs"]  || "0") || 0;
        const success    = w.success     || w["Successful Jobs"]   || "—";
        const failedPct  = w.failed_pct  || w["% Failed Jobs"]     || "—";
        const successPct = w.success_pct || w["% Successful Jobs"] || "—";
        const busyTime   = w.busy_time   || w["Busy Time"]         || "—";
        const fp         = parseFloat(failedPct);
        const isHigh     = fp > WORKER_FAIL_THRESHOLD;
        const isMed      = fp > 5 && !isHigh;
        if (isHigh) unstable++;
        const pillCls = isHigh ? "status-failed" : isMed ? "status-warn" : "status-success";
        const queue   = _workerQueue(name);
        const qcol    = QUEUE_COLORS[queue] || "#9ca3af";

        if (!queueCounts[queue]) queueCounts[queue] = { total: 0, failed: 0, workers: 0 };
        queueCounts[queue].total   += total;
        queueCounts[queue].failed  += failed;
        queueCounts[queue].workers += 1;

        // Parse worker number + display label
        // Full: "segotwvm1482.vcn.ds.volvo.net-CATIAV5:1" → "vm1482"
        // Full: "segotn13403-1.got.volvo.net-PROE:1"      → "13403-1"
        // Full: "SEGOTN15670.vcn.ds.volvo.net-OFFICE:1"   → "15670"
        let shortName = name
            .replace(/\.got\.volvo\.net.*$/i, "")
            .replace(/\.vcn\.ds\.volvo\.net.*$/i, "")
            .replace(/-PROE:\d+$/i,      "")  // strip -PROE:1
            .replace(/-CATIAV5:\d+$/i,   "")  // strip -CATIAV5:1
            .replace(/-THUMBNAIL:\d+$/i, "")  // strip -THUMBNAIL:1
            .replace(/-ILLUSTRATE:\d+$/i,"")  // strip -ILLUSTRATE:2
            .replace(/-OFFICE:\d+$/i,    "")  // strip -OFFICE:1
            .replace(/^segotwvm/i, "vm")
            .replace(/^segotn/i,   "")
            .replace(/^segotw/i,   "w")
            .trim();
        if (!shortName) shortName = name.split(".")[0];

        if (body) body.innerHTML += `<tr class="${isHigh ? "wm-row-alert" : ""}">
            <td class="wk-cell">
                <span class="wk-num" title="${name}">${shortName}</span><span class="wk-q-badge" style="background:${qcol}18;color:${qcol};border:1px solid ${qcol}40;">${queue}</span>
            </td>
            <td>${total}</td><td>${failed}</td><td>${success}</td>
            <td><span class="status-pill ${pillCls}">${failedPct}</span></td>
            <td>${successPct}</td><td>${busyTime}</td></tr>`;

        if (dash) {
            // Mini card: number + queue badge on left, total and fail% on right
            dash.innerHTML += `<div class="wcard-row ${isHigh ? "wcard-row-alert" : ""}">
                <span class="wcard-name" title="${name}">${shortName}</span>
                <span class="ops-type-pill" style="background:${qcol}18;color:${qcol};border:1px solid ${qcol}40;font-size:9px;padding:1px 5px;flex-shrink:0;">${queue.replace("QUEUE","").replace("CATIAATB","ATB")}</span>
                <span class="wcard-total" style="margin-left:auto;">T:${total}</span>
                <span class="wcard-pill ${isHigh?"wcard-fail":isMed?"wcard-warn":"wcard-ok"}" style="flex-shrink:0;">
                    ${isHigh?"⚠ ":isMed?"△ ":"✓ "}${failedPct}</span>
            </div>`;
        }
    });

    // Worker KPI bar
    const wkpiBar = document.getElementById("workerKpiBar");
    if (wkpiBar) {
        let html = `<div class="ops-kpi-chip" style="color:#374151;border-color:#374151;">
            <span class="ops-kpi-chip-val">${workers.length}</span>
            <span class="ops-kpi-chip-lbl">Workers</span></div>`;
        if (unstable > 0) html += `<div class="ops-kpi-chip" style="color:#dc2626;border-color:#ef4444;">
            <span class="ops-kpi-chip-val">${unstable}</span>
            <span class="ops-kpi-chip-lbl">Critical</span></div>`;
        Object.entries(queueCounts).sort((a,b)=>b[1].workers-a[1].workers).forEach(([q,d])=>{
            const col = QUEUE_COLORS[q]||"#6b7280";
            const fpct = d.total>0 ? ((d.failed/d.total)*100).toFixed(1) : "0.0";
            html += `<div class="ops-kpi-chip" style="color:${col};border-color:${col};" title="${q}: ${d.workers} workers">
                <span class="ops-kpi-chip-val">${d.workers}</span>
                <span class="ops-kpi-chip-lbl">${q.replace("QUEUE","").replace("CATIAHU","HUGE")}</span></div>`;
        });
        wkpiBar.innerHTML = html;
    }

    setEl("kpiTotalWorkers", workers.length || "—");
    const kpiU = document.getElementById("kpiUnstableWorkers");
    if (kpiU) kpiU.textContent = unstable > 0
        ? `⚠ ${unstable} above ${WORKER_FAIL_THRESHOLD}% threshold`
        : "All workers healthy";

    if (unstable > 0) checkWorkerAlerts(workers);
    checkWorkerStatsAge(workers);
}

// ── Render: WVS Queue ─────────────────────────────────────────────────────────
const WVS_STATUS_STYLE = {
    "READY":          { bg:"#fef3c7", color:"#d97706", border:"#f59e0b", icon:"⚡" },
    "EXECUTING":      { bg:"#eff6ff", color:"#2563eb", border:"#3b82f6", icon:"⚙"  },
    "JOB SUCCESSFUL": { bg:"#f0fdf4", color:"#16a34a", border:"#22c55e", icon:"✓"  },
    "JOB FAILED":     { bg:"#fef2f2", color:"#dc2626", border:"#ef4444", icon:"✗"  },
    "FAILED":         { bg:"#fef2f2", color:"#dc2626", border:"#ef4444", icon:"✗"  },
    "DEFAULT":        { bg:"#f8fafc", color:"#475569", border:"#94a3b8", icon:"·"  },
};

function renderWvsQueue(wvsQueue, gridCounts) {
    cachedWvsQueue = wvsQueue || [];
    const wvsBody = document.getElementById("wvsQueueBody");
    const dashWvs = document.getElementById("dashWvsContainer");
    if (wvsBody) wvsBody.innerHTML = "";
    if (dashWvs) dashWvs.innerHTML = "";

    const pillMap = {
        "READY":"status-ready","EXECUTING":"status-info",
        "JOB FAILED":"status-failed","FAILED":"status-failed","JOB SUCCESSFUL":"status-success"
    };

    (wvsQueue || []).forEach((q, idx) => {
        const statusUp = (q.status || "").toUpperCase();
        const st       = WVS_STATUS_STYLE[statusUp] || WVS_STATUS_STYLE.DEFAULT;
        const pill     = pillMap[statusUp] || "";

        if (wvsBody) wvsBody.innerHTML += `<tr>
            <td>${idx+1}</td>
            <td><code>${q.queue||"—"}</code></td>
            <td>${q.job||"—"}</td>
            <td><span class="status-pill ${pill}">${q.status||"—"}</span></td>
            <td>${q.number||"—"}</td>
            <td title="${q.name||""}">${(q.name||"").length>40?q.name.substring(0,40)+"…":q.name||"—"}</td>
            <td>${q.version||"—"}</td>
            <td>${q.context||"—"}</td>
            <td>${q.user||"—"}</td>
        </tr>`;

        if (dashWvs && idx < 10) {
            const qNum  = (q.number||q.job||"").split(".")[0].substring(0,18);
            const qName = (q.name||"—").length>38 ? q.name.substring(0,38)+"…" : q.name||"—";
            dashWvs.innerHTML += `<div class="wvs-card" style="border-left-color:${st.border};">
                <div class="wvs-card-row1">
                    <span class="wvs-num" title="${q.job}">${qNum}</span>
                    <span class="wvs-status-badge" style="background:${st.bg};color:${st.color};border-color:${st.border};">${st.icon} ${q.status}</span>
                </div>
                <div class="wvs-card-row2"><span class="wvs-name" title="${q.name||""}">${qName}</span></div>
                <div class="wvs-card-row3">
                    <span class="wvs-ctx">${q.context||"—"}</span>
                    <span class="wvs-ver">v${q.version||"—"}</span>
                </div>
            </div>`;
        }
    });

    // KPI — prefer real grid counts from Windchill, fall back to counted rows
    const gc      = gridCounts || {};
    const ready   = gc.ready     || (wvsQueue||[]).filter(q=>(q.status||"").toUpperCase()==="READY").length;
    const exec    = gc.executing || (wvsQueue||[]).filter(q=>(q.status||"").toUpperCase()==="EXECUTING").length;
    const total   = ready + exec;
    const failedA = gc.failed_approx || 0;

    setEl("kpiTotalWvsJobs", total || "—");

    // WVS KPI bar
    const vkpiBar = document.getElementById("wvsKpiBar");
    if (vkpiBar) {
        const ready   = (wvsQueue||[]).filter(q=>(q.status||"").toUpperCase()==="READY").length;
        const exec_   = (wvsQueue||[]).filter(q=>(q.status||"").toUpperCase()==="EXECUTING").length;
        const failed  = (wvsQueue||[]).filter(q=>(q.status||"").toUpperCase().includes("FAIL")).length;
        const succ    = (wvsQueue||[]).filter(q=>(q.status||"").toUpperCase().includes("SUCC")).length;
        vkpiBar.innerHTML = `
            <div class="ops-kpi-chip" style="color:#0ea5e9;border-color:#0ea5e9;">
                <span class="ops-kpi-chip-val">${total}</span>
                <span class="ops-kpi-chip-lbl">Total</span></div>
            <div class="ops-kpi-chip" style="color:#d97706;border-color:#f59e0b;">
                <span class="ops-kpi-chip-val">${ready}</span>
                <span class="ops-kpi-chip-lbl">Ready</span></div>
            <div class="ops-kpi-chip" style="color:#2563eb;border-color:#3b82f6;">
                <span class="ops-kpi-chip-val">${exec_}</span>
                <span class="ops-kpi-chip-lbl">Executing</span></div>
            <div class="ops-kpi-chip" style="color:#dc2626;border-color:#ef4444;">
                <span class="ops-kpi-chip-val">${failed}</span>
                <span class="ops-kpi-chip-lbl">Failed</span></div>
            <div class="ops-kpi-chip" style="color:#16a34a;border-color:#22c55e;">
                <span class="ops-kpi-chip-val">${succ}</span>
                <span class="ops-kpi-chip-lbl">Successful</span></div>`;
    }
    const kpiSub = document.getElementById("kpiWvsSub");
    if (kpiSub) kpiSub.textContent = failedA > 0
        ? `${ready} Ready · ${exec} Executing · ~${failedA} Recent Failed`
        : `${ready} Ready · ${exec} Executing`;
}

// ── Render: Transactions ──────────────────────────────────────────────────────
function renderTransactions(txGridCount) {
    cachedTransactions.sort((a, b) => {
        const ta = new Date((a.time||"").replace(/ (CEST|CET|UTC|EST|PST|BST)$/, ""));
        const tb = new Date((b.time||"").replace(/ (CEST|CET|UTC|EST|PST|BST)$/, ""));
        return tb - ta;
    });

    const txBody   = document.getElementById("transactionsBody");
    const dashFail = document.getElementById("dashFailureContainer");
    if (txBody)   txBody.innerHTML   = "";
    if (dashFail) dashFail.innerHTML = "";

    const rows     = cachedTransactions;
    // Use real Windchill grid count if available, otherwise count CSV rows
    const kpiCount = (txGridCount && txGridCount > 0) ? txGridCount : rows.length;
    setEl("kpiTotalFailures", kpiCount || "—");

    // KPI bar
    // Store total (FIXED) for dynamic KPI reference
    window._wmTxTotal = kpiCount;
    _updateWmTxKpiBar();
    // Render actual table rows
    renderTransactionsRows();
}

// Update WM transaction KPI bar — total FIXED, counts by target DYNAMIC (visible rows)
function _updateWmTxKpiBar() {
    const kpiBar = document.getElementById("failureKpiBar");
    if (!kpiBar) return;
    const kpiCount = window._wmTxTotal || cachedTransactions.length;
    const visRows  = [...document.querySelectorAll("#transactionsBody tr")]
                     .filter(r => r.style.display !== "none");
    const counts   = {};
    visRows.forEach(r => {
        const tgt = (r.cells[2] ? r.cells[2].innerText.trim().toUpperCase() : "UNKNOWN");
        counts[tgt] = (counts[tgt]||0) + 1;
    });
    const COLORS   = {RAPID:"#3b82f6",POTS:"#f59e0b","ESW-SYNCPART":"#8b5cf6",ODC:"#06b6d4",
                      KOLA:"#8b5cf6",GLOPPS:"#06b6d4",BEAT:"#f28c38",DEFAULT:"#6b7280"};
    // Use ops-kpi-chip style (same as OPS tables)
    let html = `<div class="ops-kpi-chip ops-kpi-chip-total" style="color:#ef4444;border-color:#ef4444;">
        <span class="ops-kpi-chip-val">${kpiCount}</span>
        <span class="ops-kpi-chip-lbl">Total (All)</span></div>`;
    html += `<div class="ops-kpi-chip" style="color:#16a34a;border-color:#22c55e;">
        <span class="ops-kpi-chip-val">${visRows.length}</span>
        <span class="ops-kpi-chip-lbl">Filtered</span></div>`;
    Object.entries(counts).sort((a,b)=>b[1]-a[1]).forEach(([tgt,cnt])=>{
        const col = COLORS[tgt] || COLORS.DEFAULT;
        html += `<div class="ops-kpi-chip" style="border-color:${col};color:${col};" title="${tgt}: ${cnt}">
            <span class="ops-kpi-chip-val">${cnt}</span>
            <span class="ops-kpi-chip-lbl">${tgt.length>10?tgt.substring(0,10)+"…":tgt}</span>
        </div>`;
    });
    if (kpiBar) kpiBar.innerHTML = html;
}

function renderTransactionsRows() {
    const txBody   = document.getElementById("transactionsBody");
    const dashFail = document.getElementById("dashFailureContainer");
    const rows     = cachedTransactions;

    if (rows.length === 0) {
        if (txBody)   txBody.innerHTML   = `<tr><td colspan="9" style="text-align:center;color:#9ca3af;padding:20px;">No data — click <strong>Run Now</strong>.</td></tr>`;
        if (dashFail) dashFail.innerHTML = `<div class="wm-empty-msg">Click <strong>Run Now</strong> in the sidebar.</div>`;
        return;
    }

    rows.forEach((t, idx) => {
        const failed  = !!(t.status||"").toUpperCase().match(/FAIL|ERR/);
        const badge   = failed ? "status-failed" : "status-success";
        const notes   = (t.notes   && t.notes   !== "N/A" && t.notes   !== "null") ? t.notes   : "—";
        const obj     = (t.object  && t.object  !== "N/A") ? t.object  : "—";
        const state   = (t.state   && t.state   !== "N/A") ? t.state   : "—";
        const att     = (t.attempts&& t.attempts!== "N/A") ? t.attempts: "—";

        if (txBody) txBody.innerHTML += `<tr class="tx-compact-row">
            <td title="${t.tx_id}"><code class="tx-code">${t.tx_id.length>24?t.tx_id.substring(0,24)+"…":t.tx_id}</code></td>
            <td class="tx-time">${fmtDate(t.time)}</td>
            <td>${t.target||"—"}</td>
            <td>${t.action||"—"}</td>
            <td><span class="status-pill ${badge}">${t.status}</span></td>
            <td class="tx-obj" title="${obj}">${obj.length>28?obj.substring(0,28)+"…":obj}</td>
            <td>${state}</td>
            <td class="tx-att">${att}</td>
            <td class="tx-notes ${notes!=="—"?"tx-notes-alert":""}" title="${notes}">${notes.length>35?notes.substring(0,35)+"…":notes}</td>
        </tr>`;

        if (dashFail && idx < 15) {
            const rawObj = (t.object && t.object !== "N/A") ? t.object : "";
            const row1   = rawObj ? (rawObj.match(/^([A-Z0-9][A-Z0-9._-]{3,})/i)||[,""])[1]||rawObj.substring(0,22) : t.tx_id.substring(0,14);
            dashFail.innerHTML += `<div class="tx-mini-card" style="border-left-color:${failed?"#ef4444":"#22c55e"};">
                <div class="tx-mini-row1">
                    <span class="tx-mini-obj" title="${rawObj||t.tx_id}">${row1.length>16?row1.substring(0,16)+"…":row1}</span>
                    <span class="tx-mini-target">${t.target||"—"}</span>
                    <span class="tx-mini-time">${fmtDate(t.time)}</span>
                </div>
                <div class="tx-mini-row2">
                    <span class="tx-mini-status ${failed?"tx-mini-status-fail":"tx-mini-status-ok"}">${t.status}</span>
                    <span class="tx-mini-notes">${notes.length>45?notes.substring(0,45)+"…":notes||"—"}</span>
                </div>
            </div>`;
        }
    });
}

// Called after renderTransactions to populate table rows
// Split so _updateWmTxKpiBar can reference DOM rows properly
// ── Load from CSV (page load + Refresh Data button) ───────────────────────────
async function loadFromCSV() {
    setBtn("btnRefreshCSV", "⏳ Loading…", true);
    updateLocalStatus("Processing", "Loading from history CSV files…", "processing");
    try {
        const res = await fetch("/api/windchill-monitoring/refresh");
        const r   = await res.json();
        if (r.success && r.data) {
            // Only populate transactions from CSV if we have no live data yet
            // Filter transactions to last 7 days on CSV load (matches live automation window)
            const _7ago = new Date();
            _7ago.setDate(_7ago.getDate() - 7);
            _7ago.setHours(0, 0, 0, 0);
            const txFiltered = (r.data.transactions || []).filter(function(t) {
                const raw = (t.time || "").replace(/ CEST| CET| UTC/g, "").trim();
                if (!raw) return true;
                const d = new Date(raw.replace(" ", "T"));
                return isNaN(d.getTime()) || d >= _7ago;
            });
            if (cachedTransactions.length === 0 && txFiltered.length > 0) {
                cachedTransactions = txFiltered;
            }
            renderTransactions(0);    // CSV load — no grid count
            renderWvsQueue(r.data.wvs_queue || [], null);
            renderWorkerStats(r.data.worker_stats || []);
            updateLocalStatus("Completed", "Dashboard loaded from CSV history.", "completed");
        } else {
            updateLocalStatus("Failed", r.message || "Could not load CSV.", "failed");
        }
    } catch (e) {
        updateLocalStatus("Failed", e.message, "failed");
    } finally {
        setBtn("btnRefreshCSV", "🔄 Refresh Data", false);
    }
}

// ── Run full automation ───────────────────────────────────────────────────────
async function runFullAutomation(silent = false) {
    if (!silent) {
        setBtn("btnRunAutomation", "⏳ Running…", true);
        showSidebarStatus(
            `<div class="filter-status-title">🔄 Running…</div>
             <div class="filter-status-msg">Transactions filter + WVS Queue live scrape…</div>`,
            "filter-status-running");
        updateLocalStatus("Processing", "Running live automation…", "processing");
    }
    try {
        const res = await fetch("/api/windchill-monitoring/run-automation", { method: "POST" });
        const r   = await res.json();

        // Transactions
        if ((r.transactions || []).length > 0) {
            cachedTransactions = [...r.transactions];
        }
        renderTransactions(r.tx_grid_count || 0);

        // Set footer to AUTOMATION RUN time (not page load time)
        const runTs = nowTime();
        setEl("coreFooterTime", runTs);

        // WVS Queue — if automation returned 0 jobs, fall back to history CSV
        const liveWvs = r.wvs_queue || [];
        if (liveWvs.length === 0) {
            // Show warning banner on WVS section
            const banner = document.getElementById("wvsStaleBanner");
            if (banner) {
                banner.textContent = "⚠ WVS Queue could not be collected in last automation run. Showing last saved data from history.";
                banner.style.display = "block";
            }
            // Keep existing cachedWvsQueue if available, or reload from server via Refresh Data
            if (cachedWvsQueue && cachedWvsQueue.length > 0) {
                renderWvsQueue(cachedWvsQueue, null);
            }
            // Also update dashboard tile to reflect 0 live jobs
            const dashKpi = document.getElementById("kpiTotalWvsJobs");
            if (dashKpi) dashKpi.textContent = "?";
        } else {
            // Clear stale banner since we have fresh data
            const banner = document.getElementById("wvsStaleBanner");
            if (banner) banner.style.display = "none";
            renderWvsQueue(liveWvs, r.wvs_grid_counts || null);
        }
        setEl("wvsFooterTime", runTs);
        setEl("wmLogTime", runTs);

        // Worker stats from CSV
        if ((r.worker_stats || []).length > 0) {
            renderWorkerStats(r.worker_stats);
        }

        // Update last-run display
        const lrEl = document.getElementById("filterLastRunTime");
        const lrDEl = document.getElementById("filterLastRun");
        if (lrEl)  lrEl.textContent    = runTs;
        if (lrDEl) lrDEl.style.display = "block";

        checkWvsAlerts(cachedWvsQueue);
        autoRefreshCount++;

        const hasErrors = (r.errors || []).length > 0;
        if (!silent) {
            const gc = r.wvs_grid_counts || {};
            const parts = [];
            if (r.tx_grid_count > 0) parts.push(`${r.tx_grid_count} failures`);
            if (gc.ready !== undefined) parts.push(`${gc.ready} Ready, ${gc.executing} Executing`);
            showSidebarStatus(
                `<div class="filter-status-title">${hasErrors ? "⚠️ Completed with errors" : "✅ Completed"}</div>
                 <div class="filter-status-msg">${parts.join(" · ") || r.message}</div>`,
                hasErrors ? "filter-status-error" : "filter-status-success");
            updateLocalStatus("Completed", r.message, hasErrors ? "warning" : "completed");
            showSection("dashboard");
        }
    } catch (e) {
        if (!silent) {
            showSidebarStatus(`<div class="filter-status-title">❌ Error</div><div class="filter-status-msg">${e.message}</div>`, "filter-status-error");
            updateLocalStatus("Failed", "Automation error: " + e.message, "failed");
        }
    } finally {
        if (!silent) setBtn("btnRunAutomation", "▶ Run Now", false);
    }
}

// ── Launch Edge ───────────────────────────────────────────────────────────────
async function launchEdgeDebug() {
    setBtn("btnLaunchEdge", "⏳…", true);
    try {
        const r = await fetch("/api/windchill-monitoring/launch-edge", { method: "POST" });
        const j = await r.json();
        setBtn("btnLaunchEdge", j.success ? "✅ Edge Running" : "🌐 Launch Edge Debug", false);
        if (!j.success) updateLocalStatus("Failed", j.message, "failed");
        else setTimeout(() => setBtn("btnLaunchEdge", "🌐 Launch Edge Debug", false), 4000);
    } catch (e) {
        setBtn("btnLaunchEdge", "🌐 Launch Edge Debug", false);
        updateLocalStatus("Failed", e.message, "failed");
    }
}

// ── Collect Stats ─────────────────────────────────────────────────────────────
async function collectStats() {
    setBtn("btnCollectStats", "⏳ Collecting…", true);
    updateLocalStatus("Processing", "Reading Job Statistics from Edge popup (up to 60s)…", "processing");
    showSidebarStatus(
        `<div class="filter-status-title">⏳ Collecting…</div>
         <div class="filter-status-msg">Reading data from Edge. Make sure you clicked <strong>Display Summary Statistics</strong> and waited for it to load.</div>`,
        "filter-status-running");
    try {
        const r = await fetch("/api/windchill-monitoring/collect-stats", {
            method: "POST",
            signal: AbortSignal.timeout(75 * 1000)   // 75s client timeout (server is 60s)
        });
        const j = await r.json();
        if (j.success && (j.worker_stats || []).length > 0) {
            renderWorkerStats(j.worker_stats);
            setEl("workerFooterTime", nowTime());
            updateLocalStatus("Completed", j.message, "completed");
            showSidebarStatus(
                `<div class="filter-status-title">✅ Collected</div>
                 <div class="filter-status-msg">${j.message}</div>`,
                "filter-status-success");
        } else {
            updateLocalStatus("Warning", j.message || "No worker data received.", "warning");
            showSidebarStatus(
                `<div class="filter-status-title">⚠️ No Data</div>
                 <div class="filter-status-msg">${j.message || "No worker data found."}</div>`,
                "filter-status-error");
        }
    } catch (e) {
        updateLocalStatus("Failed", "Collect stats error: " + e.message, "failed");
        showSidebarStatus(`<div class="filter-status-title">❌ Error</div><div class="filter-status-msg">${e.message}</div>`, "filter-status-error");
    } finally {
        setBtn("btnCollectStats", "📥 Collect Stats", false);
    }
}

// ── Export ────────────────────────────────────────────────────────────────────
function exportTable(tableId, name) {
    try {
        let csv = "data:text/csv;charset=utf-8,";
        document.getElementById(tableId).querySelectorAll("tr").forEach(r => {
            csv += Array.from(r.querySelectorAll("th,td")).map(c => `"${c.innerText.replace(/"/g,'""')}"`).join(",") + "\r\n";
        });
        const a = document.createElement("a");
        a.href = encodeURI(csv);
        a.download = `windchill_${name}_${new Date().toISOString().slice(0,10)}.csv`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        updateLocalStatus("Completed", "CSV downloaded.", "completed");
    } catch (e) { updateLocalStatus("Failed", "Export error.", "failed"); }
}

// ── Auto-refresh ──────────────────────────────────────────────────────────────
function startAutoRefresh() {
    setInterval(async () => {
        const dot = document.getElementById("wmLogDot");
        const ar  = document.getElementById("autoRefreshStatus");
        if (dot) dot.style.background = "#f59e0b";
        if (ar)  ar.textContent = "Auto-refresh running: " + nowTime();
        console.log("[AutoRefresh] 30-min cycle at " + nowTime());
        await runFullAutomation(true);
        if (dot) dot.style.background = "#22c55e";
        if (ar)  ar.textContent = "Auto-refresh: every 30 min";
        setEl("wmLogTime", nowTime());
    }, AUTO_INTERVAL_MS);

    setInterval(async () => {
        console.log("[WorkerCheck] 60-min CSV reload at " + nowTime());
        try {
            const r = await fetch("/api/windchill-monitoring/refresh");
            const j = await r.json();
            if (j.success && j.data && (j.data.worker_stats||[]).length > 0) {
                renderWorkerStats(j.data.worker_stats);
                setEl("workerFooterTime", nowTime());
            }
        } catch (e) { console.error("[WorkerCheck]", e); }
    }, WORKER_INTERVAL_MS);

    setEl("wmLogTime", nowTime());
    setEl("autoRefreshStatus", "Auto-refresh: every 30 min");
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadFromCSV();
    startAutoRefresh();
});
