#from docx2pdf import convert

#def doc_to_pdf(docx_path, pdf_path):
#    convert(docx_path, pdf_path)

import subprocess
import os

def doc_to_pdf(docx_path, output_dir):
    subprocess.run([
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", output_dir,
        docx_path
    ])
