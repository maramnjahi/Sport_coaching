from __future__ import annotations

import fitz


def extract_pdf_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[tuple[int, str]] = []
    try:
        for index in range(len(document)):
            page = document.load_page(index)
            raw = page.get_text("text") or ""
            normalized = raw.strip()
            if normalized:
                pages.append((index + 1, normalized))
    finally:
        document.close()
    return pages
