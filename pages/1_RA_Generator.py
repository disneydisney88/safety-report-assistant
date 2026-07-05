from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

import services.docx_export as docx_export
from services.ai_prompts import DISCLAIMER, MS_EXTRACTION_SYSTEM_PROMPT, RA_HIDDEN_PROMPT_CONTRACT, RA_SYSTEM_PROMPT
from services.excel_export import build_ra_excel
from services.file_extract import extract_text_from_upload, infer_steps_from_ms_text
from services.nvidia_client import generate_json
from services.validators import MethodStatementExtraction, RADraft

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
    "output_language": "Report output language / ?勗?頛詨隤?",
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

UI["output_language"] = "Report output language / \u5831\u544a\u8f38\u51fa\u8a9e\u8a00"


def load_json(name: str, fallback):
    path = CONFIG_DIR / name
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


RISK_LIBRARY = load_json("risk_library.json", [])
KEYWORD_MAP = load_json("keyword_map.json", {})
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


def clean_extracted_steps(raw_steps: list[str], titles: list[str] | None = None, max_steps: int = 14) -> list[str]:
    title_keys = {_compact_text(title) for title in (titles or []) if title}
    always_blocked_terms = [
        "施工方案",
        "methodstatement",
        "安全程序及措施",
        "拆棚之程序",
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
    ]
    action_terms = [
        "拆",
        "安裝",
        "吊",
        "搬",
        "運",
        "傳",
        "清",
        "set up",
        "install",
        "remove",
        "dismantle",
        "transport",
        "carry out",
        "inspect",
    ]
    steps: list[str] = []
    for raw in raw_steps:
        clean = str(raw or "").strip(" \t-*0123456789.)、")
        compact = _compact_text(clean)
        if not clean or len(compact) < 4:
            continue
        if compact in title_keys or any(compact == title or compact in title for title in title_keys):
            continue
        if any(term in compact for term in always_blocked_terms):
            continue
        if any(term in compact for term in blocked_terms) and not any(term in clean.lower() for term in action_terms):
            continue
        if clean not in steps:
            steps.append(clean[:260])
        if len(steps) >= max_steps:
            break
    return steps


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


def fallback_ra(data: dict) -> RADraft:
    items = []
    library_records = data.get("matched_library_records", [])
    matrix = data.get("risk_matrix", {})
    severity_scale = matrix.get("severity_scale", [])
    likelihood_scale = matrix.get("likelihood_scale", [])
    default_severity = severity_scale[-1] if severity_scale else {"code": "S5", "score": 5, "label_en": "Catastrophic"}
    default_likelihood = likelihood_scale[1] if len(likelihood_scale) > 1 else {"code": "P2", "score": 2, "label_en": "Unlikely"}
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
                    "work_step": step,
                    "hazard": local_text(data, "; ".join(hazards)),
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
    return [
        {
            "Work Step": item.work_step,
            "Hazard": item.hazard,
            "Possible Consequence": item.possible_consequence,
            "Persons at Risk": item.persons_at_risk,
            "Initial Risk": item.initial_risk_rating,
            "Existing Controls": item.existing_control_measures,
            "Additional Controls Required": item.additional_control_measures_required,
            "Residual Risk": item.residual_risk_rating,
            "Legal / CoP Reference": item.legal_cop_reference,
            "Permit / Competent Person": item.permit_certificate_competent_person_required,
            "Inspection / Monitoring": item.inspection_monitoring_points,
            "Responsible Person": item.responsible_person,
            "Remarks": item.remarks_items_to_be_confirmed,
        }
        for item in draft.items
    ]


def _rating_from_matrix(matrix: dict, likelihood: int, severity: int) -> str:
    score = likelihood * severity
    level = "MR"
    for band in matrix.get("risk_bands", []):
        if int(band.get("min", 0)) <= score <= int(band.get("max", 0)):
            level = str(band.get("level", level))
            break
    return f"P{likelihood} x S{severity} = {score} {level}"


