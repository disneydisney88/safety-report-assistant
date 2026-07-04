from __future__ import annotations

from io import BytesIO
import re
from typing import BinaryIO

from docx import Document
from pypdf import PdfReader


MAX_EXTRACT_CHARS = 18000


def _read_bytes(file_obj: BinaryIO | BytesIO | bytes) -> bytes:
    if isinstance(file_obj, bytes):
        return file_obj
    if hasattr(file_obj, "getvalue"):
        return file_obj.getvalue()
    return file_obj.read()


def extract_text_from_upload(file_obj: BinaryIO | BytesIO | bytes, file_name: str) -> str:
    suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    raw = _read_bytes(file_obj)
    if suffix == "docx":
        return extract_docx_text(raw)
    if suffix == "pdf":
        return extract_pdf_text(raw)
    if suffix == "txt":
        return raw.decode("utf-8", errors="ignore")[:MAX_EXTRACT_CHARS]
    raise ValueError("Only .docx, .pdf and .txt Method Statement files are supported in this MVP.")


def extract_docx_text(raw: bytes) -> str:
    doc = Document(BytesIO(raw))
    parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " | ") for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)[:MAX_EXTRACT_CHARS]


def extract_pdf_text(raw: bytes) -> str:
    reader = PdfReader(BytesIO(raw))
    parts: list[str] = []
    for page in reader.pages[:40]:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(text)
    extracted = "\n".join(parts)[:MAX_EXTRACT_CHARS]
    if not extracted.strip():
        raise ValueError("No selectable text found in this PDF. It may be a scanned PDF; OCR support is not enabled yet.")
    return extracted


def infer_steps_from_ms_text(text: str, max_steps: int = 14) -> list[str]:
    steps: list[str] = []
    skip_first_cells = {
        "work activity",
        "project / area",
        "severity (s)",
        "likelihood (l)",
        "risk score",
        "prepared by",
    }
    for line in (text or "").splitlines():
        cells = [cell.strip() for cell in line.split(" | ")]
        if len(cells) < 5:
            continue
        first_cell = cells[0].strip(" \t-*•0123456789.)、")
        if not first_cell or first_cell.lower() in skip_first_cells:
            continue
        if 6 <= len(first_cell) <= 180 and first_cell not in steps:
            steps.append(first_cell)
        if len(steps) >= max_steps:
            return steps

    markers = ("step", "sequence", "procedure", "method", "工序", "步驟", "程序", "施工")
    for line in (text or "").splitlines():
        clean = line.strip(" \t-*•0123456789.)、")
        if not clean or len(clean) < 8:
            continue
        lower = clean.lower()
        if lower.startswith(("method statement", "risk assessment", "table of contents")):
            continue
        numbered_line = bool(re.match(r"^\s*(\d+[\.)、]|step\s+\d+)", line, flags=re.IGNORECASE))
        looks_like_step = numbered_line or any(marker in lower for marker in markers)
        if looks_like_step and clean not in steps:
            steps.append(clean[:240])
        if len(steps) >= max_steps:
            break
    return steps
