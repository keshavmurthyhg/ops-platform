/* ============================================================
   CONVERTER.JS
============================================================ */

// ── State ────────────────────────────────────────────────────
let generatedDocxName   = null;
let generatedPdfName    = null;
let generatedPptxName   = null;
let pptConverted        = false;
let currentIncident     = null;
let currentFilename     = null;
let currentIncidentData = {};

let allSlideImages  = [];
let selectedSlides  = new Set();

const rcaSlides    = {};
const rcaZones     = { problem: new Set(), rootcause: new Set(), resolution: new Set() };
const rcaSelected  = new Set();
let   rcaDragging  = null;
const rcaCollapsed = { problem: true, rootcause: true, resolution: true };

// Zone colour map for thumbnail borders
const ZONE_COLORS = { problem:"#ef4444", rootcause:"#f59e0b", resolution:"#22c55e" };

// Lightbox
let lbImages  = [];
let lbCurrent = 0;
let lbScale   = 1.0;
let lbOpen_   = false;

// Slide preview collapsed
let slidePreviewCollapsed = false;


/* ============================================================
   DOCK
============================================================ */
function showConverterSection(name) {
    document.querySelectorAll(".dock-section").forEach(s=>s.classList.remove("active-section"));
    document.querySelectorAll(".dock-item").forEach(i=>i.classList.remove("active-dock"));
    document.getElementById(`${name}-section`)?.classList.add("active-section");
    document.querySelector(`.dock-item[onclick="showConverterSection('${name}')"]`)?.classList.add("active-dock");
}


/* ============================================================
   COLLAPSIBLE ZONES
============================================================ */
function toggleRCAZone(zone) {
    rcaCollapsed[zone] = !rcaCollapsed[zone];
    _applyZoneCollapse(zone);
    if (!rcaCollapsed[zone])
        setTimeout(()=>document.getElementById(`zone-${zone}`)?.scrollIntoView({behavior:"smooth",block:"nearest"}),150);
}
function _applyZoneCollapse(zone) {
    const body  = document.getElementById(`zone-body-${zone}`);
    const chev  = document.getElementById(`zoneChev-${zone}`);
    const sbChev= document.getElementById(`sbChev${_cap(zone)}`);
    const col   = rcaCollapsed[zone];
    if (body)   body.style.display = col?"none":"block";
    if (chev)   chev.textContent   = col?"▶":"▼";
    if (sbChev) sbChev.textContent = col?"›":"⌄";
    document.getElementById(`zone-${zone}`)?.classList.toggle("collapsed",col);
}
function expandAllZones()   { Object.keys(rcaCollapsed).forEach(z=>{rcaCollapsed[z]=false;_applyZoneCollapse(z);}); }
function collapseAllZones() { Object.keys(rcaCollapsed).forEach(z=>{rcaCollapsed[z]=true; _applyZoneCollapse(z);}); }
function _cap(s) { return s.charAt(0).toUpperCase()+s.slice(1); }


/* ============================================================
   SLIDE PREVIEW COLLAPSE
============================================================ */
function toggleSlidePreviewCollapse() {
    slidePreviewCollapsed = !slidePreviewCollapsed;
    const grid = document.getElementById("slidePreviewContainer");
    const acts = document.getElementById("slideGridActions");
    const btn  = document.getElementById("slidePreviewToggleBtn");
    if (grid) grid.style.display = slidePreviewCollapsed ? "none" : "";
    if (acts) acts.style.display = slidePreviewCollapsed ? "none" : (allSlideImages.length?"flex":"none");
    if (btn)  btn.textContent    = slidePreviewCollapsed ? "▶ Expand" : "▼ Collapse";
}


/* ============================================================
   OPTIONS
============================================================ */
function syncFormatFromOptions(v){ document.querySelectorAll("input[name='downloadFormat']").forEach(r=>r.checked=(r.value===v)); }
function getSkipTitleSlides(){ return document.getElementById("optSkipTitleSlides")?.checked??true; }
function getSkipDividers(){    return document.getElementById("optSkipDividers")?.checked??true; }
function getSelectedFormat(){  return document.getElementById("optFormat")?.value||document.querySelector("input[name='downloadFormat']:checked")?.value||"word"; }
function appendOptions(fd){
    fd.append("skip_title_slides", getSkipTitleSlides()?"true":"false");
    fd.append("skip_dividers",     getSkipDividers()?"true":"false");
    fd.append("dpi", document.getElementById("optDpi")?.value||"200");
}

function getImagesInDoc(){
    const r=document.querySelector("input[name='imagesInDoc']:checked");
    return r?r.value:"all";
}

// Called when Images in Report radio changes
function onImagesInDocChange(value){
    console.log("Images in doc mode:", value);
    // Visual feedback in status
    const map={"all":"All slides","assigned":"Unassigned slides only","none":"RCA sections only"};
    const el=document.getElementById("lastAction");
    if(el) el.innerText=`Images mode: ${map[value]||value}`;
}

// Apply Filters button — applies option changes WITHOUT resetting RCA state
// Re-runs slide conversion only (preserves RCA text + assignments)
async function applyOptions(){
    const fi=document.getElementById("pptUpload");
    if(!fi?.files?.length){
        const el=document.getElementById("lastAction");
        if(el) el.innerText="Options saved — upload a PPT to apply";
        return;
    }
    // Only re-render slides (no full preview reset, no RCA wipe)
    const fd=new FormData();
    fd.append("ppt_file", fi.files[0]);
    appendOptions(fd);
    showProgress("Applying options — re-rendering slides...");
    try{
        updateProgress(60,"Extracting slide images...");
        const res=await fetch("/converter/convert",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){failProgress(data.error);return;}
        // Refresh only the slide grid + tray — preserve RCA assignments
        _refreshSlidesOnly(data.slide_images);
        completeProgress("Options applied — slides updated");
        const el=document.getElementById("lastAction");
        if(el) el.innerText="Options applied";
    }catch(e){
        console.error(e); failProgress("Failed to apply options");
    }
}

