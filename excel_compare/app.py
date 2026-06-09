import os
import sys
from flask import Flask, redirect, url_for

# Add parent directory to system path so absolute module importing resolves flawlessly when run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from excel_compare.excel_compare_routes import excel_compare_bp

app = Flask(
    __name__, 
    template_folder=os.path.join(os.path.dirname(__file__), 'module', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'module', 'statics')
)

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.secret_key = "standalone_secret"

# Register the blueprint at base root prefix for standalone distribution simplicity
app.register_blueprint(excel_compare_bp, url_prefix="")

@app.route('/')
def home_redirect():
    # Automatically forward root lookups directly to our tool page
    return redirect(url_for('excel_compare.index'))

if __name__ == "__main__":
    print("Running Excel Compare Module as a Standalone Web Application...")
    app.run(debug=True, port=5006)