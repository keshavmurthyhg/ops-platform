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