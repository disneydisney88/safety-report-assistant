"""Deterministic Pre-RA Data Extraction Sheet.

Builds the factual basis a user confirms BEFORE the RA is generated:
high-risk flags, permit triggers, plant/tools, competency, environment
interfaces, emergency needs and a missing-information list.

Driven by config/hk_ra_master_database_v1.json (keyword_map + permit_rules),
so it works even when the AI backend is slow or unavailable; AI extraction
results are merged in on top when present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

FLAG_MODULES = [
    "work_at_height",
    "scaffolding",
    "lifting",
    "plant_vehicle",
    "confined_space",
    "excavation",
    "electrical",
    "hot_work",
    "demolition_cutting",
    "foundation",
    "chemical_health",
    "public_interface",
]

FLAG_LABELS = {
    "work_at_height": "Work at height / 高處工作",
    "scaffolding": "Scaffolding / 棚架",
    "lifting": "Lifting operation / 吊運",
    "plant_vehicle": "Plant & vehicle / 機械車輛",
    "confined_space": "Confined space / 密閉空間",
    "excavation": "Excavation / 挖掘",
    "electrical": "Electrical work / 電力工作",
    "hot_work": "Hot work / 熱工作",
    "demolition_cutting": "Demolition & cutting / 打拆切割",
    "foundation": "Foundation works / 地基工程",
    "chemical_health": "Chemical & health / 化學品及職業健康",
    "public_interface": "Public interface / 公眾介面",
}

# Plant / powered tools / lifting gear / materials worth surfacing for the
# user to confirm. Keyword -> display name.
PLANT_TOOL_KEYWORDS = {
    "mobile crane": "Mobile crane / 吊雞車",
    "吊雞車": "Mobile crane / 吊雞車",
    "tower crane": "Tower crane / 塔吊",
    "塔吊": "Tower crane / 塔吊",
    "crane": "Crane / 吊機",
    "吊機": "Crane / 吊機",
    "mewp": "MEWP / 升降台",
    "升降台": "MEWP / 升降台",
    "scissor lift": "MEWP (scissor lift)",
    "boom lift": "MEWP (boom lift)",
    "forklift": "Forklift / 叉車",
    "叉車": "Forklift / 叉車",
    "excavator": "Excavator / 挖掘機",
    "挖掘機": "Excavator / 挖掘機",
    "gondola": "Suspended working platform / 吊船",
    "吊船": "Suspended working platform / 吊船",
    "grinder": "Grinder / 打磨機",
    "打磨": "Grinder / 打磨機",
    "breaker": "Breaker / 破碎機",
    "破碎": "Breaker / 破碎機",
    "drill": "Drill / 鑽機",
    "鑽孔": "Drill / 鑽機",
    "wet coring": "Wet coring machine / 濕鑽",
    "濕鑽": "Wet coring machine / 濕鑽",
    "wire cutting": "Wire cutting machine",
    "welding": "Welding set / 電焊機",
    "燒焊": "Welding set / 電焊機",
    "電焊": "Welding set / 電焊機",
    "風煤": "Gas cutting set / 風煤",
    "gas cutting": "Gas cutting set / 風煤",
    "generator": "Generator / 發電機",
    "發電機": "Generator / 發電機",
    "chain block": "Chain block / 手拉葫蘆",
    "手拉葫蘆": "Chain block / 手拉葫蘆",
    "sling": "Slings & shackles / 吊索卸扣",
    "吊索": "Slings & shackles / 吊索卸扣",
    "ladder": "Ladder / 梯具",
    "梯": "Ladder / 梯具",
    "竹": "Bamboo / 竹料",
    "bamboo": "Bamboo / 竹料",
    "scaffold": "Scaffold materials / 棚架物料",
    "棚架": "Scaffold materials / 棚架物料",
    "110v": "110V tools / 110V 工具",
    "220v": "220V equipment / 220V 設備",
    "extension cable": "Extension cable / 拖板電纜",
    "拖板": "Extension cable / 拖板電纜",
    "油漆": "Paint / solvent / 油漆溶劑",
    "paint": "Paint / solvent / 油漆溶劑",
    "thinner": "Paint / solvent / 油漆溶劑",
    "epoxy": "Epoxy / sealant",
    "防水": "Waterproofing material / 防水物料",
}

COMPETENCY_BY_FLAG = {
    "scaffolding": ["Competent Person (scaffold) + Form 5 inspection / 合資格人士（棚架）及表格五檢查", "Trained scaffolders / 受訓棚架工人"],
    "lifting": ["Crane operator certificate / 吊機操作員證書", "Rigger & signaller training / 索具工及訊號員訓練", "Lifting supervisor / 吊運督導"],
    "electrical": ["Registered Electrical Worker (REW) / 註冊電業工人", "LOTO briefing / 上鎖掛牌簡介"],
    "confined_space": ["Competent Person (confined space) assessment / 合資格人士評估", "Certified workers / 核准工人", "Standby person / 待命人員"],
    "plant_vehicle": ["Trained plant operator (MEWP / forklift) certificate / 受訓機械操作員證書", "Banksman / 訊號指揮員"],
    "hot_work": ["Trained welder / cutter / 受訓焊工", "Fire watcher / 防火監察員"],
    "excavation": ["Competent Person (excavation) inspection / 合資格人士（挖掘）檢查"],
    "work_at_height": ["Working-at-height training / 高處工作訓練", "Green Card / 平安咭 (all workers)"],
    "foundation": ["Competent operator + plant certificates / 合資格操作員及機械證書"],
}

EMERGENCY_BY_FLAG = {
    "work_at_height": "Fall rescue plan: rescue kit / descent device, trained rescuer, suspension trauma time limit / 高處墮下救援計劃：救援套件、受訓救援員、注意懸吊創傷時限",
    "confined_space": "Tripod + lifeline + BA standby, standby person, NO unprotected rescue / 三腳架、救生繩、待命呼吸器，嚴禁無保護救援",
    "lifting": "Falling object / trapped person response, exclusion zone control / 墮物或被困應變、禁區控制",
    "electrical": "Electric shock response: isolation first, CPR / AED / 觸電應變：先隔離電源，心肺復甦 / AED",
    "hot_work": "Fire emergency: extinguisher at point of work, fire watch after completion / 火警應變：工作點滅火筒、完工後防火監察",
    "excavation": "Collapse rescue: no blind entry, emergency access / 坍塌救援：嚴禁盲目進入、緊急通道",
    "chemical_health": "Eyewash, SDS available, spill kit; heat stress: rest area, drinking water / 洗眼、SDS、洩漏套件；中暑：休息處、飲用水",
    "public_interface": "Public injury response and incident reporting / 公眾受傷應變及事故通報",
}

_ENVIRONMENT_CHECKS = [
    (["電房", "電掣房", "switch room", "live cable", "live electrical", "gas pipe", "煤氣", "水管", "water main"], "Adjacent live services / 鄰近帶電或帶壓設施"),
    (["公眾", "行人", "footpath", "道路", "traffic", "住戶", "occupied", "鄰近物業"], "Adjacent public area / 鄰近公眾範圍"),
    (["開口", "臨邊", "樓邊", "天台", "roof edge", "lift shaft", "升降機槽", "slab opening"], "Floor opening / edge / 開口及臨邊"),
    (["濕", "雨", "wet", "washing", "沖洗"], "Wet condition / 濕滑環境"),
    (["粉塵", "噪音", "dust", "noise", "打磨", "破碎", "鑽"], "Dust / noise / 粉塵噪音"),
    (["機房", "plant room", "電掣房", "restricted", "限制進入"], "Restricted access area / 限制進入區域"),
    (["夜間", "night work", "照明不足", "low light"], "Night work / low lighting / 夜間或照明不足"),
    (["吊運路線", "lifting route", "吊運範圍"], "Lifting route interface / 吊運路線交界"),
]


def load_master_db() -> dict[str, Any]:
    path = _CONFIG_DIR / "hk_ra_master_database_v1.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _split_keywords(*fields: str) -> list[str]:
    tokens: list[str] = []
    for field in fields:
        for token in re.split(r"[、,，/;；]+", str(field or "")):
            token = token.strip().lower()
            if len(token) >= 2:
                tokens.append(token)
    return tokens


def _token_hit(token: str, lower_text: str) -> bool:
    """CJK tokens match by substring; ASCII tokens require word boundaries so
    'ELS' cannot hide inside 'levels' or 'panels' and flag foundation works."""
    if not token:
        return False
    if re.search(r"[一-鿿]", token):
        return token in lower_text
    if len(token) < 3:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", lower_text) is not None


# Synonyms the master DB keyword modules do not cover yet (e.g. steps say
# 電源/380V rather than 用電/電纜).
EXTRA_MODULE_KEYWORDS = {
    "electrical": ["電源", "電壓", "供電", "380v", "220v", "110v", "隔離掣", "power supply", "isolator"],
    "lifting": ["吊籠", "物料吊機", "hoist"],
    "work_at_height": ["吊籠", "bmu"],
}


def detect_flags(text: str, db: dict[str, Any]) -> dict[str, str]:
    """Return {module: 'Yes' | 'Unknown'} from the master DB keyword_map."""
    lower = str(text or "").lower()
    flags = {module: "Unknown" for module in FLAG_MODULES}
    for entry in db.get("keyword_map", []):
        module = str(entry.get("module", ""))
        if module not in flags:
            continue
        tokens = _split_keywords(entry.get("keywords_cn", ""), entry.get("keywords_en", ""))
        tokens += [t.lower() for t in EXTRA_MODULE_KEYWORDS.get(module, [])]
        if any(_token_hit(token, lower) for token in tokens):
            flags[module] = "Yes"
    return flags


def detect_permits(text: str, db: dict[str, Any]) -> list[dict[str, str]]:
    """Match master-DB permit rules against the MS text / steps."""
    lower = str(text or "").lower()
    permits: list[dict[str, str]] = []
    for rule in db.get("permit_rules", []):
        tokens = _split_keywords(rule.get("trigger_condition", ""))
        if any(_token_hit(token, lower) for token in tokens):
            permits.append(
                {
                    "permit_name": str(rule.get("permit_name", "")),
                    "trigger": str(rule.get("trigger_condition", "")),
                    "key_controls": str(rule.get("key_controls", "")),
                    "issued_by": str(rule.get("approval_or_holder", "")),
                    "status": "To be confirmed",
                }
            )
    return permits


def detect_plant_tools(text: str) -> list[str]:
    lower = str(text or "").lower()
    found: list[str] = []
    for keyword, display in PLANT_TOOL_KEYWORDS.items():
        if keyword in lower and display not in found:
            found.append(display)
    return found


def detect_environment(text: str) -> list[str]:
    lower = str(text or "").lower()
    found: list[str] = []
    for tokens, display in _ENVIRONMENT_CHECKS:
        if any(token.lower() in lower for token in tokens):
            found.append(display)
    return found


def competency_for_flags(flags: dict[str, str]) -> list[str]:
    items: list[str] = []
    for module, status in flags.items():
        if status == "Yes":
            for entry in COMPETENCY_BY_FLAG.get(module, []):
                if entry not in items:
                    items.append(entry)
    if items and "Green Card / 平安咭 (all workers)" not in items:
        items.append("Green Card / 平安咭 (all workers)")
    return items

def emergency_for_flags(flags: dict[str, str]) -> list[str]:
    return [EMERGENCY_BY_FLAG[m] for m, s in flags.items() if s == "Yes" and m in EMERGENCY_BY_FLAG]


def missing_information(text: str, flags: dict[str, str]) -> list[str]:
    """Clarifications the user should confirm before generating the RA."""
    lower = str(text or "").lower()
    missing: list[str] = []

    def lacks(*tokens: str) -> bool:
        return not any(token.lower() in lower for token in tokens)

    if flags.get("lifting") == "Yes" and lacks("吊運路線", "lifting route", "lifting plan", "吊運計劃"):
        missing.append("Lifting route / lifting plan not stated / 未列明吊運路線或吊運計劃")
    if flags.get("lifting") == "Yes" and lacks("swl", "safe working load", "安全負荷"):
        missing.append("Crane / lifting gear SWL and model not stated / 未列明吊機或吊具 SWL 及型號")
    if flags.get("work_at_height") == "Yes" and lacks("救援", "rescue"):
        missing.append("Fall rescue arrangement not stated / 未列明高處墮下救援安排")
    if flags.get("scaffolding") == "Yes" and lacks("合資格人士", "competent person", "form 5", "表格五"):
        missing.append("Scaffold competent person / Form 5 not stated / 未列明棚架合資格人士或表格五")
    if flags.get("electrical") == "Yes" and lacks("110v", "220v", "rcd", "elcb", "漏電"):
        missing.append("Electrical supply / RCD details unclear / 未列明電源 (110V/220V) 或漏電保護")
    if flags.get("confined_space") == "Yes" and lacks("氣體測試", "gas test"):
        missing.append("Confined space gas testing not stated / 未列明密閉空間氣體測試")
    if flags.get("public_interface") == "Yes" and lacks("圍板", "hoarding", "catch fan", "接物", "公眾保護"):
        missing.append("Public protection measures unclear / 未列明公眾保護措施")
    if lacks("樓", "floor", "zone", "位置", "location", "/f", "天台", "roof"):
        missing.append("Exact working location / floor / zone not stated / 未列明確實工作位置")
    return missing


def build_pre_ra_sheet(ms_text: str, steps: list[str], data: dict[str, Any], db: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble the Pre-RA Data Extraction Sheet (deterministic baseline)."""
    db = db if db is not None else load_master_db()
    # Flags and permits come from the user's own activity / equipment / steps.
    # The full MS text is deliberately excluded here: MS boilerplate safety
    # sections (no-smoking, welding bans, confined-space notices) otherwise
    # flag hot work / confined space / scaffolding on unrelated jobs.
    steps_corpus = " ".join(
        [
            str(data.get("activity", "")),
            str(data.get("equipment", "")),
            str(data.get("location", "")),
            " ".join(steps or []),
        ]
    )
    full_corpus = steps_corpus + " " + str(ms_text or "")[:12000]
    flags = detect_flags(steps_corpus, db)
    if str(data.get("confined_space", "No")) == "Yes":
        flags["confined_space"] = "Yes"
    return {
        "flags": flags,
        "plant_tools": detect_plant_tools(full_corpus),
        "permits": detect_permits(steps_corpus, db),
        "competency": competency_for_flags(flags),
        "environment": detect_environment(full_corpus),
        "emergency": emergency_for_flags(flags),
        "missing_info": missing_information(full_corpus, flags),
    }


