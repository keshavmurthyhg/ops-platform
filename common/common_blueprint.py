"""
common/common_blueprint.py
==========================
Provides the `common_bp` Flask Blueprint that serves shared static assets
(common.css, common.js, images/) and the shared layout template (main.html).

Register this blueprint in EVERY app that uses the common layout:

    from common.common_blueprint import common_bp
    app.register_blueprint(common_bp)

The blueprint name is ``common_static`` so templates reference assets with:

    {{ url_for('common_static', filename='css/common.css') }}
    {{ url_for('common_static', filename='js/common.js') }}
    {{ url_for('common_static', filename='images/filter.png') }}
"""

import os
from flask import Blueprint

_HERE = os.path.dirname(os.path.abspath(__file__))

common_bp = Blueprint(
    "common_static",
    __name__,
    template_folder=os.path.join(_HERE, "templates"),
    static_folder=os.path.join(_HERE, "static"),
    static_url_path="/common/static",
)
