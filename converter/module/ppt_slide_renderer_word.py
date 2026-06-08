import os
import tempfile
import win32com.client
import pythoncom
subprocess.run([
    "libreoffice",

libreoffice_path = r"C:\Program Files\LibreOffice\program\soffice.exe"

subprocess.run([
    libreoffice_path,
# -----------------------------------
# Extract all visible text from slide
# -----------------------------------
def get_slide_text(slide):
    texts = []

    try:
        for shape in slide.Shapes:
            try:
                if shape.HasTextFrame:
                    if shape.TextFrame.HasText:
                        text = shape.TextFrame.TextRange.Text.strip()
                        if text:
                            texts.append(text.lower())
            except:
                continue
    except:
        pass

    return " ".join(texts)


# -----------------------------------
# Skip unwanted slides
# -----------------------------------
def should_skip_slide(slide):
    """
    Skip:
    - blank slides
    - divider slides
    - title-only slides
    """

    slide_text = get_slide_text(slide)
    text_lower = slide_text.lower().strip()

    print(f"Slide text detected: {slide_text}")

    if slide.Shapes.Count == 0:
        print("Skipping blank slide")
        return True

    shape_count = slide.Shapes.Count
    picture_count = 0
    large_picture_found = False

    for shape in slide.Shapes:
        try:
            # Picture type
            if shape.Type == 13:
                picture_count += 1

                width = shape.Width
                height = shape.Height

                print(f"Picture size: {width} x {height}")

                # Real screenshot/image occupies large area
                if width > 300 and height > 200:
                    large_picture_found = True

        except Exception as e:
            print(f"Shape check error: {e}")

    word_count = len(text_lower.split())

    print(
        f"Shape count: {shape_count}, "
        f"Picture count: {picture_count}, "
        f"Word count: {word_count}, "
        f"Large picture: {large_picture_found}"
    )

    # Skip low-content divider/title slides
    if not large_picture_found and word_count <= 10:
        print("Skipping divider/title slide")
        return True

    return False

# -----------------------------------
# Export full rendered slides
# -----------------------------------
def render_ppt_slides_to_images(ppt_path):
    """
    Export slides as full rendered PNGs.
    Keeps:
    - annotations
    - arrows
    - highlights
    - screenshots
    - textboxes

    Removes:
    - divider slides
    - repeated title slides
    """

    powerpoint = None
    presentation = None

    try:
        pythoncom.CoInitialize()

        temp_dir = tempfile.mkdtemp()
        ppt_path = os.path.abspath(ppt_path)

        powerpoint = win32com.client.Dispatch(
            "PowerPoint.Application"
        )

        powerpoint.Visible = 1

        presentation = powerpoint.Presentations.Open(
            ppt_path,
            ReadOnly=1,
            WithWindow=True
        )

        image_paths = []
        export_index = 1

        total_slides = presentation.Slides.Count
        print(f"Total slides found: {total_slides}")

        for i in range(1, total_slides + 1):
            slide = presentation.Slides(i)

            print(f"Checking slide {i}")

            if should_skip_slide(slide):
                continue

            image_path = os.path.join(
                temp_dir,
                f"slide_{export_index}.png"
            )

            print(f"Exporting slide {i}")

            slide.Export(
                image_path,
                "PNG"
            )

            if os.path.exists(image_path):
                print(f"Exported: {image_path}")
                image_paths.append(image_path)
                export_index += 1
            else:
                print(f"Export failed for slide {i}")

        print(
            f"Final exported slides: {len(image_paths)}"
        )

        return image_paths

    except Exception as e:
        print(
            f"PowerPoint export failed: {e}"
        )
        return []

    finally:
        try:
            if presentation:
                presentation.Close()
        except:
            pass

        try:
            if powerpoint:
                powerpoint.Quit()
        except:
            pass

        try:
            pythoncom.CoUninitialize()
        except:
            pass