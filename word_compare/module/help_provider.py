class HelpContentProvider:

    @staticmethod
    def get_topics():
        return [
            {
                "title": "📘 Overview",
                "content": (
                    "<h3>Word Compare Overview</h3>"
                    "<p>The Word Comparison tool compares two .docx files side-by-side, "
                    "highlighting paragraphs and table cells that were added, removed, or modified.</p>"
                    "<h4>Capabilities:</h4>"
                    "<ul>"
                    "<li><b>Paragraph Diff:</b> Line-by-line text comparison with color coding.</li>"
                    "<li><b>Table Diff:</b> Cell-level change detection across matching tables.</li>"
                    "<li><b>Image Preview:</b> Embedded images from both documents displayed side-by-side.</li>"
                    "<li><b>Download Bundle:</b> Export both highlighted .docx files as a ZIP.</li>"
                    "</ul>"
                )
            },
            {
                "title": "⚡ How to Use",
                "content": (
                    "<h3>Step-by-Step Usage</h3>"
                    "<ol>"
                    "<li>Click <b>OLD</b> file stub in the toolbar to select the base document.</li>"
                    "<li>Click <b>NEW</b> file stub to select the revised document.</li>"
                    "<li>Click <b>Run Compare</b> to process and render the diff.</li>"
                    "<li>Switch between <b>Diff View</b> and <b>Images</b> tabs to inspect changes.</li>"
                    "<li>Click <b>💾 Download</b> to get highlighted .docx files as a ZIP.</li>"
                    "</ol>"
                )
            },
            {
                "title": "🎨 Colour Legend",
                "content": (
                    "<h3>Highlight Colour Meanings</h3>"
                    "<ul>"
                    "<li><span style='background:#d6f5d6;padding:2px 8px;border-radius:4px;'>➕ Green</span> — Line added in new document</li>"
                    "<li><span style='background:#ffd6d6;padding:2px 8px;border-radius:4px;'>❌ Red</span> — Line removed from old document</li>"
                    "<li><span style='background:#fff2cc;padding:2px 8px;border-radius:4px;'>🔄 Yellow</span> — Line modified between versions</li>"
                    "<li><span style='background:#f8fafc;padding:2px 8px;border-radius:4px;'>Normal</span> — Unchanged content</li>"
                    "</ul>"
                )
            },
            {
                "title": "🖼️ Image Handling",
                "content": (
                    "<h3>Image Comparison</h3>"
                    "<p>Images embedded in both documents are extracted and displayed in the "
                    "<b>Images</b> tab. Images are deduplicated by content hash.</p>"
                    "<p>Images are shown in two columns — left for the old document, right for the new. "
                    "Hover over an image to see its index.</p>"
                    "<p><b>Note:</b> Image comparison is visual only; the download bundle preserves "
                    "all original embedded images in the highlighted .docx files.</p>"
                )
            }
        ]
