import json

from config import MAX_DOCUMENT_BYTES
from safety import selected_file
from reader_worker import run_reader


def read_pdf(selected_path, start_page=1, max_pages=5, max_characters=12000):
    if not (1 <= max_pages <= 5 and 1 <= max_characters <= 12000):
        raise ValueError("Use at most 5 pages and 12,000 characters per read.")
    return run_reader("pdf", [str(selected_path)], {
        "start_page": start_page, "max_pages": max_pages,
        "max_characters": max_characters})


def _read_pdf(
    selected_path,
    start_page=1,
    max_pages=5,
    max_characters=12000,
):
    from pypdf import PdfReader
    path = selected_file(selected_path, MAX_DOCUMENT_BYTES)

    if not path.is_file():
        raise ValueError("Select a PDF file.")

    if start_page < 1 or max_pages < 1 or max_characters < 1:
        raise ValueError("Page numbers and limits must be positive.")

    with path.open("rb") as file:
        reader = PdfReader(file)

        if reader.is_encrypted:
            if not reader.decrypt(""):
                raise ValueError(
                    "This PDF requires a password. "
                    "Password entry is not connected yet."
                )

        total_pages = len(reader.pages)

        if start_page > total_pages:
            raise ValueError("The requested page does not exist.")

        pages = []
        remaining = max_characters
        text_cut_off = False

        end_page = min(
            start_page - 1 + max_pages,
            total_pages,
        )

        for index in range(start_page - 1, end_page):
            if remaining <= 0:
                break

            text = reader.pages[index].extract_text() or ""
            content = text[:remaining]

            pages.append({
                "page_number": index + 1,
                "content": content,
                "no_text_extracted": not text.strip(),
            })

            remaining -= len(content)

            if len(content) < len(text):
                text_cut_off = True
                break

        last_page = pages[-1]["page_number"]

        return {
            "path": str(path),
            "reader": "pdf_text",
            "total_pages": total_pages,
            "start_page": start_page,
            "last_page_read": last_page,
            "pages": pages,
            "partial_document": (
                start_page != 1
                or last_page < total_pages
                or text_cut_off
            ),
            "text_cut_off": text_cut_off,
            "note": (
                "Extracted text only. Images and diagrams were not "
                "interpreted. Pages without extracted text may be "
                "blank, scanned, or require another extraction method."
            ),
        }


if __name__ == "__main__":
    selected = input("Paste a PDF path: ").strip().strip('"')

    try:
        result = read_pdf(selected)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as error:
        print(f"Could not read the PDF: {error}")