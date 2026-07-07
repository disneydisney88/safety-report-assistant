from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

import services.docx_export as docx_export
from services.ai_prompts import (
    DISCLAIMER,
    MS_EXTRACTION_SYSTEM_PROMPT,
    RA_HIDDEN_PROMPT_CONTRACT,
    RA_SYSTEM_PROMPT,
    RA_TRANSLATION_SYSTEM_PROMPT,
)
from services.excel_export import build_ra_excel
from services.file_extract import clean_extracted_steps, extract_text_from_upload, infer_steps_from_ms_text
from services.language_tools import (
    CHINESE_LANGUAGES,
    normalize_rows_language,
    rows_language_mismatch_count,
)
from services.nvidia_client import generate_json, has_api_key, model_name, test_connection
from services.validators import MethodStatementExtraction, RADraft, RAItem

st.set_page_config(page_title="RA Generator", layout="wide", initial_sidebar_state="collapsed")

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

ZH_TEXT_SIZE = "\u6587\u5b57\u5927\u5c0f"
ZH_BILINGUAL = "\u4e2d\u82f1"
ZH_TRAD = "\u7e41"
ZH_SIMP = "\u7b80"
ZH_OTHER_LANG = "\u5176\u4ed6\u8a9e\u8a00"
ZH_REPORT_LANG = "\u5831\u544a\u8a9e\u8a00"

LANGUAGE_INSTRUCTIONS = {
    "English": "Write the RA report in professional English.",
    "Traditional Chinese": "Write the RA report in Traditional Chinese. Keep common safety abbreviations in English where appropriate.",
    "Simplified Chinese": "Write the RA report in Simplified Chinese. Keep common safety abbreviations in English where appropriate.",
    "Bilingual": "Write the RA report in bilingual format. Use English first, then Traditional Chinese in the same field where practical.",
    "Bahasa Indonesia": "Write the RA report in Bahasa Indonesia.",
    "Hindi": "Write the RA report in Hindi.",
    "Nepali": "Write the RA report in Nepali.",
    "Punjabi": "Write the RA report in Punjabi.",
    "Tagalog": "Write the RA report in Tagalog.",
    "Thai": "Write the RA report in Thai.",
    "Urdu": "Write the RA report in Urdu.",
    "Vietnamese": "Write the RA report in Vietnamese.",
    "Khmer": "Write the RA report in Khmer.",
    "Burmese": "Write the RA report in Burmese.",
    "Bengali": "Write the RA report in Bengali.",
    "Sinhala": "Write the RA report in Sinhala.",
    "Japanese": "Write the RA report in Japanese. Keep standard safety abbreviations in English where appropriate.",
    "Korean": "Write the RA report in Korean. Keep standard safety abbreviations in English where appropriate.",
    "Japanese-English": "Write the RA report in bilingual format. Use Japanese first, then English in the same field where practical.",
    "Korean-English": "Write the RA report in bilingual format. Use Korean first, then English in the same field where practical.",
}

OTHER_LANGUAGE_OPTIONS = {
    "\u5176\u4ed6\u8a9e\u8a00": "",
    "Bahasa Indonesia (\u5370\u5c3c\u6587)": "Bahasa Indonesia",
    "\u0939\u093f\u0928\u094d\u0926\u0940 (\u5370\u5ea6\u6587)": "Hindi",
    "\u0928\u0947\u092a\u093e\u0932\u0940 (\u5c3c\u6cca\u723e\u6587)": "Nepali",
    "\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40 (\u65c1\u906e\u666e\u6587)": "Punjabi",
    "Tagalog (\u83f2\u5f8b\u8cd3\u6587)": "Tagalog",
    "\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22 (\u6cf0\u6587)": "Thai",
    "\u0627\u0631\u062f\u0648 (\u5df4\u57fa\u65af\u5766\u6587)": "Urdu",
    "Ti\u1ebfng Vi\u1ec7t (\u8d8a\u5357\u6587)": "Vietnamese",
    "\u1781\u17d2\u1798\u17c2\u179a (\u9ad8\u68c9\u6587)": "Khmer",
    "\u1019\u103c\u1014\u103a\u1019\u102c (\u7dec\u7538\u6587)": "Burmese",
    "\u09ac\u09be\u0982\u09b2\u09be (\u5b5f\u52a0\u62c9\u6587)": "Bengali",
    "\u0dc3\u0dd2\u0d82\u0dc4\u0dbd (\u50e7\u4f3d\u7f85\u6587)": "Sinhala",
    "\u65e5\u672c\u8a9e + English": "Japanese-English",
    "\ud55c\uad6d\uc5b4 + English": "Korean-English",
}

REPORT_LANGUAGE_OPTIONS = [
    "English",
    "Traditional Chinese",
    "Simplified Chinese",
    "Bahasa Indonesia",
    "Hindi",
    "Nepali",
    "Punjabi",
    "Tagalog",
    "Thai",
    "Urdu",
    "Vietnamese",
    "Khmer",
    "Burmese",
    "Bengali",
    "Sinhala",
    "Japanese",
    "Korean",
]

UI = {
    "title": "RA Generator",
    "caption": "Risk Assessment Report Generator / \u98a8\u96aa\u8a55\u4f30\u5831\u544a\u751f\u6210\u5668",
    "step1": "Step 1. Basic Information / \u7b2c\u4e00\u6b65\uff1a\u57fa\u672c\u8cc7\u6599",
    "help": "Upload a Method Statement/PDF or fill in the key work details. The app will extract steps, let you confirm them, then generate Word/Excel RA reports.\n\u4e0a\u8f09\u65bd\u5de5\u65b9\u6cd5\u66f8/PDF \u6216\u586b\u5beb\u4e3b\u8981\u5de5\u4f5c\u8cc7\u6599\uff1b\u7cfb\u7d71\u6703\u62bd\u53d6\u5de5\u5e8f\uff0c\u7d93\u4f60\u78ba\u8a8d\u5f8c\u751f\u6210 Word/Excel \u98a8\u96aa\u8a55\u4f30\u5831\u544a\u3002",
    "has_ms": "1. Do you have a detailed Method Statement? / 是否有詳細施工方法書？",
    "upload_ms": "Upload Method Statement / reference RA (.docx, .pdf or .txt) / 上載施工方法書或參考 RA",
    "upload_help": "Optional. The file is read locally by the app and the extracted text is used for work-step inference / AI drafting. Scanned PDFs may need OCR later.",
    "activity": "2. Construction activity / 施工活動",
    "activity_ph": "Example: Bored pile construction / work at height / confined space",
    "location": "3. Project name / 工程名稱",
    "location_ph": "Example: Ward C10 Louver Installation / Tower 1 TX Room Modification",
    "equipment": "4. Equipment and tools / 設備及工具",
    "equipment_ph": "Example: crane, drilling machine, PPE, hand tools",
    "confined": "5. Confined space involved? / 是否涉及密閉空間？",
    "standard": "Matrix version / 矩陣版本",
    "output_language": "Report output language / 報告輸出語言",
    "project": "Report title / 報告標題",
    "steps": "Copy simple construction steps here / 在此貼上簡單施工步驟",
    "steps_ph": "One step per line, for example:\n1. Set up working area\n2. Install temporary platform\n3. Carry out drilling work\n4. Clean up and demobilise",
    "prepare": "Prepare Step Confirmation / \u9810\u5099\u5de5\u5e8f\u78ba\u8a8d",
    "missing": "Please fill in required information: ",
    "step2": "Step 2. Confirm Method Statement / Steps / 第二步：確認施工方法及工序",
    "step2_help": "Check the details below. You may edit the steps. RA will be generated only after confirmation.",
    "confirmed": "Confirmed construction steps / 已確認施工步驟",
    "confined_warning": "Confined space auto-check: gas testing, ventilation, respiratory protection, permit-to-work, standby person, rescue arrangement and monitoring records must be included.",
    "generate": "Confirm and Generate RA Report / \u78ba\u8a8d\u4e26\u751f\u6210\u5831\u544a",
    "step3": "Step 3. RA Report Output / 第三步：報告輸出",
    "word": "Download Word RA Report",
    "excel": "Download Excel RA Table",
}



def load_json(name: str, fallback):
    path = CONFIG_DIR / name
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


RISK_LIBRARY = load_json("risk_library.json", [])
KEYWORD_MAP = load_json("keyword_map.json", {})
LEGAL_REF_TAGS = load_json("legal_ref_tags.json", {})
RISK_MATRICES = load_json("risk_matrix.json", {"matrices": {}}).get("matrices", {})
JURISDICTION_PROFILES = load_json("jurisdiction_profiles.json", {"jurisdiction_profiles": []}).get("jurisdiction_profiles", [])


def init_view_state() -> None:
    st.session_state.setdefault("report_language", "English")
    st.session_state.setdefault("font_size", "13")


