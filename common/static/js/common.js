/* ==========================================
   GLOBAL TOPBAR SEARCH CONTROLLER
========================================== */

function toggleGlobalSearch() {
    const wrapper = document.getElementById("topSearchWrapper");
    const input = document.getElementById("globalSearchInput");
    
    if (!wrapper || !input) return;
    
    wrapper.classList.toggle("expanded");
    
    if (wrapper.classList.contains("expanded")) {
        input.focus();
    } else {
        input.value = "";
        executePageSearch(""); // Clear page highlights when collapsing
    }
}

/**
 * Functional client-side context parsing mechanism.
 * Scans the primary active document container, matching text fragments dynamically.
 */
function executePageSearch(query) {
    const contentArea = document.querySelector(".scrollable-report-content");
    if (!contentArea) return;

    // Remove existing highlights to avoid duplication errors
    removePageSearchHighlights(contentArea);

    const cleanQuery = query.trim().toLowerCase();
    if (!cleanQuery || cleanQuery.length < 2) return;

    // Simple recursive DOM tree text-node walker execution loop
    const walkDOM = (node) => {
        if (node.nodeType === 3) { // Text Node
            const textValue = node.nodeValue;
            const index = textValue.toLowerCase().indexOf(cleanQuery);
            
            if (index >= 0) {
                const span = document.createElement("span");
                span.className = "page-search-highlight";
                span.style.backgroundColor = "#fef08a"; // Soft yellow highlight
                span.style.color = "#0f172a";
                span.style.borderRadius = "2px";
                span.style.padding = "0 2px";

                const match = textValue.substring(index, index + cleanQuery.length);
                const before = textValue.substring(0, index);
                const after = textValue.substring(index + cleanQuery.length);

                node.nodeValue = before;
                span.textContent = match;
                
                const nextNode = node.nextSibling;
                if (nextNode) {
                    node.parentNode.insertBefore(span, nextNode);
                    node.parentNode.insertBefore(document.createTextNode(after), nextNode);
                } else {
                    node.parentNode.appendChild(span);
                    node.parentNode.appendChild(document.createTextNode(after));
                }
            }
        } else if (node.nodeType === 1 && node.childNodes && !["SCRIPT", "STYLE", "INPUT", "TEXTAREA"].includes(node.tagName)) {
            for (let i = 0; i < node.childNodes.length; i++) {
                walkDOM(node.childNodes[i]);
            }
        }
    };

    walkDOM(contentArea);
}

function removePageSearchHighlights(container) {
    const highlights = container.querySelectorAll(".page-search-highlight");
    highlights.forEach(span => {
        const parent = span.parentNode;
        if (parent) {
            parent.replaceChild(document.createTextNode(span.textContent), span);
            parent.normalize(); // Merges adjacent text nodes cleanly back together
        }
    });
}

// Close search box automatically if clicking anywhere outside the search container
document.addEventListener("click", (e) => {
    const wrapper = document.getElementById("topSearchWrapper");
    if (wrapper && wrapper.classList.contains("expanded") && !wrapper.contains(e.target)) {
        toggleGlobalSearch();
    }
});

/* ==========================================
   PROGRESS FUNCTIONS
========================================== */

function showProgress(message) {
    document.getElementById("progressWrapper")
        ?.classList.remove("hidden");

    document.getElementById("progressFill")
        .style.width = "20%";

    document.getElementById("progressText")
        .innerText = message;

    document.getElementById("statusMessage")
        .innerText = "Processing...";
}


function updateProgress(percent, message) {
    document.getElementById("progressFill")
        .style.width = percent + "%";

    document.getElementById("progressText")
        .innerText = message;
}


function completeProgress(message) {
    document.getElementById("progressFill")
        .style.width = "100%";

    document.getElementById("progressText")
        .innerText = "Completed";

    document.getElementById("statusMessage")
        .innerText = message;

    setTimeout(() => {
        document.getElementById("progressWrapper")
            ?.classList.add("hidden");
    }, 1500);
}


function failProgress(message) {
    document.getElementById("statusMessage")
        .innerText = message;
}



/* ==========================================
   HOME NAVIGATION
========================================== */

function goHome() {
    window.location.href = "/";
}



/* ==========================================
   DOCK TOGGLE
========================================== */

function toggleDock() {
    const dockBar = document.getElementById("dockBar");
    const appContainer = document.querySelector(".app-container");
    const toggleIcon = document.getElementById("dockToggleIcon");

    if (!dockBar) return;

    dockBar.classList.toggle("collapsed");

    if (appContainer) {
        appContainer.classList.toggle("dock-hidden");
    }

    // Change arrow direction
    if (toggleIcon) {
        if (dockBar.classList.contains("collapsed")) {
            toggleIcon.innerHTML = "⮞";
        } else {
            toggleIcon.innerHTML = "⮜";
        }
    }
}



/* ==========================================
   CLEAR WORKSPACE
========================================== */

function clearWorkspace() {

    // Reset file inputs
    document.querySelectorAll("input[type='file']").forEach(input => {
        input.value = "";
    });

    // Reset text inputs
    document.querySelectorAll("input[type='text']").forEach(input => {
        input.value = "";
    });

    // Reset dropdowns
    document.querySelectorAll("select").forEach(select => {
        select.selectedIndex = 0;
    });

    // Clear preview areas
    const previewSections = [
        "previewContainer",
        "slidePreviewContainer",
        "searchResults",
        "rcaPreviewContainer"
    ];

    previewSections.forEach(id => {
        const section = document.getElementById(id);

        if (section) {
            section.innerHTML = "";
        }
    });

    // Reset status
    resetProcessingStatus();

    console.log("Workspace cleared");
}



/* ==========================================
   APPLY FILTERS
========================================== */

function applyFilters() {
    const filterPanel = document.getElementById("filterPanel");

    if (filterPanel) {
        filterPanel.classList.toggle("active");
    }

    console.log("Filters toggled");
}



/* ==========================================
   RESET STATUS
========================================== */

function resetProcessingStatus() {
    const statusMessage = document.getElementById("statusMessage");
    const progressWrapper = document.getElementById("progressWrapper");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");

    if (statusMessage) {
        statusMessage.innerText = "Ready";
    }

    if (progressFill) {
        progressFill.style.width = "0%";
    }

    if (progressText) {
        progressText.innerText = "";
    }

    if (progressWrapper) {
        progressWrapper.classList.add("hidden");
    }
}

// Target and link the framework help icon directly to our helper window interceptor
document.addEventListener("DOMContentLoaded", () => {
    const frameworkHelpBtn = document.querySelector(".help-btn");
    if (frameworkHelpBtn) {
        frameworkHelpBtn.setAttribute("onclick", "toggleHelpSystemModal()");
        console.log("✓ Framework Help Button successfully linked to current active module context.");
    }
});

// Structural controller to toggle modal state safely
function toggleHelpSystemModal() {
    const modal = document.getElementById("helpSystemModal");
    if (!modal) return;
    
    modal.classList.toggle("hidden");
    
    // Auto-load topics from API when shown
    if (!modal.classList.contains("hidden")) {
        if (typeof loadModuleHelpData === "function") {
            loadModuleHelpData();
        }
    }
}