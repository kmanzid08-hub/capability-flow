from io import BytesIO

from docx import Document
from legacy_doc import extract_text as extract_legacy_doc_text
from openpyxl import load_workbook
from pptx import Presentation


class UnsupportedAnalysisDocument(ValueError):
    pass


TEXT_EXTRACTABLE_EXTENSIONS = {
    ".doc",
    ".docx",
    ".txt",
    ".csv",
    ".rtf",
    ".xlsx",
    ".xlsm",
    ".pptx",
}

CLAUDE_NATIVE_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


def is_claude_native_document(extension: str) -> bool:
    return extension.lower() in CLAUDE_NATIVE_EXTENSIONS


def extract_text(content: bytes, extension: str, max_chars: int) -> str:
    extension = extension.lower()
    text = ""

    if extension == ".doc":
        try:
            result = extract_legacy_doc_text(content)
            text = result.text
        except Exception as exc:
            raise UnsupportedAnalysisDocument(
                "The legacy Word .doc file could not be read. "
                "Try opening it in Word and saving it again if the file is damaged."
            ) from exc
    elif extension == ".docx":
        document = Document(BytesIO(content))
        lines: list[str] = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                lines.append(paragraph.text)

        for table in document.tables:
            for row in table.rows:
                values = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if values:
                    lines.append(" | ".join(values))

        text = "\n".join(lines)
    elif extension in {".txt", ".csv", ".rtf"}:
        text = content.decode("utf-8", errors="ignore")
    elif extension in {".xlsx", ".xlsm"}:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        lines = []
        for sheet in workbook.worksheets:
            lines.append(f"Sheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                values = [str(value) for value in row if value not in (None, "")]
                if values:
                    lines.append(" | ".join(values))
        text = "\n".join(lines)
    elif extension == ".pptx":
        presentation = Presentation(BytesIO(content))
        slide_lines: list[str] = []
        for slide_number, slide in enumerate(presentation.slides, start=1):
            slide_lines.append(f"Slide {slide_number}")
            for shape in slide.shapes:
                shape_text = getattr(shape, "text", "")
                if shape_text and str(shape_text).strip():
                    slide_lines.append(str(shape_text))
        text = "\n".join(slide_lines)
    elif is_claude_native_document(extension):
        raise UnsupportedAnalysisDocument(
            "This file type should be analyzed directly by Claude rather than "
            "through local text extraction."
        )
    else:
        raise UnsupportedAnalysisDocument(
            f"AI extraction is not available for {extension or 'this file type'} yet."
        )

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        raise UnsupportedAnalysisDocument("No readable text was found in this document.")
    return normalized[:max_chars]
