"""Activity-grouped RA fallback.

The old local fallback emitted one RA row per Method Statement sentence and
applied the same generic hazard template to every step, producing 40+ nearly
identical rows. A proper RA groups the work into a small number of key
activities, each with its own task-specific hazards, controls and rating.

This module classifies confirmed steps into construction activity buckets
(reinforcement, formwork, concreting, striking, openings, lifting, ...),
merges steps that fall in the same bucket into ONE row, and gives each row
activity-specific content. Steps matching no bucket collapse into a single
general-activities row instead of one row each.

Content is bilingual; the caller picks the language. Severity is
activity-aware: activities whose credible worst outcome stays fatal
(collapse, fall, electrocution, struck-by, opening fall) keep S5 in the
residual (surfaced as MR for ALARP acceptance) rather than being dropped to
S4 on every row.
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Each bucket: keyword matchers (substring, lowercased) + bilingual RA content.
# `severity` is the initial S; `keep_severity` True means controls cannot
# credibly remove the fatal outcome, so residual severity is not reduced.
ACTIVITY_BUCKETS: list[dict[str, Any]] = [
    {
        "key": "access_enclosure",
        "keywords": ["圍封", "硬圍", "警告", "出入", "通道", "整理", "清理施工", "清理範圍", "照明", "通風", "存放", "擺放", "enclos", "barrier", "access", "housekeep", "lighting", "ventilation"],
        "name_zh": "施工範圍圍封、通道及物料整理",
        "name_en": "Site enclosure, access and material housekeeping",
        "hazard_zh": "非工作人員進入危險區；通道阻塞、絆倒、滑倒；物料堆放倒塌；照明或通風不足",
        "hazard_en": "Unauthorised entry; blocked access, trips and slips; material stack collapse; poor lighting or ventilation",
        "cause_zh": "未設互扣式圍欄或警告標誌；通道被物料阻塞；地庫照明及通風不足",
        "cause_en": "No interlocking barrier or warning signage; access blocked by materials; poor basement lighting / ventilation",
        "consequence_zh": "撞傷、跌倒受傷；非工作人員誤入受傷",
        "consequence_en": "Impact or fall injury; injury to persons entering the work zone",
        "existing_zh": "設置互扣式紅色硬圍欄及警告標誌；指定專人控制出入口；保持通道暢通及整潔；提供足夠臨時照明及通風",
        "existing_en": "Interlocking red hard barrier and warning signage; controlled entry point; keep access clear and tidy; provide adequate temporary lighting and ventilation",
        "additional_zh": "開工前簡介出入管制及緊急通道；每日巡查圍封及通道；物料分類存放不阻塞通道及逃生路線",
        "additional_en": "Brief access control and emergency route before work; daily inspection of barriers and access; store materials clear of access and escape routes",
        "severity": 3,
        "keep_severity": False,
    },
    {
        "key": "survey_setout",
        "keywords": ["放線", "測量", "核對", "圖則", "標高", "中心線", "邊線", "參考點", "偏移", "定位", "探測", "地下設施", "現有設施", "現有結構", "set out", "setting out", "survey", "utility", "scan"],
        "name_zh": "放線、核對圖則及地下／現有設施檢查",
        "name_en": "Setting out, drawing check and underground / existing services check",
        "hazard_zh": "鑽穿或損壞地下電纜、水管、氣管；放樣錯誤導致結構位置偏差；接觸帶電或帶壓設施",
        "hazard_en": "Striking underground cables, water or gas services; setting-out error causing structural misplacement; contact with live or pressurised services",
        "cause_zh": "未探測地下設施或未核對記錄圖；未取得挖掘／鑽孔前許可；圖則與現場不符",
        "cause_en": "Underground services not scanned or record drawings not checked; no permit before drilling / breaking; drawings inconsistent with site",
        "consequence_zh": "觸電、氣體洩漏、水浸；嚴重可致命；返工及結構風險",
        "consequence_en": "Electric shock, gas release, flooding; potentially fatal; rework and structural risk",
        "existing_zh": "由測量員按批准圖紙放線並設參考點；鑽孔／開挖前探測及核對地下設施；取得相關工作許可",
        "existing_en": "Surveyor sets out to approved drawings with reference points; scan and verify underground services before drilling / excavation; obtain the relevant permit",
        "additional_zh": "使用探測儀由合資格人士操作並記錄；不確定時人手試挖；發現不符即停工並通知工程師",
        "additional_en": "Competent person to operate and record scanner results; hand-dig trial holes where uncertain; stop and inform the engineer on any discrepancy",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "rebar",
        "keywords": ["鋼筋", "扎鐵", "紮鐵", "綁紮", "綁扎", "植筋", "箍筋", "rebar", "reinforc", "starter bar", "dowel"],
        "name_zh": "鋼筋吊運、安裝及綁紮",
        "name_en": "Reinforcement delivery, fixing and tying",
        "hazard_zh": "鋼筋外露端刺傷、割傷；人手搬運扭傷；吊運鋼筋擺動撞擊；鋼筋堆放倒塌；綁紮夾手",
        "hazard_en": "Puncture / laceration on exposed bar ends; manual-handling strain; swinging rebar bundle on lifting; rebar stack collapse; pinch injury when tying",
        "cause_zh": "鋼筋外露端未加保護帽；單人搬運過重；吊索綁紮不當；堆放不穩",
        "cause_en": "Exposed bar ends without caps; single-person handling of heavy bars; poor sling rigging; unstable stacking",
        "consequence_zh": "刺傷、割傷、骨折、扭傷；吊物擺動撞傷",
        "consequence_en": "Puncture, laceration, fracture, strain; impact from swinging load",
        "existing_zh": "外露鋼筋端加保護帽或彎鈎；機械輔助或多人搬運；由合資格索具人員吊運，設引導繩；鋼筋分類穩固堆放",
        "existing_en": "Cap or hook exposed bar ends; mechanical aid or team lifting; competent rigger to lift with tag line; stack and secure rebar by type",
        "additional_zh": "人手搬運簡介及重量限制；吊運設禁區及訊號員；配戴防割手套及安全鞋；每日檢查吊索及吊具",
        "additional_en": "Manual-handling briefing and weight limits; exclusion zone and signaller for lifting; cut-resistant gloves and safety boots; daily check of slings and lifting gear",
        "severity": 4,
        "keep_severity": False,
    },
    {
        "key": "formwork",
        "keywords": ["模板", "拉桿", "繫桿", "假支架", "支撐", "回頂", "撐板", "formwork", "falsework", "shutter", "form tie", "prop"],
        "name_zh": "井壁／板模板、拉桿及假支架安裝",
        "name_en": "Wall / slab formwork, ties and falsework installation",
        "hazard_zh": "模板或假支架倒塌；支撐不足或拉桿失效；高處安裝墮下；夾手；物料墮下",
        "hazard_en": "Formwork or falsework collapse; inadequate propping or tie failure; fall from height during installation; pinch injury; falling materials",
        "cause_zh": "假支架未按設計搭設或未經檢查；拉桿數量不足或未上緊；受力前未取得 T4 檢查簽署",
        "cause_en": "Falsework not erected to design or uninspected; insufficient or loose ties; loaded before T4 inspection sign-off",
        "consequence_zh": "倒塌壓傷可致命；高處墮下致命；夾傷、跌物傷人",
        "consequence_en": "Crushing from collapse (potentially fatal); fatal fall from height; pinch and falling-object injury",
        "existing_zh": "假支架及模板按已批准臨時工程設計搭設；由 TWC／SRP 檢查並簽發 T4 後才可受力；提供工作平台、護欄及安全通道",
        "existing_en": "Falsework and formwork to approved temporary works design; loaded only after TWC / SRP T4 sign-off; provide working platform, guardrails and safe access",
        "additional_zh": "逐項核對支撐間距、拉桿及底座；安裝期間設禁區；高處工作佩戴安全帶連掛鈎；受力前最後檢查",
        "additional_en": "Verify prop spacing, ties and base plates; exclusion zone during installation; harness with lanyard for work at height; final check before loading",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "scaffold_platform",
        "keywords": ["棚架", "金屬棚", "工作台", "工作平台", "踏板", "上落", "爬梯", "梯具", "scaffold", "working platform", "access platform", "ladder"],
        "name_zh": "金屬棚架／工作平台搭設及使用",
        "name_en": "Metal scaffold / working platform erection and use",
        "hazard_zh": "工作平台倒塌或不穩；高處墮下；踏板或護欄缺失；物料由平台墮下",
        "hazard_en": "Platform collapse or instability; fall from height; missing boards or guardrails; materials falling from platform",
        "cause_zh": "金屬棚架搭設不當或未檢查；踏板未密鋪、缺踢腳板或護欄；超載",
        "cause_en": "Metal scaffold poorly erected or uninspected; boards not fully decked, missing toe boards or guardrails; overloading",
        "consequence_zh": "高處墮下致命；物料墮下傷及下方人員",
        "consequence_en": "Fatal fall from height; falling materials striking persons below",
        "existing_zh": "由合資格人士搭設及檢查金屬棚架／工作平台；提供護欄、踢腳板及密鋪踏板；設安全上落通道；標示安全負荷",
        "existing_en": "Competent person erects and inspects the metal scaffold / working platform; guardrails, toe boards and fully decked boards; safe access; posted safe working load",
        "additional_zh": "使用前及惡劣天氣後檢查並記錄；不得擅自改動；控制平台荷載；高處工作佩戴安全帶",
        "additional_en": "Inspect and record before use and after adverse weather; no unauthorised alteration; control platform loading; harness for work at height",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "concreting",
        "keywords": ["澆築", "澆灌", "澆注", "混凝土", "落石屎", "石屎", "泵", "泵喉", "布料", "布料臂", "震動", "振動", "搗實", "concret", "casting", "pour", "pump", "vibrat"],
        "name_zh": "底板及井壁混凝土澆灌、泵送及搗實",
        "name_en": "Base and wall concrete casting, pumping and compaction",
        "hazard_zh": "爆模及側壓過大；泵喉甩脫或堵塞噴射；布料臂移動撞擊；震動器觸電及手臂振動；水泥漿灼傷及濕滑",
        "hazard_en": "Formwork blow-out and excessive side pressure; pump hose whip or blockage burst; boom movement impact; vibrator electric shock and hand-arm vibration; cement burns and wet, slippery surfaces",
        "cause_zh": "澆灌速度過快、單邊落料；泵喉接頭鬆脫；震動器電纜破損或無漏電保護；長時間接觸水泥漿",
        "cause_en": "Excessive pour rate, uneven placement; loose pump-hose coupling; damaged vibrator cable or no RCD; prolonged contact with wet cement",
        "consequence_zh": "爆模倒塌壓傷可致命；泵喉甩脫或撞擊重傷；觸電；皮膚灼傷",
        "consequence_en": "Fatal crushing from blow-out; serious injury from hose whip or impact; electric shock; skin burns",
        "existing_zh": "控制澆灌速度及分層落料，監察側壓；泵喉接頭鎖固並設安全帶；震動器經漏電斷路器（RCD）供電；穿戴防水手套、水鞋及護目",
        "existing_en": "Control pour rate and layer placement, monitor side pressure; pump-hose couplings secured with whip-check; vibrator powered via RCD; waterproof gloves, boots and eye protection",
        "additional_zh": "澆灌前確認模板、支撐及 T4 檢查；泵送設專人監察及通訊；濕滑位即時清理；限制連續使用震動器時間",
        "additional_en": "Confirm formwork, propping and T4 before pouring; dedicated spotter and communication during pumping; clear wet areas immediately; limit continuous vibrator use",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "t4_holdpoint",
        "keywords": ["t4", "hold point", "控制點", "正式檢查", "最終檢查", "驗收", "檢查並簽發", "簽發證明", "re 同意", "取得批准", "批准後"],
        "name_zh": "臨時工程 / 模板 / 鋼筋檢查及 T4 控制點",
        "name_en": "Temporary works / formwork / rebar inspection and T4 hold point",
        "hazard_zh": "未經檢查或簽署已受力／澆築；檢查時行走鋼筋網刺傷、絆倒；高處檢查墮下",
        "hazard_en": "Loading / pouring before inspection sign-off; puncture and trips walking on rebar mesh during inspection; fall during inspection at height",
        "cause_zh": "T4／hold point 未簽署已開始下一工序；檢查通道不安全",
        "cause_en": "Next stage started before T4 / hold-point sign-off; unsafe inspection access",
        "consequence_zh": "結構或假支架失效可致命；刺傷、跌倒受傷",
        "consequence_en": "Fatal structural / falsework failure; puncture and fall injuries",
        "existing_zh": "設 T4／hold point 制度：模板、支架及鋼筋經 TWC／SRP／工程師檢查並簽署後方可澆築；提供安全檢查通道及行走板",
        "existing_en": "T4 / hold-point regime: formwork, falsework and rebar inspected and signed off by TWC / SRP / engineer before pouring; safe inspection access and walk boards",
        "additional_zh": "未簽署前掛「禁止澆築」標示；檢查紀錄存檔；檢查人員佩戴合適 PPE",
        "additional_en": "'No pouring' tag until signed off; keep inspection records; inspectors wear suitable PPE",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "curing",
        "keywords": ["養護", "保養", "試件", "灑水", "覆蓋養護", "curing", "test cube"],
        "name_zh": "混凝土養護及試件處理",
        "name_en": "Concrete curing and test-cube handling",
        "hazard_zh": "養護用水令地面濕滑；井口或開口未防護；試件搬運扭傷",
        "hazard_en": "Curing water making surfaces slippery; unprotected opening or shaft; strain handling test cubes",
        "cause_zh": "養護區積水未清；開口防護不足；試件人手搬運過重",
        "cause_en": "Standing curing water not cleared; inadequate opening protection; heavy manual handling of cubes",
        "consequence_zh": "滑倒受傷；墮入開口；扭傷",
        "consequence_en": "Slip injury; fall into opening; strain",
        "existing_zh": "控制養護用水並即時清理積水；保持開口防護到位；試件以合適容器搬運",
        "existing_en": "Control curing water and clear standing water; keep opening protection in place; handle cubes in suitable containers",
        "additional_zh": "設防滑及警告標誌；人手搬運簡介；每日檢查開口防護",
        "additional_en": "Anti-slip and warning signage; manual-handling briefing; daily check of opening protection",
        "severity": 3,
        "keep_severity": False,
    },
    {
        "key": "striking",
        "keywords": ["拆模", "拆除模板", "拆支撐", "拆除臨時", "拆除回頂", "拆除假支架", "striking", "strip formwork", "remove prop", "dismantl"],
        "name_zh": "拆模及臨時支撐拆除",
        "name_en": "Striking of formwork and temporary support removal",
        "hazard_zh": "混凝土未達強度提前拆除；支撐突然失效；模板及物料墮下；釘傷；拆除後孔洞外露",
        "hazard_en": "Premature striking before concrete gains strength; sudden support failure; falling formwork and materials; nail injury; openings exposed after removal",
        "cause_zh": "未確認混凝土齡期／強度及取得 RE 同意；未申請拆除許可；由下而上或整體拆除",
        "cause_en": "Strength / age not confirmed and RE consent not obtained; no removal permit; bottom-up or wholesale removal",
        "consequence_zh": "結構或支撐失效壓傷可致命；跌物傷人；孔洞墮下",
        "consequence_en": "Fatal crushing from structural / support failure; falling-object injury; fall through opening",
        "existing_zh": "確認混凝土達規定齡期／強度並取得 RE 同意；申請拆除許可及 Temporary Works Removal Certificate；按次序逐層拆除；設圍欄、警告及專人監察",
        "existing_en": "Confirm concrete age / strength and obtain RE consent; apply for removal permit and Temporary Works Removal Certificate; strike in sequence, stage by stage; barriers, warning signage and dedicated watchperson",
        "additional_zh": "禁止突然鬆脫、拋擲或整體拆除；拆下物料即時清釘及分類清走；拆除後即時保護新形成之孔洞",
        "additional_en": "No sudden release, throwing or wholesale removal; de-nail and clear stripped materials immediately; protect newly formed openings at once",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "openings",
        "keywords": ["孔洞", "開口", "井口", "臨邊", "樓面開口", "蓋板", "opening", "penetration", "edge protection", "cover"],
        "name_zh": "井口、樓面開口及臨邊防護",
        "name_en": "Manhole, floor opening and edge protection",
        "hazard_zh": "人員墮入井口或開口；物料墮落下層；臨時蓋板被移走或未固定",
        "hazard_en": "Person falling into the manhole or opening; materials falling to the level below; temporary cover removed or unsecured",
        "cause_zh": "開口未即時加蓋或設護欄；蓋板未固定及未標示；臨邊無防護",
        "cause_en": "Opening not covered or guarded immediately; cover unsecured and unmarked; no edge protection",
        "consequence_zh": "高處或井內墮下致命；墮物擊傷下方人員",
        "consequence_en": "Fatal fall from height or into the shaft; falling object striking persons below",
        "existing_zh": "開口形成後即時加蓋或設完整護欄及踢腳板；蓋板固定並標示「不得移走」；設警告標誌",
        "existing_en": "Cover or fully guard openings with toe boards immediately once formed; fix covers and mark 'DO NOT REMOVE'; provide warning signage",
        "additional_zh": "每日檢查蓋板及護欄是否到位；禁止未經批准移走蓋板；夜間及交更時重點檢查",
        "additional_en": "Daily check that covers and guardrails are in place; no unauthorised removal of covers; focused checks at night and shift change",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "lifting",
        "keywords": ["吊運", "吊機", "吊索", "吊具", "葫蘆", "手拉葫蘆", "吊眼", "起重", "吊裝", "lifting", "hoist", "crane", "chain block", "sling", "lifting eye"],
        "name_zh": "物料吊運及起重作業",
        "name_en": "Material lifting and hoisting operations",
        "hazard_zh": "吊物墮下；吊具、鋼鏈或吊眼失效；吊物擺動撞擊；超載；人員處於吊物下方",
        "hazard_en": "Falling load; lifting gear, chain or eye failure; swinging load impact; overloading; persons under the load",
        "cause_zh": "吊具未經法定檢驗或使用前檢查；超出安全負荷；無訊號員或引導繩；吊運路線未圍封",
        "cause_en": "Lifting gear without statutory examination or pre-use check; exceeding SWL; no signaller or tag line; lifting route not cordoned",
        "consequence_zh": "吊物墮下壓傷可致命；擺動撞擊重傷",
        "consequence_en": "Fatal crushing from falling load; serious impact from swinging load",
        "existing_zh": "起重機械及吊具具備適用 LALG 法定檢驗／測試證明、吊具登記冊及使用前檢查（實際表格由合資格檢驗員按設備類別確認）；控制安全負荷；由受訓操作員及訊號員作業",
        "existing_en": "Lifting appliances and gear with applicable LALG statutory certificates, lifting-gear register and pre-use checks (exact form confirmed by the competent examiner per equipment type); control SWL; trained operator and signaller",
        "additional_zh": "吊運範圍設禁區，禁止人員在吊物下方；設引導繩控制擺動；惡劣天氣停止吊運",
        "additional_en": "Exclusion zone under the lift, no persons beneath the load; tag line to control swing; suspend lifting in adverse weather",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "cutting_drilling",
        "keywords": ["切割", "鑽孔", "鑽切", "打鑿", "鋸", "打拆", "cutting", "drilling", "coring", "breaking", "sawing"],
        "name_zh": "混凝土切割、鑽孔及打鑿",
        "name_en": "Concrete cutting, drilling and breaking",
        "hazard_zh": "粉塵及噪音；飛濺碎片；鑽穿鋼筋或地下設施；手臂振動；濕滑及水泥漿",
        "hazard_en": "Dust and noise; flying debris; drilling into rebar or buried services; hand-arm vibration; slurry and slippery surfaces",
        "cause_zh": "未採用濕式或除塵；未探測鋼筋及設施；長時間使用手持機械",
        "cause_en": "No wet method or dust extraction; rebar and services not scanned; prolonged use of hand-held tools",
        "consequence_zh": "呼吸道及聽力損害；眼部及割傷；觸電；振動損傷",
        "consequence_en": "Respiratory and hearing damage; eye and cut injuries; electric shock; vibration injury",
        "existing_zh": "採用濕式鑽孔控制粉塵並處理積水及水泥漿；鑽孔前探測鋼筋及地下設施；佩戴呼吸、聽力及眼部防護",
        "existing_en": "Wet drilling to control dust and manage water / slurry; scan rebar and services before drilling; respiratory, hearing and eye protection",
        "additional_zh": "限制連續作業時間及輪替；電動工具經 RCD 供電並使用前檢查；保持地面整潔防滑",
        "additional_en": "Limit continuous work time and rotate; power tools via RCD with pre-use check; keep floor clean and non-slip",
        "severity": 4,
        "keep_severity": False,
    },
    {
        "key": "transport_waste",
        "keywords": ["搬運", "運走", "清走", "廢料", "叉車", "唧車", "托板", "手推車", "運送", "運輸", "分類", "transport", "forklift", "pallet", "waste", "debris", "trolley"],
        "name_zh": "物料搬運、運輸及廢料清理",
        "name_en": "Material handling, transport and waste clearance",
        "hazard_zh": "叉車或唧車撞人、翻側；人手搬運扭傷；物料堆疊倒塌；通道阻塞絆倒",
        "hazard_en": "Forklift / pallet truck striking persons or overturning; manual-handling strain; stacked material collapse; blocked access and trips",
        "cause_zh": "運輸路線未圍封或無訊號員；超載或視線受阻；樓面承載力未確認；堆疊過高",
        "cause_en": "Transport route not cordoned or no banksman; overloaded or obstructed view; floor loading not confirmed; over-stacking",
        "consequence_zh": "撞擊可致命；扭傷、壓傷、絆倒受傷",
        "consequence_en": "Fatal impact; strain, crush and trip injuries",
        "existing_zh": "運輸路線圍封並確認樓面承載；由受訓操作員及訊號員作業；控制堆疊高度；保持通道整潔",
        "existing_en": "Cordon the transport route and confirm floor loading; trained operator and banksman; control stack height; keep access clear",
        "additional_zh": "人手搬運簡介及機械輔助；避免單人搬運過重；分類存放廢料並定時清走",
        "additional_en": "Manual-handling briefing and mechanical aids; avoid single-person heavy lifts; segregate and regularly remove waste",
        "severity": 4,
        "keep_severity": False,
    },
    {
        "key": "electrical",
        "keywords": ["電源", "380v", "220v", "接駁電", "電動工具", "電纜", "電力", "供電", "隔離掣", "配電", "electric", "power supply", "cable", "isolat", "distribution board"],
        "name_zh": "臨時電力供應及電動工具使用",
        "name_en": "Temporary power supply and power tool use",
        "hazard_zh": "觸電；電纜破損或被輾壓；短路及電弧；濕水環境漏電",
        "hazard_en": "Electric shock; damaged or run-over cables; short circuit and arc; earth leakage in wet conditions",
        "cause_zh": "無漏電斷路器（RCD／ELCB）；電纜佈設不當或被輾壓；非註冊電業人員接駁",
        "cause_en": "No RCD / ELCB; poor cable routing or run-over cables; connection by an unregistered person",
        "consequence_zh": "觸電可致命；灼傷；火警",
        "consequence_en": "Fatal electric shock; burns; fire",
        "existing_zh": "所有臨時電力經漏電斷路器（RCD／ELCB）供電；由註冊電業工程人員（REW）接駁及檢查；電纜架空或加保護；使用前檢查工具及電纜",
        "existing_en": "All temporary power via RCD / ELCB; connection and inspection by a registered electrical worker (REW); cables routed overhead or protected; pre-use check of tools and cables",
        "additional_zh": "電力接駁及隔離設上鎖掛牌（LOTO）記錄；濕水環境使用低電壓工具；損壞工具即時停用",
        "additional_en": "Lock-out tag-out (LOTO) record for connection and isolation; low-voltage tools in wet areas; remove damaged tools from use immediately",
        "severity": 5,
        "keep_severity": True,
    },
    {
        "key": "confined_space",
        "keywords": ["井內", "進入井", "密閉空間", "缺氧", "沼氣", "confined space", "entry into"],
        "name_zh": "進入已構成密閉空間之井內作業（如適用）",
        "name_en": "Entry into the shaft where it has become a confined space (if applicable)",
        "hazard_zh": "缺氧或有毒／易燃氣體；高溫；救援困難",
        "hazard_en": "Oxygen deficiency or toxic / flammable gas; heat; difficult rescue",
        "cause_zh": "未進行氣體測試及持續監測；無通風；無密閉空間許可及候命人員",
        "cause_en": "No gas testing and continuous monitoring; no ventilation; no confined-space permit or standby person",
        "consequence_zh": "窒息、中毒可致命",
        "consequence_en": "Fatal asphyxiation or poisoning",
        "existing_zh": "如井深或封閉已構成密閉空間，須另行執行密閉空間風險評估及許可證；開工前及作業中氣體測試及監測；機械通風；候命人員及救援安排",
        "existing_en": "If shaft depth / enclosure forms a confined space, carry out a separate confined-space risk assessment and permit; gas testing and monitoring before and during work; mechanical ventilation; standby person and rescue arrangement",
        "additional_zh": "只准核准工人進入；備救援三腳架及呼吸器；嚴禁未經保護進入救援",
        "additional_en": "Only certified workers may enter; rescue tripod and breathing apparatus available; no unprotected rescue entry",
        "severity": 5,
        "keep_severity": True,
    },
]

# Catch-all for steps that match no bucket — a SINGLE grouped row, never one
# per step.
GENERAL_BUCKET = {
    "key": "general",
    "name_zh": "一般施工作業及工地管理",
    "name_en": "General construction activities and site management",
    "hazard_zh": "一般工地危害：滑倒絆倒、人手搬運、工具使用、物料墮下、通道及作業面不安全",
    "hazard_en": "General site hazards: slips and trips, manual handling, tool use, falling materials, unsafe access and work surface",
    "cause_zh": "工地管理、通道、物料固定或作業面狀況未按實際情況妥善控制",
    "cause_en": "Site management, access, material restraint or work-surface condition not adequately controlled for actual conditions",
    "consequence_zh": "人員受傷；財物損毀",
    "consequence_en": "Personal injury; property damage",
    "existing_zh": "按施工方法書作業；開工前簡介；提供合適工作平台、通道及 PPE；設禁區及監督；保持整潔",
    "existing_en": "Work to the method statement; pre-work briefing; suitable platform, access and PPE; exclusion zone and supervision; good housekeeping",
    "additional_zh": "合資格人士檢查；加強監督；分段施工；保持整潔；按實際工序補充專項控制",
    "additional_en": "Competent-person checks; increased supervision; phased work; housekeeping; add task-specific controls per actual activity",
    "severity": 4,
    "keep_severity": False,
    "legal_zh": "香港職業安全及健康相關法例及附屬規例；勞工處指引及工作守則",
    "legal_en": "Hong Kong OSH legislation and subsidiary regulations; Labour Department guidance and CoP",
}

_LEGAL_ZH = "香港《工廠及工業經營條例》(Cap. 59) 及相關附屬規例、建築地盤（安全）規例 (Cap. 59I)、相關工作守則"
_LEGAL_EN = "Hong Kong F&IU Ordinance (Cap. 59) and subsidiary regulations, Construction Sites (Safety) Regulations (Cap. 59I), relevant CoP"

_WEATHER_BUCKET = {
    "key": "weather_emergency",
    "name_zh": "惡劣天氣、照明、通風及緊急安排",
    "name_en": "Adverse weather, lighting, ventilation and emergency arrangements",
    "hazard_zh": "強風、暴雨、雷暴導致作業危險；地庫照明及通風不足；緊急情況救援延誤",
    "hazard_en": "Strong wind, rainstorm or thunderstorm making work unsafe; poor basement lighting and ventilation; delayed rescue in an emergency",
    "cause_zh": "未設停工準則；照明通風不足；無緊急及救援安排",
    "cause_en": "No stop-work criteria; inadequate lighting / ventilation; no emergency and rescue arrangement",
    "consequence_zh": "人員受傷；中暑；緊急情況延誤救援",
    "consequence_en": "Injury; heat stress; delayed rescue in emergencies",
    "existing_zh": "設停工及復工準則（以製造商手冊、已批准施工方法書及工地規定中較嚴者為準）；提供足夠照明及機械通風；制定緊急及救援安排並簡介",
    "existing_en": "Stop-work and resumption criteria (per manufacturer's manual, approved MS and site rules, whichever is stricter); adequate lighting and mechanical ventilation; documented and briefed emergency and rescue arrangement",
    "additional_zh": "八號風球／暴雨警告停工及固定物料；急救員及急救箱到位；[由工地團隊填寫：緊急聯絡人及救援隊資料]",
    "additional_en": "Stop work and secure materials on T8 / rainstorm warning; first aiders and first-aid box in place; [To be completed by site team: emergency contacts and rescue team details]",
    "severity": 4,
    "keep_severity": False,
}


ACTIVITY_BUCKET_KEYS = frozenset(
    [str(bucket["key"]) for bucket in ACTIVITY_BUCKETS]
    + [str(GENERAL_BUCKET["key"]), str(_WEATHER_BUCKET["key"])]
)


def are_activity_grouped_rows(rows: list[dict[str, Any]]) -> bool:
    """Return True when every row belongs to the local activity-grouped fallback."""
    if not rows:
        return False
    hazard_ids = [str(row.get("Hazard ID") or row.get("hazard_id") or "") for row in rows]
    return all(hazard_id in ACTIVITY_BUCKET_KEYS for hazard_id in hazard_ids)


def _norm(text: str) -> str:
    return str(text or "").lower()


# High-confidence overrides checked BEFORE keyword scoring so an ambiguous
# step is not miscategorised, e.g. "拆模及臨時支撐拆除" mentions 支撐 (formwork)
# but is a REMOVAL step (striking).
_PRIORITY_SIGNALS: list[tuple[tuple[str, ...], str]] = [
    (("拆模", "拆除模板", "拆支撐", "拆除臨時", "拆除支撐", "拆除假支架", "拆除回頂", "strip formwork", "remove prop", "striking of", "dismantl"), "striking"),
    (("進入井", "密閉空間", "缺氧", "confined space", "entry into the shaft"), "confined_space"),
    (("t4", "正式檢查", "最終檢查", "re檢查", "re 檢查", "inspection sign-off"), "t4_holdpoint"),
]

_BUCKET_BY_KEY = {b["key"]: b for b in ACTIVITY_BUCKETS}


# --- Step-type classifier ------------------------------------------------
# Not every extracted MS line is a hazardous work activity. Headings, record
# lines and pure approval statements must NOT spawn standalone RA rows; they
# feed controls / inspection points instead. (Genuine inspections such as
# pre-use tool checks or T4 hold points DO get their own activity bucket.)

_HEADING_MARKERS = ("〔", "【", "︰以下", "as follows")
_HEADING_SUFFIXES = ("準備", "工序", "階段", "安排", "如下", "注意事項")
_RECORD_MARKERS = ("記錄存檔", "拍照記錄", "存檔", "紀錄表", "record only", "for record")
_APPROVAL_ONLY_MARKERS = ("取得批准", "取得書面批准", "批准後方可", "同意後方可", "approval obtained", "subject to approval")
_T4_INSPECTION_MARKERS = ("t4", "正式檢查", "最終檢查", "re檢查", "re 檢查", "inspection sign-off")

# A Method Statement sentence can contain a main trade activity plus a distinct
# safety-critical interface (for example lifting rebar, using power tools, or
# protecting an opening after formwork removal). Keep the main classifier
# deterministic, but also retain these interfaces as their own grouped rows.
_SECONDARY_ACTIVITY_SIGNALS: dict[str, tuple[str, ...]] = {
    "openings": ("孔洞", "開口", "井口", "臨邊", "樓面開口", "floor opening", "manhole opening", "shaft opening", "edge protection"),
    "lifting": ("吊運", "吊機", "吊索", "吊具", "起重", "吊裝", "lifting", "hoist", "crane", "sling"),
    "transport_waste": ("搬運", "運走", "清走", "廢料", "叉車", "唧車", "運送", "運輸", "分類", "transport", "forklift", "pallet", "waste", "debris"),
    "electrical": ("電源", "電動工具", "電纜", "電力", "供電", "配電", "electric", "power supply", "cable", "distribution board"),
}

_ACTION_HINTS = (
    "拆", "裝", "搭", "吊", "運", "清", "鋪", "綁", "紮", "澆", "築", "挖", "焊", "切",
    "鑽", "設置", "設立", "施工", "放線", "測量", "接駁", "搬", "養護", "檢查", "測試",
    "install", "erect", "remove", "dismantl", "lift", "pour", "cast", "cut", "drill",
    "fix", "set out", "survey", "connect", "transport", "clean", "inspect", "test", "check",
)


def classify_step_type(step_text: str) -> str:
    """Coarse MS-line type: work_activity / heading / record_only /
    permit_or_approval. Only work_activity lines may create RA rows."""
    text = _norm(step_text)
    stripped = str(step_text or "").strip()
    if not stripped or len(stripped) < 6:
        return "record_only"
    if any(marker in stripped for marker in _HEADING_MARKERS):
        return "heading"
    if any(marker in text for marker in _RECORD_MARKERS):
        return "record_only"
    if any(marker in text for marker in _T4_INSPECTION_MARKERS):
        return "work_activity"
    if any(marker in text for marker in _APPROVAL_ONLY_MARKERS):
        return "permit_or_approval"
    # Short lines ending like a section title ("模板施工前準備") are headings
    # even when they mention an action word.
    if len(stripped) <= 12 and stripped.endswith(_HEADING_SUFFIXES):
        return "heading"
    has_action = any(hint in text for hint in _ACTION_HINTS)
    if not has_action:
        if len(stripped) <= 20 and stripped.endswith(_HEADING_SUFFIXES):
            return "heading"
        return "record_only"
    return "work_activity"


def classify_step(step_text: str) -> dict[str, Any] | None:
    """Return the best-matching activity bucket for a step, or None."""
    text = _norm(step_text)
    for signals, key in _PRIORITY_SIGNALS:
        if any(sig in text for sig in signals) and key in _BUCKET_BY_KEY:
            return _BUCKET_BY_KEY[key]
    best: tuple[int, dict[str, Any]] | None = None
    for bucket in ACTIVITY_BUCKETS:
        score = sum(1 for kw in bucket["keywords"] if kw in text)
        if score and (best is None or score > best[0]):
            best = (score, bucket)
    return best[1] if best else None


def classify_step_buckets(step_text: str) -> list[dict[str, Any]]:
    """Return the primary activity plus distinct safety-critical interfaces."""
    text = _norm(step_text)
    buckets: list[dict[str, Any]] = []
    primary = classify_step(step_text)
    if primary is not None:
        buckets.append(primary)
    seen = {str(bucket["key"]) for bucket in buckets}
    for key, signals in _SECONDARY_ACTIVITY_SIGNALS.items():
        if key not in seen and any(signal in text for signal in signals):
            buckets.append(_BUCKET_BY_KEY[key])
            seen.add(key)
    return buckets


def _residual(rating_fn: Callable[[dict, int, int], str], matrix: dict, severity: int, keep: bool) -> str:
    """Residual after controls: likelihood -> P1; severity kept for fatal
    activities (collapse / fall / electrocution / struck-by), else dropped one
    notch. Deterministic, so it does not depend on hazard-text token matching."""
    residual_sev = severity if keep else (severity - 1 if severity >= 4 else severity)
    return rating_fn(matrix, 1, residual_sev)


def build_activity_grouped_items(
    data: dict[str, Any],
    matrix: dict[str, Any],
    rating_fn: Callable[[dict, int, int], str],
    step_records_fn: Callable[[list[str]], list[dict[str, str]]],
    language: str,
    include_weather: bool = True,
    include_general: bool = True,
) -> list[dict[str, Any]]:
    """Classify confirmed steps into activity buckets and emit ONE row per
    activity that has steps (plus a single general row for unmatched steps and
    a weather / emergency row). Returns RAItem-shaped dicts."""
    chinese = language in {"Traditional Chinese", "Simplified Chinese"}

    def pick(bucket: dict[str, Any], field: str) -> str:
        return str(bucket.get(f"{field}_zh" if chinese else f"{field}_en", ""))

    records = step_records_fn(data.get("confirmed_steps", []))
    # Preserve first-appearance order of buckets. Lines that are headings,
    # record-only or approval statements never spawn RA rows.
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        if classify_step_type(record["step_text"]) != "work_activity":
            continue
        buckets = classify_step_buckets(record["step_text"])
        if not buckets:
            if not include_general:
                continue
            buckets = [GENERAL_BUCKET]
        for bucket in buckets:
            key = bucket["key"]
            if key not in grouped:
                grouped[key] = {"bucket": bucket, "records": []}
                order.append(key)
            grouped[key]["records"].append(record)

    legal = _LEGAL_ZH if chinese else _LEGAL_EN
    persons = "工人、監督、分判商及附近人員" if chinese else "Workers, supervisors, subcontractors and persons nearby"
    items: list[dict[str, Any]] = []

    for key in order:
        bucket = grouped[key]["bucket"]
        recs = grouped[key]["records"]
        sev = int(bucket["severity"])
        hazard_text = pick(bucket, "hazard")
        residual = _residual(rating_fn, matrix, sev, bool(bucket.get("keep_severity")))
        span_ids = [r["source_step_id"] for r in recs]
        joined = "；".join(r["step_text"] for r in recs) if chinese else "; ".join(r["step_text"] for r in recs)
        name = pick(bucket, "name")
        if len(recs) > 1:
            span = f"{span_ids[0]}-{span_ids[-1]}"
            work_step = name + (f"（涵蓋步驟 {span}）" if chinese else f" (covers steps {span})")
        else:
            work_step = name
        items.append({
            "source_step_id": span_ids[0],
            "source_step_text_original": joined,
            "source_step_text_translated": joined,
            "hazard_id": bucket["key"],
            "hazard_category": name,
            "work_step": work_step,
            "hazard": hazard_text,
            "cause_of_hazard": pick(bucket, "cause"),
            "possible_consequence": pick(bucket, "consequence"),
            "persons_at_risk": persons,
            "initial_risk_rating": rating_fn(matrix, 2, sev),
            "existing_control_measures": pick(bucket, "existing"),
            "additional_control_measures_required": pick(bucket, "additional"),
            "residual_risk_rating": residual,
            "legal_cop_reference": str(bucket.get("legal_zh" if chinese else "legal_en", "") or legal),
            "permit_certificate_competent_person_required": (
                "合資格人士檢查；相關工作許可證（按工序）" if chinese else "Competent-person inspection; relevant permit-to-work (per activity)"
            ),
            "inspection_monitoring_points": (
                "開工前檢查；作業中監督；完工檢查" if chinese else "Pre-work check; supervision during work; close-out check"
            ),
            "responsible_person": "工地監督 / 安全主任" if chinese else "Site Supervisor / Safety Officer",
            "remarks_items_to_be_confirmed": (
                "最低可接受剩餘風險：實施措施後降至 LR；如仍為 MR 須列明 ALARP 理據並由註冊安全主任接受"
                if chinese else
                "Minimum acceptable residual risk: reduce to LR after controls; any residual MR needs ALARP justification and RSO acceptance"
            ),
        })

    if not include_weather:
        return items

    # Append a site-wide weather / emergency row.
    wb = _WEATHER_BUCKET
    items.append({
        "source_step_id": "ENV",
        "source_step_text_original": pick(wb, "name"),
        "source_step_text_translated": pick(wb, "name"),
        "hazard_id": wb["key"],
        "hazard_category": pick(wb, "name"),
        "work_step": pick(wb, "name"),
        "hazard": pick(wb, "hazard"),
        "cause_of_hazard": pick(wb, "cause"),
        "possible_consequence": pick(wb, "consequence"),
        "persons_at_risk": persons,
        "initial_risk_rating": rating_fn(matrix, 2, int(wb["severity"])),
        "existing_control_measures": pick(wb, "existing"),
        "additional_control_measures_required": pick(wb, "additional"),
        "residual_risk_rating": _residual(rating_fn, matrix, int(wb["severity"]), False),
        "legal_cop_reference": legal,
        "permit_certificate_competent_person_required": "安全主任監督；緊急應變安排" if chinese else "Safety Officer supervision; emergency response arrangement",
        "inspection_monitoring_points": "每日天氣及工地情況檢查" if chinese else "Daily weather and site condition check",
        "responsible_person": "安全主任" if chinese else "Safety Officer",
        "remarks_items_to_be_confirmed": "",
    })
    return items


# Markers of the retired one-size-fits-all backfill row. Any row still carrying
# them (e.g. restored from an old session draft) is deleted before export —
# generic fallback rows are prohibited in the final table.
GENERIC_ROW_MARKERS = (
    "Confirmed work step requiring risk assessment",
    "Fall, falling object, unsafe access or unsafe working platform related to the confirmed work step",
    "與工序相關的高處墮下、物料墮下、通道或作業面不安全",
)


def _compact(value: Any) -> str:
    return "".join(str(value or "").split()).lower()


def count_generic_rows(rows: list[dict[str, str]]) -> int:
    """Return the number of retired generic fallback rows in an RA table."""
    return sum(
        1
        for row in rows
        if any(
            marker in " ".join(
                str(row.get(key, ""))
                for key in ("Work Step", "Hazard", "Existing Controls")
            )
            for marker in GENERIC_ROW_MARKERS
        )
    )


def remove_generic_and_duplicate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Duplicate killer run before export: drop retired generic rows and
    collapse near-identical repeats (same hazard + cause + existing controls
    may appear at most twice)."""
    cleaned: list[dict[str, str]] = []
    fingerprint_counts: dict[tuple[str, str, str], int] = {}
    for row in rows:
        blob = " ".join(str(row.get(key, "")) for key in ("Work Step", "Hazard", "Existing Controls"))
        if any(marker in blob for marker in GENERIC_ROW_MARKERS):
            continue
        fingerprint = (
            _compact(row.get("Hazard", ""))[:120],
            _compact(row.get("Cause of Hazard", ""))[:120],
            _compact(row.get("Existing Controls", ""))[:120],
        )
        fingerprint_counts[fingerprint] = fingerprint_counts.get(fingerprint, 0) + 1
        if fingerprint_counts[fingerprint] > 2:
            continue
        cleaned.append(row)
    # Never return an empty table: the caller's fallback path guarantees rows.
    return cleaned or rows
