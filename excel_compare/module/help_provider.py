class HelpContentProvider:
    @staticmethod
    def get_topics():
        return [
            {
                "id": "overview",
                "title": "📘 Workspace Overview",
                "content": "<h3>Workspace Overview</h3><p>The Excel Comparison tool provides an interactive side-by-side operational overview allowing cross-functional verification between baseline workbooks and recent file changes line-by-line.</p><h4>Core Functionalities:</h4><ul><li><b>Automatic Coordinate Mapping:</b> Aligns cells at uniform dimensional indexes across separate files.</li><li><b>KPI Metrics:</b> Calculates complete transaction items automatically upon file execution.</li></ul>"
            },
            {
                "id": "actions",
                "title": "⚡ Toolbar Actions",
                "content": "<h3>Toolbar & Dashboard Controls</h3><p>Manage processing inputs directly using the top workspace configuration buttons:</p><ul><li><b>File Selection Stubs:</b> Click either block to choose a target source spreadsheet from your disk files.</li><li><b>Run Compare:</b> Validates files and initiates calculation passes on the server.</li><li><b>Clear Workspace:</b> Clears loaded datasets and re-initializes empty views.</li></ul>"
            },
            {
                "id": "navigation",
                "title": "🔄 Layout Navigation",
                "content": "<h3>Layout Views & Sheet Sub-Tabs</h3><p>Review variances through separate view modes:</p><ul><li><b>Side by Side:</b> Presents aligned dual-viewports with synchronized scrolling. Moving one panel automatically shifts the opposite viewport.</li><li><b>Change Log:</b> Collects flattened transformation summaries for text filtering tasks.</li><li><b>Sheet Tabs:</b> Dynamically changes active views between separate workbooks sheets.</li></ul>"
            }
        ]