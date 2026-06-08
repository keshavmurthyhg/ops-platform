import os
import copy
import tempfile
import subprocess

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pdf2image import convert_from_path

from common.logger import setup_logger


logger = setup_logger("ppt_slide_renderer")

LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"
POPPLER_PATH = r"C:\poppler\Library\bin"


# -----------------------------------------
# Skip unwanted slides
# -----------------------------------------
def should_skip_slide(slide):
    try:
        texts = []

        for shape in slide.shapes:
            if hasattr(shape, "text"):
                txt = shape.text.strip().lower()

                if txt:
                    texts.append(txt)

        combined_text = " ".join(texts)

        skip_keywords = [
            "thank you",
            "questions"
        ]

        for keyword in skip_keywords:
            if keyword in combined_text:
                logger.info(
                    f"Skipping slide due to keyword: {keyword}"
                )
                return True

        return False

    except Exception as e:
        logger.error(
            f"should_skip_slide error: {str(e)}"
        )
        return False


# -----------------------------------------
# Safe XML copy helper
# -----------------------------------------
def copy_shape_xml(shape, new_slide, slide_index):
    try:
        el = shape.element
        new_el = copy.deepcopy(el)

        new_slide.shapes._spTree.insert_element_before(
            new_el,
            "p:extLst"
        )

        logger.info(
            f"XML copied shape on slide {slide_index+1}"
        )

        return True

    except Exception as e:
        logger.warning(
            f"XML copy failed on slide {slide_index+1}: {str(e)}"
        )
        return False


# -----------------------------------------
# Create clean PPT
# -----------------------------------------
def create_clean_ppt(ppt_path):
    try:
        logger.info(
            f"Starting clean PPT creation: {ppt_path}"
        )

        source_prs = Presentation(ppt_path)

        clean_prs = Presentation()
        clean_prs.slide_width = source_prs.slide_width
        clean_prs.slide_height = source_prs.slide_height

        blank_layout = clean_prs.slide_layouts[6]

        for slide_index, slide in enumerate(source_prs.slides):

            logger.info(
                f"Processing slide {slide_index+1}"
            )

            if should_skip_slide(slide):
                continue

            new_slide = clean_prs.slides.add_slide(
                blank_layout
            )

            # -----------------------------------
            # Copy screenshots/images
            # -----------------------------------
            for shape in slide.shapes:
                try:
                    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                        logger.info(
                            f"Copying image on slide {slide_index+1}"
                        )

                        image = shape.image
                        image_bytes = image.blob

                        temp_img = tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix="." + image.ext
                        )

                        temp_img.write(image_bytes)
                        temp_img.close()

                        new_slide.shapes.add_picture(
                            temp_img.name,
                            shape.left,
                            shape.top,
                            shape.width,
                            shape.height
                        )

                except Exception as e:
                    logger.error(
                        f"Image copy failed on slide {slide_index+1}: {str(e)}"
                    )

            # -----------------------------------
            # Copy textboxes/shapes
            # -----------------------------------
            for shape in slide.shapes:
                try:
                    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                        continue

                    # skip group objects
                    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                        logger.info(
                            f"Skipping group shape on slide {slide_index+1}"
                        )
                        continue

                    # -----------------------------------
                    # Preserve placeholders/title slides
                    # -----------------------------------
                    if shape.is_placeholder:
                        if hasattr(shape, "text"):
                            text_value = shape.text.strip()

                            if text_value:
                                success = copy_shape_xml(
                                    shape,
                                    new_slide,
                                    slide_index
                                )

                                if not success:
                                    textbox = new_slide.shapes.add_textbox(
                                        shape.left,
                                        shape.top,
                                        shape.width,
                                        shape.height
                                    )

                                    textbox.text = text_value

                                    logger.info(
                                        f"Fallback placeholder textbox copied on slide {slide_index+1}"
                                    )

                        continue

                    # -----------------------------------
                    # Preserve textboxes with formatting
                    # -----------------------------------
                    if hasattr(shape, "text"):
                        text_value = shape.text.strip()

                        if text_value:
                            success = copy_shape_xml(
                                shape,
                                new_slide,
                                slide_index
                            )

                            if not success:
                                textbox = new_slide.shapes.add_textbox(
                                    shape.left,
                                    shape.top,
                                    shape.width,
                                    shape.height
                                )

                                textbox.text = text_value

                                logger.info(
                                    f"Fallback textbox copied on slide {slide_index+1}"
                                )

                            continue

                    # -----------------------------------
                    # Safe shapes
                    # -----------------------------------
                    if shape.shape_type in [
                        MSO_SHAPE_TYPE.AUTO_SHAPE,
                        MSO_SHAPE_TYPE.LINE,
                        MSO_SHAPE_TYPE.FREEFORM
                    ]:
                        copy_shape_xml(
                            shape,
                            new_slide,
                            slide_index
                        )

                    else:
                        logger.info(
                            f"Skipping unsupported shape type "
                            f"{shape.shape_type} on slide {slide_index+1}"
                        )

                except Exception as e:
                    logger.error(
                        f"Shape copy failed on slide {slide_index+1}: {str(e)}"
                    )

        temp_dir = tempfile.mkdtemp()

        clean_ppt_path = os.path.join(
            temp_dir,
            "clean_ppt.pptx"
        )

        clean_prs.save(clean_ppt_path)

        logger.info(
            f"Clean PPT created: {clean_ppt_path}"
        )

        return clean_ppt_path, temp_dir

    except Exception as e:
        logger.error(
            f"Clean PPT creation failed: {str(e)}"
        )
        raise


# -----------------------------------------
# PPT -> PDF -> PNG
# -----------------------------------------
def render_ppt_slides_to_images(ppt_path):
    try:
        logger.info(
            f"Starting render process for: {ppt_path}"
        )

        clean_ppt_path, temp_dir = create_clean_ppt(
            ppt_path
        )

        logger.info(
            "Starting LibreOffice PDF conversion"
        )

        subprocess.run([
            LIBREOFFICE_PATH,
            "--headless",
            "--convert-to",
            "pdf",
            clean_ppt_path,
            "--outdir",
            temp_dir
        ], check=True)

        pdf_files = [
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if f.endswith(".pdf")
        ]

        if not pdf_files:
            raise Exception(
                "No PDF generated"
            )

        pdf_path = pdf_files[0]

        logger.info(
            f"PDF generated: {pdf_path}"
        )

        pages = convert_from_path(
            pdf_path,
            dpi=200,
            poppler_path=POPPLER_PATH
        )

        final_images = []

        for i, page in enumerate(pages):
            img_path = os.path.join(
                temp_dir,
                f"slide_{i+1}.png"
            )

            page.save(
                img_path,
                "PNG"
            )

            final_images.append(img_path)

            logger.info(
                f"Generated PNG: {img_path}"
            )

        logger.info(
            f"Total PNGs generated: {len(final_images)}"
        )

        return final_images

    except Exception as e:
        logger.error(
            f"Render process failed: {str(e)}"
        )
        return []