# =============================================================================
#  CONVERTER MODULE — HELP CONTENT API
#  converter/converter_help.py
# =============================================================================

from flask import Blueprint, jsonify

converter_help_bp = Blueprint("converter_help", __name__)

_CONVERTER_HELP_TOPICS = [

    # -------------------------------------------------------------------------
    {
        "id":    "overview",
        "title": "📄 How It Works",
        "content": """
<h3>How the Converter Works</h3>
<p>The Converter transforms a PowerPoint incident walkthrough (<code>.ppt</code> /
<code>.pptx</code>) into a clean Word document (and optionally a PDF), enriched
with live incident data from ServiceNow.</p>

<h4>End-to-End Processing Pipeline</h4>
<ol>
  <li>
    <strong>Upload &amp; Incident Detection</strong><br>
    The app reads the filename and slide 1 metadata to extract the incident
    number (e.g. <code>INC109682818</code>). That number is looked up in
    ServiceNow to pull priority, description, assignee, and dates.
  </li>
  <li>
    <strong>Slide Filtering</strong><br>
    Each slide is evaluated. Title/cover slides (slide 1), divider slides
    (≤ 10 words, no image, no non-placeholder shapes), and keyword slides
    ("Thank You", "Agenda", etc.) are removed. Only content slides — those
    with screenshots, annotation shapes, or meaningful text — are kept.
  </li>
  <li>
    <strong>Background Stripping</strong><br>
    The slide master and all layouts are cleaned: decorative theme shapes
    (swooshes, triangles, gradient rectangles) are removed and the background
    is overridden to white. Crucially, <em>no shapes on the slide itself are
    ever removed</em> — every arrow, connector, highlight box, numbered circle,
    and annotation you drew is preserved.
  </li>
  <li>
    <strong>Rendering: PPTX → PDF → PNG</strong><br>
    The cleaned PPTX is converted to PDF by LibreOffice headless, then each
    PDF page is rasterised to a PNG at 200 dpi by pdf2image/Poppler. This
    approach preserves all vector shapes, fonts, and custom geometry exactly
    as PowerPoint renders them.
  </li>
  <li>
    <strong>Word Document Assembly</strong><br>
    The incident header (from ServiceNow) is written first, followed by each
    slide image on its own landscape page. The result is a self-contained
    <code>.docx</code> ready to share or upload to the ticketing system.
  </li>
  <li>
    <strong>PDF Export (optional)</strong><br>
    If PDF or Both is selected, LibreOffice converts the finished
    <code>.docx</code> to <code>.pdf</code> in one additional pass.
  </li>
</ol>

<h4>What Gets Kept vs Stripped</h4>
<table style="width:100%;border-collapse:collapse;font-size:13px;">
  <thead>
    <tr style="background:#e0f2fe;">
      <th style="padding:6px 10px;text-align:left;border:1px solid #bae6fd;">Element</th>
      <th style="padding:6px 10px;text-align:left;border:1px solid #bae6fd;">Location</th>
      <th style="padding:6px 10px;text-align:left;border:1px solid #bae6fd;">Action</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Screenshots / images</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Slide</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td>
    </tr>
    <tr style="background:#f8fafc;">
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Arrows, connectors, shapes</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Slide</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td>
    </tr>
    <tr>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Highlight boxes (empty rects)</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Slide</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td>
    </tr>
    <tr style="background:#f8fafc;">
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Numbered circles, text boxes</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Slide</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td>
    </tr>
    <tr>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Symbols (Wingdings, emoji)</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Slide</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td>
    </tr>
    <tr style="background:#f8fafc;">
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Blue/teal theme swooshes</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Master / Layout</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#991b1b;">✗ Stripped</td>
    </tr>
    <tr>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Gradient background rectangles</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Master / Layout</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#991b1b;">✗ Stripped</td>
    </tr>
    <tr style="background:#f8fafc;">
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Theme background colour (bgRef)</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Master / Layout / Slide</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#991b1b;">✗ Replaced with white</td>
    </tr>
    <tr>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Title/cover/divider slides</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;">Slide (whole slide)</td>
      <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#7c3aed;">⊘ Skipped (if enabled)</td>
    </tr>
  </tbody>
</table>
        """,
    },

    # -------------------------------------------------------------------------
    {
        "id":    "procedure",
        "title": "🚀 How to Use",
        "content": """
<h3>Step-by-Step Procedure</h3>

<h4>Step 1 — Upload the PPT</h4>
<p>Click <strong>Choose File</strong> in the top toolbar and select your
<code>.ppt</code> or <code>.pptx</code> file. The filename should contain the
incident number (e.g. <code>INC109682818-walkthrough.pptx</code>).</p>
<p>The selected filename appears immediately next to the button.</p>

<h4>Step 2 — Configure Options (optional)</h4>
<p>Open the <strong>⚙ Options</strong> dock in the sidebar to adjust:</p>
<ul>
  <li><strong>Skip Title Slides</strong> — removes the cover slide and any
      section dividers automatically.</li>
  <li><strong>Skip Divider Slides</strong> — removes low-content transition
      slides.</li>
  <li><strong>Slide DPI</strong> — controls image quality (150 = fast,
      200 = default, 300 = high quality for print).</li>
  <li><strong>Output Format</strong> — Word, PDF, or Both.</li>
</ul>

<h4>Step 3 — Preview</h4>
<p>Click <strong>Preview</strong> to:</p>
<ul>
  <li>Fetch incident metadata from ServiceNow and display it in the
      <em>Incident Preview</em> panel.</li>
  <li>Generate slide thumbnail images and display them in the
      <em>Converted PPT Slides Preview</em> panel.</li>
</ul>
<p>Review the thumbnails — this is what will appear in the final document.
If a slide is missing, check the <strong>Skip Title Slides</strong> toggle.</p>

<h4>Step 4 — Convert PPT</h4>
<p>Click <strong>🔄 Convert PPT</strong> in the Converter Actions dock.
This runs the full filtering and rendering pipeline and refreshes the slide
preview with the final cleaned images.</p>

<h4>Step 5 — Generate Report</h4>
<p>Click <strong>📝 Generate Report</strong>. The app assembles the Word
document (and PDF if selected) and switches the sidebar to the
<strong>⬇ Download Options</strong> dock automatically.</p>

<h4>Step 6 — Download</h4>
<p>Choose your format in the <strong>Download Options</strong> dock and click
the download button. Files are saved to the <code>outputs/</code> folder on
the server and sent directly to your browser.</p>

<h4>Clear Workspace</h4>
<p>Click <strong>Clear Workspace</strong> at the top of the sidebar to reset
everything and start a new conversion.</p>
        """,
    },

    # -------------------------------------------------------------------------
    {
        "id":    "features",
        "title": "✨ New Features",
        "content": """
<h3>New Features</h3>

<h4>⬇ Download Options Dock</h4>
<p>Choose your output format before generating:</p>
<ul>
  <li><strong>📄 Word (.docx)</strong> — standard Word document.</li>
  <li><strong>📕 PDF</strong> — PDF via LibreOffice (same engine as slide
      rendering, so fonts and shapes match exactly).</li>
  <li><strong>📦 Both</strong> — generates and downloads both files.</li>
</ul>
<p>The sidebar automatically switches to the Download dock once the document
is ready.</p>

<h4>⚙ Options Dock</h4>
<p>Fine-grained control over the conversion:</p>
<ul>
  <li><strong>Skip Title Slides toggle</strong> — on by default. Turn off if
      you want to include the cover slide in the output.</li>
  <li><strong>Skip Divider Slides toggle</strong> — on by default. Removes
      section break slides with minimal content.</li>
  <li><strong>Slide DPI selector</strong> — balance between file size and
      image clarity.</li>
  <li><strong>Output Format selector</strong> — synced with the Download
      Options dock radio buttons.</li>
</ul>

<h4>🎨 Clean White Background</h4>
<p>The Facet/corporate theme background (blue swooshes, gradient triangles)
is automatically removed from the master and all 16+ layouts. Every slide
renders on a clean white background without losing any annotation shapes you
drew on the slide itself.</p>

<h4>🔴 Annotation Preservation</h4>
<p>All shapes added by the user on slides are always preserved:</p>
<ul>
  <li>Red highlight rectangles and outlines</li>
  <li>Numbered circles and step markers</li>
  <li>Arrows in all directions (right, down, striped, pentagon, bent)</li>
  <li>Elbow / bent connectors between steps</li>
  <li>Wingdings and emoji symbols</li>
  <li>Yellow callout text boxes</li>
  <li>"Not Allowed" and other preset symbols</li>
</ul>

<h4>📊 Detailed Logging</h4>
<p>Every conversion is logged with full detail — see the
<strong>📋 Logs</strong> section for what to look for in the terminal.</p>
        """,
    },

    # -------------------------------------------------------------------------
    {
        "id":    "logs",
        "title": "📋 Reading the Logs",
        "content": """
<h3>Reading the Logs</h3>
<p>All converter activity is logged to the terminal (and
<code>logs/converter.log</code>). Here is how to read a typical run:</p>

<h4>1. User Preferences Block</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
------------------------------------------------------------
USER PREFERENCES — CONVERT
  Skip title slides : true
  Skip dividers     : true
  Slide DPI         : 200
  Output format     : both
------------------------------------------------------------</pre>
<p>Logged at the start of every Preview, Convert, and Generate request.
Confirms what options were active when the request was made.</p>

<h4>2. PPT Processing Header</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
============================================================
PPT PROCESSING STARTED
  File      : INC109682818-walkthrough.pptx
  Slides    : 9 total
  Skip titles: True
============================================================</pre>

<h4>3. Slide Filter Decisions</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
Slide 1 — SKIP (cover/title slide)
Slide 2 — KEEP | shapes=12  pics=2  text_boxes=4  connectors=3  groups=0  other=3
Slide 3 — KEEP | shapes=8   pics=1  text_boxes=6  connectors=2  groups=0  other=1
Slide 7 — SKIP (divider: 4 word(s), no picture, no non-placeholder shapes)
------------------------------------------------------------
Slide filter result: 7 kept, 2 skipped (skipped slides: [1, 7])</pre>
<p>Each kept slide shows a shape inventory: pictures, text boxes, connectors,
groups, and other shapes. Skipped slides show the reason.</p>

<h4>4. Master / Layout Cleanup</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
MASTER/LAYOUT CLEANUP
  master    | stripped 2 chrome shape(s): group('Group 43'), group('Group 44')
  layout[0] | stripped 1 chrome shape(s): group('Group 15')
  layout[1] | no chrome shapes found
  ...
  Master + 20 layouts cleaned | total chrome shapes removed: 6</pre>
<p>Every decorative shape removed from the master or layout is named.
"No chrome shapes found" means that layout was already clean.</p>

<h4>5. Slide Background Override</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
SLIDE BACKGROUND OVERRIDE
  Slide 2: white background applied (all 12 shapes preserved)
  Slide 3: white background applied (all 8 shapes preserved)</pre>
<p>Confirms white bg was injected on every kept slide and that the shape
count on the slide was not changed.</p>

<h4>6. Image Rendering</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
LIBREOFFICE: PPTX → PDF
  PDF created: C:\\Users\\...\\filtered.pdf
PDF2IMAGE: PDF → PNG (dpi=200)
  Pages extracted: 7
  PNG [1/7]: slide_1.png  (2540x1428 px)
  PNG [2/7]: slide_2.png  (2540x1428 px)
  ...
============================================================
PPT PROCESSING COMPLETE
  Total PNG images : 7
  Output dir       : C:\\Users\\...\\tmpXXXXXX
============================================================</pre>

<h4>7. Document Generation</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">
GENERATING DOCUMENT
  Incident : INC109682818
  Format   : BOTH
DOCX CREATED: INC109682818-walkthrough.docx  (1842 KB)
============================================================
DOCX → PDF CONVERSION
  Input : outputs/INC109682818-walkthrough.docx
  Output: outputs/
  Engine: LibreOffice headless
  PDF created : outputs/INC109682818-walkthrough.pdf  (3204 KB)
============================================================
GENERATE COMPLETE</pre>

<h4>Log file location</h4>
<p><code>&lt;project_root&gt;/logs/converter.log</code><br>
<code>&lt;project_root&gt;/logs/ppt_slide_renderer.log</code><br>
<code>&lt;project_root&gt;/logs/doc_to_pdf.log</code></p>
        """,
    },

    # -------------------------------------------------------------------------
    {
        "id":    "troubleshoot",
        "title": "🔧 Troubleshooting",
        "content": """
<h3>Troubleshooting</h3>

<h4>❌ "Valid incident not found"</h4>
<p>The app couldn't extract an INC number from the filename or slide 1.
Rename your file to include the full incident number:
<code>INC109682818-description.pptx</code></p>

<h4>❌ "[WinError 2] The system cannot find the file specified"</h4>
<p>LibreOffice is not installed at the expected path:<br>
<code>C:\\Program Files\\LibreOffice\\program\\soffice.exe</code><br>
Install LibreOffice or update <code>LIBREOFFICE_PATH</code> in
<code>ppt_slide_renderer.py</code> and <code>doc_to_pdf.py</code>.</p>

<h4>❌ "LibreOffice produced no PDF"</h4>
<p>LibreOffice ran but didn't produce output. Check the terminal for its
stderr output. Common causes: corrupted PPTX, missing fonts, or insufficient
disk space in the temp directory.</p>

<h4>❌ Blue background still visible on some slides</h4>
<p>This can happen if the presentation uses a second slide master. The app
now cleans <em>all</em> masters and all their layouts. If you still see
it, check <code>ppt_slide_renderer.log</code> for
<code>Master/Layout CLEANUP</code> — it will list exactly which chrome
shapes were stripped. If a shape was missed, its name will appear in the
log and the dev team can add it to the filter.</p>

<h4>❌ An annotation shape is missing from the output</h4>
<p>The app never removes shapes from the slide spTree — only from the
master and layout. If a shape is missing, it was already absent from the
PPTX or was in a group that LibreOffice couldn't render. Check slide shape
counts in the log (<code>Slide N — KEEP | shapes=...</code>).</p>

<h4>❌ PDF generation failed but Word succeeded</h4>
<p>The app will still offer the Word download and show an alert with the
PDF error. The most common cause is a complex DOCX with embedded fonts
that LibreOffice can't process. Try opening the DOCX in Word and saving
as PDF manually as a workaround.</p>

<h4>❌ Preview shows no slides</h4>
<p>All slides were classified as title/divider. Turn off
<strong>Skip Title Slides</strong> and <strong>Skip Divider Slides</strong>
in the Options dock and try again.</p>
        """,
    },
]


@converter_help_bp.route("/api/help/converter")
def converter_help_api():
    return jsonify({
        "module_title": "Converter — PPT to DOC Help",
        "topics":       _CONVERTER_HELP_TOPICS,
    })
