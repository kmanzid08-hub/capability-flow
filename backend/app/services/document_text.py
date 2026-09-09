import csv
import html
import json
import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree

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
    ".text",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".rtf",
    ".json",
    ".jsonl",
    ".xml",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
    ".xlsx",
    ".xlsm",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
}

GEMINI_NATIVE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif"}


EMBEDDED_IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_WORD_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def _is_zip_container(content: bytes) -> bool:
    return content.startswith(_ZIP_SIGNATURES)


def _is_ooxml_word_document(content: bytes) -> bool:
    if not _is_zip_container(content):
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = {name.replace("\\", "/").lower() for name in archive.namelist()}
        return "word/document.xml" in names
    except zipfile.BadZipFile:
        return False


def detect_word_content_type(content: bytes, extension: str) -> str:
    """Return the actual readable Word-like format when it can be identified safely."""
    extension = extension.lower()
    if extension not in {".doc", ".docx"}:
        return extension

    leading = content[:8192].lstrip()
    lower = leading.lower()

    if _is_ooxml_word_document(content):
        return ".docx"
    if content.startswith(_WORD_OLE_SIGNATURE):
        return ".doc"
    if lower.startswith(b"{\\rtf"):
        return ".rtf"
    if b"<html" in lower[:4096] or lower.startswith(b"<!doctype html"):
        return ".html"
    if lower.startswith(b"<?xml") and (
        b"worddocument" in lower[:8192]
        or b"wordprocessingml" in lower[:8192]
        or b"<w:document" in lower[:8192]
    ):
        return ".xml"
    return extension


def extract_embedded_document_images(
    content: bytes,
    extension: str,
    max_images: int,
) -> list[tuple[bytes, str, str]]:
    """Extract supported embedded images from OOXML Word documents without rendering them."""
    if detect_word_content_type(content, extension) != ".docx":
        return []

    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            candidates: list[tuple[int, str, str]] = []
            for info in archive.infolist():
                name = info.filename.replace("\\", "/")
                lower_name = name.lower()
                if not lower_name.startswith("word/media/") or info.file_size <= 0:
                    continue

                suffix = "." + lower_name.rsplit(".", 1)[-1] if "." in lower_name else ""
                mime_type = EMBEDDED_IMAGE_MEDIA_TYPES.get(suffix)
                if mime_type is None or info.file_size > 12 * 1024 * 1024:
                    continue
                candidates.append((info.file_size, name, mime_type))

            # Full-page scans are normally much larger than logos/icons, so prioritize
            # the largest images when a Word file contains more media than our vision cap.
            candidates.sort(key=lambda item: item[0], reverse=True)
            images: list[tuple[bytes, str, str]] = []
            for _, name, mime_type in candidates[:max_images]:
                image_data = archive.read(name)
                if image_data:
                    images.append((image_data, mime_type, name.rsplit("/", 1)[-1]))
            return images
    except zipfile.BadZipFile:
        return []


def is_gemini_native_document(extension: str) -> bool:
    return extension.lower() in GEMINI_NATIVE_EXTENSIONS


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _strip_markup(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\\s+", " ", text)


def _extract_rtf(content: bytes) -> str:
    text = _decode_text(content)
    text = re.sub(r"\\\\par[d]?\\b", "\n", text)
    text = re.sub(r"\\\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\\\[a-zA-Z]+-?\\d* ?", " ", text)
    return text.replace("{", " ").replace("}", " ").replace("\\", " ")


def _extract_delimited(content: bytes, delimiter: str) -> str:
    reader = csv.reader(_decode_text(content).splitlines(), delimiter=delimiter)
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in reader if row)


