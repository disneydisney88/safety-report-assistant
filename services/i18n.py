LANG_OPTIONS = {
    "繁中": "zh_hant",
    "简中": "zh_hans",
    "English": "en",
}

TEXT = {
    "app_title": {
        "zh_hant": "HK Safety Report Assistant",
        "zh_hans": "HK Safety Report Assistant",
        "en": "HK Safety Report Assistant",
    },
    "language": {"zh_hant": "介面語言", "zh_hans": "界面语言", "en": "Interface language"},
    "draft_warning": {
        "zh_hant": "AI-generated draft. To be reviewed and approved by Safety Officer / authorised person before use.",
        "zh_hans": "AI-generated draft. To be reviewed and approved by Safety Officer / authorised person before use.",
        "en": "AI-generated draft. To be reviewed and approved by Safety Officer / authorised person before use.",
    },
    "config_status": {"zh_hant": "設定狀態", "zh_hans": "设置状态", "en": "Configuration status"},
    "loaded": {"zh_hant": "已載入", "zh_hans": "已加载", "en": "Loaded"},
    "missing": {"zh_hant": "未設定", "zh_hans": "未设置", "en": "Missing"},
    "generate": {"zh_hant": "產生草稿", "zh_hans": "生成草稿", "en": "Generate draft"},
    "export_word": {"zh_hant": "匯出 Word", "zh_hans": "导出 Word", "en": "Export Word"},
    "save_record": {"zh_hant": "儲存記錄", "zh_hans": "保存记录", "en": "Save record"},
    "upload_to_drive": {"zh_hant": "上載至 Google Drive", "zh_hans": "上传至 Google Drive", "en": "Upload to Google Drive"},
    "project": {"zh_hant": "項目", "zh_hans": "项目", "en": "Project"},
    "location": {"zh_hant": "位置 / 工作區", "zh_hans": "位置 / 工作区", "en": "Location / work area"},
    "contractor": {"zh_hant": "承建商 / 分判商", "zh_hans": "承建商 / 分包商", "en": "Contractor / subcontractor"},
    "date": {"zh_hant": "日期", "zh_hans": "日期", "en": "Date"},
    "status": {"zh_hant": "狀態", "zh_hans": "状态", "en": "Status"},
    "risk_level": {"zh_hant": "風險等級", "zh_hans": "风险等级", "en": "Risk level"},
    "responsible": {"zh_hant": "負責人", "zh_hans": "负责人", "en": "Responsible person"},
    "target_date": {"zh_hant": "目標完成日期", "zh_hans": "目标完成日期", "en": "Target completion date"},
    "ai_unavailable": {
        "zh_hant": "未能連接 AI，以下為本機範本草稿。",
        "zh_hans": "未能连接 AI，以下为本机模板草稿。",
        "en": "AI is unavailable; showing a local template draft.",
    },
}


def get_lang() -> str:
    import streamlit as st

    return st.session_state.get("lang", "zh_hant")


def t(key: str, lang: str | None = None) -> str:
    lang = lang or get_lang()
    return TEXT.get(key, {}).get(lang, TEXT.get(key, {}).get("en", key))

