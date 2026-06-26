"""
search_help.py
==============
Help guide sections for the Search Module help popup.
"""

HELP_SECTIONS = [

    {
        "id": "overview",
        "icon": "🔍",
        "title": "Search Module Overview",
        "content": """
<h3>What is the Search Module?</h3>
<p>A unified cross-source issue search tool that queries tickets from
<strong>ServiceNow (SNOW)</strong>, <strong>Azure DevOps Bugs (AZURE)</strong>,
<strong>PTC Windchill (PTC)</strong>, and <strong>AOM User Stories (AOM)</strong>
in a single view.</p>

<h3>Key Capabilities</h3>
<ul>
  <li>Search across four data sources simultaneously</li>
  <li>Vendor Ticket, Azure Bug, Azure User Story, and PTC Article link columns — all clickable</li>
  <li>Azure User Story environment badges (PROD / QA / TEST / UAT / DEV / WC13) sourced from AOM data</li>
  <li>Filter by Status, Priority, User Group, and Date</li>
  <li>Sort any column by clicking its header; or set a default sort in Preferences</li>
  <li>Toggle column visibility and row source colouring in ⚙ Preferences</li>
  <li>Download results as a formatted, colour-coded Excel file</li>
</ul>

<h3>Data Flow</h3>
<p>Data is loaded from local CSV/XLSX files in the <code>data/</code> folder at server startup.
No live API calls are made during search — all querying is in-memory for speed.
The <em>Last Refreshed</em> timestamp at the bottom confirms when data was loaded.</p>
"""
    },

    {
        "id": "data_sources",
        "icon": "📂",
        "title": "Data Source Files",
        "content": """
<h3>Supported Data Files</h3>
<ul>
  <li><code>data/Azure.csv</code> — Azure DevOps bug/work-item exports</li>
  <li><code>data/Snow.xlsx</code> — ServiceNow incident exports (must include Work Notes + Additional Comments columns for link extraction)</li>
  <li><code>data/Ptc.csv</code> — PTC Windchill case exports</li>
  <li><code>data/AOM_user_stories.csv</code> — AOM user stories; used as a fourth search source and as the environment lookup for Azure User Story badges</li>
  <li><code>data/user_group_mapping.csv</code> — User-to-group mapping (auto-generated)</li>
</ul>

<h3>Column Mapping</h3>
<ul>
  <li><strong>AZURE:</strong> ID → Number, Title → Description, State → Status, Release_Windchill → Priority</li>
  <li><strong>SNOW:</strong> Number → Number, Short Description → Description, Incident State → Status</li>
  <li><strong>PTC:</strong> Case Number → Number, Subject → Description, Severity → Priority</li>
  <li><strong>AOM:</strong> ID → Number, Title → Description, State → Status; links to VPA Azure DevOps</li>
</ul>

<h3>Link Extraction from SNOW Notes</h3>
<p>The loader scans <em>Work Notes</em>, <em>Additional Comments</em>, and <em>Resolution Notes</em>
columns of Snow.xlsx to populate the extra link columns:</p>
<ul>
  <li><strong>Vendor Ticket</strong> → <code>u_vendor_reference</code> field (PTC case link)</li>
  <li><strong>Azure Bug</strong> → VCEWindchillPLM DevOps URLs in Resolution Notes only</li>
  <li><strong>Azure User Story</strong> → VPA DevOps URLs in Work Notes + Additional Comments</li>
  <li><strong>PTC Articles</strong> → ptc.com/en/support/article/ URLs in Work Notes + Additional Comments</li>
</ul>

<h3>Updating Data</h3>
<p>Replace files in <code>data/</code> and restart the server (or wait for the next scheduled
data reload). The AOM cache resets on every reload so a refreshed AOM file is always picked up.</p>
"""
    },

    {
        "id": "search",
        "icon": "🔎",
        "title": "Searching Issues",
        "content": """
<h3>Basic Search</h3>
<p>Type any keyword in the <strong>Search issue...</strong> box and press
<strong>Search</strong> or <kbd>Enter</kbd>. Matching is case-insensitive substring.</p>

<h3>Search In — Field Selection</h3>
<ul>
  <li><strong>Short Description</strong> — Title/subject (default, fastest)</li>
  <li><strong>Description</strong> — Full body text</li>
  <li><strong>Resolution Notes</strong> — Close notes / solution text</li>
</ul>

<h3>Source Selection</h3>
<p>Use <strong>ALL / AZURE / SNOW / PTC / AOM</strong> checkboxes to include or exclude sources.
AOM user stories link to VPA Azure DevOps and are tagged with their environment.</p>

<h3>What to Avoid</h3>
<ul>
  <li>Very short keywords (1–2 chars) match too broadly</li>
  <li>Avoid Description + Resolution Notes unless necessary — slower on large datasets</li>
  <li>Wildcards are not supported; plain substring only</li>
</ul>
"""
    },

    {
        "id": "filters",
        "icon": "🎯",
        "title": "Filtering Results",
        "content": """
<h3>Status Filter</h3>
<p>Select a specific ticket status from the dropdown. Leave blank to include all statuses.</p>

<h3>Priority Filter</h3>
<p>Filter to a single priority level. Values are normalised across all sources into a common scale.</p>

<h3>Group Filter</h3>
<p>Filter results to show only tickets assigned to or created by members of a specific user group.</p>

<h3>Apply Filters / Clear Workspace</h3>
<p><strong>Apply Filters</strong> runs the search with all active selections.
<strong>Clear Workspace</strong> resets the results table without clearing filter selections.</p>
"""
    },

    {
        "id": "date_filter",
        "icon": "📅",
        "title": "Date Filtering",
        "content": """
<h3>Date Field</h3>
<p>Choose <strong>Created Date</strong> or <strong>Resolved Date</strong> from the first dropdown.</p>

<h3>Filter Modes</h3>
<ul>
  <li><strong>No Filter</strong> — All dates included (default)</li>
  <li><strong>Date Range</strong> — Pick start and end dates manually</li>
  <li><strong>By Year</strong> — Select a calendar year (2020–2026)</li>
  <li><strong>Quick Select</strong> — Last 7, 30, 90 days or last 1 year</li>
</ul>

<h3>Notes</h3>
<ul>
  <li>Date filters combine with keyword search and other filters (AND logic)</li>
  <li>Tickets with no value in the selected date column are excluded when a filter is active</li>
</ul>
"""
    },

    {
        "id": "link_columns",
        "icon": "🔗",
        "title": "Link Columns",
        "content": """
<h3>Vendor Ticket</h3>
<p>Shows the PTC support case number from the SNOW <em>u_vendor_reference</em> field.
Click the amber badge to open the PTC case directly in <code>support.ptc.com</code>.
C-prefixed values (e.g. C18028229) strip the prefix before building the URL.</p>

<h3>Azure Bug</h3>
<p>Azure DevOps VCEWindchillPLM work item IDs parsed from <strong>Resolution Notes only</strong>.
Click the blue chip to open the bug in Azure DevOps.</p>

<h3>Azure User Story</h3>
<p>VPA project user story IDs parsed from <strong>Work Notes and Additional Comments</strong>.
Each ID appears as an indigo chip. Next to it is a colour-coded environment badge:</p>
<ul>
  <li><span style="background:#16a34a;color:#fff;padding:1px 6px;border-radius:8px;font-size:11px">PROD</span> — Production</li>
  <li><span style="background:#d97706;color:#fff;padding:1px 6px;border-radius:8px;font-size:11px">QA</span> — QA environment</li>
  <li><span style="background:#0891b2;color:#fff;padding:1px 6px;border-radius:8px;font-size:11px">TEST</span> — Test environment</li>
  <li><span style="background:#7c3aed;color:#fff;padding:1px 6px;border-radius:8px;font-size:11px">UAT</span> — User acceptance testing</li>
  <li><span style="background:#64748b;color:#fff;padding:1px 6px;border-radius:8px;font-size:11px">DEV</span> — Development / devA</li>
  <li><span style="background:#0f766e;color:#fff;padding:1px 6px;border-radius:8px;font-size:11px">WC13</span> — WC13 server</li>
</ul>
<p>The badge environment is sourced from <code>AOM_user_stories.csv</code> — first from the
<strong>Title</strong> suffix (e.g. <em>"Install GhostScript - PROD"</em>), then from the
<strong>Tags</strong> column if the title yields nothing, then from the surrounding note text as a final fallback.</p>

<h3>PTC Articles</h3>
<p>PTC knowledge article IDs (e.g. CS98274) parsed from Work Notes and Additional Comments.
Click the purple chip to open the article on <code>ptc.com/en/support/article/</code>.</p>
"""
    },

    {
        "id": "sorting",
        "icon": "↕️",
        "title": "Sorting",
        "content": """
<h3>Column Header Sorting</h3>
<p>Click any column header marked with <strong>↕</strong> to sort the results by that column.
Click again to reverse direction. The active sort column header turns blue.</p>
<p>Sortable columns: <strong>Number</strong>, <strong>Description</strong>,
<strong>Priority</strong>, <strong>Status</strong>, <strong>Created Date</strong>,
<strong>Resolved Date</strong>.</p>
<ul>
  <li>Number is sorted numerically (not lexicographically), so INC110461348 comes after INC110283967</li>
  <li>Dates are sorted as true dates, not strings</li>
  <li>Column sorts are independent — each click sorts the full result set fresh</li>
</ul>

<h3>Sort Preference (⚙ Preferences)</h3>
<p>Open the <strong>⚙ Settings</strong> dock and choose a <em>Default Sort</em> field
and direction, then click either dropdown to apply. This is a one-time manual action —
it does <strong>not</strong> auto-sort every new search result, so your column-click
sorts always take precedence.</p>

<h3>Default Behaviour</h3>
<p>Results arrive in the server's natural order (newest number first as returned by the search).
No automatic sort is applied until you click a column header or use the Preferences sort.</p>
"""
    },

    {
        "id": "preferences",
        "icon": "⚙️",
        "title": "Preferences (Settings)",
        "content": """
<h3>Opening Preferences</h3>
<p>Click the <strong>⚙</strong> dock icon on the left sidebar to open the Preferences panel.</p>

<h3>Visible Columns</h3>
<p>Toggle individual columns on or off. Hidden columns are excluded from the table view
but are still present in downloaded Excel files.</p>
<p>Toggle-able columns: Vendor Ticket, Azure Bug, Azure User Story, PTC Articles, Created By, Resolved Date.</p>

<h3>Row Highlight</h3>
<p>Enable or disable colour-coded row backgrounds by data source:</p>
<ul>
  <li>SNOW rows — light blue</li>
  <li>AZURE rows — light purple</li>
  <li>PTC rows — light yellow</li>
  <li>AOM rows — light green</li>
</ul>

<h3>Default Sort</h3>
<p>Set the sort field (Number, Created Date, Priority, Status) and direction
(Newest→Oldest or Oldest→Newest). Applied immediately and for all subsequent result loads.</p>
"""
    },

    {
        "id": "user_groups",
        "icon": "👥",
        "title": "User Group Mapping",
        "content": """
<h3>What are User Groups?</h3>
<p>Tag individual users into named teams (e.g. L1, L2, L3). Filter the results
table to show only issues handled by a specific group.</p>

<h3>Manage Group Tab</h3>
<ol>
  <li>Enter a <strong>Group Name</strong></li>
  <li>Search and select users from the All Users list</li>
  <li>Click <strong>Add &gt;&gt;</strong> to move them to Group Members</li>
  <li>Click <strong>Apply</strong> to save or <strong>OK</strong> to save and close</li>
</ol>

<h3>Refresh Users Tab</h3>
<p>Scans all data files to collect unique user names and saves to
<code>data/user_group_mapping.csv</code>. Run after loading new data files.</p>
"""
    },

    {
        "id": "kpi",
        "icon": "📊",
        "title": "KPI Bar",
        "content": """
<h3>Where is the KPI Bar?</h3>
<p>The KPI bar sits at the top of the main content area above the results table.
It shows four counters from the full dataset at startup:</p>
<ul>
  <li><strong>Total</strong> — All records across all sources</li>
  <li><strong>Open</strong> — Tickets with an open/active status</li>
  <li><strong>Closed</strong> — Tickets marked closed or resolved</li>
  <li><strong>Cancelled</strong> — Cancelled tickets</li>
</ul>
<p>KPI values reflect the full dataset, not the current search subset.</p>
"""
    },

    {
        "id": "results_table",
        "icon": "📋",
        "title": "Results Table",
        "content": """
<h3>Columns</h3>
<ul>
  <li><strong>SL No</strong> — Row number within current page</li>
  <li><strong>Number</strong> — Ticket ID, clickable link (colour-coded by source)</li>
  <li><strong>Description</strong> — Short description (truncated; hover for full text)</li>
  <li><strong>Vendor Ticket</strong> — PTC support case (SNOW only, amber badge, clickable)</li>
  <li><strong>Azure Bug</strong> — VCEWindchill bug IDs from Resolution Notes (blue chip)</li>
  <li><strong>Azure User Story</strong> — VPA user story IDs + environment badge (indigo chip)</li>
  <li><strong>PTC Articles</strong> — Knowledge article IDs from notes (purple chip)</li>
  <li><strong>Priority</strong></li>
  <li><strong>Status</strong> — colour-coded pill with a dot indicator (amber=Open, blue=In Progress, pink=On Hold, green=Closed/Resolved, grey=Cancelled, purple=New)</li>
  <li><strong>Number</strong> column also shows a matching dot beside the ticket link</li>
  <li><strong>Created By</strong>, <strong>Created Date</strong>, <strong>Assigned To</strong>, <strong>Resolved Date</strong></li>
</ul>

<h3>Multi-value link columns</h3>
<p>When a SNOW ticket has multiple Vendor Tickets, Azure Bugs, User Stories or PTC Articles,
each gets its own separate sub-column (Vendor Ticket 1, Vendor Ticket 2, etc.) in the Excel download.
In the table view they appear as individual clickable chips in the same cell.</p>

<h3>Column Resizing</h3>
<p>Drag the resize handle on any column header right edge to adjust width.</p>

<h3>Pagination</h3>
<p>Use the rows-per-page selector (10 / 25 / 50 / 100) and navigation arrows above the table.</p>
"""
    },

    {
        "id": "download",
        "icon": "⬇️",
        "title": "Exporting Data",
        "content": """
<h3>Download Button</h3>
<p>Click <strong>Download</strong> in the toolbar to export all currently filtered results
(not just the visible page) to a fully-formatted Excel workbook.
The download is built <strong>server-side using openpyxl</strong> for reliable,
full-fidelity formatting.</p>

<h3>File Name</h3>
<p>Files are automatically named in lowercase: <code>search-report_ddmmmyyyy_hhmm.xlsx</code>,
e.g. <code>search-report_25jun2026_1430.xlsx</code>.</p>

<h3>Search Results Sheet</h3>
<ul>
  <li>Results are exported in the order they are currently sorted in the table</li>
  <li>Single header row with merged group labels (Vendor Ticket, Azure Bug, Azure User Story, PTC Article spans their sub-columns)</li>
  <li>Dark navy header row with white bold Calibri text</li>
  <li><strong>Status column</strong> — each cell is filled with the status colour (amber=Open, blue=In Progress, pink=On Hold, green=Closed/Resolved, grey=Cancelled, purple=New) and font colour matches</li>
  <li>Alternating white / light-grey rows for readability</li>
  <li><strong>First row frozen</strong> — header stays visible when scrolling</li>
  <li><strong>Auto-filter</strong> enabled on all columns</li>
  <li>Optimised column widths; Description column wraps text</li>
  <li>No coloured dots or emoji in the file — plain text only</li>
</ul>

<h3>Dashboard Sheet</h3>
<ul>
  <li><strong>KPI cards</strong> — Total, Open, Closed, Cancelled (coloured tiles)</li>
  <li><strong>Source breakdown</strong> — SNOW / AZURE / PTC / AOM row counts</li>
  <li><strong>Monthly Pivot</strong> — created date count per month × year</li>
  <li><strong>Bar chart</strong> — monthly issue count by year from the pivot data</li>
</ul>

<h3>Exported Columns</h3>
<p>Number, Description, Vendor Ticket, Azure Bug, Azure User Story (ID + env in brackets),
PTC Articles, Priority, Status, Created By, Created Date, Assigned To, Resolved Date, Source.</p>

<h3>What to Avoid</h3>
<ul>
  <li>If no search has been run, the download button will show an alert</li>
  <li>Very large result sets (&gt; 10,000 rows) may take a few seconds — the button shows <em>Building…</em> while the server processes</li>
</ul>
"""
    },

    {
        "id": "logging",
        "icon": "📝",
        "title": "Reading the Logs",
        "content": """
<h3>Log File Location</h3>
<p><code>ops-platform/logs/search.log</code></p>

<h3>What is Logged</h3>
<ul>
  <li>Server startup and data load events (rows per source)</li>
  <li>AOM map loaded — entry count</li>
  <li>Every search query with keyword, sources, fields, result count, and per-source breakdown</li>
  <li>User group save and refresh operations</li>
  <li>Errors and exceptions with full tracebacks</li>
</ul>

<h3>Log Examples</h3>
<pre style="background:#1e293b;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto">
Data loaded — 9303 records | KPI total=9303
Loaded Azure.csv — 1656 rows
Loaded Snow.xlsx — 2000 rows
Loaded Ptc.csv — 5647 rows
Loaded data/AOM_user_stories.csv — 847 rows
Search — query='color' sources=['SNOW'] fields=['description']
  results=1 breakdown={'SNOW': 1}
Download requested — 2000 rows
Download ready — search-report_25jun2026_1430.xlsx (2000 rows)
Saving group 'L2' with 8 members
</pre>

<h3>Log Rotation</h3>
<p>Logs rotate at <strong>5 MB</strong> and keep <strong>7 backups</strong>
(<code>search.log.1</code> … <code>search.log.7</code>).</p>

<h3>Log Format</h3>
<p><code>YYYY-MM-DD HH:MM:SS [LEVEL] search — message</code></p>
"""
    },

    {
        "id": "troubleshooting",
        "icon": "🔧",
        "title": "Troubleshooting",
        "content": """
<p style="color:#ef4444;font-weight:600">❌ Azure User Story badge shows wrong environment</p>
<p>Environment comes from <code>AOM_user_stories.csv</code> — first the <strong>Title</strong>
suffix (e.g. "- PROD"), then the <strong>Tags</strong> column, then surrounding note text.
If the badge is wrong, check the Title and Tags columns in the AOM file for that story ID.
Update the AOM file and restart the server (or wait for the next data reload).</p>

<p style="color:#ef4444;font-weight:600">❌ Vendor Ticket not linking correctly</p>
<p>Vendor tickets are PTC support case numbers. The URL uses the numeric part only
(C-prefix is stripped). Confirm the <em>u_vendor_reference</em> column exists in Snow.xlsx.
Check logs for <em>Loaded Snow.xlsx</em> row count — if 0, the file may be corrupt or empty.</p>

<p style="color:#ef4444;font-weight:600">❌ Azure Bug / User Story columns empty</p>
<p>These are parsed from Work Notes and Additional Comments columns in Snow.xlsx.
Confirm those columns are included in the Snow export. Search for VPA or VCEWindchillPLM
URLs in the raw data to verify they are present.</p>

<p style="color:#ef4444;font-weight:600">❌ AOM source showing 0 results</p>
<p>Check that <code>data/AOM_user_stories.csv</code> exists and is not empty.
In logs, look for <em>Loaded data/AOM_user_stories.csv</em>. If it says
<em>AOM load skipped</em>, the file is missing or unreadable.</p>

<p style="color:#ef4444;font-weight:600">❌ Year filter missing older years</p>
<p>The By Year dropdown now covers 2020–2026. If your data has tickets older than 2020,
use <strong>Date Range</strong> mode instead and set the start date manually.</p>

<p style="color:#ef4444;font-weight:600">❌ Download file not colour-coded</p>
<p>Excel cell styles require SheetJS Pro (xlsx-js-style). If using the standard
SheetJS CDN, styles will silently be ignored and the file will still download correctly
but without colours. Check the browser console for any XLSX errors.</p>

<p style="color:#ef4444;font-weight:600">❌ Sort not working after search</p>
<p>No automatic sort is applied after search — click a column header (marked ↕) to sort.
First click = ascending, second click = descending. The Preferences sort is a one-time
manual action, not an automatic default. If sorting by Number, the sort is numeric
(INC110461348 &gt; INC110283967), not alphabetic.</p>

<p style="color:#ef4444;font-weight:600">❌ 0 Results after search</p>
<p>Check: correct sources checked? Status/Priority filter not too restrictive?
Open the browser console — if there is a JS error, it will appear there.
Check <code>search.log</code> for the query line to confirm the server received it.</p>

<p style="color:#ef4444;font-weight:600">❌ Download fails or shows "Building…" indefinitely</p>
<p>The download is server-side — check <code>search.log</code> for a <em>Download error</em> line.
The most common causes are: <code>openpyxl</code> not installed (run <code>pip install openpyxl</code>),
or the server running out of memory on very large result sets (&gt;50 000 rows).
The browser button shows <em>Building…</em> while the server processes; it restores automatically on completion or error.</p>

<p style="color:#ef4444;font-weight:600">❌ Dashboard sheet has no chart or pivot</p>
<p>The monthly pivot requires <em>Created Date</em> values that can be parsed.
If most tickets have no created date, the chart will be empty.
Check that the date columns in Snow.xlsx, Azure.csv, and Ptc.csv are exported correctly.</p>
"""
    },

    {
        "id": "structure",
        "icon": "🗂️",
        "title": "Module Structure",
        "content": """
<h3>File Layout</h3>
<ul>
  <li><code>search/search_routes.py</code> — All API routes and blueprint</li>
  <li><code>search/templates/search.html</code> — Main Jinja2 template</li>
  <li><code>search/statics/search.js</code> — All frontend logic</li>
  <li><code>search/statics/search.css</code> — All module styles</li>
  <li><code>search/module/data_loader.py</code> — CSV/XLSX loading, normalisation, link extraction, AOM lookup</li>
  <li><code>search/module/kpi.py</code> — KPI calculation + calculate_report()</li>
  <li><code>search/module/search_help.py</code> — This help content</li>
</ul>

<h3>API Routes</h3>
<ul>
  <li><code>GET  /search</code> — Main page</li>
  <li><code>GET  /search/filter-options</code> — Status, priority, group dropdowns</li>
  <li><code>POST /search/issues</code> — Run search with filters</li>
  <li><code>POST /search/save-group</code> — Save a user group</li>
  <li><code>POST /search/collect-users</code> — Refresh users from data files</li>
  <li><code>GET  /search/group-members</code> — All groups and their members</li>
  <li><code>GET  /search/help-data</code> — Help guide sections (JSON)</li>
</ul>
"""
    },

]
