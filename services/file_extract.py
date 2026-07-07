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
    raise ValueError("Only .docx, .pdf and .txt Method Statement files are supported.")


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


def _compact_text(value: str) -> str:
    return "".join(str(value or "").split()).lower()


# Chinese and English action verbs that mark a real physical work step.
# Includes testing & commissioning verbs (測試/檢查/確認/接駁) so T&C method
# statements such as BMU / gondola testing keep their real steps.
STEP_ACTION_TERMS = [
    "拆", "安裝", "搭", "吊", "搬", "運", "傳", "清", "封閉", "移除", "鋪", "綁", "紮",
    "澆", "挖", "焊", "切割", "鑽", "測試", "檢查", "確認", "接駁", "調試", "啟動",
    "set up", "install", "erect", "remove", "dismantle",
    "transport", "carry out", "lift", "hoist", "lower", "pour", "excavate", "weld",
    "cut", "drill", "deliver", "position", "inspect", "test", "check", "connect",
    "energize", "commission", "verify", "witness",
]

# Suffixes that mark a document title or section heading when the line is short
# and has no action verb, e.g. 拆棚施工方案 / 安全程序及措施 / 工地要求.
_HEADING_SUFFIXES = ("方案", "方法書", "程序", "措施", "安排", "要求", "守則", "規定", "清單", "注意事項", "工序")

# Lines starting with these are safety rules / control measures, not steps.
_CONTROL_STARTERS = ("必須", "嚴禁", "不得", "切勿", "確保", "所有工人", "工人須", "工人必須", "如遇", "如有", "如因", "為免", "為防")


def clean_extracted_steps(raw_steps: list[str], titles: list[str] | None = None, max_steps: int = 14) -> list[str]:
    """Keep only true physical work steps; drop titles, headings and controls."""
    title_keys = {_compact_text(title) for title in (titles or []) if title}
    always_blocked_terms = [
        "施工方案",
        "methodstatement",
        "安全程序及措施",
        "拆棚之程序",
        "riskassessment",
        "tableofcontents",
    ]
    blocked_terms = [
        "安全準備",
        "準備工作",
        "適用法例",
        "工地要求",
        "拆棚後安排",
        "個人防護",
        "ppe",
        "訓練",
        "permit",
        "許可證",
        "必須",
        "嚴禁",
        "如遇天氣",
        "惡劣天氣",
        "toolbox",
        "工具箱",
    ]
    steps: list[str] = []
    for raw in raw_steps:
        clean = str(raw or "").strip(" \t-*0123456789.)、")
        compact = _compact_text(clean)
        if not clean or len(compact) < 6:
            continue
        if compact in title_keys or any(compact == title or compact in title for title in title_keys):
            continue
        if any(term in compact for term in always_blocked_terms):
            continue
        # Concatenated English fragments from drawings / table cells such as
        # "Cageupbutton" or "T&CProcedureof" are labels, not work steps.
        if re.fullmatch(r"[A-Za-z&()/\-.0-9]+", clean) and len(clean) >= 8:
            continue
        # Component labels (buttons, switches, selectors) are not steps.
        if clean.lower().rstrip(" )").endswith(("button", "switch", "selector", "indicator", "checklist")):
            continue
        has_action = any(term in clean.lower() for term in STEP_ACTION_TERMS)
        # Short heading-like lines without an action verb are titles/headings.
        if not has_action and len(compact) <= 32 and clean.endswith(_HEADING_SUFFIXES):
            continue
        # Safety rules / control measures are not steps.
        if clean.startswith(_CONTROL_STARTERS):
            continue
        if any(term in compact for term in blocked_terms) and not has_action:
            continue
        if clean not in steps:
            steps.append(clean[:260])
        if len(steps) >= max_steps:
            break
    return steps


