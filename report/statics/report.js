/**
 * report.js — RCA Report Generator
 * Collapsible zones, rich-text editor, image uploads, PPT export
 */

// ── State ─────────────────────────────────────────────────────────────────────
let currentIncidentNumber = null;
let currentIncidentData   = {};

// uploaded files per zone: { problem:[], root:[], resolution:[] }
let uploadedFiles = { problem: [], root: [], resolution: [] };

// Collapsed state — all collapsed by default
const rcaCollapsed = { problem: true, root: true, resolution: true, references: true };

// Saved selection for rich text toolbar
let _rtaSavedSel = null;


// ── Colour constants ──────────────────────────────────────────────────────────
const ZONE_COLORS = { problem:"#ef4444", root:"#f59e0b", resolution:"#22c55e" };

function _cap(s){ return s.charAt(0).toUpperCase()+s.slice(1); }


// ══════════════════════════════════════════════════════════════════════════════
// DOCK SWITCHING
// ══════════════════════════════════════════════════════════════════════════════
function showReportSection(sectionId){
    document.querySelectorAll(".dock-section").forEach(el=>el.classList.remove("active-section"));
    document.querySelectorAll(".dock-item").forEach(el=>el.classList.remove("active-dock"));
    document.getElementById(`${sectionId}-section`)?.classList.add("active-section");
    document.querySelector(`.dock-item[onclick="showReportSection('${sectionId}')"]`)?.classList.add("active-dock");
}


// ══════════════════════════════════════════════════════════════════════════════
// COLLAPSIBLE ZONES
// ══════════════════════════════════════════════════════════════════════════════
function toggleRCAZone(zone){
    rcaCollapsed[zone] = !rcaCollapsed[zone];
    _applyZoneCollapse(zone);
    if(!rcaCollapsed[zone])
        setTimeout(()=>document.getElementById(`zone-${zone}`)?.scrollIntoView({behavior:"smooth",block:"nearest"}),150);
}
function _applyZoneCollapse(zone){
    const body  = document.getElementById(`zone-body-${zone}`);
    const chev  = document.getElementById(`zoneChev-${zone}`);
    const sbKeyMap = {root:"Root", references:"References"};
    const sbKey = sbKeyMap[zone] || _cap(zone);
    const sbChev= document.getElementById(`sbChev${sbKey}`);
    const col   = rcaCollapsed[zone];
    if(body)   body.style.display = col?"none":"block";
    if(chev)   chev.textContent   = col?"▶":"▼";
    if(sbChev) sbChev.textContent = col?"›":"⌄";
    document.getElementById(`zone-${zone}`)?.classList.toggle("collapsed",col);
}
function expandAllZones(){ Object.keys(rcaCollapsed).forEach(z=>{rcaCollapsed[z]=false;_applyZoneCollapse(z);}); }