// Refresh slides grid + RCA tray WITHOUT resetting RCA zone assignments or text
function _refreshSlidesOnly(images){
    if(!images?.length) return;
    // Update allSlideImages list
    allSlideImages=[];
    images.forEach((img,idx)=>{
        const src=`/converter/slide-preview/${img.filename}`;
        allSlideImages.push({filename:img.filename,src,label:`Slide ${idx+1}`,idx});
        rcaSlides[img.filename]={src,label:`Slide ${idx+1}`,idx};
    });
    lbImages=[...allSlideImages];
    _renderSlideGrid();
    document.getElementById("slideGridActions").style.display="flex";
    // Refresh tray thumbs (new filenames may differ after re-render)
    const tray=document.getElementById("rcaSlideTray");
    if(tray){
        tray.innerHTML="";
        allSlideImages.forEach(s=>tray.appendChild(_makeTrayThumb(s.filename,s.src,s.label)));
    }
    _refreshAllZoneIndicators();
    updateRCASidebar();
}

// ↻ Update Preview — refresh incident preview with current RCA text + assigned slide images
// Mirrors the report module's Update Preview behaviour exactly
async function updateConverterPreview(){
    if(!currentIncident){
        alert("Preview a PPT file first to load incident data.");
        return;
    }
    const el=document.getElementById("lastAction");
    if(el) el.innerText="Updating preview...";

    const fd=new FormData();
    fd.append("incident_number", currentIncident);
    fd.append("problem",    _getRCAText("problem"));
    fd.append("analysis",   _getRCAText("rootcause"));
    fd.append("resolution", _getRCAText("resolution"));

    // Fetch each assigned image as a blob and attach to the right field
    // Map: zone → form field name expected by update-preview route
    const zoneFieldMap={
        problem:    "problem_images",
        rootcause:  "root_images",
        resolution: "resolution_images",
    };

    try{
        // Fetch all assigned images as blobs in parallel
        const fetchTasks=[];
        for(const [zone, field] of Object.entries(zoneFieldMap)){
            for(const fn of rcaZones[zone]){
                const src=rcaSlides[fn]?.src||`/converter/slide-preview/${fn}`;
                fetchTasks.push(
                    fetch(src)
                        .then(r=>r.blob())
                        .then(blob=>({field, fn, blob}))
                        .catch(()=>null)
                );
            }
        }
        const results=await Promise.all(fetchTasks);
        for(const r of results){
            if(r) fd.append(r.field, new File([r.blob], r.fn, {type:"image/png"}));
        }

        const res=await fetch("/converter/update-preview",{method:"POST",body:fd});
        if(!res.ok) throw new Error(await res.text());
        const html=await res.text();
        const pc=document.getElementById("previewContainer");
        if(pc){
            pc.innerHTML=html;
            // Reflow any stacked images into horizontal rows
            _reflowPreviewImages(pc);
            // Scroll to preview so user can see it
            pc.scrollIntoView({behavior:"smooth",block:"start"});
        }
        if(el) el.innerText="Preview updated";
        completeProgress("Preview updated with RCA images");
    }catch(e){
        console.error(e);
        if(el) el.innerText="Preview update failed";
        failProgress("Preview update failed");
    }
}


/* ============================================================
   PROGRESS
============================================================ */
function showProgress(msg)   { _prog("Processing",msg,"20%"); document.getElementById("progressWrapper")?.classList.remove("hidden"); }
function updateProgress(p,m) { const f=document.getElementById("progressFill"); if(f) f.style.width=p+"%"; const t=document.getElementById("progressText"); if(t) t.innerText=m; }
function completeProgress(m) { _prog("Completed",m,"100%"); }
function failProgress(m)     { _prog("Failed",m,"100%"); }
function resetProcessingStatus(){ _prog("Ready","Waiting","0%"); document.getElementById("progressWrapper")?.classList.add("hidden"); }
function _prog(s,t,w){
    const e1=document.getElementById("statusMessage"); if(e1) e1.innerText=s;
    const e2=document.getElementById("progressText");  if(e2) e2.innerText=t;
    const e3=document.getElementById("progressFill");  if(e3) e3.style.width=w;
}
function updatePPTFileName(){
    const i=document.getElementById("pptUpload"), l=document.getElementById("pptFileName");
    if(l) l.innerText=i?.files?.length?i.files[0].name:"No file selected";
    if(i?.files?.length) currentFilename=i.files[0].name;
}


/* ============================================================
   PREVIEW
============================================================ */
async function loadPPTPreview(){
    const fi=document.getElementById("pptUpload");
    if(!fi?.files?.length){alert("Upload a PPT file first");return;}
    const fd=new FormData();
    fd.append("ppt_file",fi.files[0]); appendOptions(fd);
    showProgress("Reading PPT...");
    try{
        updateProgress(40,"Extracting incident details...");
        const res=await fetch("/converter/preview",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){failProgress(data.error);alert(data.error);return;}
        const pc0=document.getElementById("previewContainer");
        pc0.innerHTML=data.preview_html;
        _reflowPreviewImages(pc0);
        currentIncident=data.incident_number||null;
        currentIncidentData=data.incident_data||{};
        // Apply RCA prefill — uses problem/analysis/resolution from prepare_data/build_rca
        if(data.rca_prefill&&Object.keys(data.rca_prefill).length){
            _applyRCAPrefill(data.rca_prefill);
        }
        renderSlidePreview(data.slide_images);
        completeProgress("Preview generated successfully");
        // Show Update Preview toolbar button
        document.getElementById("tbUpdateBtn")?.classList.remove("hidden");
        // Auto-run slide conversion immediately after preview (seamless flow)
        await _autoConvertSlides(fi.files[0]);
    }catch(e){console.error(e);failProgress("Preview failed");alert("Preview failed");}
}

// Internal: auto-convert slides after preview — called automatically, not by user
async function _autoConvertSlides(file){
    if(!file) return;
    const fd=new FormData();
    fd.append("ppt_file", file);
    appendOptions(fd);
    try{
        showProgress("Converting slides...");
        const res=await fetch("/converter/convert",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){ failProgress(data.error); return; }
        pptConverted=true;
        renderSlidePreview(data.slide_images);
        completeProgress("Preview ready");
        // Enable the generate report button
        document.getElementById("generateBtn")?.classList.remove("hidden");
    }catch(e){
        console.error("Auto-convert failed:", e);
        failProgress("Slide conversion failed — click Apply Filters to retry");
    }
}


