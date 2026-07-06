"""Shared language helpers for RA report output.

Goals:
* Keep the final report in ONE selected language (plus standard safety
  abbreviations such as P, IC, S, L, LR, MR, HR, ALARP, PPE, CoP, PTW).
* Provide a deterministic English -> Chinese phrase map for the fixed strings
  that the local (non-AI) pipeline can emit, so Chinese reports do not mix in
  English boilerplate even when the AI backend is unavailable.
* Detect rows that still contain wrong-language content so the app can run an
  AI translation pass before export.

The Chinese wording below is reused verbatim from the existing reviewed
templates in this repository; this module does not invent new Chinese prose.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

CHINESE_LANGUAGES = {"Traditional Chinese", "Simplified Chinese"}

# Standard abbreviations that are allowed to stay in English inside a Chinese
# report. They are removed before "is this row still in English?" checks.
ALLOWED_ABBREVIATIONS = [
    "ALARP",
    "PPE",
    "CoP",
    "COP",
    "PTW",
    "OSH",
    "RL",
    "LR",
    "MR",
    "HR",
    "IC",
    "Form 5",
    "FORM 5",
]

_CJK_RE = re.compile(r"[一-鿿]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")

# Row keys whose values must never be rewritten by language cleanup:
# ratings keep the "P2 x S5 = 10 HR" format, IDs stay stable, and the
# original Method Statement step text is preserved as the source of truth.
PROTECTED_KEYS = {
    "source_step_id",
    "hazard_id",
    "initial_risk_rating",
    "residual_risk_rating",
    "source_step_text_original",
    "Source Step ID",
    "Hazard ID",
    "Initial Risk",
    "Residual Risk",
    "Source Step Original",
    "Hazard Category",
    "hazard_category",
}


def contains_cjk(text: Any) -> bool:
    return bool(_CJK_RE.search(str(text or "")))


def _strip_allowed_tokens(text: str) -> str:
    value = text
    for token in ALLOWED_ABBREVIATIONS:
        value = value.replace(token, " ")
    # Risk rating fragments such as "P2 x S5 = 10" are always allowed.
    value = re.sub(r"\b[PSL]\s?[1-5]\b", " ", value)
    return value


def has_substantial_english(text: Any) -> bool:
    """True when the text contains real English sentences/phrases, not just
    standard abbreviations or rating codes."""
    value = _strip_allowed_tokens(str(text or ""))
    words = _LATIN_WORD_RE.findall(value)
    return len(words) >= 3 or sum(len(word) for word in words) >= 18


# ---------------------------------------------------------------------------
# Deterministic English -> Traditional Chinese phrase map.
# Wording copied from the reviewed templates already used in this repository
# (docx_export cleanup map and the Chinese fallback rows in the RA page).
# Replacement is longest-phrase-first so full sentences win over fragments.
# ---------------------------------------------------------------------------
EN_ZH_TERMS: dict[str, str] = {
    "Confirm method statement, competent person requirement, permit-to-work, inspection points and emergency arrangement before work starts": "開工前確認施工方法書、合資格人士要求、工作許可證、檢查點及緊急安排",
    "Unsafe condition, unsafe act or failure mode associated with the confirmed work step": "與已確認工序相關的不安全狀況、不安全行為或失效模式",
    "Confirm with approved Method Statement and site-specific conditions": "根據已批准施工方法書及工地實際情況確認",
    "Cause to be confirmed against Method Statement / site condition": "根據施工方法書及工地實際情況確認成因",
    "Personal injury, property damage or unsafe work continuation": "人身受傷、財物損壞或在不安全情況下繼續工作",
    "Task-specific hazard to be verified against site condition": "須根據工地實際情況核實的工序危害",
    "Workers, supervisors, subcontractors and persons nearby": "工人、監督人員、分判商及附近人士",
    "Ensure all tools and materials are secured against falling": "確保所有工具及物料已固定防止墜下",
    "Unsafe condition, unsafe act or failure mode": "不安全狀況、不安全行為或失效模式",
    "Competent person for scaffold / platform inspection where applicable": "按需要由合資格人士檢查棚架 / 工作平台",
    "Working at height permit where required by site system": "按工地制度需要辦理高處工作許可",
    "Fall arrest system and independent lifeline where required": "按需要使用防墜系統及獨立救生繩",
    "Induction Training / Toolbox Talk / FCB / Zero Harm Lesson": "入職訓練 / 工具箱會議 / 現場控制簡介 / 零傷害課程",
    "Competent person has to inspect working platform": "合資格人士須檢查工作平台",
    "Guardrails and toe boards where applicable": "按需要設置護欄及踢腳板",
    "Confirm rescue arrangement for fall arrest": "確認防墜救援安排",
    "Inspect access equipment and work platform": "檢查通道設備及工作平台",
    "Remove tools/materials and close out inspection": "移走工具 / 物料及完成收工檢查",
    "Set up exclusion zone below work area": "在工作區下方設置禁區",
    "Set exclusion zone below work area": "在工作區下方設置禁區",
    "Inspect access equipment before use": "使用前檢查通道及工作設備",
    "Secure tools and materials against falling": "固定工具及物料防止墜下",
    "Workers shall wear full body harness": "工人須佩戴全身式安全帶",
    "Provide appropriate working platform": "提供適當工作平台",
    "Provide safe working platform": "提供安全工作平台",
    "Provide competent supervision": "提供合資格監督",
    "Workers not trained for the task": "工人未接受相關工序訓練",
    "No fixed anchoring point provided": "未提供固定錨固點",
    "Working area not fenced off": "工作區未適當圍封",
    "Lack of safety awareness": "安全意識不足",
    "No safety harness worn": "未佩戴安全帶",
    "Fence off the working area": "圍封工作區",
    "No proper access": "未提供適當通道",
    "Carry out work at height": "進行高處工作",
    "Access the work location": "前往工作位置",
    "To be confirmed by Safety Officer": "待安全主任確認",
    "To be verified by Safety Officer": "由安全主任核實",
    "To be confirmed": "待確認",
    "Fatality / Serious Injury": "死亡 / 嚴重受傷",
    "Serious injury": "嚴重受傷",
    "Fatality": "死亡",
    "Injury to persons below": "下方人士受傷",
    "Property damage": "財物損毀",
    "Fall of Person from height": "人員高處墮下",
    "Fall from height": "高處墮下",
    "Falling objects": "高空墮物",
    "Platform collapse": "平台倒塌",
    "Unsafe access": "通道不安全",
    "Weather effect": "天氣影響",
    "Adverse weather": "惡劣天氣",
    "Typhoon or Heavy Rainstorm": "颱風或暴雨",
    "Workers and persons nearby": "工人及附近人士",
    "Workers and public": "工人及公眾",
    "Workers / others nearby": "工人 / 附近其他人士",
    "People at the area": "工作區內人士",
    "People at area": "工作區內人士",
    "Members of public": "公眾",
    "and persons nearby": "及附近人士",
    "persons nearby": "附近人士",
    "Subcontractors": "分判商",
    "subcontractors": "分判商",
    "Supervisors": "監督人員",
    "supervisors": "監督人員",
    "Induction / task briefing / suitable PPE": "入職訓練 / 工序簡介 / 合適個人防護裝備",
    "Site Supervisor / Safety Officer": "工地監督 / 安全主任",
    "Hong Kong OSH legislation": "香港職安健法例",
    "Labour Department guidance": "勞工處指引",
    "relevant Codes of Practice": "相關工作守則",
    "Field control briefing": "現場控制簡介",
    "Pre-work briefing": "開工前簡介",
    "Supervisor control": "監督人員控制",
    "Suitable PPE": "合適個人防護裝備",
    "Access control": "出入管制",
    "Housekeeping": "工地整潔",
    "Safety gloves": "安全手套",
    "Safety helmet": "安全帽",
    "safety helmet": "安全帽",
    "Pre-work check": "開工前檢查",
    "Active monitoring": "施工中持續監察",
    "Close-out inspection and record": "收工檢查及記錄",
    "Close-out inspection": "收工檢查",
    "Workers": "工人",
}

_EN_ZH_ORDERED = sorted(EN_ZH_TERMS.items(), key=lambda kv: len(kv[0]), reverse=True)


def zh_term_cleanup(text: Any) -> str:
    """Replace known English safety phrases with reviewed Chinese wording."""
    value = str(text or "")
    if not _LATIN_WORD_RE.search(value):
        return value
    for source, target in _EN_ZH_ORDERED:
        if source in value:
            value = value.replace(source, target)
    return value


def en_term_cleanup(text: Any) -> str:
    """Normalise leftover Chinese fragments inside an English report."""
    value = str(text or "")
    if not contains_cjk(value):
        return value
    if "牆拉結" in value:
        return "Install temporary bracing before removing or relocating scaffold wall ties."
    if ("由上而下" in value or "逐層" in value) and ("拆" in value):
        return "Dismantle scaffold members top-down, level by level."
    if "傳遞" in value and ("竹" in value or "物料" in value):
        return "Pass dismantled bamboo / materials down to ground level and remove from site."
    scaffold_tokens = ["拆棚", "棚架", "尼龍網", "鋅鐵", "帆布", "橫杆", "竹杆", "竹枝"]
    if any(token in value for token in scaffold_tokens):
        return (
            "Dismantle scaffold bay: remove nylon net, metal sheets or canvas first; "
            "then remove ledgers and supporting bamboo members."
        )
    if "惡劣天氣" in value or "暴雨" in value or "颱風" in value:
        return "Adverse weather control for outdoor works."
    if "公眾" in value:
        return "Public interface control for persons nearby."
    return value


def localize_text(text: Any, language: str) -> str:
    if language in CHINESE_LANGUAGES:
        return zh_term_cleanup(text)
    if language == "English":
        return en_term_cleanup(text)
    return str(text or "")


def normalize_rows_language(rows: Iterable[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    """Apply deterministic language cleanup to every narrative field."""
    if language not in CHINESE_LANGUAGES and language != "English":
        return [dict(row) for row in rows]
    normalized: list[dict[str, Any]] = []
    for row in rows:
        new_row: dict[str, Any] = {}
        for key, value in row.items():
            if key in PROTECTED_KEYS or not isinstance(value, str):
                new_row[key] = value
            else:
                new_row[key] = localize_text(value, language)
        normalized.append(new_row)
    return normalized


def row_language_mismatch(row: dict[str, Any], language: str) -> bool:
    """True when a row still carries wrong-language narrative content."""
    for key, value in row.items():
        if key in PROTECTED_KEYS or not isinstance(value, str):
            continue
        if language in CHINESE_LANGUAGES and has_substantial_english(value):
            return True
        if language == "English" and contains_cjk(value):
            return True
    return False


def rows_language_mismatch_count(rows: Iterable[dict[str, Any]], language: str) -> int:
    return sum(1 for row in rows if row_language_mismatch(row, language))