def ensure_required_ra_rows(data: dict, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        rows = ra_rows(fallback_ra(data))

    language = data.get("report_language", "English")
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

    def row_en(kind: str) -> dict[str, str]:
        if kind == "weather":
            return {
                "Work Step": "Work under adverse weather or extreme site conditions",
                "Hazard": "Heavy rain; strong wind; lightning; typhoon signal; wet or slippery working surface",
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

    chinese = language in {"Traditional Chinese", "Simplified Chinese"}
    if any(keyword in joined for keyword in outdoor_keywords) and not has_weather:
        rows.append(row_zh("weather") if chinese else row_en("weather"))
    if any(keyword in joined for keyword in public_keywords) and not has_public:
        rows.append(row_zh("public") if chinese else row_en("public"))
    return rows


def build_hidden_report_prompt(data: dict) -> str:
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
    if any(token in joined for token in ["hot work", "welding", "cutting", "grinding", "熱工", "焊", "切割", "打磨"]):
        triggers.append("Hot work: include hot work permit, fire watch, combustible material control and post-work fire check.")
    if not triggers:
        triggers.append("No special trigger detected: still include task-specific hazards for each confirmed work step.")

    steps = "\n".join(f"{idx}. {step}" for idx, step in enumerate(data.get("confirmed_steps", []), start=1)) or "To be confirmed"
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
            f"- matrix version: {data.get('standard', matrix.get('matrix_name', 'To be confirmed'))}",
            f"- risk matrix name: {matrix.get('matrix_name', 'To be confirmed')}",
            "",
            "Confirmed work steps:",
            steps,
            "",
            "Work-step quality rules:",
            "- Use only real sequential work activities as work steps.",
            "- Do not treat the Method Statement title, section heading, training requirement, PPE requirement or control measure as a work step.",
            "- Hazard cause must state the direct unsafe condition or exposure; never use 'confirm with approved Method Statement' as the cause.",
            "",
            "Risk band rules from selected matrix:",
            "\n".join(band_lines) or "Use selected matrix in payload.",
            "",
            "Detected mandatory coverage triggers:",
            "\n".join(f"- {trigger}" for trigger in triggers),
            "",
            "Return the completed RADraft JSON only. Do not explain the report outside JSON.",
        ]
    )


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
    activity = col2.text_input(UI["activity"], placeholder=UI["activity_ph"])
    location = col1.text_input(UI["location"], placeholder=UI["location_ph"])
    equipment = col2.text_area(UI["equipment"], placeholder=UI["equipment_ph"])
    confined_space = col1.radio(UI["confined"], ["No", "Yes"], horizontal=True)
    matrix_version_default = f"{selected_matrix.get('matrix_id', selected_matrix_name)} / {selected_matrix.get('matrix_name', selected_matrix_name)}"
    standard = matrix_version_default
    col2.caption(f"{UI['standard']}: {matrix_version_default}")
    project = col1.text_input(UI["project"], value="Risk Assessment Report")
    version = col2.text_input("Version / 版本", value="Rev. 0")
    output_language = col2.selectbox(
        UI["output_language"],
        REPORT_LANGUAGE_OPTIONS,
        index=REPORT_LANGUAGE_OPTIONS.index(report_language) if report_language in REPORT_LANGUAGE_OPTIONS else REPORT_LANGUAGE_OPTIONS.index("English"),
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
        equipment_value = equipment.strip() or "To be confirmed from Method Statement / uploaded document"
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
    edited_activity = col2.text_input("Construction Activity / 施工活動", value=data.get("activity", ""), key="confirm_activity")
    edited_location = col1.text_input("Project name / 工程名稱", value=data.get("location", ""), key="confirm_location")
    edited_equipment = col2.text_area("Equipment & Tools / 設備及工具", value=data.get("equipment", ""), height=90, key="confirm_equipment")
    col2.caption(f"Matrix version / 矩陣版本: {data.get('standard', '-')}")
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
        if use_ai_backend:
            payload = {
                **data,
                "method_statement_text": data.get("method_statement_text", "")[:12000],
                "hidden_report_prompt": build_hidden_report_prompt(data),
                "instruction": (
                    "Prepare a professional Risk Assessment Report according to IEC 31010 and Hong Kong safety legislation / CoP. "
                    "Use the uploaded Method Statement text, confirmed steps and matched risk library first. Do not invent exact legal clause numbers. "
                    "Use the selected jurisdiction profile and selected risk matrix. Calculate risk scores as likelihood x severity and ensure LR/MR/HR matches the selected matrix band. "
                    "The RA table must include at least one risk row for every confirmed construction step. "
                    "Translate all report content, including construction steps, hazards, consequences, control measures, PPE/training and residual risk remarks, into the selected report output language. "
                    "Each high-risk activity must include hazards, consequences, specific controls, permit/certificate requirements, competent person requirements, inspection points and emergency response. "
                    "Follow hidden_report_prompt exactly; it is the controlling professional report specification. "
                    "Show roles only, no personal names. Output valid JSON matching the approved RA schema. "
                    f"{data['language_instruction']}"
                ),
            }
            with st.spinner("Generating RA report with NVIDIA AI... / NVIDIA AI 正在生成風險評估報告，請稍候..."):
                draft, flags, error = generate_json(RA_SYSTEM_PROMPT, payload, RADraft)
            if draft is None:
                st.info(f"AI unavailable or output invalid; local risk-library template used. ({error})")
                draft = fallback_ra(data)
            elif not draft.items:
                st.info("AI returned no risk rows; local risk-library template used.")
                draft = fallback_ra(data)
        else:
            with st.spinner("Generating local risk-library draft... / 正在使用本地風險庫生成草稿..."):
                draft = fallback_ra(data)
        st.session_state["ra_input"] = data
        st.session_state["ra_draft"] = draft.model_dump()
        st.session_state["ra_stage"] = "generated"
        if flags:
            st.caption("Redaction flags: " + ", ".join(flags))

if st.session_state.get("ra_stage") == "generated" and "ra_draft" in st.session_state:
    st.subheader(UI["step3"])
    data = st.session_state["ra_input"]
    draft = RADraft.model_validate(st.session_state["ra_draft"])
    rows = ensure_required_ra_rows(data, ra_rows(draft))
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

    docx = docx_export.build_ra_docx(report, rows, data.get("risk_matrix", {}))
    xlsx = build_ra_excel(report, rows, data.get("risk_matrix", {}))
    col1, col2 = st.columns(2)
    col1.download_button(UI["word"], docx, file_name="risk_assessment_report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    col2.download_button(UI["excel"], xlsx, file_name="risk_assessment_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