def format_pre_ra_for_prompt(sheet: dict[str, Any]) -> str:
    """Render the confirmed sheet as a factual-basis block for the AI brief."""
    lines: list[str] = ["Confirmed Pre-RA factual basis (user-verified; build the RA on these facts):"]
    flags = sheet.get("flags", {})
    lines.append("High-risk activity flags: " + (", ".join(f"{FLAG_LABELS.get(m, m)}={s}" for m, s in flags.items()) or "none"))
    for key, title, instruction in [
        ("plant_tools", "Plant / tools / materials involved", "trigger the matching hazards (e.g. grinder -> abrasive wheel, sparks, eye injury, electrical)"),
        ("permits", "Permits / certificates triggered", "include each in permits_checklist with correct category and issuer"),
        ("competency", "Competency / workforce requirements", "reflect in training_records and permit_certificate_competent_person_required"),
        ("environment", "Work environment / interfaces", "make hazards and controls site-specific to these interfaces"),
        ("emergency", "Emergency / rescue needs", "cover each in emergency_arrangements"),
        ("missing_info", "Missing information to confirm", "state as assumptions flagged for site verification in remarks; do not guess"),
    ]:
        values = sheet.get(key) or []
        if key == "permits":
            rendered = "; ".join(f"{p.get('permit_name')} (issued by {p.get('issued_by', 'TBC')})" for p in values) or "none detected"
        else:
            rendered = "; ".join(str(v) for v in values) or "none detected"
        lines.append(f"{title} ({instruction}): {rendered}")
    return "\n".join(lines)



