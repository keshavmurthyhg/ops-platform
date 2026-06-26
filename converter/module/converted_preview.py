import os
import shutil
import traceback
import time

from converter.module.ppt_slide_renderer import render_ppt_slides_to_images

PREVIEW_FOLDER = os.path.join("outputs", "preview_images")


def generate_slide_preview(ppt_path, skip_title_slides=True):
    """
    Render PPT slides to PNG images with a unique session timestamp prefix.
    The timestamp prefix busts the browser cache between conversions — each
    new conversion produces filenames like 1750000000_slide_1.png that the
    browser has never seen before.
    """
    try:
        print(f"Generating preview for: {ppt_path}  skip_titles={skip_title_slides}")

        slide_images = render_ppt_slides_to_images(
            ppt_path,
            skip_title_slides=skip_title_slides
        )

        print(f"Generated temp images: {slide_images}")

        if not slide_images:
            return {"success": False, "images": [], "error": "No images generated"}

        os.makedirs(PREVIEW_FOLDER, exist_ok=True)

        # Clear ALL old preview images from previous sessions
        for f in os.listdir(PREVIEW_FOLDER):
            try:
                os.remove(os.path.join(PREVIEW_FOLDER, f))
            except Exception:
                pass

        # Unique timestamp prefix — guarantees new URLs the browser never cached
        ts_prefix = str(int(time.time()))

        image_data = []
        for img_path in slide_images:
            if os.path.exists(img_path):
                orig_name      = os.path.basename(img_path)   # e.g. slide_1.png
                stamped_name   = f"{ts_prefix}_{orig_name}"   # e.g. 1750000000_slide_1.png
                permanent_path = os.path.join(PREVIEW_FOLDER, stamped_name)
                shutil.copy(img_path, permanent_path)
                image_data.append({
                    "filename": stamped_name,
                    "filepath": permanent_path
                })

        print(f"Final preview images: {image_data}")
        return {"success": True, "images": image_data, "ts_prefix": ts_prefix}

    except Exception as e:
        print("SLIDE PREVIEW ERROR:")
        traceback.print_exc()
        return {"success": False, "images": [], "error": str(e)}
