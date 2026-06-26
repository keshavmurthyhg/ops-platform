"""
search_help.py
==============
Provides the HELP_SECTIONS data structure consumed by the Search Module
help popup (rendered in search.html via Jinja or returned as JSON).

Each section has:
  id       - unique key used by JS to switch panels
  icon     - emoji shown in the left nav
  title    - displayed in nav list + panel heading
  content  - HTML string (safe subset: h3, p, ul, li, code, strong, em)
"""

HELP_SECTIONS = [

    {
        "id": "overview",
        "icon": "🔍",
        "title": "Search Module Overview",
        "content": """
<h3>What is the Search Module?</h3>
<p>The Search Module is a unified cross-source issue search tool that lets you
query tickets from <strong>ServiceNow (SNOW)</strong>, <strong>Azure DevOps (AZURE)</strong>,
and <strong>PTC Windchill (PTC)</strong> in a single view.</p>

<h3>Key Capabilities</h3>
<ul>
  <li>Search across up to three data sources simultaneously</li>
  <li>Choose <em>which fields</em> to search (Short Description, Description, Resolution Notes)</li>
  <li>Filter by Status, Priority, User Group, and Date</li>
  <li>Map users into custom groups for fast team-level filtering</li>
  <li>Paginate, resize columns, and download results as Excel</li>
  <li>View live KPI counts at the top of the results area</li>
</ul>

<h3>Data Flow</h3>
<p>Data is loaded from local CSV/XLSX files in the <code>data/</code> folder at startup.
The <em>Last Refreshed</em> timestamp at the bottom shows when the files were last read.
No live API calls are made during search — everything is queried in-memory for speed.</p>
"""
    },

    {
        "id": "data_sources",
        "icon": "📂",
        "title": "Data Source Files",
        "content": """
<h3>Supported Data Files</h3>
<ul>
  <li><code>data/Azure.csv</code> — Azure DevOps bug exports</li>
  <li><code>data/Snow.xlsx</code> — ServiceNow incident exports</li>
  <li><code>data/Ptc.csv</code> — PTC Windchill case exports</li>
  <li><code>data/user_group_mapping.csv</code> — User-to-group mapping (auto-generated)</li>
</ul>

<h3>Column Mapping</h3>
<ul>
  <li><strong>AZURE:</strong> ID → Number, Title → Description, State → Status,
      Release_Windchill → Priority</li>
  <li><strong>SNOW:</strong> Number → Number, Short Description → Description,
      Incident State → Status</li>
  <li><strong>PTC:</strong> Case Number → Number, Subject → Description,
      Severity → Priority</li>
</ul>

<h3>Updating Data</h3>
<p>Replace the files in the <code>data/</code> folder and restart the server.
The data is loaded fresh on each server start.
The <code>data/history/</code> folder is used by other modules to archive old exports.</p>
"""
    },

    {
        "id": "search",
        "icon": "🔎",
        "title": "Searching Issues",
        "content": """
<h3>Basic Search</h3>
<p>Type any keyword in the <strong>Search issue...</strong> box and press
<strong>Search</strong> or <kbd>Enter</kbd>. The search is case-insensitive
and checks for partial matches.</p>

<h3>Search In — Field Selection</h3>
<p>Use the <strong>Search In</strong> checkboxes (Source sidebar) to control
which fields are scanned:</p>
<ul>
  <li><strong>Short Description</strong> — The title/subject of the issue (default, fastest)</li>
  <li><strong>Description</strong> — Full body text of the issue</li>
  <li><strong>Resolution Notes</strong> — Close notes, resolution, or solution text</li>
</ul>
<p>You can select one, two, or all three simultaneously.</p>

<h3>Source Selection</h3>
<p>Use the <strong>ALL / AZURE / SNOW / PTC</strong> checkboxes to include or
exclude sources. Deselecting <em>ALL</em> unchecks all; checking it again
re-selects all three.</p>

<h3>What to Avoid</h3>
<ul>
  <li>Avoid very short keywords (1–2 chars) — they match too broadly</li>
  <li>Don't search on Description or Resolution Notes unless needed — it is slower</li>
  <li>Wildcards are not supported; the search is a plain substring match</li>
</ul>
"""
    },

    {
        "id": "filters",
        "icon": "🎯",
        "title": "Filtering Results",
        "content": """
<h3>Status Filter</h3>
<p>Select a specific ticket status from the dropdown (e.g. Open, Closed,
Cancelled). Leave blank to include all statuses.</p>

<h3>Priority Filter</h3>
<p>Filter to a single priority level (P1, P2, P3, etc.). Values are
normalised across all three sources into a common scale.</p>

<h3>Group Filter</h3>
<p>Filter results to only show tickets <em>assigned to</em> or <em>created by</em>
members of a specific user group. Groups are defined in the
<strong>User Group Mapping</strong> section.</p>

<h3>Apply Filters Button</h3>
<p>Click <strong>Apply Filters</strong> in the sidebar toolbar (or press the
Search button) to run the search with all active filter selections.</p>

<h3>Clear Workspace</h3>
<p>Resets the results table without clearing your filter selections.
Use this to start a fresh search without losing your sidebar configuration.</p>
"""
    },

    {
        "id": "date_filter",
        "icon": "📅",
        "title": "Date Filtering",
        "content": """
<h3>Date Field</h3>
<p>Choose whether to filter on <strong>Created Date</strong> or
<strong>Resolved Date</strong> using the first dropdown.</p>

<h3>Filter Modes</h3>
<ul>
  <li><strong>No Filter</strong> — All dates included (default)</li>
  <li><strong>Date Range</strong> — Pick a start and end date manually</li>
  <li><strong>By Year</strong> — Select a calendar year (2023–2026)</li>
  <li><strong>Quick Select</strong> — Last 7, 30, 90 days or last 1 year</li>
</ul>

<h3>Notes</h3>
<ul>
  <li>Date filters combine with keyword search and other filters (AND logic)</li>
  <li>Tickets with no date in the selected field are excluded when a date
      filter is active</li>
</ul>
"""
    },

    {
        "id": "user_groups",
        "icon": "👥",
        "title": "User Group Mapping",
        "content": """
<h3>What are User Groups?</h3>
<p>User Groups let you tag individual users (from all three data sources)
into named teams such as <em>L1</em>, <em>L2</em>, or <em>L3</em>.
Once defined, you can filter the entire results table to show only issues
handled by a specific group.</p>

<h3>Manage Group Tab</h3>
<ol>
  <li>Enter a <strong>Group Name</strong> (e.g. "L1", "Support Team")</li>
  <li>Use the <strong>Search User</strong> box to filter the All Users list</li>
  <li>Click a user to select them (highlighted blue); double-click to add instantly</li>
  <li>Click <strong>Add &gt;&gt;</strong> to move selected users to the Group Members panel</li>
  <li>Click <strong>Remove</strong> to take a member back out</li>
  <li>Click <strong>Apply</strong> to save without closing, or <strong>OK</strong> to save and close</li>
</ol>

<h3>Refresh Users Tab</h3>
<p>Scans <code>Azure.csv</code>, <code>Snow.xlsx</code>, and <code>Ptc.csv</code>
to collect every unique user name. Email addresses, system account IDs, and
queue/group names are automatically filtered out. The result is saved to
<code>data/user_group_mapping.csv</code> (existing group assignments preserved).</p>

<h3>Existing Groups Tab (Modal)</h3>
<p>Shows all currently defined groups as cards. Click <strong>✏ Edit</strong>
to load a group back into the Manage Group tab for editing.</p>

<h3>Sidebar — Group Buttons</h3>
<p>In the sidebar, each group appears as its own button. Click a group button
to expand and see its members inline. Click again to collapse. This lets you
quickly verify group membership without opening the modal.</p>

<h3>What to Avoid</h3>
<ul>
  <li>Do not manually edit <code>user_group_mapping.csv</code> while the
      server is running — it may be overwritten on the next Refresh</li>
  <li>Group names are case-sensitive — "L1" and "l1" are treated as different groups</li>
</ul>
"""
    },

    {
        "id": "kpi",
        "icon": "📊",
        "title": "KPI Bar",
        "content": """
<h3>Where is the KPI Bar?</h3>
<p>The KPI bar sits at the <strong>top of the main content area</strong>,
above the results table. It shows four counters loaded from the full dataset
at page startup (not affected by active search filters):</p>
<ul>
  <li><strong>Total</strong> — All records across all three sources</li>
  <li><strong>Open</strong> — Tickets with an open/active status</li>
  <li><strong>Closed</strong> — Tickets marked closed or resolved</li>
  <li><strong>Cancelled</strong> — Tickets that were cancelled</li>
</ul>

<h3>Note</h3>
<p>KPI values reflect the full dataset loaded at startup, not the currently
filtered/searched subset. The result count just below the KPI bar shows
the filtered count.</p>
"""
    },

    {
        "id": "results_table",
        "icon": "📋",
        "title": "Results Table",
        "content": """
<h3>Columns</h3>
<ul>
  <li><strong>SL No</strong> — Sequential row number (1-based within the current page)</li>
  <li><strong>Number</strong> — Ticket ID (clickable link to the source system)</li>
  <li><strong>Description</strong> — Short description / title (truncated to 45 chars;
      hover to see full text)</li>
  <li><strong>Priority</strong> — Normalised priority level</li>
  <li><strong>Status</strong> — Current ticket status</li>
  <li><strong>Created By</strong> — Who raised the ticket</li>
  <li><strong>Created Date</strong> — Ticket creation date</li>
  <li><strong>Assigned To</strong> — Current assignee</li>
  <li><strong>Resolved Date</strong> — When the ticket was closed/resolved</li>
</ul>

<h3>Column Resizing</h3>
<p>Drag the resize handle (right edge of each column header) to widen or
narrow columns. Widths are saved to <code>localStorage</code> and restored
on next visit.</p>

<h3>Pagination</h3>
<p>Use the rows-per-page selector (<strong>10 / 25 / 50 / 100</strong>) and
the navigation arrows (<strong>« ‹ › »</strong>) directly above the table.
The current range is shown as <em>X to Y of Z</em>.</p>
"""
    },

    {
        "id": "download",
        "icon": "⬇️",
        "title": "Exporting Data",
        "content": """
<h3>Download Button</h3>
<p>Click <strong>Download</strong> in the toolbar to export all currently
filtered results (not just the visible page) to an Excel file.</p>

<h3>File Name</h3>
<p>The file is automatically named <code>Case_Report_DDMMMYYYY.xlsx</code>
using today's date, e.g. <code>Case_Report_21JUN2026.xlsx</code>.</p>

<h3>Exported Columns</h3>
<p>Number, Description, Priority, Status, Created By, Created Date,
Assigned To, Resolved Date, Source.</p>

<h3>What to Avoid</h3>
<ul>
  <li>If no search has been run, the download button will show an alert
      ("No results available")</li>
  <li>Very large result sets (&gt; 10,000 rows) may take a few seconds to
      generate — this is normal</li>
</ul>
"""
    },

    {
        "id": "logging",
        "icon": "📝",
        "title": "Activity Logs",
        "content": """
<h3>Log File Location</h3>
<p>The Search Module writes activity logs to:</p>
<p><code>ops-platform/logs/search.log</code></p>

<h3>What is Logged</h3>
<ul>
  <li>Server startup and data load events</li>
  <li>Every search query (keyword, filters, result count)</li>
  <li>User group save and refresh operations</li>
  <li>Errors and exceptions with full tracebacks</li>
  <li>Filter option loads and page renders</li>
</ul>

<h3>Log Rotation</h3>
<p>Logs rotate at <strong>5 MB</strong> and keep <strong>7 backups</strong>
(<code>search.log.1</code> … <code>search.log.7</code>). Old logs are
automatically deleted beyond the 7th backup.</p>

<h3>Log Format</h3>
<p><code>YYYY-MM-DD HH:MM:SS [LEVEL] search — message</code></p>
"""
    },

    {
        "id": "structure",
        "icon": "🗂️",
        "title": "Module Structure",
        "content": """
<h3>File Layout</h3>
<ul>
  <li><code>search/app.py</code> — Standalone Flask app entry point</li>
  <li><code>search/search_routes.py</code> — All API routes and blueprint</li>
  <li><code>search/templates/search.html</code> — Main Jinja2 template</li>
  <li><code>search/statics/search.js</code> — All frontend logic</li>
  <li><code>search/statics/search.css</code> — All module styles</li>
  <li><code>search/module/data_loader.py</code> — CSV/XLSX loading + normalisation</li>
  <li><code>search/module/search.py</code> — Keyword search with field selection</li>
  <li><code>search/module/filters.py</code> — Status / priority filter helpers</li>
  <li><code>search/module/kpi.py</code> — KPI calculation</li>
  <li><code>search/module/user_group.py</code> — Group mapping helpers</li>
  <li><code>search/module/logger.py</code> — Shared rotating file logger</li>
  <li><code>search/module/search_help.py</code> — This help content</li>
</ul>

<h3>API Routes</h3>
<ul>
  <li><code>GET  /search</code> — Main page</li>
  <li><code>GET  /search/filter-options</code> — Status, priority, group dropdowns</li>
  <li><code>POST /search/issues</code> — Run a search with filters</li>
  <li><code>POST /search/save-group</code> — Save a user group</li>
  <li><code>POST /search/collect-users</code> — Refresh users from data files</li>
  <li><code>GET  /search/group-members</code> — All groups and their members</li>
  <li><code>GET  /search/group-users</code> — All users from mapping CSV</li>
  <li><code>GET  /search/help-data</code> — Help guide sections (JSON)</li>
</ul>
"""
    },

    {
        "id": "tips",
        "icon": "💡",
        "title": "Tips & Best Practices",
        "content": """
<h3>Performance Tips</h3>
<ul>
  <li>Search <strong>Short Description only</strong> for fastest results</li>
  <li>Add a <strong>Status</strong> or <strong>Priority</strong> filter before
      searching to narrow the dataset first</li>
  <li>Use the <strong>Group filter</strong> to focus on your team's tickets</li>
  <li>Use <strong>Date Range</strong> to limit results to a relevant time window</li>
</ul>

<h3>Group Mapping Best Practices</h3>
<ul>
  <li>Run <strong>Refresh Users</strong> whenever new data files are loaded
      so new engineers appear in the user list</li>
  <li>Use short, consistent group names: <em>L1</em>, <em>L2</em>, <em>L3</em></li>
  <li>Click <strong>Apply</strong> (not OK) when editing a group to keep the
      modal open and continue adding members</li>
</ul>

<h3>Common Issues</h3>
<ul>
  <li><strong>"0 Results" after search</strong> — Check that the correct
      sources are checked and the status/priority filter is not too restrictive</li>
  <li><strong>Users missing from group mapping</strong> — Click Refresh Users
      in the modal to re-scan the data files</li>
  <li><strong>New route returns 404</strong> — Restart the server after
      replacing files; Python caches old bytecode</li>
  <li><strong>Date filter returns nothing</strong> — The selected date column
      may be empty for many tickets; try switching Created/Resolved</li>
</ul>
"""
    },
]