/* ============================================================
   RCA PREFILL
============================================================ */
function _applyRCAPrefill(prefill){
    let had=false;
    ["problem","rootcause","resolution"].forEach(z=>{
        if(prefill[z]){
            const el=document.getElementById(`rca-text-${z}`);
            if(el){ el.innerHTML=_textToHtml(prefill[z]); _updateZoneTextStatus(z); }
            had=true;
        }
    });
    const s=document.getElementById("rcaPrefillStatus"); if(s) s.style.display=had?"flex":"none";
}
function _textToHtml(t){ return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/\n/g,"<br>"); }
function clearRCAText(){
    ["problem","rootcause","resolution"].forEach(z=>{ const e=document.getElementById(`rca-text-${z}`); if(e)e.innerHTML=""; _updateZoneTextStatus(z); });
    const s=document.getElementById("rcaPrefillStatus"); if(s) s.style.display="none";
}
function clearZoneText(zone){ const e=document.getElementById(`rca-text-${zone}`); if(e)e.innerHTML=""; _updateZoneTextStatus(zone); }


/* ============================================================
   RICH TEXT EDITOR
============================================================ */
// Saved selection for when focus leaves editor during toolbar click
let _rtaSavedSel = null;

function rtaSaveSelection(zone){
    const sel=window.getSelection();
    if(sel&&sel.rangeCount) _rtaSavedSel={zone,range:sel.getRangeAt(0).cloneRange()};
}

function rtaRestoreSelection(){
    if(!_rtaSavedSel) return false;
    const sel=window.getSelection();
    sel.removeAllRanges(); sel.addRange(_rtaSavedSel.range);
    return true;
}

/* ── Case helpers ─────────────────────────────────────────────── */
function _toTitleCase(str){
    return str.replace(/\w/g, ch=>ch.toUpperCase()).replace(/\B\w/g, ch=>ch.toLowerCase());
}
function _toSentenceCase(str){
    return str.length===0 ? str : str[0].toUpperCase()+str.slice(1).toLowerCase();
}

function applyRTACmd(zone, cmd, value){
    const editor=document.getElementById(`rca-text-${zone}`);
    if(!editor) return;
    // Restore selection if it was lost (e.g. toolbar button click)
    rtaRestoreSelection();
    editor.focus();
    if(cmd==="allCaps"){
        // 4-step cycle: ALL CAPS → Title Case → Sentence case → lowercase → ALL CAPS
        const sel=window.getSelection();
        if(sel&&sel.rangeCount&&!sel.getRangeAt(0).collapsed){
            const range=sel.getRangeAt(0);
            const text=range.toString();
            if(!text) return;
            let next;
            // Detect current state
            const upper = text.toUpperCase();
            const lower = text.toLowerCase();
            const title = text.split(/\b/).map(w=>w.length>0?w[0].toUpperCase()+w.slice(1).toLowerCase():w).join("");
            const sentence = text.length>0 ? text[0].toUpperCase()+text.slice(1).toLowerCase() : text;
            if(text===upper && text!==lower){
                // Currently ALL CAPS → go Title Case
                next = title;
            } else if(text===title && text!==lower && text!==upper){
                // Currently Title Case → go Sentence case
                next = sentence;
            } else if(text===sentence && text!==upper){
                // Currently Sentence case → go lowercase
                next = lower;
            } else {
                // lowercase or anything else → go ALL CAPS
                next = upper;
            }
            range.deleteContents();
            range.insertNode(document.createTextNode(next));
            range.collapse(false); sel.removeAllRanges(); sel.addRange(range);
        }
    } else if(cmd==="reset"){
        document.execCommand("removeFormat",false,null);
    } else if(cmd==="fontSize"){
        document.execCommand("fontSize",false,"7");
        editor.querySelectorAll('font[size="7"]').forEach(el=>{
            el.removeAttribute("size"); el.style.fontSize=value+"px";
        });
    } else if(cmd==="insertAlphaList"){
        // Insert a lettered list by converting from ordered list and applying CSS
        document.execCommand("insertOrderedList", false, null);
        const editor=document.getElementById(`rca-text-${zone}`);
        if(editor){
            // Toggle list-style-type between decimal and lower-alpha
            const lists=editor.querySelectorAll("ol");
            lists.forEach(ol=>{
                ol.style.listStyleType=ol.style.listStyleType==="lower-alpha"?"decimal":"lower-alpha";
            });
        }
    } else {
        document.execCommand(cmd,false,value||null);
    }
    _updateZoneTextStatus(zone);
}

// Colour picker popups (MS-Office style grid)
const PRESET_COLORS=[
    "#000000","#FFFFFF","#FF0000","#00FF00","#0000FF","#FFFF00","#FF6600","#9900CC",
    "#1E293B","#334155","#64748B","#94A3B8","#CBD5E1","#E2E8F0","#F1F5F9","#F8FAFC",
    "#DC2626","#EA580C","#D97706","#CA8A04","#65A30D","#16A34A","#059669","#0891B2",
    "#2563EB","#4F46E5","#7C3AED","#9333EA","#DB2777","#E11D48","#F87171","#FCA5A5",
    "#FED7AA","#FEF08A","#BBF7D0","#A7F3D0","#BAE6FD","#BFDBFE","#DDD6FE","#FBCFE8",
];

function _buildColorGrid(onSelect){
    const wrap=document.createElement("div"); wrap.className="color-grid-popup";
    const grid=document.createElement("div"); grid.className="color-grid";
    PRESET_COLORS.forEach(hex=>{
        const swatch=document.createElement("div"); swatch.className="color-swatch";
        swatch.style.background=hex; swatch.title=hex;
        swatch.addEventListener("mousedown",e=>{e.preventDefault();e.stopPropagation();onSelect(hex);wrap.remove();});
        grid.appendChild(swatch);
    });
    wrap.appendChild(grid);
    const moreRow=document.createElement("div"); moreRow.className="color-more-row";
    const moreLbl=document.createElement("span"); moreLbl.textContent="More colors…"; moreLbl.className="color-more-lbl";
    const inp=document.createElement("input"); inp.type="color"; inp.className="color-more-input";
    inp.addEventListener("input",()=>onSelect(inp.value));
    inp.addEventListener("change",()=>{onSelect(inp.value); wrap.remove();});
    moreRow.appendChild(moreLbl); moreRow.appendChild(inp);
    wrap.appendChild(moreRow);
    return wrap;
}

