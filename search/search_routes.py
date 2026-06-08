import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify
)

from search.module.data_loader import load_data
from search.module.kpi import calculate_kpi
from search.module.search import apply_search
from common.utils.parsers import (
    format_display_date
)
from common.utils.links import (
    get_url
)

from common.utils.user_group import (
    save_user_group,
    filter_dataframe_by_group
)

from search.module.data_loader import (
    load_group_filters,
    load_group_users
)



# -----------------------------------
# Blueprint
# -----------------------------------
search_bp = Blueprint(
    "search",
    __name__
)


# -----------------------------------
# Search Page
# -----------------------------------
@search_bp.route("/search")
def search_page():
    try:
        df, last_refresh = load_data()
        kpi = calculate_kpi(df)

        return render_template(
            "search.html",
            last_refresh=last_refresh,
            kpi=kpi
        )

    except Exception as e:
        return str(e)


# -----------------------------------
# Filter Options API
# -----------------------------------
@search_bp.route("/search/filter-options")
def search_filter_options():

    try:

        df, _ = load_data()

        status = sorted(
            df["Status"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        priority = sorted(
            df["Priority"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        groups = load_group_filters()

        return jsonify({
            "status": status,
            "priority": priority,
            "groups": groups
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

# -----------------------------------
# SAVE USER GROUP
# -----------------------------------
@search_bp.route(
    "/search/save-group",
    methods=["POST"]
)
def save_group():

    try:

        data = request.json

        group_name = data.get(
            "group_name",
            ""
        ).strip()

        users = data.get(
            "users",
            []
        )

        if not group_name:

            return jsonify({
                "success": False,
                "message": "Group name required"
            })

        save_user_group(
            group_name,
            users
        )

        return jsonify({
            "success": True
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


# -----------------------------------
# Search Issues API
# -----------------------------------
@search_bp.route(
    "/search/issues",
    methods=["POST"]
)
def search_issues():
    try:

        data = request.json

        query = data.get(
            "query",
            ""
        )

        sources = data.get(
            "sources",
            []
        )

        status = data.get(
            "status",
            ""
        )

        priority = data.get(
            "priority",
            ""
        )

        group = data.get(
            "group",
            ""
        )

        date_field = data.get(
            "date_field",
            "created"
        )

        start_date = data.get(
            "start_date",
            ""
        )

        end_date = data.get(
            "end_date",
            ""
        )

        df, _ = load_data()

        # -----------------------------------
        # SOURCE FILTER
        # -----------------------------------
        if sources:
            df = df[
                df["Source"].isin(sources)
            ]

        # -----------------------------------
        # STATUS FILTER
        # -----------------------------------
        if status:
            df = df[
                df["Status"].astype(str) == status
            ]


        # -----------------------------------
        # PRIORITY FILTER
        # -----------------------------------
        if priority:
            df = df[
                df["Priority"].astype(str) == priority
            ]


        # -----------------------------------
        # GROUP FILTER
        # -----------------------------------
        if group:

            from common.utils.user_group import (
                build_group_mapping
            )

            mapping_df = build_group_mapping(df)

            df = filter_dataframe_by_group(
                df,
                mapping_df,
                [group]
            )

        # -----------------------------------
        # DATE FIELD
        # -----------------------------------
        date_column = (
            "Created Date"
            if date_field == "created"
            else "Resolved Date"
        )


        # -----------------------------------
        # DATE RANGE FILTER
        # -----------------------------------

        if start_date:

            start_date = pd.to_datetime(start_date)

            df = df[
                df[date_column] >= start_date
            ]


        if end_date:

            end_date = pd.to_datetime(end_date)

            df = df[
                df[date_column] <= end_date
            ]

        # -----------------------------------
        # SEARCH
        # -----------------------------------
        filtered = apply_search(
            df,
            query
        )

        filtered = filtered.fillna("")

        results = []

        for _, row in filtered.iterrows():

            source = row.get(
                "Source",
                ""
            )

            number = str(
                row.get(
                    "Number",
                    ""
                )
            )

            # -----------------------------
            # external links
            # -----------------------------
            if source == "SNOW":
                url = get_url("incident", number)

            elif source == "PTC":
                url = get_url("ptc case", number)

            elif source == "AZURE":
                url = get_url("azure bug", number)

            else:
                url = ""

            results.append({
                "number": number,
                "description": row.get(
                    "Description",
                    ""
                ),
                "priority": row.get(
                    "Priority",
                    ""
                ),
                "status": row.get(
                    "Status",
                    ""
                ),
                "created_by": row.get(
                    "Created By",
                    ""
                ),
                "created_date": format_display_date(
                    row.get("Created Date")
                ),
                "assigned_to": row.get(
                    "Assigned To",
                    ""
                ),
                "resolved_date": format_display_date(
                    row.get("Resolved Date")
                ),
                "source": source,
                "url": url
            })

        return jsonify({
            "results": results
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })


@search_bp.route("/search/group-members")
def get_group_members():

    try:

        from common.utils.user_group import (
            load_group_mapping
        )

        mapping = load_group_mapping()

        grouped = {}

        for group_name, group_df in mapping.groupby("Group"):

            grouped[group_name] = sorted(
                group_df["Name"]
                .dropna()
                .astype(str)
                .tolist()
            )

        return jsonify({
            "groups": grouped
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

@search_bp.route("/search/group-users")
def get_group_users():

    try:

        users = load_group_users()

        return jsonify({
            "users": users
        })

    except Exception as e:

        return jsonify({
            "users": [],
            "error": str(e)
        }), 500