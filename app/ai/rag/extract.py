"""
Text extraction for the supported upload types: PDF, plain text, Markdown.

Validation happens here too, so a bad file is rejected before any work is
done: unknown extensions, declared size over the limit, empty content, and
PDFs that yield no text (scanned images need OCR, which is out of scope).
"""
import io
import re
from dataclasses import dataclass
from typing import Optional

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown",
                        ".markdown": "text/markdown"}


class UnsupportedDocumentError(ValueError):
    """The file type or content cannot be ingested."""


@dataclass
class ExtractedText:
    text: str
    content_type: str
    page_count: Optional[int] = None


def extension_of(filename: str) -> str:
    name = (filename or "").lower().strip()
    dot = name.rfind(".")
    return name[dot:] if dot >= 0 else ""


def validate_upload(filename: str, size_bytes: int, max_bytes: int) -> str:
    """Return the canonical content type or raise ``UnsupportedDocumentError``."""
    extension = extension_of(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentError(
            f"Unsupported file type '{extension or 'none'}'. Allowed: PDF, TXT, Markdown."
        )
    if size_bytes <= 0:
        raise UnsupportedDocumentError("The uploaded file is empty.")
    if size_bytes > max_bytes:
        raise UnsupportedDocumentError(
            f"File is {size_bytes / 1024 / 1024:.1f} MB; the limit is {max_bytes / 1024 / 1024:.0f} MB."
        )
    return SUPPORTED_EXTENSIONS[extension]


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnsupportedDocumentError("Could not decode the file as text.")


def _extract_pdf(data: bytes) -> ExtractedText:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001
        raise UnsupportedDocumentError("The PDF could not be read.") from exc
    text = "\n\n".join(pages)
    return ExtractedText(text=text, content_type="application/pdf", page_count=len(pages))


def clean_text(text: str) -> str:
    """Normalise whitespace and strip control characters without touching content."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(filename: str, data: bytes) -> ExtractedText:
    """Extract and clean text from a supported file. Raises on unusable input."""
    extension = extension_of(filename)
    if extension == ".pdf":
        extracted = _extract_pdf(data)
    elif extension in SUPPORTED_EXTENSIONS:
        extracted = ExtractedText(text=_decode_text(data), content_type=SUPPORTED_EXTENSIONS[extension])
    else:
        raise UnsupportedDocumentError(f"Unsupported file type '{extension or 'none'}'.")

    extracted.text = clean_text(extracted.text)
    if len(extracted.text) < 20:
        raise UnsupportedDocumentError(
            "No readable text was found in the file (scanned PDFs need OCR first)."
        )
    return extracted
