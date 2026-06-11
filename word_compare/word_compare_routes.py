import os
import base64
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from .module.logic import run_compare, generate_highlighted_bundle
from .module.help_provider import HelpContentProvider

word_compare_bp = Blueprint(
    'word_compare',
    __name__,
    template_folder='templates',
    static_folder='statics',
    static_url_path='/word_compare/static'
)


@word_compare_bp.route('/word-compare')
def index():
    return render_template('word_compare.html')


@word_compare_bp.route('/word_compare/help-data')
def help_data():
    return jsonify({"topics": HelpContentProvider.get_topics()})


@word_compare_bp.route('/word_compare/compare', methods=['POST'])
def compare_files():
    if 'oldFile' not in request.files or 'newFile' not in request.files:
        return jsonify({'error': 'Both files are required'}), 400

    file1 = request.files['oldFile']
    file2 = request.files['newFile']

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    path1 = os.path.join(upload_folder, secure_filename(file1.filename))
    path2 = os.path.join(upload_folder, secure_filename(file2.filename))
    file1.save(path1)
    file2.save(path2)

    current_app.config['WC_PATH1'] = path1
    current_app.config['WC_PATH2'] = path2
    current_app.config['WC_FILE1_NAME'] = file1.filename
    current_app.config['WC_FILE2_NAME'] = file2.filename
    current_app.config['WC_LAST_ZIP'] = None

    try:
        result = run_compare(path1, path2)
        return jsonify({
            'success': True,
            'diff': result['diff'],
            'stats': result['stats'],
            'images_old': result['images_old'],
            'images_new': result['images_new'],
            'file1_name': file1.filename,
            'file2_name': file2.filename
        })
    except Exception as e:
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
            return jsonify({'error': 'No active session data found'}), 404

        zip_path, zip_name = generate_highlighted_bundle(path1, path2, name1, name2)
        current_app.config['WC_LAST_ZIP'] = zip_path
        current_app.config['WC_LAST_ZIP_NAME'] = zip_name

    zip_name = current_app.config.get('WC_LAST_ZIP_NAME', 'WordCompare.zip')
    return send_file(zip_path, as_attachment=True, download_name=zip_name)