def build_default_sections(sheet: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Deterministic supporting sections (permits / emergency / training /
    inspection) built from the confirmed Pre-RA sheet.

    Used when the AI omits these RADraft fields so the Word report never
    skips permits / emergency / training / inspection. Content is written in
    the selected report language only (short standard technical terms such as
    Form 5 / LOTO / RPE stay in English), never mixed within a sentence.
    Placeholders in [square brackets] mark details the site team must
    complete before work starts.
    """
    language = str(data.get("report_language", "English"))
    chinese = language in {"Traditional Chinese", "Simplified Chinese"}

    def T(en: str, zh: str) -> str:
        return zh if chinese else en

    flags = sheet.get("flags", {}) or {}
    corpus = " ".join([
        str(data.get("activity", "")),
        str(data.get("equipment", "")),
        " ".join(str(s) for s in (data.get("confirmed_steps") or [])),
    ]).lower()
    bmu = any(t in corpus for t in ["bmu", "吊船", "gondola", "suspended working platform", "吊籠"])
    scaffold = flags.get("scaffolding") == "Yes" or any(t in corpus for t in ["棚", "scaffold"])
    lifting = flags.get("lifting") == "Yes" or any(t in corpus for t in ["吊運", "lifting", "crane", "吊機", "hoist", "吊眼", "吊架", "葫蘆"])
    at_height = bmu or scaffold or flags.get("work_at_height") == "Yes" or any(t in corpus for t in ["高處", "height", "外牆", "天台", "roof", "工作台", "防墮"])
    electrical = flags.get("electrical") == "Yes" or any(t in corpus for t in ["380v", "電源", "electri", "power supply", "濕鑽", "濕式鑽"])
    bamboo = any(t in corpus for t in ["竹棚", "竹枝", "竹料", "bamboo"])
    # Confined space training only when work actually enters a confined space,
    # not merely because a manhole / shaft is mentioned.
    confined = flags.get("confined_space") == "Yes" or any(t in corpus for t in ["密閉空間", "進入井內", "缺氧", "confined space"])
    # Hot work means flame / arc, NOT wet concrete drilling or sawing.
    hot_work = flags.get("hot_work") == "Yes" or any(t in corpus for t in ["燒焊", "焊接", "電焊", "風煤", "flame cut", "weld", "gas cutting"])
    cutting = any(t in corpus for t in ["切割", "鑽孔", "鑽切", "拆卸", "打拆", "demolition", "coring", "concrete cutting"])
    transport = any(t in corpus for t in ["叉車", "唧車", "托板車", "forklift", "pallet"])
    temp_works = any(t in corpus for t in ["回頂", "假支架", "模板", "falsework", "formwork", "propping", "back-prop"])
    concreting = any(t in corpus for t in ["澆築", "混凝土工程", "植筋", "扎鐵", "紮鐵", "concrete casting", "rebar"])

    permits: list[dict[str, str]] = []

    def _permit(name: str, category: str, basis: str, issued_by: str, validity: str) -> None:
        if not any(p["permit_or_form"] == name for p in permits):
            permits.append({
                "permit_or_form": name,
                "category": category,
                "legal_basis_or_sms_ref": basis,
                "issued_by": issued_by,
                "validity": validity,
                "status": T("To be confirmed", "待確認"),
            })

    cat_statutory = T("Statutory", "法定")
    cat_inhouse = T("In-house", "公司內部")
    sms = T("Company safety management system (SMS)", "公司安全管理系統")
    so_agent = T("Safety Officer / Site Agent", "安全主任 / 地盤代理人")

    if bmu:
        _permit(T("SWP Form 1 / Form 2 / Form 3", "吊船表格 Form 1 / Form 2 / Form 3"), cat_statutory,
                T("Cap. 59AC Suspended Working Platforms Regulation; CoP for Safe Use and Operation of SWP",
                  "Cap. 59AC 吊船規例；勞工處吊船安全使用及操作工作守則"),
                T("Competent person / competent examiner", "合資格人士 / 合資格檢驗員"),
                T("Form 1 weekly; Form 2/3 after thorough examination and load test",
                  "Form 1 每週；Form 2/3 於徹底檢驗及負載測試後"))
        _permit(T("Load test certificate (150% / 125% SWL)", "負載測試證明（150% / 125% SWL）"), cat_statutory,
                T("Cap. 59AC / CoP; witnessed by RPE", "Cap. 59AC / 工作守則；由 RPE 見證"),
                T("Registered Professional Engineer (RPE)", "註冊專業工程師（RPE）"),
                T("Issued after each load test", "每次負載測試後簽發"))
    if scaffold:
        _permit(T("Form 5 scaffold inspection report", "表格五（Form 5）棚架檢查報告"), cat_statutory,
                T("Cap. 59I Construction Sites (Safety) Regulations", "Cap. 59I 建築地盤（安全）規例"),
                T("Competent person", "合資格人士"),
                T("Every 14 days and after adverse weather", "每 14 天及惡劣天氣後"))
    if lifting:
        _permit(T("LALG test / examination certificates", "起重機械及起重裝置測試及檢驗證書（LALG）"), cat_statutory,
                T("Cap. 59J Lifting Appliances and Lifting Gear Regulations", "Cap. 59J 起重機械及起重裝置規例"),
                T("Competent examiner", "合資格檢驗員"),
                T("Per statutory cycle", "按法定週期"))
        _permit(T("Lifting operation permit / lifting plan", "吊運作業許可證 / 吊運計劃"), cat_inhouse, sms, so_agent,
                T("Before each lifting operation; close out on completion", "每次吊運前簽發；完工後關閉"))
    if confined:
        _permit(T("Confined space certificate and risk assessment", "密閉空間工作證明書及風險評估"), cat_statutory,
                T("Cap. 59AE Confined Spaces Regulation", "Cap. 59AE 密閉空間規例"),
                T("Competent person", "合資格人士"),
                T("Before entry; per certificate validity", "進入前簽發；按證書有效期"))
    if hot_work:
        _permit(T("Hot work permit (only if welding / flame cutting is involved)",
                  "熱工序許可證（僅適用於燒焊 / 火焰切割工序）"), cat_inhouse, sms,
                T("Safety Officer", "安全主任"),
                T("Same-day validity; close after post-work fire check", "當日有效；完工防火檢查後關閉"))
    if electrical:
        _permit(T("Electrical connection / lock-out tag-out (LOTO) record", "電力接駁 / 上鎖掛牌（LOTO）記錄"), cat_inhouse,
                T("Electricity (Wiring) Regulations where applicable; site electrical safety rules (RCD / ELCB, REW inspection)",
                  "如適用之電力（線路）規例；工地電力安全規定（RCD / ELCB、註冊電業工程人員檢查）"),
                T("Registered electrical worker (REW)", "註冊電業工程人員（REW）"),
                T("At each connection / isolation", "每次接駁 / 隔離時"))
    if temp_works or concreting:
        _permit(T("Temporary works / falsework check and T4 inspection certificate", "臨時工程 / 假支架檢查及 T4 檢查證明"), cat_inhouse,
                T("Temporary works design and site supervision requirements", "臨時工程設計及工地監督要求"),
                T("Temporary Works Coordinator (TWC) / Site Resident Professional (SRP)", "臨時工程統籌員（TWC）/ 駐地盤專業人員（SRP）"),
                T("Before loading / before concrete casting", "受力前 / 澆築混凝土前簽發"))
    if at_height:
        _permit(T("Working at height permit", "高空工作許可證"), cat_inhouse, sms,
                T("Safety Officer / Site Supervisor", "安全主任 / 工地監督"),
                T("Per work cycle", "按工作週期"))
    _permit(T("Permit-to-work (general)", "工作許可證（總）"), cat_inhouse, sms, so_agent,
            T("Issued before work starts", "開工前簽發"))

    scenarios: list[str] = []
    if at_height:
        scenarios.append(T("Fall from height / fall-arrest suspension trauma", "高處墮下 / 安全帶懸吊創傷"))
    if bmu:
        scenarios.append(T("Cradle power failure, jamming or trapped persons", "吊籠停電、卡阻或人員被困"))
    if scaffold:
        scenarios.append(T("Scaffold collapse / falling bamboo members", "棚架倒塌 / 竹枝墮下"))
    if lifting:
        scenarios.append(T("Falling load / lifting appliance failure", "吊物墮下 / 吊重設備失效"))
    if cutting:
        scenarios.append(T("Structural element falling or shifting during cutting / lifting", "切割或吊運期間混凝土件墮下或移位"))
    if confined:
        scenarios.append(T("Oxygen deficiency / toxic gas in confined space", "密閉空間缺氧 / 中毒"))
    if electrical:
        scenarios.append(T("Electric shock", "觸電"))
    scenarios.append(T("Injured worker requiring hospital transfer", "工人受傷需送院"))
    scenarios.append(T("Adverse weather (typhoon signal T8 / red or black rainstorm warning)", "惡劣天氣（八號風球 / 紅色或黑色暴雨警告）"))

    rescue_bits: list[str] = []
    if at_height:
        rescue_bits.append(T(
            "Fall rescue: rescue kit and descent device available on site; designated trained rescue personnel; "
            "release suspension promptly to prevent suspension trauma",
            "高處墮下救援：工地備有救援套件及下降器材；指定已受訓救援人員；及時解除懸吊以防懸吊創傷"))
    if bmu:
        rescue_bits.append(T(
            "Trapped cradle: apply the emergency manual descent procedure; if ineffective, escalate to building "
            "management, the specialist contractor and the Fire Services Department",
            "吊籠被困：啟動緊急手動下降程序；如無效，通知管理處、專業承辦商及消防處"))
    if confined:
        rescue_bits.append(T(
            "Confined space: standby person with rescue tripod and breathing apparatus; entry for rescue without "
            "protection is prohibited",
            "密閉空間：候命人員配備救援三腳架及呼吸器；嚴禁未經保護進入救援"))
    rescue_bits.append(T(
        "Calling emergency services alone shall not be relied upon as the sole rescue arrangement; a site-specific "
        "rescue plan, rescue equipment and trained rescue personnel shall be in place before work commences",
        "不得只依賴召喚 999 作為唯一救援安排；開工前必須制定現場專用救援計劃，並備有救援器材及已受訓救援人員"))

    emergency = {
        "foreseeable_scenarios": scenarios,
        "rescue_plan": T("; ", "；").join(rescue_bits),
        "first_aid": T(
            "First aiders and first-aid box provided per Cap. 59 first aid requirements; location briefed before work. "
            "[To be completed by site team: first aider names and first-aid box location]",
            "按 Cap. 59 急救規定配備急救員及急救箱；開工前簡介位置。[由工地團隊填寫：急救員姓名及急救箱位置]"),
        "emergency_contacts": T(
            "[To be completed by site team: emergency contact names, phone numbers / radio channel, first aider, "
            "rescue team leader and nearest A&E hospital]",
            "[由工地團隊填寫：緊急聯絡人姓名、電話 / 對講機頻道、急救員、救援隊負責人及最近急症室]"),
        "assembly_point": T(
            "Designated site assembly point with headcount procedure. [To be completed by site team: assembly point location]",
            "地盤指定集合點及點名核實程序。[由工地團隊填寫：集合點位置]"),
        "adverse_weather_arrangements": T(
            "On typhoon signal T8, thunderstorm or rainstorm warning: stop work, secure plant and materials, withdraw "
            "workers from height and outdoor positions; stop-work and resumption criteria (including any wind speed "
            "limit) shall follow the manufacturer's manual, the approved Method Statement and site safety rules, "
            "whichever is stricter",
            "八號風球、雷暴或暴雨警告時：停工、固定機械及物料、撤離高處及戶外崗位；停工及復工準則（包括風速限制）"
            "以製造商手冊、已批准施工方法書及工地安全規定中較嚴者為準"),
    }

    training: list[dict[str, str]] = [{
        "role": T("All workers", "所有工人"),
        "required_training_certificate": T("Green Card (mandatory basic safety training) plus pre-work briefing / toolbox talk",
                                           "平安咭（強制基本安全訓練）及開工前簡介 / 工具箱會"),
        "legal_basis": T("Cap. 59 F&IU (Safety Training) Regulation", "Cap. 59 工廠及工業經營（安全訓練）規例"),
        "expiry_renewal": T("Green Card renewal every 3 years", "平安咭每 3 年續期"),
        "record_location": T("Site safety file", "地盤安全檔案"),
    }]

    def _training(role_en: str, role_zh: str, cert_en: str, cert_zh: str, basis_en: str, basis_zh: str) -> None:
        training.append({
            "role": T(role_en, role_zh),
            "required_training_certificate": T(cert_en, cert_zh),
            "legal_basis": T(basis_en, basis_zh),
            "expiry_renewal": T("Per certificate", "按證書列明"),
            "record_location": T("Site safety file", "地盤安全檔案"),
        })

    if bmu:
        _training("SWP / BMU operator", "吊船操作員",
                  "SWP operation training certificate", "吊船操作訓練證書",
                  "Cap. 59AC / SWP CoP", "Cap. 59AC / 吊船工作守則")
    if scaffold and bamboo:
        _training("Bamboo scaffolder", "竹棚架搭棚工人",
                  "Bamboo scaffolder training certificate", "竹棚架工藝訓練證書",
                  "Cap. 59I; CoP for Bamboo Scaffolding Safety", "Cap. 59I；竹棚架安全工作守則")
    elif scaffold:
        _training("Scaffold / working platform erector", "棚架 / 工作平台搭建工人",
                  "Metal scaffold / working platform competency", "金屬棚架 / 工作平台搭建資格",
                  "Cap. 59I Construction Sites (Safety) Regulations", "Cap. 59I 建築地盤（安全）規例")
    if lifting:
        _training("Lifting supervisor", "吊運督導",
                  "Lifting supervisor training", "吊運督導訓練",
                  "Cap. 59J LALG Regulations", "Cap. 59J 起重機械及起重裝置規例")
        _training("Rigger / slinger / signaller", "索具工 / 掛鉤工 / 信號員",
                  "Rigger and signaller training record", "索具及信號員訓練紀錄",
                  "Cap. 59J LALG Regulations", "Cap. 59J 起重機械及起重裝置規例")
        _training("Competent person - lifting gear pre-use inspection", "合資格人士（吊具使用前檢查）",
                  "Competent person appointment and training", "合資格人士委任及訓練",
                  "Cap. 59J LALG Regulations", "Cap. 59J 起重機械及起重裝置規例")
    if transport:
        _training("Forklift operator", "叉車操作員",
                  "Forklift operator certificate", "叉車操作員證書",
                  "F&IU (Loadshifting Machinery) Regulation", "工廠及工業經營（移土機械）規例")
        _training("Electric pallet jack authorised operator", "電動唧車獲授權操作員",
                  "In-house authorisation and operation briefing", "公司內部授權及操作簡介",
                  "Company SMS", "公司安全管理系統")
    if electrical:
        _training("Registered electrical worker (REW)", "註冊電業工程人員（REW）",
                  "Electrical worker registration", "電業工程人員註冊證明",
                  "Electricity (Registration) Regulations", "電力（註冊）規例")
    if temp_works or concreting:
        _training("Temporary Works Coordinator (TWC) / falsework competent person", "臨時工程統籌員（TWC）/ 假支架合資格人士",
                  "Temporary works / falsework inspection competency", "臨時工程 / 假支架檢查資格",
                  "Temporary works procedures; T4 inspection requirement", "臨時工程程序；T4 檢查要求")
    if cutting:
        _training("Rebar scanner / utility locator operator", "鋼筋探測 / 地下設施探測操作員",
                  "Scanner operation training", "探測儀器操作訓練",
                  "Site requirements before drilling / cutting", "鑽孔 / 切割前工地要求")
    if at_height:
        _training("Competent person - working platform / access equipment", "合資格人士（工作台 / 通道設備）",
                  "Working platform inspection competency", "工作台檢查資格",
                  "Cap. 59I Construction Sites (Safety) Regulations", "Cap. 59I 建築地盤（安全）規例")
    if confined:
        _training("Certified worker / standby person (confined space)", "核准工人 / 候命人員（密閉空間）",
                  "Confined space certified worker", "密閉空間核准工人證書",
                  "Cap. 59AE", "Cap. 59AE 密閉空間規例")
    _training("First aider / rescue team member", "急救員 / 救援隊成員",
              "First aid certificate; rescue drill record", "急救證書；救援演習紀錄",
              "Cap. 59 first aid requirements", "Cap. 59 急救規定")

    inspection: list[dict[str, str]] = [{
        "item": T("Pre-use check of plant, tools and access equipment", "機械、工具及通道設備開工前檢查"),
        "frequency": T("Daily before work", "每天開工前"),
        "by_whom": T("Site supervisor / operator", "工地監督 / 操作員"),
        "record_form": T("Daily checklist", "每日檢查表"),
    }, {
        "item": T("Safety Officer / supervisor safety walk", "安全主任 / 監督安全巡查"),
        "frequency": T("Weekly minimum; daily during high-risk stages", "每週最少一次；高風險工序期間每天"),
        "by_whom": T("Safety Officer / Safety Supervisor", "安全主任 / 安全督導員"),
        "record_form": T("Inspection report", "巡查報告"),
    }, {
        "item": T("Toolbox talk / Method Statement briefing", "工具箱會 / 施工方法書簡介"),
        "frequency": T("Before start and weekly", "開工前及每週"),
        "by_whom": T("Site supervisor", "工地監督"),
        "record_form": T("Attendance record", "出席紀錄"),
    }, {
        "item": T("Risk assessment review", "風險評估檢討"),
        "frequency": T("On change of method / conditions, after incident, or at least every 12 months",
                       "工法 / 環境改變、事故後，或最遲每 12 個月"),
        "by_whom": T("Safety Officer", "安全主任"),
        "record_form": T("RA revision record", "風險評估修訂紀錄"),
    }]
    if scaffold:
        inspection.insert(0, {
            "item": T("Scaffold inspection (Form 5)", "棚架檢查（表格五）"),
            "frequency": T("Every 14 days and after adverse weather", "每 14 天及惡劣天氣後"),
            "by_whom": T("Competent person", "合資格人士"),
            "record_form": "Form 5",
        })
    if bmu:
        inspection.insert(0, {
            "item": T("SWP weekly inspection (Form 1) and daily pre-use checks", "吊船每週檢查（Form 1）及每天使用前檢查"),
            "frequency": T("Weekly and daily before use", "每週及每天使用前"),
            "by_whom": T("Competent person", "合資格人士"),
            "record_form": T("SWP Form 1 / daily checklist", "SWP Form 1 / 每日檢查表"),
        })
    if lifting:
        inspection.append({
            "item": T("Lifting gear and anchor point inspection", "吊具及錨固點檢查"),
            "frequency": T("Before each use", "每次使用前"),
            "by_whom": T("Competent person", "合資格人士"),
            "record_form": T("Lifting gear register", "吊具登記冊"),
        })
    if temp_works or concreting:
        inspection.append({
            "item": T("Back-propping / falsework / formwork and rebar inspection before casting (T4)",
                      "回頂 / 假支架 / 模板及鋼筋澆築前檢查（T4）"),
            "frequency": T("Before loading and before each concrete pour", "受力前及每次澆築混凝土前"),
            "by_whom": T("TWC / SRP / engineer", "TWC / SRP / 工程師"),
            "record_form": T("T4 inspection certificate", "T4 檢查證明"),
        })
    if cutting:
        inspection.append({
            "item": T("Openings formed after demolition: covers, guardrails and toe boards in place",
                      "拆卸後形成之孔洞：即時加蓋或設置完整護欄及踢腳板"),
            "frequency": T("Immediately after forming and daily thereafter", "形成後即時及其後每天"),
            "by_whom": T("Site supervisor", "工地監督"),
            "record_form": T("Daily checklist / inspection report", "每日檢查表 / 巡查報告"),
        })

    return {
        "permits_checklist": permits,
        "emergency_arrangements": emergency,
        "training_records": training,
        "inspection_schedule": inspection,
    }