def _extract_odf(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            xml = archive.read("content.xml")
        root = ElementTree.fromstring(xml)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise UnsupportedAnalysisDocument("The OpenDocument file could not be read.") from exc
    chunks: list[str] = []
    for element in root.iter():
        if element.text and element.text.strip():
            chunks.append(element.text.strip())
        if element.tail and element.tail.strip():
            chunks.append(element.tail.strip())
    return "\n".join(chunks)


def _extract_word_xml_text(xml: bytes) -> str:
    """Recover visible WordprocessingML text even when python-docx rejects the package."""
    try:
        root = ElementTree.fromstring(xml)
        paragraphs: list[str] = []
        for element in root.iter():
            if element.tag.endswith("}p"):
                pieces = [
                    child.text or ""
                    for child in element.iter()
                    if child.tag.endswith("}t") and child.text
                ]
                joined = "".join(pieces).strip()
                if joined:
                    paragraphs.append(joined)
        if paragraphs:
            return "\n".join(paragraphs)

        pieces = [
            element.text or ""
            for element in root.iter()
            if element.tag.endswith("}t") and element.text
        ]
        return "\n".join(piece.strip() for piece in pieces if piece.strip())
    except ElementTree.ParseError:
        decoded = xml.decode("utf-8", errors="ignore")
        pieces = re.findall(r"(?is)<w:t(?:\\s+[^>]*)?>(.*?)</w:t>", decoded)
        cleaned = [html.unescape(re.sub(r"<[^>]+>", "", piece)).strip() for piece in pieces]
        return "\n".join(piece for piece in cleaned if piece)


def _extract_docx_xml_fallback(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
            lower_to_name = {name.replace("\\", "/").lower(): name for name in names}
            ordered_parts = ["word/document.xml"]
            ordered_parts.extend(
                sorted(
                    name for name in lower_to_name if re.fullmatch(r"word/header\\d+\\.xml", name)
                )
            )
            ordered_parts.extend(
                sorted(
                    name for name in lower_to_name if re.fullmatch(r"word/footer\\d+\\.xml", name)
                )
            )
            ordered_parts.extend(
                name
                for name in ("word/footnotes.xml", "word/endnotes.xml", "word/comments.xml")
                if name in lower_to_name
            )

            chunks: list[str] = []
            for logical_name in ordered_parts:
                actual_name = lower_to_name.get(logical_name)
                if actual_name is None:
                    continue
                recovered = _extract_word_xml_text(archive.read(actual_name)).strip()
                if recovered:
                    chunks.append(recovered)
            return "\n".join(chunks)
    except (zipfile.BadZipFile, KeyError):
        return ""


def _extract_docx_text(content: bytes) -> str:
    lines: list[str] = []
    try:
        document = Document(BytesIO(content))
        lines.extend(p.text for p in document.paragraphs if p.text.strip())
        for table in document.tables:
            for row in table.rows:
                values = [c.text.strip() for c in row.cells if c.text.strip()]
                if values:
                    lines.append(" | ".join(values))
    except Exception:
        # A partially damaged OOXML package can still contain a perfectly readable
        # word/document.xml, so fall through to direct XML recovery.
        pass

    text = "\n".join(lines).strip()
    if text:
        return text
    return _extract_docx_xml_fallback(content)


def _candidate_binary_strings(content: bytes) -> list[str]:
    ascii_strings = [
        match.decode("cp1252", errors="ignore")
        for match in re.findall(rb"[\\x20-\\x7e]{5,}", content)
    ]
    utf16_strings = [
        match.decode("utf-16le", errors="ignore")
        for match in re.findall(rb"(?:[\\x20-\\x7e]\\x00){5,}", content)
    ]

    seen: set[str] = set()
    output: list[str] = []
    for raw in [*utf16_strings, *ascii_strings]:
        cleaned = " ".join(raw.replace("\x00", " ").split()).strip()
        if len(cleaned) < 5 or cleaned in seen:
            continue
        letters = sum(character.isalpha() for character in cleaned)
        if letters < 3:
            continue
        alpha_ratio = letters / max(1, len(cleaned))
        if alpha_ratio < 0.18:
            continue
        # Skip common binary/container metadata that is not document evidence.
        lowered = cleaned.lower()
        if lowered.startswith(("microsoft office", "worddocument", "summaryinformation")):
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def _looks_like_recovered_document_text(text: str) -> bool:
    normalized = " ".join(text.split())
    if len(normalized) < 60:
        return False
    words = [word for word in normalized.split() if any(character.isalpha() for character in word)]
    return len(words) >= 10


def _extract_legacy_doc_text(content: bytes) -> str:
    primary_error: Exception | None = None
    try:
        extracted = str(extract_legacy_doc_text(content).text)
        if extracted and extracted.strip():
            return extracted
    except Exception as exc:
        primary_error = exc

    # Pure-Python last-resort recovery. Legacy binary Word files can store visible
    # text in compressed single-byte or UTF-16LE runs even when the higher-level
    # parser cannot reconstruct the document structure.
    recovered = "\n".join(_candidate_binary_strings(content)).strip()
    if _looks_like_recovered_document_text(recovered):
        return (
            "[Recovered from a legacy Microsoft Word document; formatting may be incomplete.]\n"
            + recovered
        )

    message = (
        "This appears to be a legacy Microsoft Word .doc file. Capability Flow tried "
        "automatic legacy Word recovery but could not recover enough readable text. "
        "Open the file in Word or LibreOffice and save it as .docx or PDF, then analyze it again."
    )
    raise UnsupportedAnalysisDocument(message) from primary_error


def _extract_word_like_text(content: bytes, declared_extension: str) -> str:
    actual = detect_word_content_type(content, declared_extension)
    if actual == ".docx":
        return _extract_docx_text(content)
    if actual == ".doc":
        return _extract_legacy_doc_text(content)
    if actual == ".rtf":
        return _extract_rtf(content)
    if actual in {".html", ".xml"}:
        return _strip_markup(_decode_text(content))

    # Some old Word workflows produce text-based files with a .doc suffix.
    decoded = _decode_text(content)
    if "\x00" not in decoded[:4096] and _looks_like_recovered_document_text(decoded):
        return decoded

    if declared_extension == ".doc":
        return _extract_legacy_doc_text(content)
    return _extract_docx_text(content)


def extract_text(content: bytes, extension: str, max_chars: int) -> str:
    extension = extension.lower()
    text = ""
    try:
        if extension in {".doc", ".docx"}:
            text = _extract_word_like_text(content, extension)
        elif extension in {".txt", ".text", ".md", ".markdown", ".yaml", ".yml"}:
            text = _decode_text(content)
        elif extension == ".csv":
            text = _extract_delimited(content, ",")
        elif extension == ".tsv":
            text = _extract_delimited(content, "\t")
        elif extension == ".rtf":
            text = _extract_rtf(content)
        elif extension in {".json", ".jsonl"}:
            raw = _decode_text(content)
            if extension == ".json":
                try:
                    text = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    text = raw
            else:
                text = raw
        elif extension in {".xml", ".html", ".htm"}:
            text = _strip_markup(_decode_text(content))
        elif extension in {".xlsx", ".xlsm"}:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
            lines = []
            for sheet in workbook.worksheets:
                lines.append(f"Sheet: {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    values = [str(v) for v in row if v not in (None, "")]
                    if values:
                        lines.append(" | ".join(values))
            text = "\n".join(lines)
            workbook.close()
        elif extension == ".pptx":
            presentation = Presentation(BytesIO(content))
            lines = []
            for number, slide in enumerate(presentation.slides, start=1):
                lines.append(f"Slide {number}")
                for shape in slide.shapes:
                    value = getattr(shape, "text", "")
                    if value and str(value).strip():
                        lines.append(str(value))
            text = "\n".join(lines)
        elif extension in {".odt", ".ods", ".odp"}:
            text = _extract_odf(content)
        elif is_gemini_native_document(extension):
            raise UnsupportedAnalysisDocument(
                "This file type should be analyzed directly by Gemini rather than "
                "through local text extraction."
            )
        else:
            raise UnsupportedAnalysisDocument(
                f"AI extraction is not available for {extension or 'this file type'} yet."
            )
    except UnsupportedAnalysisDocument:
        raise
    except Exception as exc:
        raise UnsupportedAnalysisDocument(
            f"The {extension or 'uploaded'} file could not be read after automatic recovery."
        ) from exc

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        if (
            extension in {".doc", ".docx"}
            and detect_word_content_type(content, extension) == ".docx"
        ):
            raise UnsupportedAnalysisDocument(
                "No readable text was found in this Word document. It may contain only images."
            )
        raise UnsupportedAnalysisDocument("No readable text was found in this document.")
    return normalized[:max_chars]
