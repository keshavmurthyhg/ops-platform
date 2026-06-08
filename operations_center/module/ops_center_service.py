from operations_center.module.ops_center_data_loader import (
    load_support_mails,
    load_integration_failures,
)

from operations_center.module.ops_center_incident_engine import (
    detect_critical_failures
)

from operations_center.module.ops_center_incident_loader import (
    load_incident_tracker
)

from operations_center.module.ops_center_azure_loader import (
    load_azure_tracker
)

from operations_center.module.ops_center_ptc_loader import (
    load_ptc_tracker
)

def get_operations_dashboard_data():

    # ---------------------------------
    # LOAD DATA
    # ---------------------------------

    support_data = load_support_mails()

    failure_data = load_integration_failures()

    incident_data = (
        load_incident_tracker()
    )

    # ---------------------------------
    # PENDING ACTIONS
    # ---------------------------------

    pending_actions = len([

        row for row in support_data

        if "Action Required"
        in str(
            row.get(
                "Categories",
                ""
            )
        )

    ])

    # ---------------------------------
    # CRITICAL SERVER DETECTION
    # ---------------------------------

    critical_servers = (
        detect_critical_failures(
            failure_data
        )
    )

    # ---------------------------------
    # ADDITIONAL TRACKERS
    # ---------------------------------

    azure_data = load_azure_tracker()

    ptc_data = load_ptc_tracker()

    # ---------------------------------
    # SUMMARY
    # ---------------------------------

    summary = {

        "support_count": len(
            support_data
        ),

        "failure_count": len(
            failure_data
        ),

        "pending_actions":
            pending_actions,

        "critical_servers": len(
            critical_servers
        ),

        "active_incidents": len(
            incident_data
        ),

        "azure_count": len(
            azure_data
        ),

        "ptc_count": len(
            ptc_data
        )
    }

    # ---------------------------------
    # FINAL RESPONSE
    # ---------------------------------

    return {

        "support_data": support_data,

        "failure_data": failure_data,

        "incident_data": incident_data,

        "azure_data": azure_data,
        
        "ptc_data": ptc_data,
        
        "summary": summary

    }