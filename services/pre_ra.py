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

    Used when the AI omits these RADraft fields (its sections call timed out
    or the local template is in use) so the Word report never jumps from the
    PPE section straight to the pre-work checklist with sections missing.
    Content is bilingual-tagged so it reads acceptably in any report language;
    it is a review baseline, not a substitute for the AI/site-specific text.
    """
    flags = sheet.get("flags", {}) or {}
    corpus = " ".join([
        str(data.get("activity", "")),
        str(data.get("equipment", "")),
        " ".join(str(s) for s in (data.get("confirmed_steps") or [])),
    ]).lower()
    bmu = any(t in corpus for t in ["bmu", "吊船", "gondola", "suspended working platform", "吊籠"])
    scaffold = flags.get("scaffolding") == "Yes" or any(t in corpus for t in ["棚", "scaffold"])
    lifting = flags.get("lifting") == "Yes" or any(t in corpus for t in ["吊運", "lifting", "crane", "吊機", "hoist"])
    at_height = bmu or scaffold or flags.get("work_at_height") == "Yes" or any(t in corpus for t in ["高處", "height", "外牆", "天台", "roof"])
    electrical = flags.get("electrical") == "Yes" or any(t in corpus for t in ["380v", "電源", "electri", "power supply"])
    confined = flags.get("confined_space") == "Yes"
    hot_work = flags.get("hot_work") == "Yes"

    permits: list[dict[str, str]] = []

    def _permit(name: str, category: str, basis: str, issued_by: str, validity: str) -> None:
        if not any(p["permit_or_form"] == name for p in permits):
            permits.append({
                "permit_or_form": name,
                "category": category,
                "legal_basis_or_sms_ref": basis,
                "issued_by": issued_by,
                "validity": validity,
                "status": "To be confirmed 待確認",
            })

    if bmu:
        _permit("SWP Form 1 / Form 2 / Form 3 吊船表格", "Statutory 法定",
                "Cap. 59AC 吊船規例 / CoP for Safe Use and Operation of SWP",
                "合資格人士 / 合資格檢驗員 Competent person / examiner",
                "Form 1 每週 weekly; Form 2/3 於徹底檢驗及負載測試後 after thorough examination & load test")
        _permit("負載測試證明 Load test certificate (150% / 125% SWL)", "Statutory 法定",
                "Cap. 59AC / CoP; 由 RPE 見證 witnessed by RPE",
                "註冊專業工程師 RPE", "每次負載測試後簽發 issued after each load test")
    if scaffold:
        _permit("表格五 Form 5 棚架檢查報告", "Statutory 法定",
                "Cap. 59I 建築地盤（安全）規例 Construction Sites (Safety) Regulations",
                "合資格人士 Competent person",
                "每 14 天及惡劣天氣後 every 14 days and after adverse weather")
    if lifting:
        _permit("LALG 測試及檢驗證書 (Form 3/4/5/7)", "Statutory 法定",
                "Cap. 59J 起重機械及起重裝置規例 LALG Regulations",
                "合資格檢驗員 Competent examiner", "按法定週期 per statutory cycle")
        _permit("吊運作業許可證 / 吊運計劃 Lifting permit / lifting plan", "In-house 內部",
                "公司安全管理系統 Company SMS", "安全主任 / 地盤代理人 Safety Officer / Site Agent",
                "每次吊運前 before each lifting operation; 完工後關閉 close out on completion")
    if confined:
        _permit("密閉空間工作證明書及風險評估 Confined space certificate & RA", "Statutory 法定",
                "Cap. 59AE 密閉空間規例", "合資格人士 Competent person", "進入前簽發 before entry; 按證書有效期 per certificate")
    if hot_work:
        _permit("熱工序許可證 Hot work permit", "In-house 內部", "公司安全管理系統 Company SMS",
                "安全主任 Safety Officer", "當日有效 same-day validity; 完工火警檢查後關閉 close after fire check")
    if electrical:
        _permit("電力接駁 / 上鎖掛牌記錄 Electrical connection & LOTO record", "In-house 內部",
                "電力（線路）規例 Electricity (Wiring) Regulations; 公司 SMS",
                "註冊電業工程人員 Registered electrical worker", "每次接駁 / 隔離時 at each connection / isolation")
    if at_height:
        _permit("高空工作許可證 Working at height permit", "In-house 內部", "公司安全管理系統 Company SMS",
                "安全主任 / 工地監督 Safety Officer / Site Supervisor", "按工作週期 per work cycle")
    _permit("工作許可證 Permit-to-work（總）", "In-house 內部", "公司安全管理系統 Company SMS",
            "安全主任 / 地盤代理人 Safety Officer / Site Agent", "開工前簽發 before work starts")

    scenarios: list[str] = []
    if at_height:
        scenarios.append("高處墮下 / 安全帶懸吊創傷 Fall from height / suspension trauma")
    if bmu:
        scenarios.append("吊籠停電、卡阻或人員被困 Cradle power failure, jamming or trapped persons")
    if scaffold:
        scenarios.append("棚架倒塌 / 竹枝墮下 Scaffold collapse / falling bamboo")
    if lifting:
        scenarios.append("吊物墮下 / 吊機翻側 Falling load / crane overturning")
    if confined:
        scenarios.append("密閉空間缺氧 / 中毒 Oxygen deficiency / toxic gas in confined space")
    if electrical:
        scenarios.append("觸電 Electric shock")
    scenarios.append("工人受傷需送院 Injured worker requiring hospital transfer")
    scenarios.append("惡劣天氣（八號風球 / 紅黑雨）Adverse weather (T8 / red & black rainstorm)")

    rescue_bits: list[str] = []
    if at_height:
        rescue_bits.append("高處墮下救援：備救援套件 / 下降器材，指定受訓救援人員，10 分鐘內解除懸吊（懸吊創傷風險）"
                           " Fall rescue: rescue kit / descent device on site, designated trained rescuers, release suspension within minutes")
    if bmu:
        rescue_bits.append("吊籠被困：啟動緊急手動下降程序；如失效通知管理處 / 專業承辦商 / 消防處"
                           " Trapped cradle: emergency manual descent; escalate to building management / specialist contractor / Fire Services")
    if confined:
        rescue_bits.append("密閉空間：候命人員配救援三腳架及呼吸器，嚴禁未經保護進入救人"
                           " Confined space: standby person with tripod & BA set; no unprotected rescue entry")
    rescue_bits.append("「只召喚 999」不視為救援計劃 Calling 999 alone is not a rescue plan")

    emergency = {
        "foreseeable_scenarios": scenarios,
        "rescue_plan": "；".join(rescue_bits),
        "first_aid": "按 Cap. 59 急救規定配備急救員及急救箱；急救箱位置須於開工前簡介 First aiders and first-aid box per Cap. 59; location briefed before work",
        "emergency_contacts": "工地管理 / 安全主任 / 最近急症室（只列職位，不列私人資料）Site management / Safety Officer / nearest A&E (roles only)",
        "assembly_point": "地盤指定集合點；點名核實人數 Designated assembly point with headcount",
        "adverse_weather_arrangements": "八號風球 / 雷暴 / 暴雨警告：停工、固定設備及物料、撤離高處及戶外崗位；停工及復工風速限制以製造商手冊、已批准施工方法書及工地規定中較嚴者為準"
                                        " T8 / thunderstorm / rainstorm: stop work, secure plant & materials, withdraw from height and outdoor positions; wind-speed limits per manufacturer's manual / approved MS / site rules, whichever is stricter",
    }

    training: list[dict[str, str]] = [{
        "role": "所有工人 All workers",
        "required_training_certificate": "平安咭 Green Card（強制基本安全訓練）+ 開工前簡介 / 工具箱會 toolbox talk",
        "legal_basis": "Cap. 59 F&IU (Safety Training) 規例",
        "expiry_renewal": "平安咭每 3 年續期 renew every 3 years",
        "record_location": "地盤安全檔案 Site safety file",
    }]
    if bmu:
        training.append({
            "role": "吊船操作員 SWP/BMU operator",
            "required_training_certificate": "吊船操作訓練證書 SWP operation training certificate",
            "legal_basis": "Cap. 59AC / 吊船 CoP",
            "expiry_renewal": "按證書列明 per certificate",
            "record_location": "地盤安全檔案 Site safety file",
        })
        training.append({
            "role": "註冊電業工程人員 Registered electrical worker",
            "required_training_certificate": "電業工程人員註冊證明（380V 接駁）Registration for electrical work",
            "legal_basis": "電力（註冊）規例 Electricity (Registration) Regulations",
            "expiry_renewal": "按註冊有效期 per registration validity",
            "record_location": "地盤安全檔案 Site safety file",
        })
    if scaffold:
        training.append({
            "role": "搭棚工人 Scaffolder",
            "required_training_certificate": "竹棚架工藝訓練證書 Bamboo scaffolder training certificate",
            "legal_basis": "Cap. 59I; 竹棚架安全工作守則 CoP for Bamboo Scaffolding Safety",
            "expiry_renewal": "按證書列明 per certificate",
            "record_location": "地盤安全檔案 Site safety file",
        })
    if lifting:
        training.append({
            "role": "吊機操作員 / 信號員 Crane operator / signaller",
            "required_training_certificate": "操作員證書及信號員訓練紀錄 Operator certificate & signaller training record",
            "legal_basis": "Cap. 59J LALG 規例",
            "expiry_renewal": "按證書列明 per certificate",
            "record_location": "地盤安全檔案 Site safety file",
        })
    if confined:
        training.append({
            "role": "核准工人 / 候命人員 Certified worker / standby person",
            "required_training_certificate": "密閉空間核准工人證書 Confined space certified worker",
            "legal_basis": "Cap. 59AE",
            "expiry_renewal": "按證書列明 per certificate",
            "record_location": "地盤安全檔案 Site safety file",
        })

    inspection: list[dict[str, str]] = [{
        "item": "機械、工具及通道設備開工前檢查 Pre-use check of plant, tools and access",
        "frequency": "每天開工前 daily before work",
        "by_whom": "工地監督 / 操作員 Site supervisor / operator",
        "record_form": "每日檢查表 Daily checklist",
    }, {
        "item": "安全主任 / 監督巡查 Safety walk",
        "frequency": "每週最少一次（高風險工序每天）weekly minimum; daily for high-risk stages",
        "by_whom": "安全主任 / 安全督導員 Safety Officer / Safety Supervisor",
        "record_form": "巡查報告 Inspection report",
    }, {
        "item": "工具箱會 / 方法書簡介 Toolbox talk / MS briefing",
        "frequency": "開工前及每週 before start and weekly",
        "by_whom": "工地監督 Site supervisor",
        "record_form": "出席紀錄 Attendance record",
    }, {
        "item": "風險評估檢討 RA review",
        "frequency": "工法 / 環境改變、事故後或最遲每 12 個月 on change of method/conditions, after incident, or at least every 12 months",
        "by_whom": "安全主任 Safety Officer",
        "record_form": "RA 修訂紀錄 RA revision record",
    }]
    if scaffold:
        inspection.insert(0, {
            "item": "棚架檢查（表格五）Scaffold inspection (Form 5)",
            "frequency": "每 14 天及惡劣天氣後 every 14 days and after adverse weather",
            "by_whom": "合資格人士 Competent person",
            "record_form": "表格五 Form 5",
        })
    if bmu:
        inspection.insert(0, {
            "item": "吊船每週檢查（Form 1）及使用前檢查 SWP weekly (Form 1) and pre-use checks",
            "frequency": "每週及每天使用前 weekly and daily before use",
            "by_whom": "合資格人士 Competent person",
            "record_form": "SWP Form 1 / 每日檢查表",
        })
    if lifting:
        inspection.append({
            "item": "吊具及索具檢查 Lifting gear inspection",
            "frequency": "每次使用前 before each use",
            "by_whom": "合資格人士 Competent person",
            "record_form": "吊具登記冊 Lifting gear register",
        })

    return {
        "permits_checklist": permits,
        "emergency_arrangements": emergency,
        "training_records": training,
        "inspection_schedule": inspection,
    }