function _toggleColorPopup(btn, zone, cmdType){
    // Close any open
    document.querySelectorAll(".color-grid-popup").forEach(p=>p.remove());
    const popup=_buildColorGrid(hex=>{
        rtaRestoreSelection();
        applyRTACmd(zone, cmdType, hex);
    });
    popup.style.position="absolute";
    const rect=btn.getBoundingClientRect();
    popup.style.top=(rect.bottom+window.scrollY+4)+"px";
    popup.style.left=(rect.left+window.scrollX)+"px";
    document.body.appendChild(popup);
    // Close on outside click
    setTimeout(()=>{
        document.addEventListener("mousedown",function handler(e){
            if(!popup.contains(e.target)){popup.remove(); document.removeEventListener("mousedown",handler);}
        });
    },10);
}

// Auto-correct / spell suggestion (client-side dictionary approach)
const COMMON_CORRECTIONS={
    "teh":"the","taht":"that","recieve":"receive","seperate":"separate",
    "occured":"occurred","definately":"definitely","accomodate":"accommodate",
    "relevent":"relevant","existance":"existence","neccessary":"necessary",
    "wiht":"with","hte":"the","adn":"and","ot":"to","fo":"of","od":"do",
    "documet":"document","documnet":"document","incidnet":"incident",
    "porblem":"problem","reslution":"resolution","roote":"route","cuase":"cause",
    "verifed":"verified","faild":"failed","erorr":"error","configration":"configuration",
};

function _autoCorrect(editor){
    const sel=window.getSelection();
    if(!sel||!sel.rangeCount) return;
    const range=sel.getRangeAt(0);
    if(!range.collapsed) return;
    const node=range.startContainer;
    if(node.nodeType!==Node.TEXT_NODE) return;
    const text=node.textContent;
    const pos=range.startOffset;
    // Find word just typed (triggered on space)
    const beforeCursor=text.substring(0,pos);
    const match=beforeCursor.match(/(\b\w+)\s$/);
    if(!match) return;
    const word=match[1];
    const lower=word.toLowerCase();
    if(COMMON_CORRECTIONS[lower]){
        const corrected=word[0]===word[0].toUpperCase()?
            COMMON_CORRECTIONS[lower][0].toUpperCase()+COMMON_CORRECTIONS[lower].slice(1):
            COMMON_CORRECTIONS[lower];
        const start=pos-word.length-1;
        node.textContent=text.substring(0,start)+corrected+" "+text.substring(pos);
        const newRange=document.createRange();
        newRange.setStart(node,start+corrected.length+1);
        newRange.collapse(true);
        sel.removeAllRanges(); sel.addRange(newRange);
    }
}

function onRTAKeydown(zone, e){
    if(e.key===" ") setTimeout(()=>_autoCorrect(document.getElementById(`rca-text-${zone}`)),0);
    _updateZoneTextStatus(zone);
}


/* ============================================================
   CONVERT
============================================================ */
async function convertPPTSlides(){
    const fi=document.getElementById("pptUpload");
    if(!fi?.files?.length){alert("Upload a PPT first");return;}
    const fd=new FormData(); fd.append("ppt_file",fi.files[0]); appendOptions(fd);
    showProgress("Converting PPT...");
    try{
        updateProgress(60,"Extracting slide images...");
        const res=await fetch("/converter/convert",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){failProgress(data.error);alert(data.error);return;}
        pptConverted=true; renderSlidePreview(data.slide_images);
        document.getElementById("generateBtn")?.classList.remove("hidden");
        completeProgress("PPT conversion completed");
    }catch(e){console.error(e);failProgress("Conversion failed");}
}


/* ============================================================
   GENERATE STANDARD REPORT
============================================================ */
async function generateDocument(){
    const fi=document.getElementById("pptUpload"), fmt=getSelectedFormat();
    const fd=new FormData(); fd.append("ppt_file",fi.files[0]); fd.append("format",fmt); appendOptions(fd);
    showProgress("Generating report...");
    try{
        updateProgress(80,`Creating ${fmt.toUpperCase()}...`);
        const res=await fetch("/converter/generate",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){failProgress(data.error);alert(data.error);return;}
        generatedDocxName=data.docx_filename||null; generatedPdfName=data.pdf_filename||null;
        _showDownloadBtns(fmt,data); showConverterSection("download");
        completeProgress("Document generated successfully");
    }catch(e){console.error(e);failProgress("Generation failed");}
}


/* ============================================================
   DOWNLOAD
============================================================ */
function hideAllDownloadBtns(){ ["downloadWordBtn","downloadPdfBtn","downloadBothBtn","downloadPptxBtn"].forEach(id=>document.getElementById(id)?.classList.add("hidden")); }
function _showDownloadBtns(fmt,data){
    hideAllDownloadBtns();
    if(data.docx_filename||fmt==="word") document.getElementById("downloadWordBtn")?.classList.remove("hidden");
    if(data.pdf_filename)  document.getElementById("downloadPdfBtn")?.classList.remove("hidden");
    // downloadPptxBtn is intentionally kept hidden — Export as PPT auto-downloads
}
function downloadFormat(type){
    if(type==="word"&&generatedDocxName) window.location.href=`/converter/download/${generatedDocxName}`;
    else if(type==="pdf"&&generatedPdfName) window.location.href=`/converter/download/${generatedPdfName}`;
    else if(type==="pptx"&&generatedPptxName) window.location.href=`/converter/download-pptx/${generatedPptxName}`;
    else if(type==="both"){ if(generatedDocxName) window.location.href=`/converter/download/${generatedDocxName}`; if(generatedPdfName) setTimeout(()=>window.location.href=`/converter/download/${generatedPdfName}`,800); }
}
function downloadConvertedDoc(){ downloadFormat("word"); }


