// =============================================================================
//  OPS CENTER — EXCEL / POWER QUERY REFRESH
//  ops_power_query.js
//
//  Handles triggering Power Query refresh on the operations_tracker.xlsx file.
//  Requires the Flask route: POST /api/operations-center/refresh-power-query
//
//  Included by operations_center.html AFTER operations_center.js
// =============================================================================

async function refreshPowerQuery() {
    updateProcessingStatus("Excel Refresh", "Triggering Power Query refresh...", "processing");
    try {
        const resp = await fetch("/api/operations-center/refresh-power-query");
        const data = await resp.json();
        if (data.success) {
            updateProcessingStatus("Excel Refresh", "Power Query refresh complete", "completed");
        } else {
            updateProcessingStatus("Excel Refresh Failed", data.message || "Unknown error", "failed");
        }
    } catch (err) {
        updateProcessingStatus("Excel Refresh Failed", String(err), "failed");
    }
}
