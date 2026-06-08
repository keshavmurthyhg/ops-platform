import os
import shutil
import traceback

from converter.module.ppt_slide_renderer import (
    render_ppt_slides_to_images
)


PREVIEW_FOLDER = os.path.join(
    "outputs",
    "preview_images"
)


def generate_slide_preview(ppt_path):
    try:
        print(
            f"Generating preview for: {ppt_path}"
        )

        # Generate temp images
        slide_images = render_ppt_slides_to_images(
            ppt_path
        )

        print(
            f"Generated temp images: {slide_images}"
        )

        if not slide_images:
            return {
                "success": False,
                "images": [],
                "error": "No images generated"
            }

        # Create permanent preview folder
        os.makedirs(
            PREVIEW_FOLDER,
            exist_ok=True
        )

        # Clear old preview images
        for file in os.listdir(PREVIEW_FOLDER):
            file_path = os.path.join(
                PREVIEW_FOLDER,
                file
            )

            try:
                os.remove(file_path)
            except:
                pass

        image_data = []

        for img_path in slide_images:

            if os.path.exists(img_path):

                filename = os.path.basename(
                    img_path
                )

                permanent_path = os.path.join(
                    PREVIEW_FOLDER,
                    filename
                )

                # Copy temp image → permanent folder
                shutil.copy(
                    img_path,
                    permanent_path
                )

                image_data.append({
                    "filename": filename,
                    "filepath": permanent_path
                })

        print(
            f"Final preview images: {image_data}"
        )

        return {
            "success": True,
            "images": image_data
        }

    except Exception as e:
        print(
            "SLIDE PREVIEW ERROR:"
        )

        traceback.print_exc()

        return {
            "success": False,
            "images": [],
            "error": str(e)
        }