/* ============================================================
   SLIDE PREVIEW GRID
============================================================ */
function renderSlidePreview(images){
    const container=document.getElementById("slidePreviewContainer");
    allSlideImages=[]; selectedSlides.clear();
    if(!images?.length){
        container.innerHTML=`<p class="preview-placeholder">No slide images found</p>`;
        document.getElementById("slideGridActions").style.display="none";
        _resetRCAState(); return;
    }
    images.forEach((img,idx)=>{
        const src=`/converter/slide-preview/${img.filename}`;
        allSlideImages.push({filename:img.filename,src,label:`Slide ${idx+1}`,idx});
    });
    _renderSlideGrid();
    document.getElementById("slideGridActions").style.display="flex";
    lbImages=[...allSlideImages];
    _resetRCAState(); _populateRCATray(images);
}

function _renderSlideGrid(){
    const container=document.getElementById("slidePreviewContainer");
    container.innerHTML=allSlideImages.map(s=>`
        <div class="ppt-preview-card" id="grid-card-${s.filename}" data-filename="${s.filename}">
            <div class="ppt-card-check ${selectedSlides.has(s.filename)?"checked":""}"
                 onclick="toggleSlideSelect('${s.filename}',event)" title="Select">
                ${selectedSlides.has(s.filename)?"☑":"☐"}
            </div>
            <img src="${s.src}" class="slide-preview-image" alt="${s.label}"
                 onclick="lbOpen(${s.idx})" title="Click to enlarge">
            <div class="ppt-card-footer">
                <span class="ppt-card-label">${s.label}</span>
                <button class="ppt-card-dl" onclick="downloadSingleImage('${s.filename}',${s.idx+1})" title="Download">⬇</button>
            </div>
            <div class="ppt-card-zone-dots" id="zone-dots-${s.filename}"></div>
        </div>`).join("");
    // Reapply zone indicators
    _refreshAllZoneIndicators();
}

function toggleSlideSelect(fn,e){
    e.stopPropagation();
    selectedSlides.has(fn)?selectedSlides.delete(fn):selectedSlides.add(fn);
    _refreshGridChecks();
}
function selectAllSlides()    { allSlideImages.forEach(s=>selectedSlides.add(s.filename)); _refreshGridChecks(); }
function clearSlideSelection(){ selectedSlides.clear(); _refreshGridChecks(); }
function _refreshGridChecks(){
    allSlideImages.forEach(s=>{
        const card=document.getElementById(`grid-card-${s.filename}`);
        const chk=card?.querySelector(".ppt-card-check");
        if(card) card.classList.toggle("selected",selectedSlides.has(s.filename));
        if(chk){ chk.textContent=selectedSlides.has(s.filename)?"☑":"☐"; chk.classList.toggle("checked",selectedSlides.has(s.filename)); }
    });
}


/* ============================================================
   ZONE COLOUR INDICATORS ON THUMBNAILS
============================================================ */
function _refreshZoneIndicators(fn){
    // Tray thumb border
    const thumb=document.querySelector(`#rcaSlideTray .rca-thumb[data-file="${fn}"]`);
    const inZones=Object.keys(rcaZones).filter(z=>rcaZones[z].has(fn));
    if(thumb){
        if(inZones.length===0){ thumb.style.borderColor="transparent"; thumb.style.boxShadow=""; }
        else if(inZones.length===1){ thumb.style.borderColor=ZONE_COLORS[inZones[0]]; thumb.style.boxShadow=`0 0 0 2px ${ZONE_COLORS[inZones[0]]}44`; }
        else{
            const gradient=inZones.map(z=>ZONE_COLORS[z]).join(", ");
            thumb.style.borderColor="transparent";
            thumb.style.boxShadow=inZones.map(z=>`0 0 0 2px ${ZONE_COLORS[z]}`).join(", ");
        }
        thumb.classList.toggle("assigned", inZones.length>0);
    }
    // Grid card dots
    const dotsEl=document.getElementById(`zone-dots-${fn}`);
    if(dotsEl){
        dotsEl.innerHTML=inZones.map(z=>`<span class="zone-dot" style="background:${ZONE_COLORS[z]}" title="${z}"></span>`).join("");
    }
    // Grid card border
    const card=document.getElementById(`grid-card-${fn}`);
    if(card){
        if(inZones.length===1) card.style.outline=`2px solid ${ZONE_COLORS[inZones[0]]}`;
        else if(inZones.length>1) card.style.outline=`2px solid ${ZONE_COLORS[inZones[0]]}`;
        else card.style.outline="";
    }
}
function _refreshAllZoneIndicators(){ allSlideImages.forEach(s=>_refreshZoneIndicators(s.filename)); }


/* ============================================================
   IMAGE DOWNLOADS
============================================================ */
function downloadSingleImage(fn,idx){
    window.location.href=`/converter/download-image/${fn}?incident=${currentIncident||"IMG"}&idx=${String(idx).padStart(3,"0")}`;
}
async function downloadAllImages(){
    if(!allSlideImages.length){alert("No slide images available");return;}
    await _downloadZip(allSlideImages.map(s=>s.filename));
}
async function downloadSelectedImages(){
    if(!selectedSlides.size){alert("Select slides first");return;}
    await _downloadZip([...selectedSlides]);
}
async function _downloadZip(filenames){
    if(!filenames.length) return;
    showProgress("Preparing ZIP...");
    try{
        const res=await fetch("/converter/download-images-zip",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filenames,incident:currentIncident||"IMG"})});
        if(!res.ok){failProgress("ZIP failed");return;}
        const blob=await res.blob();
        const url=URL.createObjectURL(blob);
        const a=document.createElement("a"); a.href=url;
        const cd=res.headers.get("content-disposition");
        a.download=cd?.match(/filename="(.+)"/)?.[1]||"slides.zip";
        document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
        completeProgress(`Downloaded ${filenames.length} image(s)`);
    }catch(e){console.error(e);failProgress("ZIP failed");}
}


