from io import BytesIO

from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


class UnsupportedAnalysisDocument(ValueError):
    pass


def extract_text(content: bytes, extension: str, max_chars: int) -> str:
    extension = extension.lower()
    text = ""

    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    elif extension == ".docx":
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    elif extension in {".txt", ".csv", ".rtf"}:
        text = content.decode("utf-8", errors="ignore")
    elif extension in {".xlsx", ".xlsm"}:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        lines: list[str] = []
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
        for slide in presentation.slides:
            for shape in slide.shapes:
                shape_text = getattr(shape, "text", "")
                if shape_text:
                    slide_lines.append(str(shape_text))
        text = "\n".join(slide_lines)
    elif extension in {".jpg", ".jpeg", ".png"}:
        raise UnsupportedAnalysisDocument(
            "Image documents are stored safely, but this release does not run OCR. "
            "Upload a PDF or text-based copy for AI extraction."
        )
    else:
        raise UnsupportedAnalysisDocument(
            f"AI extraction is not available for {extension or 'this file type'} yet."
        )

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        raise UnsupportedAnalysisDocument(
            "No readable text was found. If this is a scanned document, upload a "
            "text-searchable PDF."
        )
    return normalized[:max_chars]