def infer_steps_from_ms_text(text: str, max_steps: int = 14) -> list[str]:
    def normalize_step(value: str) -> str:
        clean = re.sub(r"\s+", "", value.strip())
        clean = re.sub(r"^[一二三四五六七八九十\d]+[\.、:：)\)]", "", clean)
        clean = re.sub(r"(.{2,12})\1{2,}", r"\1", clean)
        return clean.strip(" ：:.-")

    def normalize_line(value: str) -> str:
        clean = re.sub(r"\s+", " ", value.strip())
        clean = re.sub(r"^\s*\d+\s*[\.)、]?\s*", "", clean)
        clean = clean.replace(" /", "/").replace("/ ", "/")
        clean = clean.replace(" 。", "。").replace(" ，", "，")
        clean = re.sub(r"(.{6,20})\1{1,}", r"\1", clean)
        return clean.strip(" ：:.-")

    def is_heading_or_control(value: str) -> bool:
        clean = normalize_step(value)
        if len(clean) < 6 or len(clean) > 240:
            return True
        if re.search(r"(.{3,12})\1{1,}", clean):
            return True
        heading_terms = ["施工方案", "安全程序及措施", "安全準備", "準備工作", "拆棚後安排", "適用法例", "工地要求", "圖一", "圖二"]
        if any(term in clean for term in heading_terms) and len(clean) <= 32:
            return True
        control_starts = ["必須", "所有", "每日", "如遇", "如因", "如竹棚", "為免", "嚴禁", "參加", "合資格", "派遣", "安裝足夠", "有關實際"]
        if any(clean.startswith(term) for term in control_starts):
            return True
        control_terms = ["大原則", "訓練", "佩帶", "安全帽", "安全帶", "嚴禁", "檢查", "記錄", "提醒工人", "非作業人員"]
        action_terms = ["拆除", "拆卸", "傳遞", "運走", "清走", "安裝", "封閉"]
        if any(term in clean for term in control_terms) and not any(term in clean for term in action_terms):
            return True
        return False

    def unique_append(target: list[str], value: str) -> None:
        clean = normalize_line(value)
        compact = normalize_step(clean)
        if clean and clean not in target and not is_heading_or_control(compact):
            target.append(clean[:260])

    lines = (text or "").splitlines()

    # Prefer the real construction sequence section, e.g. "二. 拆棚工序".
    in_sequence = False
    section_steps: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        compact = normalize_step(line)
        idx += 1
        if not compact:
            continue
        if any(marker in compact for marker in ["拆棚工序", "施工工序", "施工程序", "工作程序", "工作步驟"]):
            in_sequence = True
            continue
        if in_sequence and re.match(r"^[ABC]\)?|^[一二三四五六七八九十][\.:：]", line) and section_steps:
            break
        if in_sequence and re.match(r"^\s*\d+[\.)、]\s*", line):
            combined = line
            while idx < len(lines):
                next_line = lines[idx].strip()
                if not next_line:
                    idx += 1
                    continue
                if re.match(r"^\s*\d+[\.)、]\s*", next_line) or re.match(r"^[ABC]\)?|^[一二三四五六七八九十][\.:：]", next_line):
                    break
                compact_next = normalize_step(next_line)
                if (
                    any(stop in compact_next for stop in ["有限公司", "Tel", "Fax", "____", "WINGLEE", "SCAFFOLDING", "HennessyRoad"])
                    or re.fullmatch(r"\d+/\d+", compact_next)
                ):
                    idx += 1
                    continue
                next_line = re.sub(r"[（(]\s*圖[一二三四五六七八九十\d]+\s*[）)]", "", next_line).strip()
                if not next_line:
                    idx += 1
                    continue
                combined += next_line
                idx += 1
            unique_append(section_steps, combined)
            if len(section_steps) >= max_steps:
                return section_steps
    if section_steps:
        return section_steps[:max_steps]

    steps: list[str] = []
    skip_first_cells = {
        "work activity",
        "project / area",
        "severity (s)",
        "likelihood (l)",
        "risk score",
        "prepared by",
    }
    for line in lines:
        cells = [cell.strip() for cell in line.split(" | ")]
        if len(cells) < 5:
            continue
        first_cell = normalize_step(cells[0])
        if not first_cell or first_cell.lower() in skip_first_cells:
            continue
        unique_append(steps, first_cell)
        if len(steps) >= max_steps:
            return steps

    markers = ("step", "sequence", "procedure", "work sequence", "工序", "程序", "步驟")
    for line in lines:
        clean = normalize_step(line)
        if not clean or len(clean) < 8:
            continue
        lower = clean.lower()
        if lower.startswith(("method statement", "risk assessment", "table of contents")):
            continue
        numbered_line = bool(re.match(r"^\s*(\d+[\.)、]|step\s+\d+)", line, flags=re.IGNORECASE))
        looks_like_step = numbered_line or any(marker in lower for marker in markers)
        if looks_like_step:
            unique_append(steps, clean)
        if len(steps) >= max_steps:
            break
    return steps