/* ============================================================
   LIGHTBOX
============================================================ */
function lbOpen(idx){
    lbCurrent=idx; lbScale=1.0; lbOpen_=true;
    document.getElementById("lbOverlay").classList.add("lb-visible");
    _lbRender();
    document.addEventListener("keydown",_lbKey);
}
function lbClose(){
    lbOpen_=false;
    document.getElementById("lbOverlay").classList.remove("lb-visible");
    document.removeEventListener("keydown",_lbKey);
}
function lbNav(dir){ lbCurrent=(lbCurrent+dir+lbImages.length)%lbImages.length; lbScale=1.0; _lbRender(); }
function lbZoom(delta){ lbScale=Math.min(4,Math.max(0.3,lbScale+delta)); _lbApplyScale(); }
function lbFit(){ lbScale=1.0; _lbApplyScale(); }
function lbDownload(){
    const img=lbImages[lbCurrent]; if(!img) return;
    downloadSingleImage(img.filename, img.idx+1);
}
function lbAddToZone(zone){
    const img=lbImages[lbCurrent]; if(!img) return;
    if(rcaCollapsed[zone]){rcaCollapsed[zone]=false; _applyZoneCollapse(zone);}
    _addToZone(zone, img.filename);
    updateRCASidebar();
    // Visual feedback
    const btn=document.getElementById(`lbZoneBtn-${zone}`);
    if(btn){ btn.textContent=`✓ Added`; setTimeout(()=>btn.textContent={problem:"🔴 Problem",rootcause:"🟡 Root Cause",resolution:"🟢 Resolution"}[zone],1200); }
}
function _lbRender(){
    const img=lbImages[lbCurrent]; if(!img) return;
    const imgEl=document.getElementById("lbImg");
    if(imgEl){ imgEl.src=img.src; imgEl.style.transform=`scale(${lbScale})`; }
    document.getElementById("lbTitle").textContent=img.label;
    document.getElementById("lbPos").textContent=`${lbCurrent+1} / ${lbImages.length}`;
    // Update zone button states
    ["problem","rootcause","resolution"].forEach(z=>{
        const btn=document.getElementById(`lbZoneBtn-${z}`);
        if(btn&&img) btn.classList.toggle("lb-zone-active", rcaZones[z].has(img.filename));
    });
}
function _lbApplyScale(){ const i=document.getElementById("lbImg"); if(i) i.style.transform=`scale(${lbScale})`; }
function _lbKey(e){
    if(e.key==="ArrowRight"||e.key==="ArrowDown") lbNav(+1);
    else if(e.key==="ArrowLeft"||e.key==="ArrowUp") lbNav(-1);
    else if(e.key==="Escape") lbClose();
    else if(e.key==="+"||e.key==="=") lbZoom(+0.2);
    else if(e.key==="-") lbZoom(-0.2);
    e.stopPropagation();
}


/* ============================================================
   CLEAR WORKSPACE
============================================================ */
function clearWorkspace(){
    // Clear server-side preview store & disk cache
    fetch("/converter/clear-cache",{method:"POST"}).catch(()=>{});
    const pi=document.getElementById("pptUpload"); if(pi) pi.value="";
    const pn=document.getElementById("pptFileName"); if(pn) pn.innerText="No file selected";
    document.getElementById("previewContainer").innerHTML=`<p class="preview-placeholder">Preview will appear here</p>`;
    document.getElementById("slidePreviewContainer").innerHTML=`<p class="preview-placeholder">Converted slide images will appear here</p>`;
    document.getElementById("slideGridActions").style.display="none";
    hideAllDownloadBtns();
    ["convertBtn","generateBtn","tbUpdateBtn"].forEach(id=>document.getElementById(id)?.classList.add("hidden"));
    generatedDocxName=null; generatedPdfName=null; generatedPptxName=null; pptConverted=false;
    currentIncident=null; currentFilename=null; currentIncidentData={};
    allSlideImages=[]; selectedSlides.clear(); lbImages=[];
    _resetRCAState();
    ["problem","rootcause","resolution"].forEach(z=>{ const e=document.getElementById(`rca-text-${z}`); if(e)e.innerHTML=""; _updateZoneTextStatus(z); });
    const s=document.getElementById("rcaPrefillStatus"); if(s) s.style.display="none";
    document.getElementById("rcaAssignmentPanel").style.display="none";
    resetProcessingStatus();
    // Reset options to defaults
    const imgAll=document.getElementById("imgModeAll");
    if(imgAll) imgAll.checked=true;
    const el=document.getElementById("lastAction"); if(el) el.innerText="Ready";
}


/* ============================================================
   RCA TRAY
============================================================ */
function _resetRCAState(){
    Object.keys(rcaSlides).forEach(k=>delete rcaSlides[k]);
    Object.keys(rcaZones).forEach(z=>{rcaZones[z].clear();_renderZoneImages(z);});
    rcaSelected.clear();
    document.getElementById("rcaQuickAssign")?.classList.remove("visible");
    updateRCASidebar();
}

function _populateRCATray(images){
    const tray=document.getElementById("rcaSlideTray");
    const panel=document.getElementById("rcaAssignmentPanel");
    if(!images?.length||!tray) return;
    panel.style.display="block"; tray.innerHTML="";
    images.forEach((img,idx)=>{
        const fn=img.filename, src=`/converter/slide-preview/${fn}`, label=`Slide ${idx+1}`;
        rcaSlides[fn]={src,label,idx};
        tray.appendChild(_makeTrayThumb(fn,src,label));
    });
    Object.keys(rcaCollapsed).forEach(_applyZoneCollapse);
    showConverterSection("rca");
    updateRCASidebar();
    panel.scrollIntoView({behavior:"smooth",block:"start"});
}

function _makeTrayThumb(fn,src,label){
    const div=document.createElement("div");
    div.className="rca-thumb"; div.dataset.file=fn; div.draggable=true;
    div.innerHTML=`<div class="rca-thumb-select">✓</div><img src="${src}" alt="${label}" draggable="false"><div class="rca-thumb-label">${label}</div>`;
    div.addEventListener("dragstart",e=>{rcaDragging=fn;div.classList.add("dragging");e.dataTransfer.effectAllowed="copy";e.dataTransfer.setData("text/plain",fn);});
    div.addEventListener("dragend",()=>{rcaDragging=null;div.classList.remove("dragging");});
    div.addEventListener("click",()=>_toggleThumbSel(fn));
    return div;
}

