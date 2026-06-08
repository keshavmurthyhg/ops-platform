def render_download_buttons(incident_number):
    return f"""
    <div class="action-row">

        <form action="/generate-report" method="POST">
            <input type="hidden" name="incident_number" value="{incident_number}">
            <input type="hidden" name="report_type" value="word">
            <button type="submit">Word</button>
        </form>

        <form action="/generate-report" method="POST">
            <input type="hidden" name="incident_number" value="{incident_number}">
            <input type="hidden" name="report_type" value="pdf">
            <button type="submit">PDF</button>
        </form>

        <form action="/generate-bulk" method="POST">
            <input type="hidden" name="incident_numbers" value="{incident_number}">
            <input type="hidden" name="report_type" value="zip">
            <button type="submit">ZIP</button>
        </form>

    </div>
    """