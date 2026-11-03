"""Safe, local-only text extraction for user-supplied source documents."""

import hashlib
import io
import re
import textwrap
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import PurePosixPath

from pypdf import PdfReader


MAX_SOURCE_BYTES = 5_000_000
MAX_EXTRACTED_CHARS = 100_000
MAX_SOURCE_STATEMENTS = 100
MAX_DOCX_ENTRIES = 200
MAX_DOCX_EXPANDED_BYTES = 10_000_000
MAX_PDF_PAGES = 100
MAX_STATEMENT_CHARS = 2000
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".docx", ".pdf"}
WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class SourceError(Exception):
    """Base class for safe source-extraction errors."""


class SourceTooLarge(SourceError):
    """The uploaded file or extracted text exceeds configured limits."""


class UnsupportedSource(SourceError):
    """The uploaded file type is not supported."""


class SourceExtractionError(SourceError):
    """The source could not be safely converted to text."""


def _safe_filename(filename: str | None) -> str:
    raw = (filename or "").replace("\\", "/")
    name = PurePosixPath(raw).name
    name = "".join(char for char in name if char.isprintable() and char not in '< >:"|?*')
    name = name.strip().strip(".")
    if not name:
        raise SourceExtractionError("The uploaded file must have a valid filename.")
    return name[:180]


def _extract_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_DOCX_ENTRIES:
                raise SourceTooLarge("The Word document contains too many internal files.")
            expanded_size = sum(item.file_size for item in entries)
            if expanded_size > MAX_DOCX_EXPANDED_BYTES:
                raise SourceTooLarge("The Word document expands beyond the safe extraction limit.")
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
    except SourceError:
        raise
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise SourceExtractionError("The Word document is invalid or cannot be read.") from exc

    paragraphs = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{WORD_NAMESPACE}t":
                parts.append(node.text or "")
            elif node.tag in {f"{WORD_NAMESPACE}tab", f"{WORD_NAMESPACE}br"}:
                parts.append(" ")
        value = "".join(parts).strip()
        if value:
            paragraphs.append(value)
    return "\n\n".join(paragraphs)


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise SourceExtractionError("Password-protected PDFs are not supported.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise SourceTooLarge("The PDF exceeds the 100-page extraction limit.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except SourceError:
        raise
    except Exception as exc:
        raise SourceExtractionError("The PDF is invalid or its text could not be extracted.") from exc
    return "\n\n".join(page.strip() for page in pages if page.strip())


def _split_long_text(value: str) -> list[str]:
    if len(value) <= MAX_STATEMENT_CHARS:
        return [value]
    chunks = []
    for sentence in re.split(r"(?<=[.!?])\s+", value):
        if not sentence:
            continue
        if len(sentence) <= MAX_STATEMENT_CHARS:
            candidate = f"{chunks[-1]} {sentence}" if chunks else sentence
            if chunks and len(candidate) <= MAX_STATEMENT_CHARS:
                chunks[-1] = candidate
            else:
                chunks.append(sentence)
            continue
        chunks.extend(
            textwrap.wrap(
                sentence,
                width=MAX_STATEMENT_CHARS,
                break_long_words=True,
                break_on_hyphens=False,
            )
        )
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def split_into_statements(extracted_text: str) -> list[str]:
    normalized = extracted_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n")).strip()
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", normalized) if item.strip()]
    statements = []
    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if len(lines) > 1 and all(
            re.match(r"^(?:[-*•]|\d+[.)])\s+", line) for line in lines
        ):
            units = [re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", line) for line in lines]
        else:
            units = [" ".join(lines)]
        for unit in units:
            statements.extend(_split_long_text(unit))
            if len(statements) > MAX_SOURCE_STATEMENTS:
                raise SourceTooLarge(
                    "The document contains more than 100 separate statements. Split it into smaller files."
                )
    return statements


def extract_source_document(filename: str | None, content: bytes) -> dict:
    """Extract text, preserve a content hash, and return reviewable statement-sized chunks."""
    if len(content) > MAX_SOURCE_BYTES:
        raise SourceTooLarge("Source files must be 5 MB or smaller.")
    safe_name = _safe_filename(filename)
    extension = PurePosixPath(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedSource("Supported source files are TXT, Markdown, CSV, DOCX, and PDF.")

    if extension == ".docx":
        extracted = _extract_docx(content)
    elif extension == ".pdf":
        extracted = _extract_pdf(content)
    else:
        try:
            extracted = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SourceExtractionError("Text files must use UTF-8 encoding.") from exc
        if "\x00" in extracted:
            raise SourceExtractionError("The uploaded file does not appear to be a UTF-8 text document.")

    extracted = extracted.replace("\x00", "").strip()
    if not extracted:
        raise SourceExtractionError(
            "No readable text was found. Scanned PDFs need OCR, which this prototype does not provide."
        )
    if len(extracted) > MAX_EXTRACTED_CHARS:
        raise SourceTooLarge("Extracted text exceeds 100,000 characters. Split the document and retry.")

    statements = split_into_statements(extracted)
    if not statements:
        raise SourceExtractionError("No usable statements could be extracted from this file.")

    digest = hashlib.sha256(content).hexdigest()
    return {
        "filename": safe_name,
        "source_label": f"{safe_name} (SHA-256: {digest})",
        "sha256": digest,
        "character_count": len(extracted),
        "statement_count": len(statements),
        "statements": statements,
    }
