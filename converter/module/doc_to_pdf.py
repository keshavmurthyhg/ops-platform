import os
import subprocess

from common.logger import setup_logger

logger = setup_logger("doc_to_pdf")

LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"


def doc_to_pdf(docx_path, output_dir):
    """
    Convert a .docx to PDF using LibreOffice headless.
    Returns the path to the generated PDF.
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX not found: {docx_path}")

    os.makedirs(output_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("DOCX → PDF CONVERSION")
    logger.info("  Input : %s", docx_path)
    logger.info("  Output: %s", output_dir)
    logger.info("  Engine: LibreOffice headless")
    logger.info("  Path  : %s", LIBREOFFICE_PATH)

    result = subprocess.run(
        [LIBREOFFICE_PATH, "--headless", "--convert-to", "pdf",
         "--outdir", output_dir, docx_path],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        logger.error("LibreOffice stderr: %s", result.stderr)
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {result.returncode}): {result.stderr}"
        )

    base     = os.path.splitext(os.path.basename(docx_path))[0]
    pdf_path = os.path.join(output_dir, base + ".pdf")

    if not os.path.exists(pdf_path):
        raise RuntimeError(
            f"LibreOffice ran but no PDF found at: {pdf_path}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    size_kb = os.path.getsize(pdf_path) // 1024
    logger.info("  PDF created : %s  (%d KB)", pdf_path, size_kb)
    logger.info("=" * 60)
    return pdf_path
