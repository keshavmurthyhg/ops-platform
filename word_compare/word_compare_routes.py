import os
import base64
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from .module.logic import run_compare, generate_highlighted_bundle
from .module.help_provider import HelpContentProvider
from common.logger import setup_logger

logger = setup_logger("word_compare")

word_compare_bp = Blueprint(
    'word_compare',
    __name__,
    template_folder='templates',
    static_folder='statics',
    static_url_path='/word_compare/static'
)


@word_compare_bp.route('/word-compare')
def index():
    logger.info("Word Compare page loaded")
    return render_template('word_compare.html')


@word_compare_bp.route('/word_compare/help-data')
def help_data():
    return jsonify({"topics": HelpContentProvider.get_topics()})


@word_compare_bp.route('/word_compare/compare', methods=['POST'])
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

    current_app.config['WC_PATH1']     = path1
    current_app.config['WC_PATH2']     = path2
    current_app.config['WC_FILE1_NAME'] = file1.filename
    current_app.config['WC_FILE2_NAME'] = file2.filename
    current_app.config['WC_LAST_ZIP']  = None

    logger.info("Comparing: %s vs %s", file1.filename, file2.filename)

    try:
        result = run_compare(path1, path2)

        current_app.config['WC_SECTION_DATA'] = result['section_data']
        current_app.config['WC_SECTION_KEYS'] = result['sections']
        current_app.config['WC_TOTALS']        = result['totals']

        t = result['totals']
        logger.info(
            "Compare complete: added=%s removed=%s modified=%s total=%s",
            t.get('added'), t.get('removed'), t.get('modified'), t.get('total')
        )

        return jsonify({
            'success':      True,
            'sections':     result['sections'],
            'section_data': result['section_data'],
            'totals':       result['totals'],
            'images_old':   result['images_old'],
            'images_new':   result['images_new'],
            'file1_name':   file1.filename,
            'file2_name':   file2.filename,
        })

    except Exception as e:
        logger.error("Compare failed: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@word_compare_bp.route('/word_compare/download', methods=['GET'])
def download_report():
    zip_path = current_app.config.get('WC_LAST_ZIP')

    if not zip_path or not os.path.exists(zip_path):
        path1 = current_app.config.get('WC_PATH1')
        path2 = current_app.config.get('WC_PATH2')
        name1 = current_app.config.get('WC_FILE1_NAME', 'old.docx')
        name2 = current_app.config.get('WC_FILE2_NAME', 'new.docx')

        if not path1 or not path2:
            logger.warning("Download requested but no session data found")
            return jsonify({'error': 'No active session data found'}), 404

        logger.info("Generating download bundle: %s vs %s", name1, name2)

        zip_path, zip_name = generate_highlighted_bundle(
            path1, path2, name1, name2,
            section_data = current_app.config.get('WC_SECTION_DATA'),
            section_keys = current_app.config.get('WC_SECTION_KEYS'),
            totals       = current_app.config.get('WC_TOTALS'),
        )
        current_app.config['WC_LAST_ZIP']      = zip_path
        current_app.config['WC_LAST_ZIP_NAME'] = zip_name

    zip_name = current_app.config.get('WC_LAST_ZIP_NAME', 'WordCompare.zip')
    logger.info("Download served: %s", zip_name)
    return send_file(zip_path, as_attachment=True, download_name=zip_name)