function _toggleThumbSel(fn){
    rcaSelected.has(fn)?rcaSelected.delete(fn):rcaSelected.add(fn);
    _refreshTrayVisuals();
    document.getElementById("rcaQuickAssign")?.classList.toggle("visible",rcaSelected.size>0);
}
function clearSelection(){ rcaSelected.clear();_refreshTrayVisuals();document.getElementById("rcaQuickAssign")?.classList.remove("visible"); }
function _refreshTrayVisuals(){
    document.querySelectorAll("#rcaSlideTray .rca-thumb").forEach(c=>{
        const fn=c.dataset.file;
        c.classList.toggle("selected",rcaSelected.has(fn));
    });
    _refreshAllZoneIndicators();
}
function quickAssign(zone){
    if(rcaCollapsed[zone]){rcaCollapsed[zone]=false;_applyZoneCollapse(zone);}
    rcaSelected.forEach(fn=>_addToZone(zone,fn));
    clearSelection(); updateRCASidebar();
}


/* ============================================================
   DRAG-AND-DROP
============================================================ */
function onDragOver(e,zone){e.preventDefault();e.dataTransfer.dropEffect="copy";document.getElementById(`zone-${zone}`)?.classList.add("dragover");}
function onDragLeave(e,zone){document.getElementById(`zone-${zone}`)?.classList.remove("dragover");}
function onDrop(e,zone){
    e.preventDefault(); document.getElementById(`zone-${zone}`)?.classList.remove("dragover");
    const fn=e.dataTransfer.getData("text/plain")||rcaDragging;
    if(fn){if(rcaCollapsed[zone]){rcaCollapsed[zone]=false;_applyZoneCollapse(zone);}_addToZone(zone,fn);updateRCASidebar();}
}


/* ============================================================
   ZONE IMAGE STATE
============================================================ */
function _addToZone(zone,fn){
    if(!rcaSlides[fn]) return;
    rcaZones[zone].add(fn);
    _renderZoneImages(zone);
    _refreshZoneIndicators(fn);
    _updateZoneImageCount(zone);
}
function _removeFromZone(zone,fn){
    rcaZones[zone].delete(fn);
    _renderZoneImages(zone);
    _refreshZoneIndicators(fn);
    _updateZoneImageCount(zone);
    updateRCASidebar();
}
function _renderZoneImages(zone){
    const c=document.getElementById(`zone-images-${zone}`); if(!c) return; c.innerHTML="";
    rcaZones[zone].forEach(fn=>{
        const {src,label,idx}=rcaSlides[fn];
        const w=document.createElement("div"); w.className="rca-zone-thumb";
        w.innerHTML=`<img src="${src}" alt="${label}" title="${label}" onclick="lbOpen(${idx})" style="border-color:${ZONE_COLORS[zone]}"><button class="rca-remove-btn">✕</button>`;
        w.querySelector(".rca-remove-btn").addEventListener("click",()=>_removeFromZone(zone,fn));
        c.appendChild(w);
    });
    _updateZoneImageCount(zone);
    _refreshAllZoneIndicators();
}
function _updateZoneImageCount(zone){
    const n=rcaZones[zone].size;
    const h=document.getElementById(`zoneImgCount-${zone}`); if(h) h.textContent=`${n} image${n!==1?"s":""}`;
    const il=document.getElementById(`zoneImgCountInline-${zone}`); if(il) il.textContent=n?`(${n})`:"";
    const chip=document.getElementById(`sbChip${_cap(zone)}`); if(chip){chip.textContent=`${n}`;chip.classList.toggle("has-content",n>0);}
}
function clearRCAAssignments(){
    Object.keys(rcaZones).forEach(z=>{rcaZones[z].clear();_renderZoneImages(z);_updateZoneImageCount(z);});
    rcaSelected.clear(); _refreshTrayVisuals();
    document.getElementById("rcaQuickAssign")?.classList.remove("visible");
    clearRCAText(); updateRCASidebar(); _refreshAllZoneIndicators();
}


/* ============================================================
   RCA TEXT
============================================================ */
function onRCATextChange(zone){ _updateZoneTextStatus(zone); }
function _updateZoneTextStatus(zone){
    const el=document.getElementById(`rca-text-${zone}`);
    const len=(el?.innerText||"").trim().length;
    const s=document.getElementById(`zoneTextStatus-${zone}`);
    if(s){s.textContent=len>0?`✎ ${len} chars`:"";s.className=`rca-text-status${len>0?" has-text":""}`;}
}
function insertRCAPlaceholder(zone,placeholder){
    const el=document.getElementById(`rca-text-${zone}`); if(!el) return;
    el.focus();
    const sel=window.getSelection();
    if(sel&&sel.rangeCount){
        const range=sel.getRangeAt(0); range.deleteContents();
        range.insertNode(document.createTextNode(placeholder)); range.collapse(false);
        sel.removeAllRanges(); sel.addRange(range);
    } else { el.innerHTML+=placeholder; }
    _updateZoneTextStatus(zone);
}
function updateRCASidebar(){
    Object.keys(rcaZones).forEach(z=>_updateZoneImageCount(z));
    const total=Object.values(rcaZones).reduce((s,z)=>s+z.size,0);
    const b=document.getElementById("rcaGenerateBtn"); if(b) b.disabled=total===0;
    const b2=document.getElementById("rcaCreatePptBtn"); if(b2) b2.disabled=total===0;
}
function _getRCAText(zone){
    const el=document.getElementById(`rca-text-${zone}`);
    return el?(el.innerText||"").trim():"";
}


/* ============================================================
   GENERATE RCA WORD REPORT
============================================================ */
async function generateWithRCA(){
    const fi=document.getElementById("pptUpload");
    if(!fi?.files?.length){alert("Upload PPT first");return;}
    const total=Object.values(rcaZones).reduce((s,z)=>s+z.size,0);
    if(total===0){alert("Assign at least one slide to an RCA section first");return;}
    const rcaText={problem:_getRCAText("problem"),rootcause:_getRCAText("rootcause"),resolution:_getRCAText("resolution")};
    const fd=new FormData();
    fd.append("ppt_file",fi.files[0]); fd.append("format",getSelectedFormat());
    fd.append("rca_assignments",JSON.stringify({problem:[...rcaZones.problem],rootcause:[...rcaZones.rootcause],resolution:[...rcaZones.resolution]}));
    fd.append("rca_text",JSON.stringify(rcaText));
    fd.append("images_in_doc", getImagesInDoc());
    fd.append("all_slide_filenames", JSON.stringify(allSlideImages.map(s=>s.filename)));
    appendOptions(fd);
    showProgress("Generating RCA report..."); updateProgress(40,"Assembling RCA sections...");
    try{
        const res=await fetch("/converter/generate-rca",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){failProgress(data.error);alert(data.error);return;}
        generatedDocxName=data.docx_filename||null; generatedPdfName=data.pdf_filename||null;
        _showDownloadBtns(getSelectedFormat(),data); showConverterSection("download");
        completeProgress("RCA report generated");
    }catch(e){console.error(e);failProgress("RCA generation failed");}
}


