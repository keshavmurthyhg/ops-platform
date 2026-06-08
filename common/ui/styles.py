TABLE_STYLE = "width:100%; border-collapse: collapse; font-size:14px; border:2px solid black;"
CELL_STYLE = "border:1px solid black; padding:6px;"
HEADER_CELL_STYLE = "border:1px solid black; padding:6px; font-weight:bold;"

def get_table_style():
    return """
    <style>
        .tbl {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            margin-bottom: 20px;
            background: white;
        }

        .tbl td,
        .tbl th {
            border: 1px solid #d1d5db;
            padding: 10px;
            vertical-align: top;
            text-align: left;
            font-size: 13px;
            line-height: 1.5;
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: normal;
        }

        .tbl .hdr {
            background: #f3f4f6;
            font-weight: bold;
            width: 180px;
        }

        .tbl a {
            color: #2563eb;
            text-decoration: none;
        }

        .tbl a:hover {
            text-decoration: underline;
        }
    </style>
    """