// ══════════════════════════════════════════════════════════════════════════════
// LOAD PREVIEW
// ══════════════════════════════════════════════════════════════════════════════
function loadPreview(){
    const input = document.getElementById("incident_number");
    const inc   = (input?.value||"").trim();
    if(!inc || inc.toLowerCase()==="number"){ alert("Please enter a valid Incident Number."); return; }

    updateProcessingStatus("Loading","Fetching incident data...","processing");
    document.getElementById("lastAction").innerText = "Loading…";

    fetch("/get-rca-data",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({incident_number:inc})
    })
    .then(r=>{ if(!r.ok) throw new Error(`Server error: ${r.status}`); return r.json(); })
    .then(data=>{
        if(data.error) throw new Error(data.error);
        currentIncidentNumber = inc;
        currentIncidentData   = data.incident_data || {};
        // Store references list for the panel renderer
        currentIncidentData._refs = data.references_list || [];

        const pc = document.getElementById("previewContainer");
        if(pc){ pc.innerHTML = data.preview_html||"<p>No preview available</p>"; _reflowPreviewImages(pc); }

        // Pre-fill rich text editors
        _setEditorText("problem",    data.problem_statement || "");
        _setEditorText("root",       data.root_cause        || "");
        _setEditorText("resolution", data.resolution        || "");

        // Pre-fill References (auto-extracted from notes)
        if(data.references_text){ _setEditorText("references", data.references_text); }
        // Render the clickable references HTML panel — always from _refs so
        // subsequent mutations via updateRefEnvironment are visible immediately
        _renderRefsPanel(currentIncidentData._refs);

        // Update sidebar chips
        _updateZoneTextStatus("problem");
        _updateZoneTextStatus("root");
        _updateZoneTextStatus("resolution");
        _updateRefsChip(data.references_list || []);

        document.getElementById("activeIncident").innerText = inc;
        document.getElementById("lastAction").innerText     = "Preview loaded";
        document.getElementById("downloadStatus").innerText = "Ready to download";
        document.getElementById("downloadMessage").innerText = "Select format to download:";
        updateProcessingStatus("Ready","Preview loaded","completed");

        const rc = document.getElementById("reportsCount");
        if(rc) rc.innerText = parseInt(rc.innerText||0)+1;

        showReportSection("rca");
    })
    .catch(err=>{
        console.error(err);
        alert(`Failed to load preview: ${err.message}`);
        document.getElementById("lastAction").innerText = "Error loading incident";
        updateProcessingStatus("Error",err.message,"failed");
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// UPDATE PREVIEW
// ══════════════════════════════════════════════════════════════════════════════
function triggerUpdatePreview(){
    if(!currentIncidentNumber){ alert("Load an incident first."); return; }
    document.getElementById("lastAction").innerText = "Updating preview…";

    const fd = new FormData();
    fd.append("incident_number", currentIncidentNumber);
    fd.append("problem",    _getEditorText("problem"));
    fd.append("analysis",   _getEditorText("root"));
    fd.append("resolution", _getEditorText("resolution"));
    fd.append("references", _getEditorText("references"));

    // Send live references list (with user-edited environments) so the
    // Update Preview re-render reflects badge changes.
    // Only send when non-empty — empty list would suppress server-side extraction.
    const liveRefs = (window.currentIncidentData && window.currentIncidentData._refs) || [];
    if(liveRefs.length > 0) fd.append("references_json", JSON.stringify(liveRefs));

    uploadedFiles.problem.forEach(f    => fd.append("problem_images",    f));
    uploadedFiles.root.forEach(f       => fd.append("root_images",       f));
    uploadedFiles.resolution.forEach(f => fd.append("resolution_images", f));

    fetch("/update-preview",{method:"POST",body:fd})
    .then(r=>{ if(!r.ok) throw new Error("Update failed"); return r.text(); })
    .then(html=>{
        const pc=document.getElementById("previewContainer");
        if(pc){ pc.innerHTML=html; _reflowPreviewImages(pc); pc.scrollIntoView({behavior:"smooth",block:"start"}); }
        document.getElementById("lastAction").innerText = "Preview updated";
        // Re-render the sidebar refs panel so badge colours stay current
        // (the panel DOM is untouched by the preview update, but re-rendering
        // keeps it in sync with currentIncidentData._refs after any mutations)
        _renderRefsPanel(currentIncidentData._refs || []);
    })
    .catch(err=>{ alert(`Update failed: ${err.message}`); });
}


// ══════════════════════════════════════════════════════════════════════════════
// DOWNLOAD / EXPORT
// ══════════════════════════════════════════════════════════════════════════════
function downloadReport(format){
    if(!currentIncidentNumber){ alert("Load an incident first."); return; }
    document.getElementById("lastAction").innerText = `Generating ${format.toUpperCase()}…`;

    if(format === "ppt"){
        _exportPPT(); return;
    }

    const fd = new FormData();
    fd.append("incident_number",   currentIncidentNumber);
    fd.append("problem_statement", _getEditorText("problem"));
    fd.append("root_cause",        _getEditorText("root"));
    fd.append("resolution",        _getEditorText("resolution"));

    // Send the live (possibly user-edited) references list so env changes are reflected
    const liveRefs = (window.currentIncidentData && window.currentIncidentData._refs) || [];
    fd.append("references_json", JSON.stringify(liveRefs));

    // Images in report option
    const imgMode = document.querySelector("input[name='imagesInDoc']:checked")?.value || "all";
    fd.append("images_in_doc", imgMode);
    if(imgMode !== "none"){
        uploadedFiles.problem.forEach(f    => fd.append("problem_images",    f));
        uploadedFiles.root.forEach(f       => fd.append("root_images",       f));
        uploadedFiles.resolution.forEach(f => fd.append("resolution_images", f));
    }

    const url = format==="zip" ? "/download/zip" : `/download/${format}`;
    fetch(url,{method:"POST",body:fd})
    .then(r=>{ if(!r.ok) throw new Error("Download failed."); return r.blob(); })
    .then(blob=>{
        const u=URL.createObjectURL(blob);
        const a=document.createElement("a"); a.href=u;
        if(format==="word")      a.download=`${currentIncidentNumber}.docx`;
        else if(format==="pdf")  a.download=`${currentIncidentNumber}.pdf`;
        else                     a.download=`${currentIncidentNumber}.zip`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(u);
        document.getElementById("lastAction").innerText = `${format.toUpperCase()} Downloaded`;
        document.getElementById("downloadStatus").innerText = `${format.toUpperCase()} Generated`;
    })
    .catch(err=>{ alert(`Download failed: ${err.message}`); document.getElementById("lastAction").innerText="Download failed"; });
}

async function _exportPPT(){
    const fd = new FormData();
    fd.append("incident_number", currentIncidentNumber);
    fd.append("incident_data",   JSON.stringify(currentIncidentData));
    fd.append("problem",    _getEditorText("problem"));
    fd.append("root_cause", _getEditorText("root"));
    fd.append("resolution", _getEditorText("resolution"));

    // Send the live (possibly user-edited) references list
    const liveRefs = (window.currentIncidentData && window.currentIncidentData._refs) || [];
    fd.append("references_json", JSON.stringify(liveRefs));
    uploadedFiles.problem.forEach(f    => fd.append("problem_images",    f));
    uploadedFiles.root.forEach(f       => fd.append("root_images",       f));
    uploadedFiles.resolution.forEach(f => fd.append("resolution_images", f));

    updateProcessingStatus("Building","Creating PPT…","processing");
    try{
        const res  = await fetch("/download/ppt",{method:"POST",body:fd});
        const data = await res.json();
        if(data.error){ alert(data.error); updateProcessingStatus("Error",data.error,"failed"); return; }
        const a=document.createElement("a");
        a.href=`/report/download-pptx/${data.filename}`;
        a.download=data.filename;
        document.body.appendChild(a); a.click();
        setTimeout(()=>document.body.removeChild(a),1000);
        document.getElementById("lastAction").innerText = "PPT Downloaded";
        updateProcessingStatus("Done","PPT ready","completed");
    }catch(e){
        alert("PPT export failed: "+e.message);
        updateProcessingStatus("Error",e.message,"failed");
    }
}


// ══════════════════════════════════════════════════════════════════════════════
// IMAGE UPLOADS
// ══════════════════════════════════════════════════════════════════════════════
function handleImageUpload(zone, input){
    Array.from(input.files).forEach(f=>uploadedFiles[zone].push(f));
    _renderFileChips(zone);
    _updateZoneImgCount(zone);
    input.value="";
}
function _renderFileChips(zone){
    const c=document.getElementById(`${zone}_preview_files`); if(!c) return;
    c.innerHTML="";
    uploadedFiles[zone].forEach((f,i)=>{
        const chip=document.createElement("div"); chip.className="file-chip";
        chip.innerHTML=`${f.name} <span class="remove-file" onclick="removeFile('${zone}',${i})">×</span>`;
        c.appendChild(chip);
    });
}
function removeFile(zone,idx){ uploadedFiles[zone].splice(idx,1); _renderFileChips(zone); _updateZoneImgCount(zone); }
function _updateZoneImgCount(zone){
    const n=uploadedFiles[zone].length;
    const el=document.getElementById(`zoneImgCount-${zone}`);
    if(el) el.textContent=`${n} image${n!==1?"s":""}`;
    const sbKey=zone==="root"?"Root":_cap(zone);
    const chip=document.getElementById(`sbChip${sbKey}`);
    if(chip){ chip.textContent=String(n); chip.classList.toggle("has-content",n>0); }
}


// ══════════════════════════════════════════════════════════════════════════════
// RICH TEXT EDITOR
// ══════════════════════════════════════════════════════════════════════════════
function rtaSaveSelection(zone){
    const sel=window.getSelection();
    if(sel&&sel.rangeCount) _rtaSavedSel={zone,range:sel.getRangeAt(0).cloneRange()};
}
function rtaRestoreSelection(){
    if(!_rtaSavedSel) return false;
    const sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(_rtaSavedSel.range); return true;
}

function applyRTACmd(zone,cmd,value){
    const editor=document.getElementById(`rca-editor-${zone}`); if(!editor) return;
    rtaRestoreSelection(); editor.focus();
    if(cmd==="allCaps"){
        const sel=window.getSelection();
        if(sel&&sel.rangeCount&&!sel.getRangeAt(0).collapsed){
            const range=sel.getRangeAt(0); const text=range.toString(); if(!text) return;
            const upper=text.toUpperCase(), lower=text.toLowerCase();
            const title=text.split(/\b/).map(w=>w.length>0?w[0].toUpperCase()+w.slice(1).toLowerCase():w).join("");
            const sentence=text.length>0?text[0].toUpperCase()+text.slice(1).toLowerCase():text;
            let next;
            if(text===upper&&text!==lower)                   next=title;
            else if(text===title&&text!==lower&&text!==upper) next=sentence;
            else if(text===sentence&&text!==upper)            next=lower;
            else                                              next=upper;
            range.deleteContents(); range.insertNode(document.createTextNode(next));
            range.collapse(false); sel.removeAllRanges(); sel.addRange(range);
        }
    } else if(cmd==="reset"){
        document.execCommand("removeFormat",false,null);
    } else if(cmd==="fontSize"){
        document.execCommand("fontSize",false,"7");
        editor.querySelectorAll('font[size="7"]').forEach(el=>{el.removeAttribute("size");el.style.fontSize=value+"px";});
    } else if(cmd==="insertAlphaList"){
        document.execCommand("insertOrderedList",false,null);
        editor.querySelectorAll("ol").forEach(ol=>{ol.style.listStyleType=ol.style.listStyleType==="lower-alpha"?"decimal":"lower-alpha";});
    } else {
        document.execCommand(cmd,false,value||null);
    }
    onZoneTextChange(zone);
}

// Preset colours for the colour grid popup
const PRESET_COLORS=[
    "#000000","#FFFFFF","#FF0000","#00FF00","#0000FF","#FFFF00","#FF6600","#9900CC",
    "#1E293B","#334155","#64748B","#94A3B8","#CBD5E1","#E2E8F0","#F1F5F9","#F8FAFC",
    "#DC2626","#EA580C","#D97706","#CA8A04","#65A30D","#16A34A","#059669","#0891B2",
    "#2563EB","#4F46E5","#7C3AED","#9333EA","#DB2777","#E11D48","#F87171","#FCA5A5",
    "#FED7AA","#FEF08A","#BBF7D0","#A7F3D0","#BAE6FD","#BFDBFE","#DDD6FE","#FBCFE8",
];
function _toggleColorPopup(btn,zone,cmdType){
    document.querySelectorAll(".color-grid-popup").forEach(p=>p.remove());
    const popup=document.createElement("div"); popup.className="color-grid-popup";
    const grid=document.createElement("div"); grid.className="color-grid";
    PRESET_COLORS.forEach(hex=>{
        const sw=document.createElement("div"); sw.className="color-swatch"; sw.style.background=hex; sw.title=hex;
        sw.addEventListener("mousedown",e=>{e.preventDefault();e.stopPropagation();rtaRestoreSelection();applyRTACmd(zone,cmdType,hex);popup.remove();});
        grid.appendChild(sw);
    });
    popup.appendChild(grid);
    const moreRow=document.createElement("div"); moreRow.className="color-more-row";
    const moreLabel=document.createElement("span"); moreLabel.textContent="More colors…"; moreLabel.className="color-more-lbl";
    const inp=document.createElement("input"); inp.type="color"; inp.className="color-more-input";
    inp.addEventListener("input",()=>{rtaRestoreSelection();applyRTACmd(zone,cmdType,inp.value);});
    inp.addEventListener("change",()=>popup.remove());
    moreRow.appendChild(moreLabel); moreRow.appendChild(inp); popup.appendChild(moreRow);
    popup.style.cssText=`position:fixed;z-index:99999;`;
    document.body.appendChild(popup);
    const rect=btn.getBoundingClientRect();
    popup.style.top=(rect.bottom+4)+"px"; popup.style.left=rect.left+"px";
    setTimeout(()=>{ document.addEventListener("mousedown",function h(e){if(!popup.contains(e.target)){popup.remove();document.removeEventListener("mousedown",h);}});},10);
}

// Auto-correct on spacebar
const COMMON_CORRECTIONS={
    "teh":"the","taht":"that","recieve":"receive","seperate":"separate",
    "occured":"occurred","definately":"definitely","accomodate":"accommodate",
    "wiht":"with","hte":"the","adn":"and","incidnet":"incident","porblem":"problem",
    "reslution":"resolution","roote":"route","cuase":"cause","erorr":"error",
};
function _autoCorrect(editor){
    const sel=window.getSelection(); if(!sel||!sel.rangeCount) return;
    const range=sel.getRangeAt(0); if(!range.collapsed) return;
    const node=range.startContainer; if(node.nodeType!==Node.TEXT_NODE) return;
    const text=node.textContent, pos=range.startOffset;
    const before=text.substring(0,pos); const match=before.match(/(\b\w+)\s$/);
    if(!match) return;
    const word=match[1], lower=word.toLowerCase();
    if(COMMON_CORRECTIONS[lower]){
        const corrected=word[0]===word[0].toUpperCase()?COMMON_CORRECTIONS[lower][0].toUpperCase()+COMMON_CORRECTIONS[lower].slice(1):COMMON_CORRECTIONS[lower];
        const start=pos-word.length-1;
        node.textContent=text.substring(0,start)+corrected+" "+text.substring(pos);
        const nr=document.createRange(); nr.setStart(node,start+corrected.length+1); nr.collapse(true);
        sel.removeAllRanges(); sel.addRange(nr);
    }
}
function onRTAKeydown(zone,e){ if(e.key===" ") setTimeout(()=>_autoCorrect(document.getElementById(`rca-editor-${zone}`)),0); onZoneTextChange(zone); }

function onZoneTextChange(zone){ _updateZoneTextStatus(zone); }
function _updateZoneTextStatus(zone){
    const el=document.getElementById("rca-editor-"+zone);
    const len=(el?.innerText||"").trim().length;
    // Update zone header char count
    const s=document.getElementById("zoneTextStatus-"+zone);
    if(s){s.textContent=len>0?"✎ "+len+" chars":"";s.className="rca-text-status"+(len>0?" has-text":"");}
    // For references zone: keep sidebar chip showing ref count, update zoneImgCount with char info
    if(zone==="references"){
        const origRefs=(window.currentIncidentData&&window.currentIncidentData._refs)||[];
        const n=origRefs.length;
        const chip=document.getElementById("sbChipReferences");
        if(chip){ chip.textContent=String(n>0?n:(len>0?len:0)); chip.classList.toggle("has-content",n>0||len>0); }
        const cnt=document.getElementById("zoneImgCount-references");
        if(cnt) cnt.textContent=n>0?n+" reference"+(n!==1?"s":""):(len>0?len+" chars":"0 references");
    }
}
function insertRCAPlaceholder(zone,ph){
    const el=document.getElementById(`rca-editor-${zone}`); if(!el) return; el.focus();
    const sel=window.getSelection();
    if(sel&&sel.rangeCount){const r=sel.getRangeAt(0);r.deleteContents();r.insertNode(document.createTextNode(ph));r.collapse(false);sel.removeAllRanges();sel.addRange(r);}
    else el.innerHTML+=ph;
    onZoneTextChange(zone);
}
function clearZoneText(zone){ const el=document.getElementById(`rca-editor-${zone}`); if(el) el.innerHTML=""; onZoneTextChange(zone); }
function _setEditorText(zone,text){
    const el=document.getElementById(`rca-editor-${zone}`); if(!el) return;
    el.innerHTML=text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/\n/g,"<br>");
    onZoneTextChange(zone);
}
function _getEditorText(zone){ return (document.getElementById(`rca-editor-${zone}`)?.innerText||"").trim(); }


// ══════════════════════════════════════════════════════════════════════════════
// PREVIEW IMAGE REFLOW — force multiple images side-by-side
// ══════════════════════════════════════════════════════════════════════════════
function _reflowPreviewImages(container){
    if(!container) return;
    container.querySelectorAll("td, th").forEach(cell=>{
        const imgs=cell.querySelectorAll("img"); if(imgs.length<=1) return;
        const wrap=document.createElement("div");
        wrap.style.cssText="display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start;margin-top:8px;";
        imgs.forEach(img=>{img.style.cssText="max-width:320px;max-height:200px;width:auto;height:auto;border-radius:4px;border:1px solid #e2e8f0;";wrap.appendChild(img);});
        cell.appendChild(wrap);
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// CLEAR WORKSPACE
// ══════════════════════════════════════════════════════════════════════════════
function clearPreview(){
    currentIncidentNumber=null; currentIncidentData={};
    uploadedFiles={problem:[],root:[],resolution:[]};
    document.getElementById("incident_number").value="";
    ["problem","root","resolution","references"].forEach(z=>{
        const el=document.getElementById(`rca-editor-${z}`); if(el) el.innerHTML="";
        if(z!=="references"){ _renderFileChips(z); _updateZoneImgCount(z); }
        _updateZoneTextStatus(z);
    });
    _renderRefsPanel([]);
    const sbRef=document.getElementById("sbChipReferences"); if(sbRef){ sbRef.textContent="0"; sbRef.classList.remove("has-content"); }
    const pc=document.getElementById("previewContainer"); if(pc) pc.innerText="Preview will appear here";
    document.getElementById("activeIncident").innerText  = "-";
    document.getElementById("lastAction").innerText      = "Waiting for input";
    document.getElementById("downloadStatus").innerText  = "Not generated";
    document.getElementById("downloadMessage").innerText = "Load an incident to enable downloads.";
    showReportSection("rca");
}


// ══════════════════════════════════════════════════════════════════════════════
// PROGRESS BAR
// ══════════════════════════════════════════════════════════════════════════════
function updateProcessingStatus(message,detail,state){
    const status=document.getElementById("statusMessage"); if(status) status.innerText=message;
    const text=document.getElementById("progressText");   if(text) text.innerText=detail||"";
    const fill=document.getElementById("progressFill");
    const wrapper=document.getElementById("progressWrapper");
    if(!fill||!wrapper) return;
    fill.classList.remove("ops-bar-processing","ops-bar-completed","ops-bar-failed");
    if(state==="processing"){ wrapper.classList.remove("hidden"); fill.style.width="70%"; fill.classList.add("ops-bar-processing");
    } else if(state==="completed"){ wrapper.classList.remove("hidden"); fill.style.width="100%"; fill.classList.add("ops-bar-completed"); setTimeout(()=>{ wrapper.classList.add("hidden"); fill.style.width="0%"; fill.classList.remove("ops-bar-completed"); },2000);
    } else { wrapper.classList.remove("hidden"); fill.style.width="100%"; fill.classList.add("ops-bar-failed"); setTimeout(()=>{ wrapper.classList.add("hidden"); fill.style.width="0%"; fill.classList.remove("ops-bar-failed"); },3000); }
}


// ══════════════════════════════════════════════════════════════════════════════
// HELP MODAL
// ══════════════════════════════════════════════════════════════════════════════
function loadModuleHelpData(){
    fetch("/api/help/report").then(r=>r.json()).then(data=>{
        const t=document.getElementById("helpModuleTitle"); if(t) t.textContent="💡 "+(data.module_title||"Help");
        const idx=document.getElementById("helpModalIndexPane"), con=document.getElementById("helpModalContentPane");
        if(!idx||!con) return;
        idx.innerHTML=""; con.innerHTML="";
        const topics=data.topics||[];
        if(!topics.length){con.innerHTML="<p>No help topics.</p>";return;}
        topics.forEach((topic,i)=>{
            const btn=document.createElement("button"); btn.className="help-topic-btn"+(i===0?" active-help-topic":"");
            btn.textContent=topic.title;
            btn.onclick=()=>{document.querySelectorAll(".help-topic-btn").forEach(b=>b.classList.remove("active-help-topic"));btn.classList.add("active-help-topic");con.innerHTML=topic.content;};
            idx.appendChild(btn);
        });
        con.innerHTML=topics[0].content;
    }).catch(()=>{const p=document.getElementById("helpModalContentPane");if(p)p.innerHTML="<p>Help could not be loaded.</p>";});
}


// ══════════════════════════════════════════════════════════════════════════════
// REFERENCES — render clickable links panel with editable environment dropdown
// ══════════════════════════════════════════════════════════════════════════════
const ENV_OPTIONS = ["", "PROD", "QA", "TEST", "UAT", "DEV", "STAGE"];
const ENV_COLORS  = {PROD:"#16a34a",QA:"#d97706",TEST:"#0891b2",UAT:"#7c3aed",DEV:"#64748b",STAGE:"#64748b"};

function _envBadgeColor(env){ return ENV_COLORS[env] || "#64748b"; }

function updateRefEnvironment(idx, value){
    // Mutate the live references list so every subsequent download picks it up
    const refs = (window.currentIncidentData && window.currentIncidentData._refs) || [];
    if(refs[idx]) refs[idx].environment = value || null;

    // Update ONLY the badge colour of this select in-place — no full re-render.
    // Re-rendering destroys the <select> DOM node mid-interaction, which
    // causes the dropdown to close and never re-open after the first pick.
    const sel = document.querySelector(`select[data-ref-idx="${idx}"]`);
    if(sel){
        const color = value ? _envBadgeColor(value) : "#94a3b8";
        sel.style.background = color;
    }
}

function _renderRefsPanel(refsList){
    const container=document.getElementById("refsRendered"); if(!container) return;
    if(!refsList||!refsList.length){ container.innerHTML=""; return; }

    const rows=refsList.map((r,i)=>{
        const color=r.type==="azure_user_story"?"#2563EB":"#9333EA";
        const icon =r.type==="azure_user_story"?"🔵":"🟣";
        const env  =r.environment||"";
        const badgeColor=env?_envBadgeColor(env):"#94a3b8";

        // Inline env dropdown — styled to look like a badge
        const opts=ENV_OPTIONS.map(o=>
            `<option value="${o}"${o===env?" selected":""}>${o||"— none —"}</option>`
        ).join("");
        const envSelect=`<select
            data-ref-idx="${i}"
            onchange="updateRefEnvironment(${i},this.value)"
            style="margin-left:6px;font-size:10px;font-weight:700;padding:1px 5px;
                   border-radius:10px;border:none;cursor:pointer;
                   background:${badgeColor};color:white;
                   appearance:none;-webkit-appearance:none;outline:none;"
            title="Edit environment">${opts}</select>`;

        const ctx=r.context?`<div style="font-size:11px;color:#64748b;margin-top:3px;">${r.context}</div>`:"";
        return `<tr>
          <td style="padding:7px 10px;border:1px solid #e2e8f0;width:170px;vertical-align:top;">
            <span style="font-size:11px;font-weight:700;color:${color};">${icon} ${r.label}</span>${envSelect}
          </td>
          <td style="padding:7px 10px;border:1px solid #e2e8f0;vertical-align:top;">
            <a href="${r.url}" target="_blank" style="color:${color};word-break:break-all;font-size:12px;">${r.url}</a>${ctx}
          </td></tr>`;
    }).join("");

    container.innerHTML=`<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
      <thead><tr style="background:#f1f5f9;">
        <th style="padding:5px 10px;text-align:left;border:1px solid #e2e8f0;font-size:11px;">Reference</th>
        <th style="padding:5px 10px;text-align:left;border:1px solid #e2e8f0;font-size:11px;">Link &amp; Context</th>
      </tr></thead><tbody>${rows}</tbody></table>`;
}

function _updateRefsChip(refsList){
    const n=(refsList||[]).length;
    const chip=document.getElementById("sbChipReferences");
    if(chip){ chip.textContent=String(n); chip.classList.toggle("has-content",n>0); }
    const cnt=document.getElementById("zoneImgCount-references");
    if(cnt) cnt.textContent=`${n} reference${n!==1?"s":""}`;
}


// ══════════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded",()=>{
    showReportSection("rca");
    Object.keys(rcaCollapsed).forEach(_applyZoneCollapse);
});