def render_top_toolbar() -> str:
    init_view_state()
    size_map = {"11": "11pt", "13": "13pt", "15": "15pt"}
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 2.2rem; }}
        .stApp, .stMarkdown, .stTextInput, .stTextArea, .stSelectbox, .stRadio {{
            font-size: {size_map[st.session_state["font_size"]]};
        }}
        .language-toolbar {{
            border: 1px solid rgba(120, 130, 150, 0.30);
            border-radius: 8px;
            padding: 10px 12px 2px 12px;
            margin: 0 0 12px 0;
            background: rgba(248, 250, 252, 0.88);
        }}
        .language-toolbar-title {{
            color: #334155;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .ra-header {{
            border: 1px solid rgba(120, 130, 150, 0.35);
            border-radius: 8px;
            padding: 20px 24px;
            margin-bottom: 14px;
            background: linear-gradient(135deg, rgba(23, 105, 170, 0.16), rgba(15, 118, 110, 0.10));
        }}
        .ra-header h1 {{
            font-size: 30px;
            line-height: 1.15;
            margin: 0 0 8px 0;
            letter-spacing: 0;
        }}
        .ra-header p {{
            margin: 3px 0;
        }}
        .ra-kicker {{
            color: #2f6f7a;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.82rem;
            letter-spacing: 0;
            margin-bottom: 6px;
        }}
        .ra-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }}
        .ra-chip {{
            border: 1px solid rgba(120, 130, 150, 0.35);
            border-radius: 999px;
            padding: 5px 10px;
            background: rgba(255, 255, 255, 0.10);
            font-size: 0.88rem;
        }}
        .ra-workflow {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0 18px 0;
        }}
        .ra-step {{
            border: 1px solid rgba(120, 130, 150, 0.32);
            border-radius: 8px;
            padding: 12px 14px;
            background: rgba(255, 255, 255, 0.06);
        }}
        .ra-step strong {{
            display: block;
            margin-bottom: 4px;
        }}
        @media (max-width: 900px) {{
            .ra-workflow {{
                grid-template-columns: 1fr;
            }}
        }}
        .ra-form-band {{
            border-top: 3px solid #1769aa;
            padding-top: 10px;
            margin-top: 8px;
        }}
        div[data-testid="stFormSubmitButton"] button {{
            background: #1769aa;
            color: white;
            border: 1px solid #1769aa;
            font-weight: 700;
        }}
        div[data-testid="stButton"] button {{
            background: #0f766e;
            color: white;
            border: 1px solid #0f766e;
            font-weight: 700;
        }}
        div[data-testid="stFileUploader"] button {{
            background: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #1d4ed8 !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
        }}
        div[data-testid="stFileUploader"] button:hover {{
            background: #1d4ed8 !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }}
        .field-highlight {{
            margin: 0.15rem 0 0.35rem 0;
            padding: 0.42rem 0.62rem;
            border-left: 4px solid #2563eb;
            border-radius: 6px;
            background: #eff6ff;
            color: #1e3a8a;
            font-weight: 800;
        }}
        .field-highlight-green {{
            border-left-color: #0f766e;
            background: #ecfdf5;
            color: #14532d;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="language-toolbar-title">Language / Display 語言及顯示</div>', unsafe_allow_html=True)
    with st.container(border=True):
        cols = st.columns([0.9, 1.2, 1.2, 1.4])
        font_options = ["11", "13", "15"]
        with cols[0]:
            font_size = st.selectbox("文字大小 / Text size", font_options, index=font_options.index(st.session_state["font_size"]) if st.session_state["font_size"] in font_options else 1)
            st.session_state["font_size"] = font_size
        with cols[1]:
            main_language = st.selectbox(
                "Main language / 主要語言",
                ["English", "Traditional Chinese", "Simplified Chinese"],
                index=["English", "Traditional Chinese", "Simplified Chinese"].index(st.session_state["report_language"]) if st.session_state["report_language"] in ["English", "Traditional Chinese", "Simplified Chinese"] else 0,
            )
            st.session_state["report_language"] = main_language
        with cols[2]:
            choice = st.selectbox("Other languages / 其他語言", list(OTHER_LANGUAGE_OPTIONS))
            if OTHER_LANGUAGE_OPTIONS[choice]:
                st.session_state["report_language"] = OTHER_LANGUAGE_OPTIONS[choice]
        with cols[3]:
            st.info(f"{ZH_REPORT_LANG}: {st.session_state['report_language']}")
    return st.session_state["report_language"]


def split_steps(text: str) -> list[str]:
    steps: list[str] = []
    for line in (text or "").splitlines():
        clean = line.strip(" \t-*0123456789.)")
        if clean:
            steps.append(clean)
    return steps


def _compact_text(value: str) -> str:
    return "".join(str(value or "").split()).lower()


def step_records(steps: list[str]) -> list[dict[str, str]]:
    return [{"source_step_id": f"S{idx:03d}", "step_text": step} for idx, step in enumerate(steps, start=1)]


def profile_options() -> dict[str, dict]:
    return {profile["display_name"]: profile for profile in JURISDICTION_PROFILES}


def matrix_options() -> dict[str, dict]:
    return {matrix["matrix_name"]: matrix for matrix in RISK_MATRICES.values()}


def risk_band_for_score(matrix: dict, score: int) -> dict:
    for band in matrix.get("risk_bands", []):
        if int(band["min"]) <= score <= int(band["max"]):
            return band
    return {}


def matrix_dataframe(matrix: dict) -> pd.DataFrame:
    severity = matrix.get("severity_scale", [])
    likelihood = matrix.get("likelihood_scale", [])
    rows = []
    for like in likelihood:
        row = {"Likelihood \\ Severity": f"{like['code']} {like['label_en']}"}
        for sev in severity:
            score = int(like["score"]) * int(sev["score"])
            band = risk_band_for_score(matrix, score)
            row[f"{sev['code']} {sev['label_en']}"] = f"{score} {band.get('level', '')}"
        rows.append(row)
    return pd.DataFrame(rows)


def matched_library_records(activity: str, equipment: str, steps: list[str], confined_space: str) -> list[dict]:
    text = " ".join([activity, equipment, " ".join(steps)]).lower()
    matches: list[dict] = []
    for record in RISK_LIBRARY:
        keywords = [str(k).lower() for k in record.get("trigger_keywords", [])]
        if any(k and k in text for k in keywords):
            matches.append(record)
    if confined_space == "Yes":
        matches.extend([r for r in RISK_LIBRARY if r.get("category") == "Confined Space"])
    seen = set()
    unique = []
    for record in matches:
        record_id = record.get("id")
        if record_id not in seen:
            unique.append(record)
            seen.add(record_id)
    return unique[:8]


def infer_steps(activity: str, confined_space: str) -> list[str]:
    lower = activity.lower()
    if "bored" in lower or "pile" in lower:
        steps = [
            "Set out and prepare working area",
            "Position boring plant and check stability",
            "Install casing / temporary support where required",
            "Carry out boring / drilling operation",
            "Remove spoil and maintain housekeeping",
            "Lower reinforcement cage",
            "Concrete pouring and tremie operation",
            "Demobilise plant and reinstate work area",
        ]
    elif "hot" in lower or "welding" in lower or "cutting" in lower:
        steps = [
            "Confirm hot work permit and prepare work area",
            "Remove or protect combustible materials",
            "Set up fire watch and firefighting equipment",
            "Carry out cutting / welding / grinding",
            "Inspect area after completion and maintain fire watch",
        ]
    elif "height" in lower or "scaffold" in lower or "platform" in lower:
        steps = [
            "Inspect access equipment and work platform",
            "Set up exclusion zone below work area",
            "Access the work location",
            "Carry out work at height",
            "Remove tools/materials and close out inspection",
        ]
    else:
        steps = [
            "Prepare work area and brief workers",
            "Deliver tools, equipment and materials to work location",
            "Carry out the main work activity",
            "Inspect completed work and remove waste",
            "Demobilise and hand back work area",
        ]
    if confined_space == "Yes":
        steps = [
            "Confirm confined space risk assessment and permit-to-work",
            "Test atmosphere and record gas monitoring result",
            "Set up ventilation, rescue arrangement and standby person",
        ] + steps + ["Exit confined space and close permit after final check"]
    return steps


def local_text(data: dict, english: str) -> str:
    language = data.get("report_language", "English")
    if language in {"English", "Bilingual"}:
        return english
    return english


# Reviewed Traditional Chinese generic RA row content, keyed by RAItem fields.
# Shared by the Chinese local fallback and the per-step coverage fallback so a
# Chinese report never falls back to English library sentences.
ZH_GENERIC_ITEM = {
    "hazard": "與工序相關的高處墮下、物料墮下、通道或作業面不安全",
    "cause_of_hazard": "工作通道、臨邊防護、物料固定或作業面狀況未按實際工地情況妥善控制",
    "possible_consequence": "嚴重受傷或死亡；下方人士受傷；財物損壞",
    "persons_at_risk": "工人、監督人員、分判商及附近人士",
    "existing_control_measures": "按已批准施工方法書施工；開工前簡介；設置工作平台及通道；設置禁區及警告標誌；使用合適個人防護裝備",
    "additional_control_measures_required": "由合資格人士檢查相關工作平台、棚架或設備；加強現場監督；按工序分段施工；保持通道及工作面整潔",
    "legal_cop_reference": "香港職安健法例、勞工處指引及相關工作守則",
    "permit_certificate_competent_person_required": "按工程要求進行相關訓練、工具箱講座及合資格人士檢查",
    "inspection_monitoring_points": "開工前檢查；施工中監察；收工檢查及記錄",
    "responsible_person": "工地監督 / 安全主任",
    "remarks_items_to_be_confirmed": "須按實際工地情況確認危害成因及控制措施",
}


_DISPLAY_TO_ITEM_KEYS = {
    "Source Step ID": "source_step_id",
    "Source Step Original": "source_step_text_original",
    "Source Step Translated": "source_step_text_translated",
    "Hazard ID": "hazard_id",
    "Hazard Category": "hazard_category",
    "Work Step": "work_step",
    "Hazard": "hazard",
    "Cause of Hazard": "cause_of_hazard",
    "Possible Consequence": "possible_consequence",
    "Persons at Risk": "persons_at_risk",
    "Initial Risk": "initial_risk_rating",
    "Existing Controls": "existing_control_measures",
    "Additional Controls Required": "additional_control_measures_required",
    "Residual Risk": "residual_risk_rating",
    "Legal / CoP Reference": "legal_cop_reference",
    "Permit / Competent Person": "permit_certificate_competent_person_required",
    "Inspection / Monitoring": "inspection_monitoring_points",
    "Responsible Person": "responsible_person",
    "Remarks": "remarks_items_to_be_confirmed",
}


def _scaffold_hazard_id_for_step(step_text: str) -> str:
    """Pick the most relevant scaffold-dismantling hazard for a confirmed step
    so the local fallback differentiates steps instead of repeating one row."""
    text = str(step_text or "")
    if any(token in text for token in ["拉結", "連牆", "拉扱", "斜撐", "wall tie"]):
        return "SCAF-DIS-06"
    if any(token in text for token in ["傳", "搬", "運", "竹料", "竹枝", "落至地面", "傳到地面"]):
        return "SCAF-DIS-03"
    if any(token in text for token in ["次序", "橫杆", "直杆", "軒", "針", "由上而下", "逐層"]):
        return "SCAF-DIS-05"
    if any(token in text for token in ["網", "帆布", "鋅鐵", "尼龍", "斜棚"]):
        return "SCAF-DIS-02"
    return "SCAF-DIS-02"


def _fallback_ra_zh(data: dict) -> RADraft:
    """Chinese local fallback, one row per confirmed step.

    For bamboo-scaffold dismantling each step is mapped to the most relevant
    reviewed scaffold hazard so the steps differ; other work uses the generic
    Chinese row. Adverse-weather / public-interface rows are appended later by
    ensure_required_ra_rows.
    """
    matrix = data.get("risk_matrix", {})
    scaffold = is_scaffold_dismantling_work(data)
    items = []
    for record in step_records(data.get("confirmed_steps", [])):
        if scaffold:
            hazard_id = _scaffold_hazard_id_for_step(record["step_text"])
            source = {"source_step_id": record["source_step_id"], "step_text": record["step_text"]}
            display = scaffold_required_row(data, hazard_id, source, chinese=True)
            item = {_DISPLAY_TO_ITEM_KEYS[key]: value for key, value in display.items() if key in _DISPLAY_TO_ITEM_KEYS}
            item["source_step_text_original"] = record["step_text"]
            item["source_step_text_translated"] = record["step_text"]
            item["work_step"] = record["step_text"]
            items.append(item)
        else:
            items.append(
                {
                    "source_step_id": record["source_step_id"],
                    "source_step_text_original": record["step_text"],
                    "source_step_text_translated": record["step_text"],
                    "work_step": record["step_text"],
                    "initial_risk_rating": _rating_from_matrix(matrix, 2, 5),
                    "residual_risk_rating": _rating_from_matrix(matrix, 1, 5),
                    **ZH_GENERIC_ITEM,
                }
            )
    return RADraft(disclaimer=DISCLAIMER, overall_risk_level="待確認", items=items)


def fallback_ra(data: dict) -> RADraft:
    if data.get("report_language", "English") in CHINESE_LANGUAGES:
        return _fallback_ra_zh(data)
    items = []
    library_records = data.get("matched_library_records", [])
    matrix = data.get("risk_matrix", {})
    severity_scale = matrix.get("severity_scale", [])
    likelihood_scale = matrix.get("likelihood_scale", [])
    default_severity = severity_scale[-1] if severity_scale else {"code": "S5", "score": 5, "label_en": "Catastrophic"}
    default_likelihood = likelihood_scale[1] if len(likelihood_scale) > 1 else {"code": "P2", "score": 2, "label_en": "Unlikely"}
    step_ids = {record["step_text"]: record["source_step_id"] for record in step_records(data.get("confirmed_steps", []))}
    for step in data["confirmed_steps"]:
        source_records = library_records or [{}]
        for record in source_records[:2]:
            hazards = record.get("hazards") or ["Task-specific hazard to be verified against site condition"]
            consequences = record.get("possible_consequences") or ["Personal injury, property damage or unsafe work continuation"]
            controls = record.get("mandatory_controls") or ["Pre-work briefing", "Supervisor control", "Suitable PPE", "Access control", "Housekeeping"]
            additional = record.get("additional_controls") or ["Confirm method statement, competent person requirement, permit-to-work, inspection points and emergency arrangement before work starts"]
            initial_score = int(default_likelihood["score"]) * int(default_severity["score"])
            initial_band = risk_band_for_score(matrix, initial_score)
            initial_rating = f"{default_likelihood['code']} x {default_severity['code']} = {initial_score} {initial_band.get('level', record.get('initial_risk', 'MR'))}"
            residual_likelihood = likelihood_scale[0] if likelihood_scale else {"code": "P1", "score": 1}
            residual_score = int(residual_likelihood["score"]) * int(default_severity["score"])
            residual_band = risk_band_for_score(matrix, residual_score)
            residual_rating = f"{residual_likelihood['code']} x {default_severity['code']} = {residual_score} {residual_band.get('level', 'MR')}"
            items.append(
                {
                    "source_step_id": step_ids.get(step, ""),
                    "source_step_text_original": step,
                    "source_step_text_translated": step,
                    "hazard_id": str(record.get("id", "")),
                    "hazard_category": str(record.get("category", "")),
                    "work_step": step,
                    "hazard": local_text(data, "; ".join(hazards)),
                    "cause_of_hazard": local_text(data, str(record.get("cause_of_hazard") or record.get("cause") or "Unsafe condition, unsafe act or failure mode associated with the confirmed work step")),
                    "possible_consequence": local_text(data, "; ".join(consequences)),
                    "persons_at_risk": local_text(data, "Workers, supervisors, subcontractors and persons nearby"),
                    "initial_risk_rating": initial_rating,
                    "existing_control_measures": local_text(data, "; ".join(controls)),
                    "additional_control_measures_required": local_text(data, "; ".join(additional)),
                    "residual_risk_rating": residual_rating,
                    "legal_cop_reference": "; ".join(record.get("legal_ref_tags", ["To be verified by Safety Officer"])),
                    "permit_certificate_competent_person_required": "; ".join(record.get("permit_required", ["To be confirmed by Safety Officer"]) + record.get("competent_person_required", [])),
                    "inspection_monitoring_points": "; ".join(record.get("inspection_points", ["Pre-work check", "Active monitoring", "Close-out inspection"])),
                    "responsible_person": "Site Supervisor / Safety Officer",
                    "remarks_items_to_be_confirmed": "Confirm with approved Method Statement and site-specific conditions",
                }
            )
    return RADraft(disclaimer=DISCLAIMER, overall_risk_level="To be confirmed", items=items)


def ra_rows(draft: RADraft) -> list[dict[str, str]]:
    def value(item, attr: str, default: str = "") -> str:
        if isinstance(item, dict):
            return str(item.get(attr, default) or default)
        return str(getattr(item, attr, default) or default)

    return [
        {
            "Source Step ID": value(item, "source_step_id"),
            "Source Step Original": value(item, "source_step_text_original"),
            "Source Step Translated": value(item, "source_step_text_translated"),
            "Hazard ID": value(item, "hazard_id"),
            "Hazard Category": value(item, "hazard_category"),
            "Work Step": value(item, "work_step", "To be confirmed"),
            "Hazard": value(item, "hazard", "To be confirmed"),
            "Cause of Hazard": value(item, "cause_of_hazard", "To be confirmed"),
            "Possible Consequence": value(item, "possible_consequence", "To be confirmed"),
            "Persons at Risk": value(item, "persons_at_risk", "Workers / others nearby"),
            "Initial Risk": value(item, "initial_risk_rating", "To be confirmed"),
            "Existing Controls": value(item, "existing_control_measures", "To be confirmed"),
            "Additional Controls Required": value(item, "additional_control_measures_required", "To be confirmed"),
            "Residual Risk": value(item, "residual_risk_rating", "To be confirmed"),
            "Legal / CoP Reference": value(item, "legal_cop_reference", "To be verified by Safety Officer"),
            "Permit / Competent Person": value(item, "permit_certificate_competent_person_required", "To be confirmed"),
            "Inspection / Monitoring": value(item, "inspection_monitoring_points", "To be confirmed"),
            "Responsible Person": value(item, "responsible_person", "To be confirmed"),
            "Remarks": value(item, "remarks_items_to_be_confirmed", "To be confirmed"),
        }
        for item in draft.items
    ]


def split_points_for_rows(value: str) -> list[str]:
    parts = [part.strip(" \t-•") for part in re.split(r"\n|;|；", str(value or ""))]
    return [part for part in parts if part and part != "-"]


def similar_text(a: str, b: str) -> float:
    left = _compact_text(a)
    right = _compact_text(b)
    if not left or not right:
        return 0.0
    if left in right or right in left:
        return 0.95
    return SequenceMatcher(None, left, right).ratio()


def _rating_from_matrix(matrix: dict, likelihood: int, severity: int) -> str:
    score = likelihood * severity
    level = "MR"
    for band in matrix.get("risk_bands", []):
        if int(band.get("min", 0)) <= score <= int(band.get("max", 0)):
            level = str(band.get("level", level))
            break
    return f"P{likelihood} x S{severity} = {score} {level}"


SCAFFOLD_DISMANTLING_HAZARDS = [
    ("SCAF-DIS-01", "Pre-dismantling inspection", "Scaffold not inspected or unsafe before dismantling", "Missing competent person inspection, Form 5 / inspection record or unsafe scaffold condition not identified"),
    ("SCAF-DIS-02", "Fall from height", "Fall from height during scaffold dismantling", "Unprotected edge, unsafe access, insufficient lifeline or worker not clipped on"),
    ("SCAF-DIS-03", "Falling objects", "Falling objects / flying bamboo", "Throwing bamboo, unsecured materials, no toe board / net / exclusion zone below"),
    ("SCAF-DIS-04", "Access control", "Unauthorised access into dismantling zone", "Barricade, warning signs or access control not maintained"),
    ("SCAF-DIS-05", "Sequence instability", "Scaffold instability due to incorrect dismantling sequence", "Incorrect top-down sequence or last-fixed-first-removed principle not followed"),
    ("SCAF-DIS-06", "Wall tie relocation", "Scaffold instability during wall tie relocation", "Premature wall tie removal, insufficient temporary bracing or tie layout not confirmed"),
    ("SCAF-DIS-07", "Manual handling", "Manual handling injury during bamboo passing", "Awkward posture, excessive load, poor team coordination or inadequate landing area"),
    ("SCAF-DIS-08", "Ground struck-by", "Struck-by bamboo at ground level", "Passing bamboo without exclusion zone, banksman or communication"),
    ("SCAF-DIS-09", "Unfinished scaffold", "Unfinished scaffold / open end not protected", "Closing position without temporary guardrail, bracing or warning tag"),
    ("SCAF-DIS-10", "Adverse weather", "Adverse weather affecting scaffold stability", "Strong wind, heavy rain, lightning or slippery working platform"),
    ("SCAF-DIS-11", "Post-dismantling storage", "Post-dismantling bamboo storage blocking access", "Bamboo or debris not cleared, obstructing access / traffic / plant route"),
    ("SCAF-DIS-12", "Emergency response", "Emergency rescue after fall / collapse / falling object incident", "Rescue plan, communication, first aid or emergency access not confirmed"),
]


SCAFFOLD_REQUIRED_HAZARD_IDS = ["SCAF-DIS-01", "SCAF-DIS-02", "SCAF-DIS-03", "SCAF-DIS-05", "SCAF-DIS-06", "SCAF-DIS-10", "SCAF-DIS-12"]


SCAFFOLD_HAZARD_TEXT_ZH = {
    "SCAF-DIS-01": ("拆棚前棚架未經檢查或狀況不安全", "未由合資格人士完成拆棚前檢查、表格五 / 檢查紀錄，或未識別棚架不安全狀況"),
    "SCAF-DIS-02": ("拆棚期間高處墮下", "臨邊未受保護、通道不安全、未設獨立救生繩或工人未扣好安全帶"),
    "SCAF-DIS-03": ("高空墮物 / 飛竹", "竹枝被拋擲、物料未固定、未設踢腳板 / 安全網 / 下方禁區"),
    "SCAF-DIS-05": ("拆棚次序錯誤導致棚架失穩", "未按由上而下及最後固定、最先拆除原則拆卸"),
    "SCAF-DIS-06": ("拆除或遷移牆拉結期間棚架失穩", "過早拆除牆拉結、臨時斜撐不足或未確認拉結佈置"),
    "SCAF-DIS-10": ("惡劣天氣影響棚架穩定", "強風、暴雨、雷暴或工作平台濕滑"),
    "SCAF-DIS-12": ("高處墮下、倒塌或墮物事故後緊急救援", "未確認救援計劃、通訊、急救或緊急通道"),
}


def is_scaffold_dismantling_work(data: dict) -> bool:
    text = " ".join([
        data.get("activity", ""),
        data.get("equipment", ""),
        " ".join(data.get("confirmed_steps", [])),
        data.get("method_statement_text", "")[:3000],
    ]).lower()
    return any(token in text for token in ["拆棚", "拆棚架", "dismantl", "scaffold dismant", "bamboo scaffold"])


def scaffold_required_row(data: dict, hazard_id: str, source: dict[str, str], chinese: bool) -> dict[str, str]:
    matrix = data.get("risk_matrix", {})
    hazard_info = next((item for item in SCAFFOLD_DISMANTLING_HAZARDS if item[0] == hazard_id), None)
    if not hazard_info:
        hazard_info = (hazard_id, "Scaffold dismantling", "Scaffold dismantling hazard", "Direct unsafe condition related to scaffold dismantling")
    hid, category, hazard_en, cause_en = hazard_info
    work_step = source.get("step_text") or ("拆卸棚架" if chinese else "Dismantle scaffold")
    if chinese:
        hazard_zh, cause_zh = SCAFFOLD_HAZARD_TEXT_ZH.get(hid, (hazard_en, cause_en))
        return {
            "Source Step ID": source.get("source_step_id", ""),
            "Source Step Original": source.get("step_text", ""),
            "Source Step Translated": work_step,
            "Hazard ID": hid,
            "Hazard Category": category,
            "Work Step": work_step,
            "Hazard": hazard_zh,
            "Cause of Hazard": cause_zh,
            "Possible Consequence": "嚴重受傷；死亡；棚架局部或整體倒塌；下方人士受傷；財物損毀",
            "Persons at Risk": "棚架工人、合資格人士、監督人員、下方工人及附近人士",
            "Initial Risk": _rating_from_matrix(matrix, 3, 5),
            "Existing Controls": "按已批准施工方案及拆棚次序施工；由合資格人士監督；設置禁區、圍欄及警告標誌；使用安全帶及獨立救生繩；禁止拋擲竹枝或物料",
            "Additional Controls Required": "開工前核實表格五 / 棚架檢查紀錄；確認牆拉結遷移及臨時支撐安排；逐段由上而下拆卸；惡劣天氣停工及復工前再檢查；確認墮下及墮物救援安排",
            "Residual Risk": _rating_from_matrix(matrix, 1, 5),
            "Legal / CoP Reference": "香港職安健法例、建築地盤安全規例、竹棚架安全守則及勞工處相關指引",
            "Permit / Competent Person": "如工程安全制度要求，須使用拆棚 / 改棚工作許可；表格五及合資格人士檢查須由安全主任核實",
            "Inspection / Monitoring": "每日開工前檢查；合資格人士持續監督；拆除牆拉結前後檢查；惡劣天氣後復工檢查；保存檢查紀錄",
            "Responsible Person": "合資格人士 / 工地監督 / 安全主任",
            "Remarks": "如圖則、拉結位置或許可要求未明確，須於開工前確認並記錄",
        }
    return {
        "Source Step ID": source.get("source_step_id", ""),
        "Source Step Original": source.get("step_text", ""),
        "Source Step Translated": "Scaffold dismantling work",
        "Hazard ID": hid,
        "Hazard Category": category,
        "Work Step": "Scaffold dismantling work",
        "Hazard": hazard_en,
        "Cause of Hazard": cause_en,
        "Possible Consequence": "Serious injury; fatality; partial or total scaffold collapse; injury to persons below; property damage",
        "Persons at Risk": "Scaffold workers, competent person, supervisors, workers below and persons nearby",
        "Initial Risk": _rating_from_matrix(matrix, 3, 5),
        "Existing Controls": "Follow approved dismantling method and sequence; competent person supervision; exclusion zone, barriers and warning signs; safety harness with independent lifeline; no throwing or flying bamboo",
        "Additional Controls Required": "Verify Form 5 / scaffold inspection record before work; confirm wall-tie relocation and temporary bracing; dismantle top-down by stage; suspend work in adverse weather and inspect before restart; confirm fall and falling-object rescue arrangement",
        "Residual Risk": _rating_from_matrix(matrix, 1, 5),
        "Legal / CoP Reference": "Hong Kong OSH legislation, Construction Sites (Safety) Regulations, Code of Practice for Bamboo Scaffolding Safety and Labour Department guidance",
        "Permit / Competent Person": "Permit-to-work for scaffold dismantling / alteration, if required by project safety system; Form 5 and competent person inspection to be verified by Safety Officer",
        "Inspection / Monitoring": "Daily pre-work inspection; full-time competent person supervision; inspection before and after wall-tie removal; post-weather restart inspection; inspection record retention",
        "Responsible Person": "Competent Person / Site Supervisor / Safety Officer",
        "Remarks": "Confirm drawings, wall-tie positions and permit requirements before work starts where not clearly stated",
    }


def quality_check_ra(data: dict, rows: list[dict[str, str]]) -> dict[str, object]:
    comments: list[str] = []
    result = "PASS FOR SO REVIEW"
    seen = set()
    for row in rows:
        key = (
            str(row.get("Source Step ID") or row.get("Work Step", "")).strip().lower(),
            str(row.get("Hazard", "")).strip().lower(),
        )
        if key in seen:
            comments.append("Duplicate RA row detected for the same source step and hazard.")
        seen.add(key)

    visible_keys = [
        "Work Step",
        "Hazard",
        "Cause of Hazard",
        "Possible Consequence",
        "Persons at Risk",
        "Existing Controls",
        "Additional Controls Required",
        "Legal / CoP Reference",
        "Permit / Competent Person",
        "Inspection / Monitoring",
        "Responsible Person",
        "Remarks",
    ]
    all_text = "\n".join(" ".join(str(row.get(key, "")) for key in visible_keys) for row in rows)
    if "[PERMIT_REDACTED]" in all_text:
        comments.append("Permit wording was redacted incorrectly.")
    if re.search(r"task-specific fall|unsafe working platform hazard", all_text, flags=re.I):
        comments.append("Generic fallback hazard wording remains in the RA table.")
    language = data.get("report_language", "English")
    if language == "English" and re.search(r"[\u4e00-\u9fff]", all_text):
        comments.append("Mixed language detected: English report contains Chinese in the main RA table.")
    if language in {"Traditional Chinese", "Simplified Chinese"} and re.search(r"\b(Follow approved Method Statement|Task-specific|Workers, supervisors|Site Supervisor)\b", all_text):
        comments.append("Mixed language detected: Chinese report contains English fallback sentences.")
    for row in rows:
        cause = str(row.get("Cause of Hazard", ""))
        if re.search(r"minimum acceptable residual risk|to be confirmed|SO review|Safety Officer", cause, flags=re.I):
            comments.append("Cause / remarks mapping needs review: assumptions or review notes may be in the cause field.")
            break
    if is_scaffold_dismantling_work(data):
        hazard_text = "\n".join(str(row.get("Hazard", "")) + " " + str(row.get("Hazard ID", "")) for row in rows).lower()
        required_tokens = ["scaf-dis-02", "scaf-dis-03", "scaf-dis-05", "scaf-dis-06", "scaf-dis-10"]
        missing = [token.upper() for token in required_tokens if token not in hazard_text]
        if missing:
            comments.append("Missing scaffold dismantling critical hazards: " + ", ".join(missing))
    if comments:
        result = "REVISE REQUIRED"
    return {"result": result, "comments": comments}


def ensure_required_ra_rows(data: dict, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        rows = ra_rows(fallback_ra(data))

    language = data.get("report_language", "English")
    chinese = language in {"Traditional Chinese", "Simplified Chinese"}
    joined = " ".join(
        [
            data.get("activity", ""),
            data.get("location", ""),
            data.get("equipment", ""),
            " ".join(data.get("confirmed_steps", [])),
            data.get("method_statement_text", "")[:3000],
        ]
    ).lower()
    outdoor_keywords = ["outdoor", "external", "outside", "road", "public", "weather", "rain", "typhoon", "scaffold", "facade", "roof", "height", "戶外", "室外", "道路", "公眾", "天氣", "颱風", "棚架", "外牆", "屋頂", "高空"]
    public_keywords = ["public", "pedestrian", "traffic", "road", "footpath", "nearby", "公眾", "行人", "交通", "道路", "附近"]
    has_weather = any("weather" in str(row.get("Work Step", "")).lower() or "天氣" in str(row.get("Work Step", "")) or "惡劣" in str(row.get("Work Step", "")) for row in rows)
    has_public = any("control interface with public" in str(row.get("Work Step", "")).lower() or "公眾" in str(row.get("Work Step", "")) or "行人" in str(row.get("Work Step", "")) for row in rows)
    matrix = data.get("risk_matrix", {})

    exploded_rows: list[dict[str, str]] = []
    for row in rows:
        hazards = split_points_for_rows(row.get("Hazard", ""))
        consequences = split_points_for_rows(row.get("Possible Consequence", ""))
        if len(hazards) > 1 and not any(token in str(row.get("Work Step", "")) for token in ["惡劣天氣", "公眾", "weather", "public"]):
            for idx, hazard in enumerate(hazards):
                new_row = dict(row)
                new_row["Hazard"] = hazard
                if len(consequences) == len(hazards):
                    new_row["Possible Consequence"] = consequences[idx]
                exploded_rows.append(new_row)
        else:
            exploded_rows.append(row)
    rows = exploded_rows

    def generic_step_row(step: str) -> dict[str, str]:
        if chinese:
            return {
                "Work Step": step,
                "Hazard": ZH_GENERIC_ITEM["hazard"],
                "Cause of Hazard": ZH_GENERIC_ITEM["cause_of_hazard"],
                "Possible Consequence": ZH_GENERIC_ITEM["possible_consequence"],
                "Persons at Risk": ZH_GENERIC_ITEM["persons_at_risk"],
                "Initial Risk": _rating_from_matrix(matrix, 2, 5),
                "Existing Controls": ZH_GENERIC_ITEM["existing_control_measures"],
                "Additional Controls Required": ZH_GENERIC_ITEM["additional_control_measures_required"],
                "Residual Risk": _rating_from_matrix(matrix, 1, 5),
                "Legal / CoP Reference": ZH_GENERIC_ITEM["legal_cop_reference"],
                "Permit / Competent Person": ZH_GENERIC_ITEM["permit_certificate_competent_person_required"],
                "Inspection / Monitoring": ZH_GENERIC_ITEM["inspection_monitoring_points"],
                "Responsible Person": ZH_GENERIC_ITEM["responsible_person"],
                "Remarks": ZH_GENERIC_ITEM["remarks_items_to_be_confirmed"],
            }
        display_step = "Confirmed work step requiring risk assessment" if re.search(r"[\u4e00-\u9fff]", step) else step
        return {
            "Work Step": display_step,
            "Hazard": "Fall, falling object, unsafe access or unsafe working platform related to the confirmed work step",
            "Cause of Hazard": "Access, edge protection, material restraint or working platform condition not adequately controlled for the actual site condition",
            "Possible Consequence": "Serious injury or fatality; injury to persons below; property damage",
            "Persons at Risk": "Workers, supervisors, subcontractors and persons nearby",
            "Initial Risk": _rating_from_matrix(matrix, 2, 5),
            "Existing Controls": "Follow approved Method Statement; pre-work briefing; provide safe working platform and access; establish exclusion zone and warning signs; use suitable PPE",
            "Additional Controls Required": "Competent person inspection of relevant platform, scaffold or equipment; enhanced supervision; stage-by-stage work sequence; maintain good housekeeping",
            "Residual Risk": _rating_from_matrix(matrix, 1, 5),
            "Legal / CoP Reference": "Hong Kong OSH legislation, Labour Department guidance and relevant Codes of Practice",
            "Permit / Competent Person": "Working-at-height training, toolbox talk and competent person inspection as required by project",
            "Inspection / Monitoring": "Pre-work inspection; active monitoring; close-out inspection and record",
            "Responsible Person": "Site Supervisor / Safety Officer",
            "Remarks": "Cause and controls shall be verified against actual site condition",
        }

    step_meta = step_records(data.get("confirmed_steps", []))
    covered_ids = {str(row.get("Source Step ID", "")).strip() for row in rows if row.get("Source Step ID")}
    for meta in step_meta:
        step_id = meta["source_step_id"]
        step = meta["step_text"].strip()
        if not step:
            continue
        text_covered = any(
            similar_text(step, str(row.get("Source Step Original") or row.get("Source Step Translated") or row.get("Work Step", ""))) >= 0.72
            for row in rows
        )
        if step_id not in covered_ids and not text_covered:
            fallback = generic_step_row(step)
            fallback["Source Step ID"] = step_id
            fallback["Source Step Original"] = step
            fallback["Source Step Translated"] = step
            rows.append(fallback)
            covered_ids.add(step_id)

    if is_scaffold_dismantling_work(data):
        existing_hazard_ids = {str(row.get("Hazard ID", "")).strip().upper() for row in rows}
        source = step_meta[0] if step_meta else {"source_step_id": "S001", "step_text": "拆卸棚架" if chinese else "Dismantle scaffold"}
        for hazard_id in SCAFFOLD_REQUIRED_HAZARD_IDS:
            if hazard_id not in existing_hazard_ids:
                rows.append(scaffold_required_row(data, hazard_id, source, chinese))
                existing_hazard_ids.add(hazard_id)

    def row_en(kind: str) -> dict[str, str]:
        if kind == "weather":
            return {
                "Work Step": "Work under adverse weather or extreme site conditions",
                "Hazard": "Heavy rain; strong wind; lightning; typhoon signal; wet or slippery working surface",
                "Cause of Hazard": "Adverse weather creates unstable access, slippery working surface, poor visibility or loss of control of materials and plant",
                "Possible Consequence": "Serious injury; fall from height; struck by object; loss of control of materials or plant",
                "Persons at Risk": "Workers, supervisors, subcontractors, visitors and persons nearby",
                "Initial Risk": _rating_from_matrix(matrix, 3, 4),
                "Existing Controls": "Check weather forecast and warning signals before work; stop work during unsafe weather; secure loose materials; maintain safe access and housekeeping",
                "Additional Controls Required": "Define stop-work trigger levels; inspect working platform and anchorage after adverse weather; brief workers before restart; record supervisor approval to resume",
                "Residual Risk": _rating_from_matrix(matrix, 1, 4),
                "Legal / CoP Reference": "Hong Kong OSH legislation, Labour Department guidance and project adverse weather procedure",
                "Permit / Competent Person": "Supervisor inspection and restart approval; relevant permit review where applicable",
                "Inspection / Monitoring": "Weather monitoring before and during work; post-weather inspection; close-out record",
                "Responsible Person": "Site Supervisor / Safety Officer",
                "Remarks": "Minimum acceptable residual risk: MR or lower before work resumes",
            }
        return {
            "Work Step": "Control interface with public, pedestrians, traffic or adjacent occupied areas",
            "Hazard": "Falling objects; unauthorised access; moving plant interface; obstruction to public route; dust, noise or nuisance",
            "Cause of Hazard": "Public route, occupied area, traffic or plant interface is not physically separated from the work area",
            "Possible Consequence": "Injury to public; property damage; traffic incident; complaint or enforcement action",
            "Persons at Risk": "Public, pedestrians, occupants, visitors, workers and traffic controllers",
            "Initial Risk": _rating_from_matrix(matrix, 3, 5),
            "Existing Controls": "Set up barriers, warning signs and exclusion zones; maintain clear access route; supervise lifting or material movement; keep work area tidy",
            "Additional Controls Required": "Provide covered walkway or catch-fan where required; appoint banksman / traffic marshal; schedule high-risk work outside peak public interface periods; communicate with affected parties",
            "Residual Risk": _rating_from_matrix(matrix, 1, 5),
            "Legal / CoP Reference": "Hong Kong OSH legislation, public protection requirements and project traffic / pedestrian management plan",
            "Permit / Competent Person": "Permit / temporary traffic or public protection arrangement where applicable",
            "Inspection / Monitoring": "Daily inspection of barriers, signs, public route and dropped-object controls",
            "Responsible Person": "Site Supervisor / Safety Officer",
            "Remarks": "Minimum acceptable residual risk: MR or lower; stop work if public protection is not maintained",
        }

    def row_zh(kind: str) -> dict[str, str]:
        if kind == "weather":
            return {
                "Work Step": "惡劣天氣或極端工地情況下工作",
                "Hazard": "暴雨；強風；雷暴；颱風信號；工作面濕滑",
                "Cause of Hazard": "惡劣天氣導致通道不穩、工作面濕滑、能見度下降或物料 / 機械失控",
                "Possible Consequence": "嚴重受傷；高處墮下；被物件擊中；物料或機械失控",
                "Persons at Risk": "工人、監督人員、分判商、訪客及附近人士",
                "Initial Risk": _rating_from_matrix(matrix, 3, 4),
                "Existing Controls": "開工前檢查天氣預報及警告信號；不安全天氣下停止工作；固定鬆散物料；保持安全通道及整潔",
                "Additional Controls Required": "訂明停工觸發標準；惡劣天氣後檢查工作平台及錨固；復工前向工人簡介；記錄監督批准復工",
                "Residual Risk": _rating_from_matrix(matrix, 1, 4),
                "Legal / CoP Reference": "香港職安健法例、勞工處指引及工程惡劣天氣程序",
                "Permit / Competent Person": "監督人員檢查及復工批准；如適用須覆核相關許可證",
                "Inspection / Monitoring": "開工前及施工期間監察天氣；惡劣天氣後檢查；保存收工記錄",
                "Responsible Person": "工地監督 / 安全主任",
                "Remarks": "最低可接受剩餘風險：MR 或以下方可復工",
            }
        return {
            "Work Step": "控制與公眾、行人、交通或鄰近佔用範圍的介面",
            "Hazard": "高空墮物；未經授權進入；流動機械介面；阻塞公眾通道；塵埃、噪音或滋擾",
            "Cause of Hazard": "公眾通道、佔用範圍、交通或機械介面未與施工區有效分隔",
            "Possible Consequence": "公眾受傷；財物損毀；交通意外；投訴或執法行動",
            "Persons at Risk": "公眾、行人、佔用人、訪客、工人及交通管制人員",
            "Initial Risk": _rating_from_matrix(matrix, 3, 5),
            "Existing Controls": "設置圍欄、警告標誌及禁區；保持通道暢通；監督吊運或物料搬運；保持工作區整潔",
            "Additional Controls Required": "按需要設置有蓋通道或接物防護；委任訊號員 / 交通指揮員；避開公眾介面高峰時段進行高風險工作；通知受影響人士",
            "Residual Risk": _rating_from_matrix(matrix, 1, 5),
            "Legal / CoP Reference": "香港職安健法例、公眾保護要求及工程交通 / 行人管理計劃",
            "Permit / Competent Person": "如適用須取得臨時交通或公眾保護安排批准",
            "Inspection / Monitoring": "每日檢查圍欄、標誌、公眾通道及防墮物控制措施",
            "Responsible Person": "工地監督 / 安全主任",
            "Remarks": "最低可接受剩餘風險：MR 或以下；如未能維持公眾保護須停工",
        }

    if any(keyword in joined for keyword in outdoor_keywords) and not has_weather:
        rows.append(row_zh("weather") if chinese else row_en("weather"))
    if any(keyword in joined for keyword in public_keywords) and not has_public:
        rows.append(row_zh("public") if chinese else row_en("public"))
    return rows


def build_hidden_report_prompt(data: dict, step_batch: list[dict[str, str]] | None = None, suppress_extra_rows: bool = False, include_sections: bool = True) -> str:
    matrix = data.get("risk_matrix", {}) or {}
    joined = " ".join(
        [
            data.get("activity", ""),
            data.get("location", ""),
            data.get("equipment", ""),
            " ".join(data.get("confirmed_steps", [])),
            data.get("method_statement_text", "")[:3000],
        ]
    ).lower()
    triggers = []
    if data.get("confined_space") == "Yes":
        triggers.append("Confined space: include gas testing, ventilation, permit-to-work, standby person and rescue controls.")
    if any(token in joined for token in ["outdoor", "external", "outside", "height", "scaffold", "roof", "facade", "weather", "rain", "typhoon", "戶外", "室外", "高空", "棚架", "外牆", "天氣", "颱風"]):
        triggers.append("Outdoor / weather-exposed work: create one separate adverse-weather risk row near the end; do not repeat weather wording in every ordinary work-step row.")
    if any(token in joined for token in ["public", "pedestrian", "traffic", "road", "footpath", "nearby", "公眾", "行人", "交通", "道路", "附近"]):
        triggers.append("Public interface: create a separate public-interface / falling-object risk row where relevant; do not repeat public wording in every ordinary work-step row.")
    if any(token in joined for token in ["crane", "lifting", "hoist", "plant", "machine", "forklift", "吊", "起重", "機械", "叉車"]):
        triggers.append("Plant / lifting interface: include exclusion zone, competent operator, lifting gear inspection, communication and stability controls.")
    if is_scaffold_dismantling_work(data):
        triggers.append("Scaffold dismantling: include scaffold inspection, Form 5 / competent person inspection, independent lifeline, exclusion zone, flying bamboo prohibition, wall tie relocation, temporary bracing, manual bamboo passing, post-dismantling clearance and emergency rescue.")
    if any(token in joined for token in ["hot work", "welding", "cutting", "grinding", "熱工", "焊", "切割", "打磨"]):
        triggers.append("Hot work: include hot work permit, fire watch, combustible material control and post-work fire check.")
    if not triggers:
        triggers.append("No special trigger detected: still include task-specific hazards for each confirmed work step.")

    batch_records = step_batch if step_batch is not None else step_records(data.get("confirmed_steps", []))
    steps = "\n".join(f"{record['source_step_id']}: {record['step_text']}" for record in batch_records) or "To be confirmed"
    band_lines = []
    for band in matrix.get("risk_bands", []):
        band_lines.append(f"- {band.get('level')}: {band.get('min')} to {band.get('max')} ({band.get('action', '')})")

    return "\n".join(
        [
            RA_HIDDEN_PROMPT_CONTRACT.strip(),
            "",
            "Project-specific drafting brief:",
            f"- report_language: {data.get('report_language', 'English')}",
            f"- project/report title: {data.get('project', 'Risk Assessment Report')}",
            f"- project name: {data.get('location', 'To be confirmed')}",
            f"- construction activity: {data.get('activity', 'To be confirmed')}",
            f"- equipment/tools: {data.get('equipment', 'To be confirmed')}",
            f"- confined_space: {data.get('confined_space', 'No')}",
            f"- workforce/trades: {data.get('workforce', '') or 'Not stated - assume typical trade crew and flag for site verification'}",
            f"- duration/time of work: {data.get('duration', '') or 'Not stated - flag day/night and typhoon-season considerations for site verification'}",
            f"- matrix version: {data.get('standard', matrix.get('matrix_name', 'To be confirmed'))}",
            f"- risk matrix name: {matrix.get('matrix_name', 'To be confirmed')}",
            f"- include_supporting_sections: {'true - fill ppe_by_trade, permits_checklist, emergency_arrangements, training_records and inspection_schedule' if include_sections else 'false - fill risk items only; leave the supporting section fields empty in this batch'}",
            "",
            "Confirmed work steps:",
            steps,
            "",
            "Confirmed step records with stable IDs:",
            json.dumps(batch_records, ensure_ascii=False, indent=2),
            "",
            "Work-step quality rules:",
            "- Use only real sequential work activities as work steps.",
            "- Do not treat the Method Statement title, section heading, training requirement, PPE requirement or control measure as a work step.",
            "- Hazard cause must state the direct unsafe condition or exposure; never use 'confirm with approved Method Statement' as the cause.",
            "- Populate cause_of_hazard separately. Do not put assumptions, residual-risk targets, missing information, or Safety Officer review notes into cause_of_hazard.",
            "- Create at least one risk item for every confirmed work step.",
            "- Copy the exact source_step_id into every risk item. Do not rely on translated work-step text for matching.",
            "- Do not redact normal safety terms. Permit names, permit-to-work, Form 5, competent person, PPE, CoP title and legal reference tags are allowed report text.",
            "- If a work step has multiple distinct hazards, split them into separate risk items/rows instead of placing several hazards in one hazard cell.",
            (
                "- This request covers a BATCH of the confirmed steps only. Cover every step listed above. Do NOT add adverse weather, public interface or other extra rows in this batch; they are handled separately."
                if suppress_extra_rows
                else "- Add adverse weather and public interface as separate final rows when applicable."
            ),
            "",
            "Risk band rules from selected matrix:",
            "\n".join(band_lines) or "Use selected matrix in payload.",
            "",
            "Detected mandatory coverage triggers:",
            "\n".join(f"- {trigger}" for trigger in triggers),
            "",
            "Scaffold dismantling hazard template when applicable:",
            "\n".join(f"- {hid}: {hazard} ({category}) cause: {cause}" for hid, category, hazard, cause in SCAFFOLD_DISMANTLING_HAZARDS) if is_scaffold_dismantling_work(data) else "Not applicable.",
            "",
            "Approved legal / Code of Practice reference catalogue (cite legal_cop_reference ONLY from names in this controlled list; do not invent CoP titles or exact clause numbers; add 'to be verified' where a clause number is needed):",
            "\n".join(f"- {value}" for value in LEGAL_REF_TAGS.values()) or "Use Hong Kong OSH legislation and relevant Codes of Practice; mark clause numbers to be verified.",
            "",
            "Project / site-specific in-house safety rules provided by the user:",
            (
                (data.get("site_rules", "").strip()[:2000]
                 + "\n-> Incorporate these in-house rules into the relevant control measures. Where an in-house rule is STRICTER than the general standard, follow the in-house rule and reflect it in existing/additional controls. Note in remarks that project in-house rules apply.")
                if data.get("site_rules", "").strip()
                else "None provided. Note in remarks that project / site in-house safety rules (if any) shall be checked and take precedence where stricter."
            ),
            "",
            "Return the completed RADraft JSON only. Do not explain the report outside JSON.",
        ]
    )


# Steps per AI request. Batching keeps each response comfortably inside the
# model output-token limit so long Method Statements no longer truncate the
# JSON (which previously forced the generic local fallback).
RA_BATCH_SIZE = 6
RA_TRANSLATION_BATCH_SIZE = 8


def _ai_generation_payload(data: dict, batch: list[dict[str, str]], suppress_extra_rows: bool, include_sections: bool = True) -> dict:
    return {
        **data,
        "confirmed_steps": [record["step_text"] for record in batch],
        "confirmed_step_records": batch,
        "method_statement_text": data.get("method_statement_text", "")[:12000],
        "hidden_report_prompt": build_hidden_report_prompt(data, batch, suppress_extra_rows, include_sections),
        "instruction": (
            "Prepare a professional Risk Assessment Report according to IEC 31010 and Hong Kong safety legislation / CoP. "
            "Use the uploaded Method Statement text, confirmed steps and matched risk library first. Do not invent exact legal clause numbers. "
            "Use the selected jurisdiction profile and selected risk matrix. Calculate risk scores as likelihood x severity and ensure LR/MR/HR matches the selected matrix band. "
            "The RA table must include at least one risk row for every confirmed construction step listed in confirmed_step_records. "
            "Every item must include the correct source_step_id from confirmed_step_records. "
            "If one confirmed step has multiple hazards, create multiple items with the same source_step_id and different hazard_id. "
            "Write every narrative field fully in the selected report output language, including construction steps, hazards, causes, consequences, control measures, PPE/training and remarks. "
            "Each high-risk activity must include hazards, consequences, specific controls, permit/certificate requirements, competent person requirements, inspection points and emergency response. "
            "Follow hidden_report_prompt exactly; it is the controlling professional report specification. "
            "Show roles only, no personal names. Output valid JSON matching the approved RA schema. "
            f"{data.get('language_instruction', '')}"
        ),
    }


def generate_ra_with_ai(data: dict) -> tuple[RADraft | None, list[str], str | None]:
    """Generate the RA draft with NVIDIA AI, batching long step lists."""
    records = step_records(data.get("confirmed_steps", []))
    if len(records) <= RA_BATCH_SIZE:
        payload = _ai_generation_payload(data, records, suppress_extra_rows=False, include_sections=True)
        return generate_json(RA_SYSTEM_PROMPT, payload, RADraft)

    all_items: list = []
    all_flags: list[str] = []
    errors: list[str] = []
    sections_draft: RADraft | None = None
    batches = [records[start : start + RA_BATCH_SIZE] for start in range(0, len(records), RA_BATCH_SIZE)]
    progress = st.progress(0.0, text=f"Generating RA rows in {len(batches)} batches... / 分批生成風險評估列...")
    for index, batch in enumerate(batches, start=1):
        # Supporting sections (permits, emergency, training, inspection) are
        # requested once, on the final batch, then attached to the merged draft.
        is_last = index == len(batches)
        payload = _ai_generation_payload(data, batch, suppress_extra_rows=True, include_sections=is_last)
        draft, flags, error = generate_json(RA_SYSTEM_PROMPT, payload, RADraft)
        all_flags.extend(flags)
        if error:
            errors.append(f"batch {index}: {error}")
        if draft is not None and draft.items:
            all_items.extend(draft.items)
        if draft is not None and any(getattr(draft, field, None) for field in ("permits_checklist", "inspection_schedule", "training_records", "ppe_by_trade", "emergency_arrangements")):
            sections_draft = draft
        progress.progress(index / len(batches), text=f"Batch {index}/{len(batches)} done / 已完成 {index}/{len(batches)} 批")
    progress.empty()
    unique_flags = list(dict.fromkeys(all_flags))
    if not all_items:
        return None, unique_flags, "; ".join(errors) or "ai_returned_no_items"
    # Steps whose batch failed are covered later by ensure_required_ra_rows.
    merged = RADraft(
        disclaimer=DISCLAIMER,
        overall_risk_level="To be confirmed",
        items=all_items,
        ppe_by_trade=getattr(sections_draft, "ppe_by_trade", []) if sections_draft else [],
        permits_checklist=getattr(sections_draft, "permits_checklist", []) if sections_draft else [],
        emergency_arrangements=getattr(sections_draft, "emergency_arrangements", None) if sections_draft else None,
        training_records=getattr(sections_draft, "training_records", []) if sections_draft else [],
        inspection_schedule=getattr(sections_draft, "inspection_schedule", []) if sections_draft else [],
    )
    return merged, unique_flags, None


def _translate_draft_with_ai(draft: RADraft, language: str, instruction: str) -> RADraft | None:
    """Translate all draft rows into the target language with the AI backend."""
    translated_items: list = []
    for start in range(0, len(draft.items), RA_TRANSLATION_BATCH_SIZE):
        chunk = draft.items[start : start + RA_TRANSLATION_BATCH_SIZE]
        payload = {
            "target_language": language,
            "language_instruction": instruction,
            "ra_draft": {
                "disclaimer": draft.disclaimer,
                "overall_risk_level": draft.overall_risk_level,
                "items": [item.model_dump() for item in chunk],
            },
        }
        result, _flags, error = generate_json(RA_TRANSLATION_SYSTEM_PROMPT, payload, RADraft)
        if error or result is None or len(result.items) != len(chunk):
            return None
        translated_items.extend(result.items)
    return draft.model_copy(update={"items": translated_items})


def enforce_output_language(data: dict, draft: RADraft, use_ai: bool) -> RADraft:
    """Make sure the whole draft is in the selected report language.

    1. If wrong-language rows remain and the AI backend is available, run a
       dedicated translation pass over the draft.
    2. Always finish with the deterministic phrase cleanup as a safety net.
    """
    language = data.get("report_language", "English")
    if language not in CHINESE_LANGUAGES and language != "English":
        return draft
    rows = [item.model_dump() for item in draft.items]
    if use_ai and has_api_key() and rows_language_mismatch_count(rows, language):
        with st.spinner("Normalising report language... / 正在統一報告語言..."):
            translated = _translate_draft_with_ai(draft, language, data.get("language_instruction", ""))
        if translated is not None:
            draft = translated
            rows = [item.model_dump() for item in draft.items]
    normalized = normalize_rows_language(rows, language)
    return draft.model_copy(update={"items": [RAItem.model_validate(row) for row in normalized]})


report_language = render_top_toolbar()

st.markdown(
    """
    <div class="ra-header">
      <div class="ra-kicker">OSH Risk Assessment Tool / 職安健風險評估工具</div>
      <h1>RA Generator</h1>
      <p><strong>Risk Assessment Report Generator / &#39080;&#38570;&#35413;&#20272;&#22577;&#21578;&#29983;&#25104;&#22120;</strong></p>
      <p>Upload a Method Statement or PDF, confirm extracted work steps, then export a formatted RA report.</p>
      <p>上載施工方法書或 PDF，確認抽取工序，再輸出正式風險評估報告。</p>
      <p>Version: 0.1 MVP</p>
      <p>Author: KL Choy | Email: <a href="mailto:choykaleung@yahoo.com.hk">choykaleung@yahoo.com.hk</a> | LinkedIn: <a href="https://www.linkedin.com/in/ka-leung-choy" target="_blank">www.linkedin.com/in/ka-leung-choy</a></p>
      <div class="ra-meta">
        <span class="ra-chip">NVIDIA AI backend</span>
        <span class="ra-chip">Word / Excel export</span>
        <span class="ra-chip">HK OSH + IEC 31010</span>
        <span class="ra-chip">PDF / DOCX / TXT upload</span>
      </div>
    </div>
    <div class="ra-workflow">
      <div class="ra-step"><strong>1. Input / 輸入</strong>MS/PDF, activity, project name, equipment</div>
      <div class="ra-step"><strong>2. Confirm / 確認</strong>Review extracted steps and risk basis</div>
      <div class="ra-step"><strong>3. Export / 輸出</strong>A3 Word RA table and Excel workbook</div>
    </div>
    """,
    unsafe_allow_html=True,
)
if "ra_stage" not in st.session_state:
    st.session_state["ra_stage"] = "collect"

st.subheader(UI["step1"])
st.write(UI["help"])
st.markdown('<div class="ra-form-band"></div>', unsafe_allow_html=True)

with st.form("basic_info"):
    col1, col2 = st.columns(2)
    profiles = profile_options()
    matrices = matrix_options()
    profile_names = list(profiles)
    default_profile_name = profile_names[0] if profile_names else "Hong Kong - Labour Department OSH / CoP"
    selected_profile_name = col1.selectbox("Jurisdiction / assessment standard / 地區及評估標準", profile_names, index=profile_names.index(default_profile_name) if default_profile_name in profile_names else 0)
    selected_profile = profiles[selected_profile_name]
    matrix_names = list(matrices)
    default_matrix_id = selected_profile.get("default_matrix")
    default_matrix_name = next((name for name, matrix in matrices.items() if matrix.get("matrix_id") == default_matrix_id), matrix_names[0])
    selected_matrix_name = col2.selectbox("Risk matrix / 風險矩陣", matrix_names, index=matrix_names.index(default_matrix_name))
    selected_matrix = matrices[selected_matrix_name]
    has_ms = col1.radio(UI["has_ms"], ["Yes", "No / Not sure"], horizontal=True)
    uploaded_ms = col1.file_uploader(UI["upload_ms"], type=["docx", "pdf", "txt"], help=UI["upload_help"])
    col2.markdown('<div class="field-highlight field-highlight-green">2. Construction activity / 施工活動</div>', unsafe_allow_html=True)
    activity = col2.text_input(UI["activity"], placeholder=UI["activity_ph"])
    location = col1.text_input(UI["location"], placeholder=UI["location_ph"])
    equipment = col2.text_area(UI["equipment"], placeholder=UI["equipment_ph"])
    workforce = col1.text_input(
        "Workforce / trades (optional) / 工作人員及工種（可選）",
        placeholder="e.g. 6 trained scaffolders + 1 competent person / 例：6名熟練搭棚工人及1名合資格人士",
    )
    duration = col2.text_input(
        "Duration & time of work (optional) / 工期及作業時間（可選）",
        placeholder="e.g. 5 days, day work only, typhoon season / 例：5天日間工作，颱風季節",
    )
    confined_space = col1.radio(UI["confined"], ["No", "Yes"], horizontal=True)
    matrix_version_default = f"{selected_matrix.get('matrix_id', selected_matrix_name)} / {selected_matrix.get('matrix_name', selected_matrix_name)}"
    standard = matrix_version_default
    col2.caption(f"{UI['standard']}: {matrix_version_default}")
    project = col1.text_input(UI["project"], value="Risk Assessment Report")
    version = col2.text_input("Version / 版本", value="Rev. 0")
    col2.markdown('<div class="field-highlight">Report output language / 報告輸出語言</div>', unsafe_allow_html=True)
    output_language = col2.selectbox(
        UI["output_language"],
        REPORT_LANGUAGE_OPTIONS,
        index=REPORT_LANGUAGE_OPTIONS.index(report_language) if report_language in REPORT_LANGUAGE_OPTIONS else REPORT_LANGUAGE_OPTIONS.index("English"),
    )
    site_rules = st.text_area(
        "Project / site-specific in-house safety rules (optional) / 項目或地盤專屬安全規則（可選）",
        placeholder="Paste client / main contractor / site-specific safety rules here, e.g. permit system, "
        "no-work weather triggers, specific PPE, exclusion zone standards.\n"
        "貼上客戶／總承建商／地盤專屬安全規則，例如許可證制度、停工天氣標準、指定 PPE、禁區要求。",
        height=110,
    )
    method_steps = st.text_area(UI["steps"], placeholder=UI["steps_ph"], height=180)
    submitted = st.form_submit_button(UI["prepare"])

with st.expander("Selected risk matrix", expanded=False):
    st.dataframe(matrix_dataframe(selected_matrix), hide_index=True, width="stretch")
    st.caption(selected_matrix.get("formula", ""))
    st.caption(selected_matrix.get("override_rule", ""))

if submitted:
    ms_text = ""
    ms_file_name = ""
    ms_error = ""
    if uploaded_ms is not None:
        ms_file_name = uploaded_ms.name
        try:
            ms_text = extract_text_from_upload(uploaded_ms, uploaded_ms.name)
        except Exception as exc:
            ms_error = str(exc)

    missing = []
    has_usable_ms = bool(ms_text.strip())
    if not activity.strip() and not has_usable_ms:
        missing.append("Construction activity")
    if not location.strip() and not has_usable_ms:
        missing.append("Project name")
    if not equipment.strip() and not has_usable_ms:
        missing.append("Equipment and tools")
    if missing:
        st.error(UI["missing"] + ", ".join(missing))
    else:
        provided_steps = split_steps(method_steps)
        ai_ms_extraction: MethodStatementExtraction | None = None
        ms_ai_error = ""
        if ms_text.strip() and not provided_steps:
            with st.spinner("AI is reading the Method Statement and separating title, headings and real work steps... / AI 正在分析施工方法書，分開標題、章節及真正工序..."):
                extraction_payload = {
                    "file_name": ms_file_name,
                    "report_language": output_language,
                    "user_activity": activity.strip(),
                    "user_project_name": location.strip(),
                    "method_statement_text": ms_text[:12000],
                    "instructions": [
                        "Extract title separately from work steps.",
                        "Work steps must be sequential physical work activities only.",
                        "Reject headings, safety rules, PPE/training requirements, permit requirements, weather stop-work rules and control measures.",
                        "If the document contains a section named 拆棚工序 / construction sequence / work procedure, use that section as priority.",
                    ],
                }
                extracted, _flags, ms_ai_error = generate_json(MS_EXTRACTION_SYSTEM_PROMPT, extraction_payload, MethodStatementExtraction)
                ai_ms_extraction = extracted if isinstance(extracted, MethodStatementExtraction) else None

        title_candidates = [
            ms_file_name.rsplit(".", 1)[0] if ms_file_name else "",
            project.strip(),
            activity.strip(),
        ]
        if ai_ms_extraction:
            title_candidates.extend([ai_ms_extraction.document_title, ai_ms_extraction.construction_activity, ai_ms_extraction.project_name])
        ai_steps = clean_extracted_steps(ai_ms_extraction.work_steps if ai_ms_extraction else [], title_candidates)
        local_steps = clean_extracted_steps(infer_steps_from_ms_text(ms_text), title_candidates)
        ms_steps = ai_steps or local_steps
        ai_activity = "" if not ai_ms_extraction else ai_ms_extraction.construction_activity
        ai_project_name = "" if not ai_ms_extraction else ai_ms_extraction.project_name
        ai_document_title = "" if not ai_ms_extraction else ai_ms_extraction.document_title
        activity_value = activity.strip() or (ai_activity if ai_activity and ai_activity != "To be confirmed" else f"Works described in uploaded Method Statement: {ms_file_name}")
        location_value = location.strip() or "To be confirmed from Method Statement / project information"
        # getattr: survive Streamlit partial hot-reload where the page is new but
        # already-imported service modules (old schema) have not restarted yet.
        ai_equipment = str(getattr(ai_ms_extraction, "plant_equipment", "") or "").strip()
        equipment_value = equipment.strip() or ai_equipment or "To be confirmed from Method Statement / uploaded document"
        if ai_project_name and ai_project_name != "To be confirmed" and not location.strip():
            location_value = ai_project_name
        project_value = project.strip() or (ai_document_title if ai_document_title and ai_document_title != "To be confirmed" else (ms_file_name.rsplit(".", 1)[0] if ms_file_name else "Risk Assessment Report"))
        steps = provided_steps or ms_steps or infer_steps(activity_value, confined_space)
        library_matches = matched_library_records(activity_value, equipment_value, steps, confined_space)
        st.session_state["ra_input"] = {
            "has_ms": has_ms,
            "activity": activity_value,
            "location": location_value,
            "equipment": equipment_value,
            "confined_space": confined_space,
            "site_rules": site_rules.strip(),
            "workforce": workforce.strip() or str(getattr(ai_ms_extraction, "workforce_trades", "") or ""),
            "duration": duration.strip() or str(getattr(ai_ms_extraction, "duration_time_of_work", "") or ""),
            "standard": standard,
            "jurisdiction_profile": selected_profile,
            "risk_matrix": selected_matrix,
            "project": project_value,
            "version": version,
            "report_language": output_language,
            "language_instruction": LANGUAGE_INSTRUCTIONS[output_language],
            "method_statement_file": ms_file_name,
            "method_statement_text": ms_text,
            "method_statement_error": ms_error,
            "method_statement_ai_error": ms_ai_error,
            "method_statement_ai_extraction": ai_ms_extraction.model_dump() if ai_ms_extraction else {},
            "steps_source": "User provided" if provided_steps else ("NVIDIA AI Method Statement extraction" if ai_steps else ("Uploaded Method Statement inferred" if ms_steps else "AI / industry standard inferred")),
            "confirmed_steps": steps,
            "matched_library_records": library_matches,
            "keyword_map": KEYWORD_MAP,
            "use_ai_backend": True,
        }
        st.session_state["ra_stage"] = "confirm"
        st.session_state.pop("ra_draft", None)

if st.session_state.get("ra_stage") in {"confirm", "generated"}:
    data = st.session_state["ra_input"]
    st.subheader(UI["step2"])
    st.info(UI["step2_help"])
    col1, col2 = st.columns(2)
    edited_project = col1.text_input("Report title / 報告標題", value=data.get("project", ""), key="confirm_project")
    col2.markdown('<div class="field-highlight field-highlight-green">Construction activity / 施工活動</div>', unsafe_allow_html=True)
    edited_activity = col2.text_input("Construction Activity / 施工活動", value=data.get("activity", ""), key="confirm_activity")
    edited_location = col1.text_input("Project name / 工程名稱", value=data.get("location", ""), key="confirm_location")
    edited_equipment = col2.text_area("Equipment & Tools / 設備及工具", value=data.get("equipment", ""), height=90, key="confirm_equipment")
    col2.caption(f"Matrix version / 矩陣版本: {data.get('standard', '-')}")
    col1.markdown('<div class="field-highlight">Report output language / 報告輸出語言</div>', unsafe_allow_html=True)
    edited_output_language = col1.selectbox(
        UI["output_language"],
        REPORT_LANGUAGE_OPTIONS,
        index=REPORT_LANGUAGE_OPTIONS.index(data.get("report_language", "English")) if data.get("report_language", "English") in REPORT_LANGUAGE_OPTIONS else REPORT_LANGUAGE_OPTIONS.index("English"),
        key="confirm_output_language",
    )
    col1.write(f"**Confined Space:** {data['confined_space']}")
    col2.write(f"**Jurisdiction:** {data['jurisdiction_profile']['display_name']}")
    col2.write(f"**Risk Matrix:** {data['risk_matrix']['matrix_name']}")
    col2.write(f"**Steps Source:** {data['steps_source']}")
    if data.get("method_statement_text") and data.get("steps_source") == "AI / industry standard inferred":
        st.warning(
            "上載的文件中找不到真實施工工序（文件可能是圖則、通告或掃描檔）。"
            "以下步驟只是行業通用範本，請在下方自行修改或貼上實際工序後再生成報告。\n\n"
            "No real work steps were found in the uploaded document (it may be a drawing, notice or scanned file). "
            "The steps below are a generic industry template - please edit them or paste the actual work steps before generating."
        )
    if data.get("method_statement_file"):
        col1.write(f"**Uploaded MS:** {data['method_statement_file']}")
        col1.write(f"**MS Extracted Text:** {len(data.get('method_statement_text', ''))} characters")
    if data.get("method_statement_error"):
        st.warning(f"Method Statement upload warning: {data['method_statement_error']}")
    if data.get("method_statement_ai_error"):
        st.info(f"AI Method Statement extraction fallback used: {data['method_statement_ai_error']}")
    if data.get("method_statement_ai_extraction"):
        ai_info = data["method_statement_ai_extraction"]
        with st.expander("AI Method Statement structure / AI 施工方法書結構分析", expanded=False):
            st.write(f"**Document title / 文件標題:** {ai_info.get('document_title', '-')}")
            st.write(f"**Construction activity / 施工活動:** {ai_info.get('construction_activity', '-')}")
            st.write(f"**Project name / 工程名稱:** {ai_info.get('project_name', '-')}")
            if ai_info.get("plant_equipment"):
                st.write(f"**Plant & equipment / 機械及設備:** {ai_info['plant_equipment']}")
            if ai_info.get("workforce_trades"):
                st.write(f"**Workforce / 工作人員:** {ai_info['workforce_trades']}")
            if ai_info.get("working_height_environment"):
                st.write(f"**Height & environment / 高度及環境:** {ai_info['working_height_environment']}")
            if ai_info.get("duration_time_of_work"):
                st.write(f"**Duration / 工期:** {ai_info['duration_time_of_work']}")
            provisions = ai_info.get("existing_safety_provisions") or []
            if provisions:
                st.write("**Safety provisions stated in MS / 文件已列明的安全措施:**")
                st.write("\n".join(f"- {item}" for item in provisions[:15]))
            rejected = ai_info.get("rejected_headings_or_controls") or []
            if rejected:
                st.write("**Rejected headings / controls / 已排除標題或控制措施:**")
                st.write("\n".join(f"- {item}" for item in rejected[:20]))
            if ai_info.get("extraction_notes"):
                st.caption(ai_info["extraction_notes"])
    if data.get("method_statement_text"):
        with st.expander("Method Statement extracted text", expanded=False):
            st.text_area("Extracted text preview", data["method_statement_text"][:6000], height=260, disabled=True)
    with st.expander("Selected risk matrix details / 已選風險矩陣詳情", expanded=False):
        st.dataframe(matrix_dataframe(data["risk_matrix"]), hide_index=True, width="stretch")

    if data.get("matched_library_records"):
        with st.expander("Matched risk library records", expanded=False):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "ID": r.get("id"),
                            "Category": r.get("category"),
                            "Activity": r.get("activity"),
                            "Initial Risk": r.get("initial_risk"),
                        }
                        for r in data["matched_library_records"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )

    confirmed_text = st.text_area(UI["confirmed"], "\n".join(data["confirmed_steps"]), height=220, key="confirmed_steps_text")

    if data["confined_space"] == "Yes":
        st.warning(UI["confined_warning"])

    use_ai_backend = st.checkbox(
        "Use NVIDIA AI backend",
        value=bool(data.get("use_ai_backend", True)),
        help="Unchecked uses local risk library immediately. Checked sends redacted data to the server-side NVIDIA API.",
    )

    # Live AI-backend status so the user knows whether the detailed AI report or
    # the generic local template will be produced.
    if use_ai_backend:
        if not has_api_key():
            st.error(
                "⚠️ AI 後端未啟用：Streamlit Secrets 未設定 `NVIDIA_API_KEY`。"
                "現在只會輸出**通用本地範本**（每個工序內容相近）。"
                "請在 Streamlit Cloud → Settings → Secrets 加入 NVIDIA_API_KEY 以獲得詳細 AI 報告。\n\n"
                "AI backend OFF: NVIDIA_API_KEY is not set, so only the generic local template will be produced."
            )
        else:
            if st.button("測試 AI 連線 / Test AI connection"):
                ok, message = test_connection()
                if ok:
                    st.success(f"AI 連線正常 / AI connected: {model_name()} ({message})")
                else:
                    st.error(f"AI 連線失敗 / AI connection failed: {message} — 會改用本地範本。")

    if st.button(UI["generate"]):
        confirmed_steps = split_steps(confirmed_text)
        data["confirmed_steps"] = confirmed_steps
        data["project"] = edited_project.strip() or "Risk Assessment Report"
        data["activity"] = edited_activity.strip() or "To be confirmed"
        data["location"] = edited_location.strip() or "To be confirmed"
        data["equipment"] = edited_equipment.strip() or "To be confirmed"
        data["standard"] = data.get("standard") or "To be confirmed"
        data["matched_library_records"] = matched_library_records(data["activity"], data["equipment"], confirmed_steps, data["confined_space"])
        data["report_language"] = edited_output_language
        data["language_instruction"] = LANGUAGE_INSTRUCTIONS[edited_output_language]
        data["use_ai_backend"] = use_ai_backend
        flags = []
        ra_source = "local"
        ra_source_reason = ""
        if use_ai_backend:
            with st.spinner("Generating RA report with NVIDIA AI... / NVIDIA AI 正在生成風險評估報告，請稍候..."):
                draft, flags, error = generate_ra_with_ai(data)
            if draft is None:
                ra_source_reason = str(error)
                st.info(f"AI unavailable or output invalid; local risk-library template used. ({error})")
                draft = fallback_ra(data)
            elif not draft.items:
                ra_source_reason = "ai_returned_no_items"
                st.info("AI returned no risk rows; local risk-library template used.")
                draft = fallback_ra(data)
            else:
                ra_source = "ai"
        else:
            ra_source_reason = "ai_backend_unchecked"
            with st.spinner("Generating local risk-library draft... / 正在使用本地風險庫生成草稿..."):
                draft = fallback_ra(data)
        data["ra_source"] = ra_source
        data["ra_source_reason"] = ra_source_reason
        draft = enforce_output_language(data, draft, use_ai_backend)
        st.session_state["ra_input"] = data
        st.session_state["ra_draft"] = draft.model_dump()
        st.session_state["ra_stage"] = "generated"
        flags = [flag for flag in flags if flag != "PERMIT_REDACTED"]
        if flags:
            st.caption("Redaction flags: " + ", ".join(flags))

if st.session_state.get("ra_stage") == "generated" and "ra_draft" in st.session_state:
    st.subheader(UI["step3"])
    data = st.session_state["ra_input"]
    if data.get("ra_source") == "ai":
        st.success("✅ 本報告由 NVIDIA AI 生成（詳細、逐工序）/ Generated by NVIDIA AI (detailed, per work step).")
    else:
        reason = data.get("ra_source_reason", "")
        hint = "（Streamlit Secrets 缺少 NVIDIA_API_KEY）" if reason == "missing_api_key" else (f"（原因 / reason: {reason}）" if reason else "")
        st.warning(
            "📄 本報告使用**本地通用範本**，並非 AI 生成，所以各工序內容相近。"
            f"{hint} 若要詳細、逐工序、按控制階層的 AI 報告，請確認 Streamlit Secrets 已設定 "
            "`NVIDIA_API_KEY`（及 `NVIDIA_MAX_TOKENS = 8192`），並在第二步勾選 Use NVIDIA AI backend 後重新生成。\n\n"
            "This report used the LOCAL generic template (not AI), so steps look similar."
        )
    draft = RADraft.model_validate(st.session_state["ra_draft"])
    rows = ensure_required_ra_rows(data, ra_rows(draft))
    rows = normalize_rows_language(rows, data.get("report_language", "English"))
    checker = quality_check_ra(data, rows)
    if checker["result"] == "PASS FOR SO REVIEW":
        st.success("RA Quality Checker: PASS FOR SO REVIEW")
    else:
        st.warning(f"RA Quality Checker: {checker['result']}")
        with st.expander("Checker comments / 檢查意見", expanded=True):
            for comment in checker.get("comments", []):
                st.write(f"- {comment}")
    st.markdown('<div class="field-highlight">Report output language / 報告輸出語言</div>', unsafe_allow_html=True)
    download_language = st.selectbox(
        UI["output_language"],
        REPORT_LANGUAGE_OPTIONS,
        index=REPORT_LANGUAGE_OPTIONS.index(data.get("report_language", "English")) if data.get("report_language", "English") in REPORT_LANGUAGE_OPTIONS else REPORT_LANGUAGE_OPTIONS.index("English"),
        key="download_output_language",
    )
    if download_language != data.get("report_language"):
        st.info("Download headings and table labels will use the selected language. To rewrite the RA content itself in that language, select the language in Step 2 and Generate again with NVIDIA AI backend.")
    report = {
        "title": data["project"],
        "Project": data["project"],
        "Construction Activity": data["activity"],
        "Task Location": data["location"],
        "Assessment Standard": data["standard"],
        "Jurisdiction Profile": data["jurisdiction_profile"]["display_name"],
        "Risk Matrix": data["risk_matrix"]["matrix_name"],
        "Assessment Date": date.today().isoformat(),
        "Version": data["version"],
        "Next Review Date": (date.today() + timedelta(days=365)).isoformat(),
        "Report Language": download_language,
        "Method Statement Source": data.get("method_statement_file") or data.get("steps_source", "-"),
        "Method Statement Extract": data.get("method_statement_text", ""),
        "Confirmed Steps": data.get("confirmed_steps", []),
    }

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    def _dump_rows(value):
        return [row.model_dump() if hasattr(row, "model_dump") else dict(row) for row in (value or [])]

    emergency_obj = getattr(draft, "emergency_arrangements", None)
    sections = {
        "ppe_by_trade": list(getattr(draft, "ppe_by_trade", []) or []),
        "permits_checklist": _dump_rows(getattr(draft, "permits_checklist", [])),
        "emergency_arrangements": (emergency_obj.model_dump() if hasattr(emergency_obj, "model_dump") else dict(emergency_obj)) if emergency_obj else {},
        "training_records": _dump_rows(getattr(draft, "training_records", [])),
        "inspection_schedule": _dump_rows(getattr(draft, "inspection_schedule", [])),
    }
    if sections["permits_checklist"]:
        with st.expander("Permits & statutory documentation / 許可證及法定文件", expanded=False):
            st.dataframe(pd.DataFrame(sections["permits_checklist"]), hide_index=True, width="stretch")
    if sections["emergency_arrangements"]:
        with st.expander("Emergency arrangements / 應急安排", expanded=False):
            ea = sections["emergency_arrangements"]
            for scenario in ea.get("foreseeable_scenarios", []):
                st.write(f"- {scenario}")
            for key in ("rescue_plan", "first_aid", "emergency_contacts", "assembly_point", "adverse_weather_arrangements"):
                if ea.get(key):
                    st.write(f"**{key}:** {ea[key]}")
    if sections["training_records"]:
        with st.expander("Training & competency records / 訓練及資格紀錄", expanded=False):
            st.dataframe(pd.DataFrame(sections["training_records"]), hide_index=True, width="stretch")
    if sections["inspection_schedule"]:
        with st.expander("Monitoring & inspection schedule / 監察及巡查時間表", expanded=False):
            st.dataframe(pd.DataFrame(sections["inspection_schedule"]), hide_index=True, width="stretch")

    docx = docx_export.build_ra_docx(report, rows, data.get("risk_matrix", {}), sections)
    xlsx = build_ra_excel(report, rows, data.get("risk_matrix", {}))
    col1, col2 = st.columns(2)
    col1.download_button(UI["word"], docx, file_name="risk_assessment_report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    col2.download_button(UI["excel"], xlsx, file_name="risk_assessment_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
