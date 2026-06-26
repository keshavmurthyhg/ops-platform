def get_preview_css():
    return """
    <style>
        body {
            margin:0;
            font-family:Arial;
        }

        .container {
            display:flex;
            width:100%;
            height:380px;
            border:1px solid #ccc;
        }

        .pane {
            width:50%;
            overflow-y:auto;
            border-right:1px solid #ddd;
            font-family:Consolas, monospace;
        }

        .line {
            height:24px;
            line-height:24px;
            padding:0 6px;
            margin:0;
            font-size:12px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
            border-radius:3px;
            box-sizing:border-box;
        }

        .normal {
            background:white;
        }

        .removed {
            background:#ffd6d6;
        }

        .added {
            background:#d6f5d6;
        }

        .updated {
            background:#fff2cc;
        }

        .blank {
            background:white;
        }
    </style>
    """
