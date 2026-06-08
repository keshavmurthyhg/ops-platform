import os

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_file
)

from datetime import datetime

from excel_merge.module.services.excel_merge_service import (
    process_excel_merge
)

excel_merge_bp = Blueprint(
    'excel_merge_bp',
    __name__
)

UPLOAD_FOLDER = 'uploads/excel_merge'
OUTPUT_FOLDER = 'outputs/excel_merge'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@excel_merge_bp.route('/excel-merge')
def excel_merge():
    return render_template('excel_merge.html')


@excel_merge_bp.route(
    '/excel-merge/process',
    methods=['POST']
)
def process_merge():

    try:

        if 'file1' not in request.files:
            return jsonify({
                'success': False,
                'message': 'File 1 missing'
            })

        if 'file2' not in request.files:
            return jsonify({
                'success': False,
                'message': 'File 2 missing'
            })

        file1 = request.files['file1']
        file2 = request.files['file2']

        key_column = request.form.get('key_column')

        latest_logic = request.form.get(
            'latest_logic',
            'new_file'
        )

        date_column = request.form.get(
            'date_column',
            ''
        )

        timestamp = datetime.now().strftime(
            '%d%b%Y_%H%M%S'
        )

        file1_name = file1.filename.replace(' ', '_')
        file2_name = file2.filename.replace(' ', '_')

        file1_path = os.path.join(
            UPLOAD_FOLDER,
            f'{timestamp}_1_{file1_name}'
        )

        file2_path = os.path.join(
            UPLOAD_FOLDER,
            f'{timestamp}_2_{file2_name}'
        )

        file1.save(file1_path)
        file2.save(file2_path)

        result = process_excel_merge(
            old_file=file1_path,
            new_file=file2_path,
            key_column=key_column,
            latest_logic=latest_logic,
            date_column=date_column,
            output_folder=OUTPUT_FOLDER
        )

        return jsonify(result)

    except Exception as e:

        return jsonify({
            'success': False,
            'message': str(e)
        })


@excel_merge_bp.route(
    '/excel-merge/download/<filename>'
)
def download_output(filename):

    file_path = os.path.join(
        OUTPUT_FOLDER,
        filename
    )

    return send_file(
        file_path,
        as_attachment=True
    )