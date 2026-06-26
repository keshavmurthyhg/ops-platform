// =============================================================================
//  OPS CENTER — LIVE DATA LOADERS
//  ops_live_data.js
//
//  Loads live data from Outlook (support emails) and the integration failure
//  API. These make real network calls to the Flask backend.
//
//  Depends on: operations_center.js (updateProcessingStatus, buildFilters,
//              applyFilters, populateServerDropdown)
//
//  Included by operations_center.html AFTER operations_center.js
// =============================================================================


function populateServerDropdown() {

    const env =
        document.getElementById(
            "failureEnvironmentFilter"
        )?.value || "All";

    const serverDropdown =
        document.getElementById(
            "failureServerFilter"
        );

    if(!serverDropdown) return;

    const servers = new Set();

    document
        .querySelectorAll(
            "#failureTableBody tr"
        )
        .forEach(row => {

            const rowEnv =
                row.cells[4]
                    .innerText
                    .trim();

            const rowServer =
                row.cells[5]
                    .innerText
                    .trim();

            if(
                env === "All" ||
                rowEnv === env
            ){
                servers.add(rowServer);
            }
        });

    serverDropdown.innerHTML =
        '<option value="All">All</option>';

    [...servers]
        .sort()
        .forEach(server => {

            serverDropdown.innerHTML +=
                `<option value="${server}">
                    ${server}
                </option>`;
        });
}

function populateFailureFiltersFromTable() {

    const envSet = new Set();
    const serverSet = new Set();

    document
        .querySelectorAll(
            "#failureTableBody tr"
        )
        .forEach(row => {

            envSet.add(
                row.cells[4].innerText.trim()
            );

            serverSet.add(
                row.cells[5].innerText.trim()
            );
        });

    const envDropdown =
        document.getElementById(
            "failureEnvironmentFilter"
        );

    const serverDropdown =
        document.getElementById(
            "failureServerFilter"
        );

    if(envDropdown){

        envDropdown.innerHTML =
            '<option value="All">All</option>';

        [...envSet]
            .sort()
            .forEach(env => {

                envDropdown.innerHTML +=
                    `<option value="${env}">
                        ${env}
                    </option>`;
            });
    }

    if(serverDropdown){

        serverDropdown.innerHTML =
            '<option value="All">All</option>';

        [...serverSet]
            .sort()
            .forEach(server => {

                serverDropdown.innerHTML +=
                    `<option value="${server}">
                        ${server}
                    </option>`;
            });
    }
}

async function loadSupportEmails() {

    try {

        updateProcessingStatus(
            "Support Emails",
            "Connecting to Outlook...",
            "processing"
        );

        const response =
            await fetch(
                "/api/operations-center/support-emails"
            );

        const result =
            await response.json();
        
        console.log("SUPPORT EMAIL SAMPLE:", result.data[0]);
        console.log("SUPPORT EMAIL COUNT:", result.data.length);

        if (!result.success) {

            updateStatus(
                result.message
            );

            return;
        }

        const tbody =
            document.getElementById(
                "supportTableBody"
            );

        if (!tbody) return;

        tbody.innerHTML = "";

        let pendingCount = 0;

        result.data.forEach(row => {

            if (
                row.category &&
                row.category.includes(
                    "Action Required"
                )
            ) {
                pendingCount++;
            }

            tbody.innerHTML += `

                <tr>

                    <td>${row.date_received || ""}</td>

                    <td>${row.name || ""}</td>

                    <td>${row.subject || ""}</td>

                    <td>${row.importance || ""}</td>

                    <td>${row.category || ""}</td>

                </tr>

            `;
        });

        const supportCard =
            document.getElementById(
                "supportCountCard"
            );

        if (supportCard) {

            supportCard.innerText =
                result.data.length;
        }

        const pendingCard =
            document.getElementById(
                "pendingActionCard"
            );

        if (pendingCard) {

            pendingCard.innerText =
                pendingCount;
        }

        updateProcessingStatus(
            "Completed",
            result.data.length +
            " support emails loaded",
            "completed"
        );

        window.supportData = result.data || [];
        
        console.log(
            "WINDOW SUPPORT DATA:",
            window.supportData
        );
        
        if (
            document
                .getElementById("supportSection")
                .style.display === "flex"
        ) {
            buildFilters("support");
            applyFilters();
        }
        updateKpis("support");
    }

    catch(error) {

        console.error(error);

        updateProcessingStatus(
            "Failed",
            "Support email load failed",
            "failed"
        );
    }
}

async function loadIntegrationFailures() {

    try {

        updateProcessingStatus(
            "Integration Failures",
            "Loading RAPID / ODC failures...",
            "processing"
        );

        const response =
            await fetch(
                "/api/operations-center/integration-failures"
            );

        const result =
            await response.json();

        if (!result.success) {

            updateProcessingStatus(
                "Failed",
                result.message ||
                "Unable to load failures",
                "failed"
            );
            
            return;
        }

        const tbody =
            document.getElementById(
                "failureTableBody"
            );

        if (!tbody) return;

        tbody.innerHTML = "";

        result.data.forEach(row => {

            tbody.innerHTML += `

                <tr>

                    <td>${row["Failure Time"] || ""}</td>

                    <td>${row["Integration"] || ""}</td>

                    <td>${row["Object Number"] || ""}</td>

                    <td>${row["Error Message"] || ""}</td>

                    <td>${row["Environment"] || ""}</td>

                    <td>${row["Windchill Server"] || ""}</td>

                </tr>

            `;

        });

        updateProcessingStatus(
            "Completed",
            result.data.length +
            " integration failures loaded",
            "completed"
        );


        populateFailureFiltersFromTable();

        if (
            document
                .getElementById("failureSection")
                .style.display === "flex"
        ) {
            buildFilters("failure");
            populateFailureFiltersFromTable();
            applyFilters();
        }
    }

    catch(error) {

        console.error(error);

        updateProcessingStatus(
            "Failed",
            "Integration failure load failed",
            "failed"
        );
    }
}