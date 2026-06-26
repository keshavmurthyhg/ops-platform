import os
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from .module.logic import run_compare
from .module.services import ExcelExportService
from .module.help_provider import HelpContentProvider
from common.home_help_provider import HomeHelpProvider
from common.logger import setup_logger

logger = setup_logger("excel_compare")

excel_compare_bp = Blueprint(
    'excel_compare',
    __name__,
    template_folder='templates',
    static_folder='statics',
    static_url_path='/excel_compare/static'
)


@excel_compare_bp.route('/excel-compare')
def index():
    logger.info("Excel Compare page loaded")
    return render_template('excel_compare.html')


@excel_compare_bp.route('/excel_compare/help-data')
def help_data():
    return jsonify({"topics": HelpContentProvider.get_topics()})


@excel_compare_bp.route('/api/help/home-platform')
def home_platform_help():
    return jsonify({
        "module_title": "🏠 Ops Platform Portal Guide",
        "topics": HomeHelpProvider.get_platform_topics()
    })


@excel_compare_bp.route('/excel_compare/compare', methods=['POST'])
def compare_files():
    if 'oldFile' not in request.files or 'newFile' not in request.files:
        logger.warning("Compare called without both files")
        return jsonify({'error': 'Both files are required'}), 400

    file1 = request.files['oldFile']
    file2 = request.files['newFile']

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    path1 = os.path.join(upload_folder, secure_filename(file1.filename))
    path2 = os.path.join(upload_folder, secure_filename(file2.filename))
    file1.save(path1)
    file2.save(path2)

    current_app.config['COMPARE_PATH1']    = path1
    current_app.config['COMPARE_PATH2']    = path2
    current_app.config['LAST_COMPARE_ZIP'] = None

    logger.info("Comparing: %s vs %s", file1.filename, file2.filename)

    try:
        result = run_compare(path1, path2)

        t = result['totals']
        logger.info(
            "Compare complete: modified=%s added=%s removed=%s",
            t.get('modified'), t.get('added'), t.get('removed')
        )

        return jsonify({
            'success':    True,
            'sheets':     result['sheets'],
            'sheet_data': result['sheet_data'],
            'totals':     result['totals'],
            'file1_name': file1.filename,
            'file2_name': file2.filename
        })

    except Exception as e:
        logger.error("Compare failed: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@excel_compare_bp.route('/excel_compare/download', methods=['GET'])
def download_report():
    zip_path = current_app.config.get('LAST_COMPARE_ZIP')

    if not zip_path or not os.path.exists(zip_path):
        path1 = current_app.config.get('COMPARE_PATH1')
        path2 = current_app.config.get('COMPARE_PATH2')

        if not path1 or not path2:
            logger.warning("Download requested but no session data found")
            return jsonify({'error': 'No active session data found'}), 404

        logger.info("Generating download bundle")
        zip_path, zip_name = ExcelExportService.generate_bundle(path1, path2)
        current_app.config['LAST_COMPARE_ZIP']  = zip_path
        current_app.config['LAST_COMPARE_NAME'] = zip_name

    zip_name = current_app.config.get('LAST_COMPARE_NAME', 'ExcelCompare.zip')
    logger.info("Download served: %s", zip_name)
    return send_file(zip_path, as_attachment=True, download_name=zip_name)