/* ============================================================
   CREATE RCA PPTX
============================================================ */
async function createRCAPPT(){
    const fi=document.getElementById("pptUpload");
    if(!fi?.files?.length){alert("Upload PPT first");return;}
    const total=Object.values(rcaZones).reduce((s,z)=>s+z.size,0);
    if(total===0){alert("Assign at least one slide to an RCA section first");return;}
    const rcaText={problem:_getRCAText("problem"),rootcause:_getRCAText("rootcause"),resolution:_getRCAText("resolution")};
    const fd=new FormData();
    fd.append("ppt_file",fi.files[0]);
    fd.append("rca_assignments",JSON.stringify({problem:[...rcaZones.problem],rootcause:[...rcaZones.rootcause],resolution:[...rcaZones.resolution]}));
    fd.append("rca_text",JSON.stringify(rcaText));
    fd.append("incident_data",JSON.stringify(currentIncidentData));
    showProgress("Building RCA PowerPoint..."); updateProgress(50,"Creating slides...");
    try{
        const res=await fetch("/converter/create-ppt",{method:"POST",body:fd});
        const data=await res.json();
        if(data.error){failProgress(data.error);alert(data.error);return;}
        generatedPptxName=data.pptx_filename;
        const sizeTxt=data.size_kb?` (${data.size_kb} KB)`:""; 
        completeProgress(`PPT ready: ${data.pptx_filename}${sizeTxt}`);
        // Trigger browser download via anchor (prevents page navigation / fetch abort)
        const dlA=document.createElement("a");
        dlA.href=`/converter/download-pptx/${data.pptx_filename}`;
        dlA.download=data.pptx_filename;
        dlA.style.display="none";
        document.body.appendChild(dlA);
        dlA.click();
        setTimeout(()=>document.body.removeChild(dlA), 1000);
        // Button feedback
        const pptBtn=document.getElementById("exportPptBtn");
        if(pptBtn){
            pptBtn.textContent="✓ Downloading…";
            setTimeout(()=>{ pptBtn.textContent="📊 Export as PPT"; },3000);
        }
    }catch(e){
        console.error("PPT export error:", e);
        if(generatedPptxName){
            completeProgress("PPT saved — retrying download…");
            const dlA=document.createElement("a");
            dlA.href=`/converter/download-pptx/${generatedPptxName}`;
            dlA.download=generatedPptxName;
            document.body.appendChild(dlA); dlA.click();
            setTimeout(()=>document.body.removeChild(dlA),1000);
        } else {
            failProgress("PPT creation failed");
            alert("PPT creation failed: "+e.message);
        }
    }
}


/* ============================================================
   HELP MODAL
============================================================ */
function loadModuleHelpData(){
    fetch(window._helpEndpoint||"/api/help/converter")
        .then(r=>r.json()).then(data=>{
            const t=document.getElementById("helpModuleTitle"); if(t) t.textContent="💡 "+(data.module_title||"Help");
            const idx=document.getElementById("helpModalIndexPane"),con=document.getElementById("helpModalContentPane");
            if(!idx||!con) return;
            idx.innerHTML=""; con.innerHTML="";
            const topics=data.topics||[];
            if(!topics.length){con.innerHTML="<p>No help topics.</p>";return;}
            topics.forEach((topic,i)=>{
                const btn=document.createElement("button");
                btn.className="help-topic-btn"+(i===0?" active-help-topic":"");
                btn.textContent=topic.title;
                btn.onclick=()=>{document.querySelectorAll(".help-topic-btn").forEach(b=>b.classList.remove("active-help-topic"));btn.classList.add("active-help-topic");con.innerHTML=topic.content;};
                idx.appendChild(btn);
            });
            con.innerHTML=topics[0].content;
        }).catch(()=>{const p=document.getElementById("helpModalContentPane");if(p) p.innerHTML="<p>Help could not be loaded.</p>";});
}
window._helpEndpoint="/api/help/converter";


/* ============================================================
   PREVIEW IMAGE REFLOW — make stacked images appear side-by-side
============================================================ */
function _reflowPreviewImages(container){
    if(!container) return;
    // Find all <td> cells that contain img tags (the RCA value cells)
    container.querySelectorAll("td, th").forEach(cell=>{
        const imgs=cell.querySelectorAll("img");
        if(imgs.length<=1) return;
        // Create a flex wrapper for the images
        const wrap=document.createElement("div");
        wrap.style.cssText="display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start;margin-top:8px;";
        // Move all imgs into the wrapper
        imgs.forEach(img=>{
            img.style.cssText="max-width:320px;max-height:200px;width:auto;height:auto;border-radius:4px;border:1px solid #e2e8f0;";
            wrap.appendChild(img);
        });
        cell.appendChild(wrap);
    });
    // Also handle img tags that are direct children of the container
    const topImgs=container.querySelectorAll("p > img, div > img");
    topImgs.forEach(img=>{
        img.style.cssText="max-width:320px;max-height:200px;width:auto;height:auto;display:inline-block;margin:3px;";
    });
}


/* ============================================================
   INIT
============================================================ */
document.addEventListener("DOMContentLoaded",()=>{
    showConverterSection("converter");
    ["convertBtn","generateBtn","tbUpdateBtn"].forEach(id=>document.getElementById(id)?.classList.add("hidden"));
    hideAllDownloadBtns();
    document.getElementById("rcaAssignmentPanel").style.display="none";
    document.getElementById("slideGridActions").style.display="none";
    Object.keys(rcaCollapsed).forEach(_applyZoneCollapse);
});
