import io
import json

from safety import selected_file
from config import MODEL_ROOT
from image_utils import load_image
from reader_worker import run_reader


MODEL_FOLDER = MODEL_ROOT / "ocr"
_engine = None


def get_engine():
    global _engine

    if _engine is None:
        from rapidocr import RapidOCR
        MODEL_FOLDER.mkdir(parents=True, exist_ok=True)

        print("Loading OCR models; first run may download them...")

        _engine = RapidOCR(
            params={
                "Global.model_root_dir": str(MODEL_FOLDER),
            }
        )

    return _engine


def read_image_text(selected_path):
    return run_reader("ocr", [str(selected_path)])


def _read_image_text(selected_path):
    path = selected_file(selected_path)
    background = load_image(selected_path)
    width, height = background.size
    buffer = io.BytesIO()
    background.save(buffer, format="PNG")

    engine = get_engine()
    result = engine(buffer.getvalue())

    texts = getattr(result, "txts", None)
    scores = getattr(result, "scores", None)
    boxes = getattr(result, "boxes", None)

    lines = []

    if texts is not None:
        for index, text in enumerate(texts):
            confidence = (
                float(scores[index])
                if scores is not None
                else None
            )

            box = (
                boxes[index].tolist()
                if boxes is not None
                else None
            )

            lines.append({
                "text": str(text),
                "confidence": (
                    round(confidence, 3)
                    if confidence is not None
                    else None
                ),
                "box": box,
            })

    return {
        "path": str(path),
        "reader": "image_ocr",
        "image_width": width,
        "image_height": height,
        "lines": lines,
        "content": "\n".join(line["text"] for line in lines),
        "no_text_detected": not lines,
        "note": (
            "Automatically recognized text may contain errors "
            "or omissions. Reading order may mix columns. "
            "Confidence scores are not guaranteed accuracy. "
            "Images, icons and diagram relationships were not interpreted."
        ),
    }


def main():
    selected = input(
        "Paste an image path: "
    ).strip().strip('"')

    try:
        result = read_image_text(selected)

        if result["no_text_detected"]:
            print(
                "No text was recognized. This does not prove "
                "the image contains no text."
            )
            return

        print("\n--- Extracted text ---\n")
        print(result["content"])

        print("\n--- Recognition details ---")
        print(json.dumps(
            result["lines"],
            indent=2,
            ensure_ascii=False,
        ))

    except Exception as error:
        print(f"Could not read image text: {error}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nOCR stopped.")