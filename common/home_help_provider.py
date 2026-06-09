class HomeHelpProvider:
    @staticmethod
    def get_platform_topics():
        return [
            {
                "id": "welcome",
                "title": "🏠 Platform Introduction",
                "content": """
                    <h3>Welcome to the Operations Management Platform</h3>
                    <p>This centralized platform consolidates engineering, analysis, and data utilities into a single unified ecosystem designed for live cross-functional compliance tracking and metrics automation.</p>
                    <h4>Core Layout Features:</h4>
                    <ul>
                        <li><b>Persistent Sidebar:</b> Access any tool module instantly via the left navigation grid matrix.</li>
                        <li><b>Taskbar Status Footer:</b> Active backend tasks report progress or success states dynamically along the bottom platform status monitor.</li>
                    </ul>
                """
            },
            {
                "id": "modules",
                "title": "📦 Module Directory",
                "content": """
                    <h3>Platform Module Directory</h3>
                    <p>The system provides highly specialized environments for data calculations:</p>
                    <ul>
                        <li><b>Excel Compare:</b> Aligns workbook sheets at a granular coordinate level for row/cell diff checking with synchronized dual-viewport scroll-locks.</li>
                        <li><b>DCN Analytics Dashboard:</b> Renders sequence skip anomalies, trend metrics charts, and monthly timeline pivot summaries.</li>
                        <li><b>RCA & Bulk Generators:</b> Automated template engines for batch regulatory document generation and ZIP report packaging.</li>
                    </ul>
                """
            },
            {
                "id": "actions",
                "title": "🧹 Global Workspace Actions",
                "content": """
                    <h3>Universal Control Mechanics</h3>
                    <p>The platform top header nav bar and toolbars offer shared behaviors across pages:</p>
                    <ul>
                        <li><b>Clear Workspace:</b> Flushes temporary file upload streams, clears data masks, and resets view configurations back to clean baseline parameters.</li>
                        <li><b>Global Search (🔍):</b> Targeted client-side text filtering. Type target parameter tokens and press <i>Enter</i> to instantly narrow row counts down to matching rows without latency.</li>
                    </ul>
                """
            }
        ]