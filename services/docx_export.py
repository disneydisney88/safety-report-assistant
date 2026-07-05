from __future__ import annotations

from io import BytesIO
import re
from typing import Any

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from services.ai_prompts import DISCLAIMER

LABELS = {
    "English": {
        "disclaimer": DISCLAIMER,
        "risk_index_guide": "Risk Index Guide:",
        "main_title": "RISK ASSESSMENT",
        "purpose": "1.0 Purpose and Scope",
        "sequence": "2.0 Method Statement / Work Sequence",
        "requirements": "3.0 Applicable Statutory / Site Requirements",
        "matrix": "4.0 Risk Matrix",
        "ra_table": "5.0 Hazard Identification & Risk Assessment Table",
        "ppe": "6.0 PPE Requirements",
        "checklist": "7.0 Mandatory Pre-start Checklist",
        "approval": "8.0 Approval / Acknowledgement",
        "item": "Item",
        "job_task": "Job Task",
        "hazard": "Hazard",
        "people": "People Affected",
        "cause": "Cause of Hazard",
        "harm": "Worst Harm Due to Hazard",
        "existing": "Existing Control Measures",
        "risk_level": "Risk Level (RL)",
        "further": "Further control measures",
        "training_ppe": "Required training & PPE",
        "action_by": "Action by",
        "residual": "Expected residue RL",
        "actual": "Remark / Actual residue RL",
        "role": "Role",
        "position": "Position",
        "name": "Name",
        "signature": "Signature",
        "date": "Date",
    },
    "Traditional Chinese": {
        "disclaimer": "AI 生成草稿，使用前須由安全主任 / 獲授權人士審閱及批准。",
        "risk_index_guide": "風險指數指引：",
        "main_title": "風險評估",
        "purpose": "1.0 目的及範圍",
        "sequence": "2.0 施工方法 / 工作程序",
        "requirements": "3.0 適用法例 / 工地要求",
        "matrix": "4.0 風險矩陣",
        "ra_table": "5.0 危害識別及風險評估表",
        "ppe": "6.0 個人防護裝備要求",
        "checklist": "7.0 開工前必要檢查清單",
        "approval": "8.0 批核 / 確認",
        "item": "項目",
        "job_task": "工作工序",
        "hazard": "危害",
        "people": "受影響人士",
        "cause": "危害成因",
        "harm": "最嚴重後果",
        "existing": "現有控制措施",
        "risk_level": "風險等級 (RL)",
        "further": "進一步控制措施",
        "training_ppe": "所需訓練及 PPE",
        "action_by": "負責人",
        "residual": "預期剩餘風險",
        "actual": "備註 / 實際剩餘風險",
        "role": "角色",
        "position": "職位",
        "name": "姓名",
        "signature": "簽署",
        "date": "日期",
    },
    "Simplified Chinese": {
        "disclaimer": "AI 生成草稿，使用前须由安全主任 / 获授权人士审阅及批准。",
        "risk_index_guide": "风险指数指引：",
        "main_title": "风险评估",
        "purpose": "1.0 目的及范围",
        "sequence": "2.0 施工方法 / 工作程序",
        "requirements": "3.0 适用法规 / 工地要求",
        "matrix": "4.0 风险矩阵",
        "ra_table": "5.0 危害识别及风险评估表",
        "ppe": "6.0 个人防护装备要求",
        "checklist": "7.0 开工前必要检查清单",
        "approval": "8.0 批核 / 确认",
        "item": "项目",
        "job_task": "工作工序",
        "hazard": "危害",
        "people": "受影响人士",
        "cause": "危害成因",
        "harm": "最严重后果",
        "existing": "现有控制措施",
        "risk_level": "风险等级 (RL)",
        "further": "进一步控制措施",
        "training_ppe": "所需培训及 PPE",
        "action_by": "负责人",
        "residual": "预期剩余风险",
        "actual": "备注 / 实际剩余风险",
        "role": "角色",
        "position": "职位",
        "name": "姓名",
        "signature": "签署",
        "date": "日期",
    },
}


STATIC_TEXT = {
    "English": {
        "purpose_body": "This risk assessment covers the work activity stated above and shall be read together with the approved Method Statement, drawings, permits and site instructions. All control measures shall be reviewed by the Safety Officer / authorised person before use.",
        "matrix_body": "Risk Rating = Severity (S) x Likelihood (L). Residual risk shall be maintained at ALARP level by implementing all stated control measures.",
        "requirements": [
            "Factories and Industrial Undertakings Ordinance and relevant subsidiary regulations, including safe place of work, safe access and suitable supervision.",
            "Relevant Labour Department guidance, Codes of Practice and client / project safety rules applicable to the selected jurisdiction.",
            "Permit-to-work, competent person inspection, access control, emergency and rescue arrangements shall be implemented where required.",
            "Names of individuals shall not be shown in this draft; only roles / positions are used for privacy and data protection.",
        ],
        "ppe": [
            "Safety helmet with chin strap",
            "Reflective vest / high-visibility clothing",
            "Safety footwear",
            "Protective gloves suitable for the task",
            "Eye protection where cutting, drilling, dust or particle hazard exists",
            "Full body harness with suitable anchorage / independent lifeline where required",
        ],
        "checklist": [
            "Approved Method Statement, drawings, permits and risk assessment available on site.",
            "Competent persons, supervisors and workers confirmed and briefed.",
            "Cordon-off, warning notices, access control and protection to affected persons established.",
            "Plant, tools, lifting / access equipment and PPE inspected before use.",
            "Emergency, first-aid, rescue and communication arrangements confirmed.",
            "Weather / site condition checked and suitable for the work.",
            "Residual risk and control measures reviewed by Safety Officer / authorised person.",
        ],
    },
    "Traditional Chinese": {
        "purpose_body": "本風險評估涵蓋上述工作活動，並須與已批准的施工方法書、圖則、工作許可證及工地指示一併使用。所有控制措施須由安全主任 / 獲授權人士審閱後方可使用。",
        "matrix_body": "風險評級 = 嚴重程度 (S) x 可能性 (L)。實施所有列明控制措施後，剩餘風險須維持在 ALARP 水平。",
        "requirements": [
            "《工廠及工業經營條例》及相關附屬規例，包括安全工作地點、安全通道及適當監督要求。",
            "適用於所選地區的勞工處指引、工作守則及客戶 / 工程安全規則。",
            "如適用，須執行工作許可證、合資格人士檢查、出入管制、緊急及救援安排。",
            "本草稿只顯示崗位 / 職責，不顯示個人姓名，以保障私隱及資料保護。",
        ],
        "ppe": [
            "安全帽連帽帶",
            "反光衣 / 高能見度衣物",
            "安全鞋",
            "適合工序的防護手套",
            "如涉及切割、鑽孔、粉塵或飛濺物危害，須佩戴護眼裝備",
            "如有需要，須使用全身式安全帶及合適錨固點 / 獨立救生繩",
        ],
        "checklist": [
            "工地已備有獲批准施工方法書、圖則、許可證及風險評估。",
            "已確認合資格人士、監督人員及工人，並完成安全簡介。",
            "已設置圍封、警告告示、出入管制及對受影響人士的保護措施。",
            "開工前已檢查機械、工具、吊運 / 通道設備及 PPE。",
            "已確認緊急、急救、救援及通訊安排。",
            "已檢查天氣 / 工地情況，並確認適合進行工作。",
            "安全主任 / 獲授權人士已檢討剩餘風險及控制措施。",
        ],
    },
    "Simplified Chinese": {
        "purpose_body": "本风险评估涵盖上述工作活动，并须与已批准的施工方法书、图则、工作许可证及工地指示一并使用。所有控制措施须由安全主任 / 获授权人士审阅后方可使用。",
        "matrix_body": "风险评级 = 严重程度 (S) x 可能性 (L)。实施所有列明控制措施后，剩余风险须维持在 ALARP 水平。",
        "requirements": [
            "《工厂及工业经营条例》及相关附属规例，包括安全工作地点、安全通道及适当监督要求。",
            "适用于所选地区的劳工处指引、工作守则及客户 / 工程安全规则。",
            "如适用，须执行工作许可证、合资格人士检查、出入管制、紧急及救援安排。",
            "本草稿只显示岗位 / 职责，不显示个人姓名，以保障隐私及资料保护。",
        ],
        "ppe": [
            "安全帽连帽带",
            "反光衣 / 高能见度衣物",
            "安全鞋",
            "适合工序的防护手套",
            "如涉及切割、钻孔、粉尘或飞溅物危害，须佩戴护眼装备",
            "如有需要，须使用全身式安全带及合适锚固点 / 独立救生绳",
        ],
        "checklist": [
            "工地已备有获批准施工方法书、图则、许可证及风险评估。",
            "已确认合资格人士、监督人员及工人，并完成安全简介。",
            "已设置围封、警告告示、出入管制及对受影响人士的保护措施。",
            "开工前已检查机械、工具、吊运 / 通道设备及 PPE。",
            "已确认紧急、急救、救援及通讯安排。",
            "已检查天气 / 工地情况，并确认适合进行工作。",
            "安全主任 / 获授权人士已检讨剩余风险及控制措施。",
        ],
    },
}


def _labels(language: str) -> dict[str, str]:
    if language == "Bilingual":
        zh = LABELS["Traditional Chinese"]
        en = LABELS["English"]
        return {key: f"{en[key]} / {zh[key]}" for key in en}
    return LABELS.get(language, LABELS["English"])


def _static(language: str) -> dict[str, Any]:
    if language == "Bilingual":
        en = STATIC_TEXT["English"]
        zh = STATIC_TEXT["Traditional Chinese"]
        return {
            "disclaimer": f"{en['disclaimer']}\n{zh['disclaimer']}",
            "risk_index_guide": f"{en['risk_index_guide']} / {zh['risk_index_guide']}",
            "purpose_body": f"{en['purpose_body']}\n{zh['purpose_body']}",
            "matrix_body": f"{en['matrix_body']}\n{zh['matrix_body']}",
            "requirements": [f"{a}\n{b}" for a, b in zip(en["requirements"], zh["requirements"])],
            "ppe": [f"{a} / {b}" for a, b in zip(en["ppe"], zh["ppe"])],
            "checklist": [f"{a}\n{b}" for a, b in zip(en["checklist"], zh["checklist"])],
        }
    return STATIC_TEXT.get(language, STATIC_TEXT["English"])


SAFE_LABELS = {
    "English": LABELS["English"],
    "Traditional Chinese": {
        "main_title": "\u98a8\u96aa\u8a55\u4f30",
        "purpose": "1.0 \u76ee\u7684\u53ca\u7bc4\u570d",
        "sequence": "2.0 \u65bd\u5de5\u65b9\u6cd5 / \u5de5\u4f5c\u7a0b\u5e8f",
        "requirements": "3.0 \u9069\u7528\u6cd5\u4f8b / \u5de5\u5730\u8981\u6c42",
        "matrix": "4.0 \u98a8\u96aa\u77e9\u9663",
        "ra_table": "5.0 \u5371\u5bb3\u8b58\u5225\u53ca\u98a8\u96aa\u8a55\u4f30\u8868",
        "ppe": "6.0 \u500b\u4eba\u9632\u8b77\u88dd\u5099\u8981\u6c42",
        "checklist": "7.0 \u958b\u5de5\u524d\u5fc5\u8981\u6aa2\u67e5\u6e05\u55ae",
        "approval": "8.0 \u6279\u6838 / \u78ba\u8a8d",
        "item": "\u9805\u76ee",
        "job_task": "\u5de5\u4f5c\u5de5\u5e8f",
        "hazard": "\u5371\u5bb3",
        "people": "\u53d7\u5f71\u97ff\u4eba\u58eb",
        "cause": "\u5371\u5bb3\u6210\u56e0",
        "harm": "\u6700\u56b4\u91cd\u5f8c\u679c",
        "existing": "\u73fe\u6709\u63a7\u5236\u63aa\u65bd",
        "risk_level": "\u98a8\u96aa\u7b49\u7d1a (RL)",
        "further": "\u9032\u4e00\u6b65\u63a7\u5236\u63aa\u65bd",
        "training_ppe": "\u6240\u9700\u8a13\u7df4\u53ca PPE",
        "action_by": "\u8ca0\u8cac\u4eba",
        "residual": "\u9810\u671f\u5269\u9918\u98a8\u96aa",
        "actual": "\u5099\u8a3b / \u5be6\u969b\u5269\u9918\u98a8\u96aa",
        "role": "\u89d2\u8272",
        "position": "\u8077\u4f4d",
        "name": "\u59d3\u540d",
        "signature": "\u7c3d\u7f72",
        "date": "\u65e5\u671f",
    },
    "Simplified Chinese": {
        "main_title": "\u98ce\u9669\u8bc4\u4f30",
        "purpose": "1.0 \u76ee\u7684\u53ca\u8303\u56f4",
        "sequence": "2.0 \u65bd\u5de5\u65b9\u6cd5 / \u5de5\u4f5c\u7a0b\u5e8f",
        "requirements": "3.0 \u9002\u7528\u6cd5\u89c4 / \u5de5\u5730\u8981\u6c42",
        "matrix": "4.0 \u98ce\u9669\u77e9\u9635",
        "ra_table": "5.0 \u5371\u5bb3\u8bc6\u522b\u53ca\u98ce\u9669\u8bc4\u4f30\u8868",
        "ppe": "6.0 \u4e2a\u4eba\u9632\u62a4\u88c5\u5907\u8981\u6c42",
        "checklist": "7.0 \u5f00\u5de5\u524d\u5fc5\u8981\u68c0\u67e5\u6e05\u5355",
        "approval": "8.0 \u6279\u6838 / \u786e\u8ba4",
        "item": "\u9879\u76ee",
        "job_task": "\u5de5\u4f5c\u5de5\u5e8f",
        "hazard": "\u5371\u5bb3",
        "people": "\u53d7\u5f71\u54cd\u4eba\u58eb",
        "cause": "\u5371\u5bb3\u6210\u56e0",
        "harm": "\u6700\u4e25\u91cd\u540e\u679c",
        "existing": "\u73b0\u6709\u63a7\u5236\u63aa\u65bd",
        "risk_level": "\u98ce\u9669\u7b49\u7ea7 (RL)",
        "further": "\u8fdb\u4e00\u6b65\u63a7\u5236\u63aa\u65bd",
        "training_ppe": "\u6240\u9700\u57f9\u8bad\u53ca PPE",
        "action_by": "\u8d1f\u8d23\u4eba",
        "residual": "\u9884\u671f\u5269\u4f59\u98ce\u9669",
        "actual": "\u5907\u6ce8 / \u5b9e\u9645\u5269\u4f59\u98ce\u9669",
        "role": "\u89d2\u8272",
        "position": "\u804c\u4f4d",
        "name": "\u59d3\u540d",
        "signature": "\u7b7e\u7f72",
        "date": "\u65e5\u671f",
    },
}


SAFE_STATIC_TEXT = {
    "English": {
        **STATIC_TEXT["English"],
        "disclaimer": DISCLAIMER,
        "risk_index_guide": "Risk Index Guide:",
        "minimum_acceptable_risk": "Minimum acceptable residual risk: all residual risk shall be reduced to ALARP and normally MR or below unless specifically accepted by authorised management.",
        "pi_note": "P: probability or likelihood rating; IC: Impact Consequence rating.",
        "remarks_note": "Remark / Actual residual RL shall record the final residual risk score and corresponding risk code after additional controls are implemented.",
        "risk_guide_rows": [
            ("E63323", "Extreme / High", "Unacceptable risk; introduce alternative method or additional controls before work proceeds."),
            ("F4A63A", "Major", "Only acceptable with identified controls, additional supervision and monitoring."),
            ("FFFF4A", "Moderate", "Acceptable with identified control measures and supervising / monitoring."),
            ("A6CE39", "Minor", "Acceptable with identified control measures in place."),
        ],
    },
    "Traditional Chinese": {
        "disclaimer": "AI \u751f\u6210\u8349\u7a3f\uff0c\u4f7f\u7528\u524d\u9808\u7531\u5b89\u5168\u4e3b\u4efb / \u7372\u6388\u6b0a\u4eba\u58eb\u5be9\u95b1\u53ca\u6279\u51c6\u3002",
        "risk_index_guide": "\u98a8\u96aa\u6307\u6578\u6307\u5f15\uff1a",
        "minimum_acceptable_risk": "\u6700\u4f4e\u53ef\u63a5\u53d7\u5269\u9918\u98a8\u96aa\uff1a\u6240\u6709\u5269\u9918\u98a8\u96aa\u9808\u964d\u81f3 ALARP \u6c34\u5e73\uff0c\u4e00\u822c\u61c9\u70ba MR \u6216\u4ee5\u4e0b\uff1b\u5982\u9ad8\u65bc MR\uff0c\u9808\u7531\u7372\u6388\u6b0a\u7ba1\u7406\u5c64\u7279\u5225\u63a5\u53d7\u3002",
        "pi_note": "P\uff1a\u53ef\u80fd\u6027 / \u767c\u751f\u6a5f\u6703\u8a55\u7d1a\uff1bIC\uff1a\u5f71\u97ff\u5f8c\u679c\u8a55\u7d1a\u3002",
        "remarks_note": "\u5099\u8a3b / \u5be6\u969b\u5269\u9918\u98a8\u96aa\u9808\u8a18\u9304\u5be6\u65bd\u9032\u4e00\u6b65\u63a7\u5236\u63aa\u65bd\u5f8c\u7684\u6700\u7d42\u5269\u9918\u98a8\u96aa\u5206\u6578\u53ca\u5c0d\u61c9\u98a8\u96aa\u4ee3\u865f\u3002",
        "risk_guide_rows": [
            ("E63323", "\u6975\u9ad8 / \u9ad8\u98a8\u96aa", "\u4e0d\u53ef\u63a5\u53d7\uff1b\u958b\u5de5\u524d\u5fc5\u9808\u6539\u7528\u5176\u4ed6\u65b9\u6cd5\u6216\u589e\u52a0\u63a7\u5236\u63aa\u65bd\u3002"),
            ("F4A63A", "\u91cd\u5927\u98a8\u96aa", "\u53ea\u6709\u5728\u5df2\u78ba\u8a8d\u63a7\u5236\u3001\u52a0\u5f37\u76e3\u7763\u53ca\u76e3\u5bdf\u4e0b\u65b9\u53ef\u63a5\u53d7\u3002"),
            ("FFFF4A", "\u4e2d\u7b49\u98a8\u96aa", "\u5728\u5df2\u8b58\u5225\u63a7\u5236\u63aa\u65bd\u53ca\u9069\u7576\u76e3\u7763 / \u76e3\u5bdf\u4e0b\u53ef\u63a5\u53d7\u3002"),
            ("A6CE39", "\u8f03\u4f4e\u98a8\u96aa", "\u5728\u5df2\u8b58\u5225\u63a7\u5236\u63aa\u65bd\u5230\u4f4d\u5f8c\u53ef\u63a5\u53d7\u3002"),
        ],
        "purpose_body": "\u672c\u98a8\u96aa\u8a55\u4f30\u6db5\u84cb\u4e0a\u8ff0\u5de5\u4f5c\u6d3b\u52d5\uff0c\u4e26\u9808\u8207\u5df2\u6279\u51c6\u7684\u65bd\u5de5\u65b9\u6cd5\u66f8\u3001\u5716\u5247\u3001\u5de5\u4f5c\u8a31\u53ef\u8b49\u53ca\u5de5\u5730\u6307\u793a\u4e00\u4f75\u4f7f\u7528\u3002\u6240\u6709\u63a7\u5236\u63aa\u65bd\u9808\u7531\u5b89\u5168\u4e3b\u4efb / \u7372\u6388\u6b0a\u4eba\u58eb\u5be9\u95b1\u5f8c\u65b9\u53ef\u4f7f\u7528\u3002",
        "matrix_body": "\u98a8\u96aa\u8a55\u7d1a = \u56b4\u91cd\u7a0b\u5ea6 (S) x \u53ef\u80fd\u6027 (L)\u3002\u5be6\u65bd\u6240\u6709\u5217\u660e\u63a7\u5236\u63aa\u65bd\u5f8c\uff0c\u5269\u9918\u98a8\u96aa\u9808\u7dad\u6301\u5728 ALARP \u6c34\u5e73\u3002",
        "requirements": ["\u9075\u5b88\u9999\u6e2f\u8077\u696d\u5b89\u5168\u53ca\u5065\u5eb7\u76f8\u95dc\u6cd5\u4f8b\u53ca\u9644\u5c6c\u898f\u4f8b\u3002", "\u9075\u5b88\u52de\u5de5\u8655\u6307\u5f15\u3001\u5de5\u4f5c\u5b88\u5247\u53ca\u5ba2\u6236 / \u5de5\u7a0b\u5b89\u5168\u8981\u6c42\u3002", "\u5982\u9069\u7528\uff0c\u9808\u57f7\u884c\u5de5\u4f5c\u8a31\u53ef\u8b49\u3001\u5408\u8cc7\u683c\u4eba\u58eb\u6aa2\u67e5\u3001\u51fa\u5165\u7ba1\u5236\u53ca\u6551\u63f4\u5b89\u6392\u3002"],
        "ppe": ["\u5b89\u5168\u5e3d\u9023\u5e3d\u5e36", "\u53cd\u5149\u8863 / \u9ad8\u80fd\u898b\u5ea6\u8863\u7269", "\u5b89\u5168\u978b", "\u9069\u5408\u5de5\u5e8f\u7684\u9632\u8b77\u624b\u5957", "\u8b77\u773c\u88dd\u5099", "\u5168\u8eab\u5f0f\u5b89\u5168\u5e36\u53ca\u5408\u9069\u9328\u56fa\u9ede / \u7368\u7acb\u6551\u751f\u7e69"],
        "checklist": ["\u5df2\u5099\u6709\u6279\u51c6\u65bd\u5de5\u65b9\u6cd5\u66f8\u3001\u5716\u5247\u3001\u8a31\u53ef\u8b49\u53ca\u98a8\u96aa\u8a55\u4f30\u3002", "\u5df2\u78ba\u8a8d\u5408\u8cc7\u683c\u4eba\u58eb\u3001\u76e3\u7763\u4eba\u54e1\u53ca\u5de5\u4eba\uff0c\u4e26\u5b8c\u6210\u7c21\u4ecb\u3002", "\u5df2\u8a2d\u7f6e\u570d\u5c01\u3001\u8b66\u544a\u544a\u793a\u53ca\u51fa\u5165\u7ba1\u5236\u3002", "\u958b\u5de5\u524d\u5df2\u6aa2\u67e5\u6a5f\u68b0\u3001\u5de5\u5177\u3001\u901a\u9053\u8a2d\u5099\u53ca PPE\u3002", "\u5df2\u78ba\u8a8d\u7dca\u6025\u3001\u6025\u6551\u3001\u6551\u63f4\u53ca\u901a\u8a0a\u5b89\u6392\u3002", "\u5df2\u6aa2\u67e5\u5929\u6c23 / \u5de5\u5730\u60c5\u6cc1\u3002", "\u5b89\u5168\u4e3b\u4efb / \u7372\u6388\u6b0a\u4eba\u58eb\u5df2\u6aa2\u8a0e\u5269\u9918\u98a8\u96aa\u53ca\u63a7\u5236\u63aa\u65bd\u3002"],
    },
}

SAFE_STATIC_TEXT["Simplified Chinese"] = SAFE_STATIC_TEXT["Traditional Chinese"]


def _labels(language: str) -> dict[str, str]:
    if language == "Bilingual":
        zh = SAFE_LABELS["Traditional Chinese"]
        en = SAFE_LABELS["English"]
        return {key: f"{en.get(key, key)} / {zh[key]}" for key in zh}
    return SAFE_LABELS.get(language, SAFE_LABELS["English"])


def _static(language: str) -> dict[str, Any]:
    if language == "Bilingual":
        en = SAFE_STATIC_TEXT["English"]
        zh = SAFE_STATIC_TEXT["Traditional Chinese"]
        return {
            "disclaimer": f"{en['disclaimer']}\n{zh['disclaimer']}",
            "risk_index_guide": f"{en['risk_index_guide']} / {zh['risk_index_guide']}",
            "purpose_body": f"{en['purpose_body']}\n{zh['purpose_body']}",
            "matrix_body": f"{en['matrix_body']}\n{zh['matrix_body']}",
            "requirements": [f"{a}\n{b}" for a, b in zip(en["requirements"], zh["requirements"])],
            "ppe": [f"{a} / {b}" for a, b in zip(en["ppe"], zh["ppe"])],
            "checklist": [f"{a}\n{b}" for a, b in zip(en["checklist"], zh["checklist"])],
        }
    return SAFE_STATIC_TEXT.get(language, SAFE_STATIC_TEXT["English"])


def build_docx(title: str, sections: dict[str, Any]) -> BytesIO:
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph(DISCLAIMER)
    for heading, value in sections.items():
        doc.add_heading(str(heading), level=2)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            keys = list(value[0].keys())
            table = doc.add_table(rows=1, cols=len(keys))
            table.style = "Table Grid"
            for idx, key in enumerate(keys):
                table.rows[0].cells[idx].text = str(key)
            for row in value:
                cells = table.add_row().cells
                for idx, key in enumerate(keys):
                    cells[idx].text = str(row.get(key, ""))
        elif isinstance(value, list):
            for item in value:
                doc.add_paragraph(str(item), style="List Bullet")
        else:
            doc.add_paragraph(str(value))
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_borders(cell, color: str = "000000", size: str = "6") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def _set_cell_margins(cell, margin: int = 35) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.find(qn("w:tcMar"))
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side in ("top", "left", "bottom", "right"):
        tag = qn(f"w:{side}")
        element = tc_mar.find(tag)
        if element is None:
            element = OxmlElement(f"w:{side}")
            tc_mar.append(element)
        element.set(qn("w:w"), str(margin))
        element.set(qn("w:type"), "dxa")


def _set_cell_text(cell, text: Any, bold: bool = False, size: float = 10.0, align: int | None = None) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    if align is not None:
        paragraph.alignment = align
    run = paragraph.add_run(str(text or "-"))
    run.bold = bold
    run.font.name = "Calibri"
    run.font.size = Pt(size)


def _zh_term_cleanup(text: Any) -> str:
    value = str(text or "")
    replacements = {
        "Inspect access equipment and work platform": "\u6aa2\u67e5\u901a\u9053\u8a2d\u5099\u53ca\u5de5\u4f5c\u5e73\u53f0",
        "Set up exclusion zone below work area": "\u5728\u5de5\u4f5c\u5340\u4e0b\u65b9\u8a2d\u7f6e\u7981\u5340",
        "Access the work location": "\u524d\u5f80\u5de5\u4f5c\u4f4d\u7f6e",
        "Carry out work at height": "\u9032\u884c\u9ad8\u8655\u5de5\u4f5c",
        "Remove tools/materials and close out inspection": "\u79fb\u8d70\u5de5\u5177 / \u7269\u6599\u53ca\u5b8c\u6210\u6536\u5de5\u6aa2\u67e5",
        "Fall from height": "\u9ad8\u8655\u589c\u4e0b",
        "Fall of Person from height": "\u4eba\u54e1\u9ad8\u8655\u589c\u4e0b",
        "Falling objects": "\u9ad8\u7a7a\u589c\u7269",
        "Platform collapse": "\u5e73\u53f0\u5012\u584c",
        "Unsafe access": "\u901a\u9053\u4e0d\u5b89\u5168",
        "Weather effect": "\u5929\u6c23\u5f71\u97ff",
        "Adverse weather": "\u60e1\u52a3\u5929\u6c23",
        "Typhoon or Heavy Rainstorm": "\u98b1\u98a8\u6216\u66b4\u96e8",
        "Serious injury": "\u56b4\u91cd\u53d7\u50b7",
        "Fatality": "\u6b7b\u4ea1",
        "Fatality / Serious Injury": "\u6b7b\u4ea1 / \u56b4\u91cd\u53d7\u50b7",
        "Injury to persons below": "\u4e0b\u65b9\u4eba\u58eb\u53d7\u50b7",
        "Property damage": "\u8ca1\u7269\u640d\u58de",
        "Workers, supervisors, subcontractors and persons nearby": "\u5de5\u4eba\u3001\u76e3\u7763\u4eba\u54e1\u3001\u5206\u5224\u5546\u53ca\u9644\u8fd1\u4eba\u58eb",
        "Workers, supervisors, subcontractors and persons nearby": "\u5de5\u4eba\u3001\u76e3\u7763\u4eba\u54e1\u3001\u5206\u5224\u5546\u53ca\u9644\u8fd1\u4eba\u58eb",
        "Workers, supervisors, subcontractors and persons nearby": "\u5de5\u4eba\u3001\u76e3\u7763\u4eba\u54e1\u3001\u5206\u5224\u5546\u53ca\u9644\u8fd1\u4eba\u58eb",
        "Workers, supervisors, subcontractors and persons nearby": "\u5de5\u4eba\u3001\u76e3\u7763\u4eba\u54e1\u3001\u5206\u5224\u5546\u53ca\u9644\u8fd1\u4eba\u58eb",
        "Workers and persons nearby": "\u5de5\u4eba\u53ca\u9644\u8fd1\u4eba\u58eb",
        "Workers and public": "\u5de5\u4eba\u53ca\u516c\u773e",
        "People at area": "\u5de5\u4f5c\u5340\u5167\u4eba\u58eb",
        "People at the area": "\u5de5\u4f5c\u5340\u5167\u4eba\u58eb",
        "Members of public": "\u516c\u773e",
        "persons nearby": "\u9644\u8fd1\u4eba\u58eb",
        "subcontractors": "\u5206\u5224\u5546",
        "supervisors": "\u76e3\u7763\u4eba\u54e1",
        "and persons nearby": "\u53ca\u9644\u8fd1\u4eba\u58eb",
        "Unsafe condition, unsafe act or failure mode associated with the confirmed work step": "\u8207\u5df2\u78ba\u8a8d\u5de5\u5e8f\u76f8\u95dc\u7684\u4e0d\u5b89\u5168\u72c0\u6cc1\u3001\u4e0d\u5b89\u5168\u884c\u70ba\u6216\u5931\u6548\u6a21\u5f0f",
        "Unsafe condition, unsafe act or failure mode": "\u4e0d\u5b89\u5168\u72c0\u6cc1\u3001\u4e0d\u5b89\u5168\u884c\u70ba\u6216\u5931\u6548\u6a21\u5f0f",
        "Lack of safety awareness": "\u5b89\u5168\u610f\u8b58\u4e0d\u8db3",
        "Working area not fenced off": "\u5de5\u4f5c\u5340\u672a\u9069\u7576\u570d\u5c01",
        "Workers not trained for the task": "\u5de5\u4eba\u672a\u63a5\u53d7\u76f8\u95dc\u5de5\u5e8f\u8a13\u7df4",
        "No proper access": "\u672a\u63d0\u4f9b\u9069\u7576\u901a\u9053",
        "No fixed anchoring point provided": "\u672a\u63d0\u4f9b\u56fa\u5b9a\u9328\u56fa\u9ede",
        "No safety harness worn": "\u672a\u4f69\u6234\u5b89\u5168\u5e36",
        "Confirm with approved Method Statement and site-specific conditions": "\u6839\u64da\u5df2\u6279\u51c6\u65bd\u5de5\u65b9\u6cd5\u66f8\u53ca\u5de5\u5730\u5be6\u969b\u60c5\u6cc1\u78ba\u8a8d",
        "Confirm method statement, competent person requirement, permit-to-work, inspection points and emergency arrangement before work starts": "\u958b\u5de5\u524d\u78ba\u8a8d\u65bd\u5de5\u65b9\u6cd5\u66f8\u3001\u5408\u8cc7\u683c\u4eba\u58eb\u8981\u6c42\u3001\u5de5\u4f5c\u8a31\u53ef\u8b49\u3001\u6aa2\u67e5\u9ede\u53ca\u7dca\u6025\u5b89\u6392",
        "Provide safe working platform": "\u63d0\u4f9b\u5b89\u5168\u5de5\u4f5c\u5e73\u53f0",
        "Guardrails and toe boards where applicable": "\u6309\u9700\u8981\u8a2d\u7f6e\u8b77\u6b04\u53ca\u8e22\u8173\u677f",
        "Fall arrest system and independent lifeline where required": "\u6309\u9700\u8981\u4f7f\u7528\u9632\u589c\u7cfb\u7d71\u53ca\u7368\u7acb\u6551\u751f\u7e69",
        "Inspect access equipment before use": "\u4f7f\u7528\u524d\u6aa2\u67e5\u901a\u9053\u53ca\u5de5\u4f5c\u8a2d\u5099",
        "Set exclusion zone below work area": "\u5728\u5de5\u4f5c\u5340\u4e0b\u65b9\u8a2d\u7f6e\u7981\u5340",
        "Secure tools and materials against falling": "\u56fa\u5b9a\u5de5\u5177\u53ca\u7269\u6599\u9632\u6b62\u589c\u4e0b",
        "Ensure all tools and materials are secured against falling": "\u78ba\u4fdd\u6240\u6709\u5de5\u5177\u53ca\u7269\u6599\u5df2\u56fa\u5b9a\u9632\u6b62\u589c\u4e0b",
        "Fence off the working area": "\u570d\u5c01\u5de5\u4f5c\u5340",
        "Provide appropriate working platform": "\u63d0\u4f9b\u9069\u7576\u5de5\u4f5c\u5e73\u53f0",
        "Workers shall wear full body harness": "\u5de5\u4eba\u9808\u4f69\u6234\u5168\u8eab\u5f0f\u5b89\u5168\u5e36",
        "Competent person has to inspect working platform": "\u5408\u8cc7\u683c\u4eba\u58eb\u9808\u6aa2\u67e5\u5de5\u4f5c\u5e73\u53f0",
        "Confirm rescue arrangement for fall arrest": "\u78ba\u8a8d\u9632\u589c\u6551\u63f4\u5b89\u6392",
        "Provide competent supervision": "\u63d0\u4f9b\u5408\u8cc7\u683c\u76e3\u7763",
        "Working at height permit where required by site system": "\u6309\u5de5\u5730\u5236\u5ea6\u9700\u8981\u8fa6\u7406\u9ad8\u8655\u5de5\u4f5c\u8a31\u53ef",
        "Competent person for scaffold / platform inspection where applicable": "\u6309\u9700\u8981\u7531\u5408\u8cc7\u683c\u4eba\u58eb\u6aa2\u67e5\u68da\u67b6 / \u5de5\u4f5c\u5e73\u53f0",
        "Induction Training / Toolbox Talk / FCB / Zero Harm Lesson": "\u5165\u8077\u8a13\u7df4 / \u5de5\u5177\u7bb1\u6703\u8b70 / \u73fe\u5834\u63a7\u5236\u7c21\u4ecb / \u96f6\u50b7\u5bb3\u8ab2\u7a0b",
        "Field control briefing": "\u73fe\u5834\u63a7\u5236\u7c21\u4ecb",
        "Safety gloves": "\u5b89\u5168\u624b\u5957",
        "Safety helmet": "\u5b89\u5168\u5e3d",
        "safety helmet": "\u5b89\u5168\u5e3d",
        "Pre-work briefing": "\u958b\u5de5\u524d\u7c21\u4ecb",
        "Supervisor control": "\u76e3\u7763\u4eba\u54e1\u63a7\u5236",
        "Suitable PPE": "\u5408\u9069\u500b\u4eba\u9632\u8b77\u88dd\u5099",
        "Access control": "\u51fa\u5165\u7ba1\u5236",
        "Housekeeping": "\u5de5\u5730\u6574\u6f54",
        "To be confirmed": "\u5f85\u78ba\u8a8d",
        "To be verified by Safety Officer": "\u7531\u5b89\u5168\u4e3b\u4efb\u6838\u5be6",
        "Site Supervisor / Safety Officer": "\u5de5\u5730\u76e3\u7763 / \u5b89\u5168\u4e3b\u4efb",
        "Induction / task briefing / suitable PPE": "\u5165\u8077\u8a13\u7df4 / \u5de5\u5e8f\u7c21\u4ecb / \u5408\u9069\u500b\u4eba\u9632\u8b77\u88dd\u5099",
        "Workers / others nearby": "\u5de5\u4eba / \u9644\u8fd1\u5176\u4ed6\u4eba\u58eb",
        "Workers": "\u5de5\u4eba",
        "Supervisors": "\u76e3\u7763\u4eba\u54e1",
        "Subcontractors": "\u5206\u5224\u5546",
        "Site Supervisor / Safety Officer": "\u5de5\u5730\u76e3\u7763 / \u5b89\u5168\u4e3b\u4efb",
        "To be verified by Safety Officer": "\u7531\u5b89\u5168\u4e3b\u4efb\u6838\u5be6",
        "Hong Kong OSH legislation": "\u9999\u6e2f\u8077\u5b89\u5065\u6cd5\u4f8b",
        "Labour Department guidance": "\u52de\u5de5\u8655\u6307\u5f15",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value


def _en_term_cleanup(text: Any) -> str:
    value = str(text or "")
    if re.search(r"[\u4e00-\u9fff]", value):
        scaffold_tokens = ["拆棚", "棚架", "尼龍網", "鋅鐵", "帆布", "橫杆", "竹杆", "竹枝"]
        if any(token in value for token in scaffold_tokens):
            return "Dismantle scaffold bay: remove nylon net, metal sheets or canvas first; then remove ledgers and supporting bamboo members."
        if "惡劣天氣" in value or "暴雨" in value or "颱風" in value:
            return "Adverse weather control for outdoor works."
        if "公眾" in value:
            return "Public interface control for persons nearby."
    return value


def _display_text(text: Any, language: str) -> str:
    if language in {"Traditional Chinese", "Simplified Chinese"}:
        return _zh_term_cleanup(text)
    if language == "English":
        return _en_term_cleanup(text)
    return str(text or "-")


def _is_weather_row(row: dict[str, Any]) -> bool:
    text = " ".join(str(row.get(key, "")) for key in ("Work Step", "Hazard", "Remarks")).lower()
    return any(token in text for token in ["weather", "typhoon", "rain", "惡劣天氣", "天氣", "颱風", "暴雨", "強風"])


def _clean_for_main_risk_row(text: Any, language: str, is_weather: bool = False) -> str:
    value = _display_text(text, language)
    if not is_weather:
        remove_terms = [
            "Weather effect",
            "天氣影響",
            "Stop work in adverse weather",
            "不安全天氣下停止工作",
            "惡劣天氣",
        ]
        for term in remove_terms:
            value = value.replace(term, "")
    generic_causes = [
        "Confirm with approved Method Statement and site-specific conditions",
        "根據已批准施工方法書及工地實際情況確認",
        "Cause to be confirmed against Method Statement / site condition",
    ]
    if any(term in value for term in generic_causes):
        return "-"
    return value


def _split_points(text: Any) -> list[str]:
    raw = str(text or "").replace("\r", "\n")
    parts: list[str] = []
    for chunk in re.split(r"\n|;|\u2022|\u30fb|\uff1b", raw):
        clean = re.sub(r"^\s*\d+[\.)、]\s*", "", chunk.strip(" \t-"))
        if clean and clean != "-":
            parts.append(clean)
    return parts


def _numbered_text(text: Any) -> str:
    points = _split_points(text)
    if not points:
        return "-"
    points = [point for point in points if point.strip()]
    if not points:
        return "-"
    return "\n".join(f"{idx}. {point}" for idx, point in enumerate(points, start=1))


def _risk_fill(score: int) -> str:
    if score >= 16:
        return "E63323"  # red
    if score >= 10:
        return "F4A63A"  # orange
    if score >= 5:
        return "FFFF4A"  # yellow
    return "A6CE39"  # green


def _extract_score(rating: Any) -> int | None:
    text = str(rating or "")
    match = re.search(r"=\s*(\d+)", text)
    if match:
        return int(match.group(1))
    numbers = [int(item) for item in re.findall(r"\b\d+\b", text)]
    return max(numbers) if numbers else None


def _extract_level_code(rating: Any) -> str:
    text = str(rating or "").upper()
    for code in ("HR", "MR", "LR"):
        if re.search(rf"\b{code}\b", text):
            return code
    for word, code in (("HIGH", "HR"), ("MEDIUM", "MR"), ("LOW", "LR")):
        if word in text:
            return code
    return ""


def _extract_probability_impact(rating: Any) -> tuple[str, str]:
    text = str(rating or "")
    p_match = re.search(r"\bP\s*([1-5])\b", text, flags=re.IGNORECASE)
    s_match = re.search(r"\bS\s*([1-5])\b", text, flags=re.IGNORECASE)
    if p_match or s_match:
        return (p_match.group(1) if p_match else "-", s_match.group(1) if s_match else "-")
    factors = re.search(r"([1-5])\s*x\s*([1-5])", text, flags=re.IGNORECASE)
    if factors:
        return factors.group(1), factors.group(2)
    return "-", "-"


def _style_table(table, header_fill: str = "E8EEF5") -> None:
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for row_idx, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_borders(cell)
            _set_cell_margins(cell)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
            if row_idx == 0:
                _set_cell_shading(cell, header_fill)


def _set_table_widths(table, widths: list[float]) -> None:
    table.autofit = False
    total_dxa = int(sum(widths) * 1440)
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), str(total_dxa))
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < len(row.cells):
                row.cells[idx].width = Inches(width)
                tc_pr = row.cells[idx]._tc.get_or_add_tcPr()
                tc_w = tc_pr.find(qn("w:tcW"))
                if tc_w is None:
                    tc_w = OxmlElement("w:tcW")
                    tc_pr.append(tc_w)
                tc_w.set(qn("w:type"), "dxa")
                tc_w.set(qn("w:w"), str(int(width * 1440)))


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(9 if level > 1 else 6)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.name = "Calibri"
    run.font.size = Pt(15 if level > 1 else 18)
    run.font.color.rgb = RGBColor(31, 77, 120) if level > 1 else RGBColor(11, 37, 69)


def _add_key_value_table(doc: Document, rows: list[tuple[str, Any]]) -> None:
    table = doc.add_table(rows=0, cols=2)
    for label, value in rows:
        cells = table.add_row().cells
        _set_cell_text(cells[0], label, bold=True, size=10.5)
        _set_cell_text(cells[1], value, size=10.5)
    _style_table(table)
    _set_table_widths(table, [2.2, 8.8])


def _risk_score_tables(doc: Document, matrix: dict[str, Any], language: str = "English") -> None:
    static = _static(language)
    severity = matrix.get("severity_scale", [])
    likelihood = matrix.get("likelihood_scale", [])
    bands = matrix.get("risk_bands", [])

    if severity and likelihood:
        grid = doc.add_table(rows=3 + len(likelihood), cols=2 + len(severity))
        grid.style = "Table Grid"
        grid.alignment = WD_TABLE_ALIGNMENT.CENTER
        grid.cell(0, 0).merge(grid.cell(0, 1))
        grid.cell(0, 2).merge(grid.cell(0, 1 + len(severity)))
        matrix_title = "PROJECT RISK MATRIX"
        impact_title = "IMPACT SEVERITY"
        probability_title = "Probability / Likelihood"
        if language in {"Traditional Chinese", "Simplified Chinese"}:
            matrix_title = "\u5de5\u7a0b\u98a8\u96aa\u77e9\u9663"
            impact_title = "\u5f71\u97ff\u56b4\u91cd\u7a0b\u5ea6"
            probability_title = "\u53ef\u80fd\u6027 / \u767c\u751f\u6a5f\u6703"
        _set_cell_text(grid.cell(0, 0), matrix_title, bold=True, size=10)
        _set_cell_text(grid.cell(0, 2), impact_title, bold=True, size=10)
        _set_table_widths(grid, [0.5, 2.25, 1.1, 1.1, 1.1, 1.1, 1.1])
        _set_cell_text(grid.cell(1, 0), "P", bold=True, size=9)
        _set_cell_text(grid.cell(1, 1), probability_title, bold=True, size=9)
        severity_zh = {
            "Insignificant": "極輕微",
            "Minor": "輕微",
            "Moderate": "中等",
            "Major": "嚴重",
            "Catastrophic": "災難性",
        }
        likelihood_zh = {
            "Rare": "罕見",
            "Unlikely": "不大可能",
            "Possible": "可能",
            "Likely": "頗可能",
            "Almost Certain": "幾乎肯定",
        }
        for col, sev in enumerate(severity, start=2):
            sev_label = str(sev.get("label_en", ""))
            if language in {"Traditional Chinese", "Simplified Chinese"}:
                sev_label = severity_zh.get(sev_label, sev_label)
            _set_cell_text(grid.cell(1, col), str(sev.get("score", "")), bold=True, size=9)
            _set_cell_text(grid.cell(2, col), sev_label, bold=True, size=8.5)
            _set_cell_shading(grid.cell(1, col), "FFF44F")
            _set_cell_shading(grid.cell(2, col), "FFF44F")
        _set_cell_text(grid.cell(2, 0), "", size=7)
        _set_cell_text(grid.cell(2, 1), "", size=7)
        for row, like in enumerate(reversed(likelihood), start=3):
            like_score = int(like.get("score", 1))
            _set_cell_text(grid.cell(row, 0), like_score, bold=True, size=9)
            like_label = str(like.get("label_en", ""))
            if language in {"Traditional Chinese", "Simplified Chinese"}:
                like_label = likelihood_zh.get(like_label, like_label)
            _set_cell_text(grid.cell(row, 1), f"{like.get('code', '')} - {like_label}", size=8.5)
            for col, sev in enumerate(severity, start=2):
                score = like_score * int(sev.get("score", 1))
                cell = grid.cell(row, col)
                _set_cell_text(cell, score, bold=True, size=10)
                _set_cell_shading(cell, _risk_fill(score))
        _style_table(grid, header_fill="F2F4F7")
        doc.add_paragraph(static["risk_index_guide"])
        guide = doc.add_table(rows=1, cols=3)
        guide_headers = ["Colour", "Risk Index", "Conditions for Tolerance"]
        if language in {"Traditional Chinese", "Simplified Chinese"}:
            guide_headers = ["\u984f\u8272", "\u98a8\u96aa\u6307\u6578", "\u53ef\u5bb9\u5fcd\u689d\u4ef6"]
        for idx, header in enumerate(guide_headers):
            _set_cell_text(guide.rows[0].cells[idx], header, bold=True, size=9)
        guide_rows = static.get("risk_guide_rows", [])
        for fill, label, action in guide_rows:
            cells = guide.add_row().cells
            _set_cell_text(cells[0], "", size=9)
            _set_cell_shading(cells[0], fill)
            _set_cell_text(cells[1], label, size=9)
            _set_cell_text(cells[2], action, size=9)
        _style_table(guide, header_fill="F2F4F7")
        _set_table_widths(guide, [1.0, 1.6, 6.4])
        return


def _combined_controls(row: dict[str, Any]) -> str:
    parts = []
    if row.get("Existing Controls"):
        parts.append("Existing Control Measures:\n" + _numbered_text(row["Existing Controls"]))
    if row.get("Additional Controls Required"):
        parts.append("Further Control Measures:\n" + _numbered_text(row["Additional Controls Required"]))
    if row.get("Permit / Competent Person"):
        parts.append("Permit / Competent Person:\n" + _numbered_text(row["Permit / Competent Person"]))
    if row.get("Inspection / Monitoring"):
        parts.append("Inspection / Monitoring:\n" + _numbered_text(row["Inspection / Monitoring"]))
    if row.get("Legal / CoP Reference"):
        parts.append("Reference:\n" + _numbered_text(row["Legal / CoP Reference"]))
    return "\n".join(parts) or "-"


def build_ra_docx(report: dict[str, Any], ra_rows: list[dict[str, Any]], matrix: dict[str, Any] | None = None) -> BytesIO:
    language = str(report.get("Report Language", "English"))
    lbl = _labels(language)
    static = _static(language)
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(16.54)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.45)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.4)
    section.right_margin = Inches(0.4)

    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(11)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.add_run(lbl["main_title"])
    title_run.bold = True
    title_run.font.size = Pt(20)
    title_run.font.color.rgb = RGBColor(11, 37, 69)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(str(report.get("title", "Risk Assessment Report"))).bold = True
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Version: {report.get('Version', '-')} | Author: KL Choy | choykaleung@yahoo.com.hk | www.linkedin.com/in/ka-leung-choy")

    if language in {"Traditional Chinese", "Simplified Chinese"}:
        metadata_rows = [
            ("\u5831\u544a\u6a19\u984c", report.get("Project", "-")),
            ("\u5de5\u7a0b\u540d\u7a31", report.get("Task Location", "-")),
            ("\u5de5\u4f5c\u7bc4\u570d", report.get("Construction Activity", "-")),
            ("\u65bd\u5de5\u65b9\u6cd5\u66f8\u4f86\u6e90", report.get("Method Statement Source", "-")),
            ("\u77e9\u9663\u7248\u672c", report.get("Assessment Standard", "-")),
            ("\u5730\u5340 / \u6a19\u6e96", report.get("Jurisdiction Profile", "-")),
            ("\u98a8\u96aa\u77e9\u9663", report.get("Risk Matrix", "-")),
            ("\u7de8\u88fd", "\u5b89\u5168\u9867\u554f / \u5b89\u5168\u4e3b\u4efb"),
            ("\u7248\u672c", report.get("Version", "-")),
            ("\u8a55\u4f30\u65e5\u671f", report.get("Assessment Date", "-")),
            ("\u4e0b\u6b21\u6aa2\u8a0e\u65e5\u671f", report.get("Next Review Date", "-")),
        ]
    else:
        metadata_rows = [
            ("Report Title", report.get("Project", "-")),
            ("Project Name", report.get("Task Location", "-")),
            ("Scope of Works", report.get("Construction Activity", "-")),
            ("Method Statement Source", report.get("Method Statement Source", "-")),
            ("Matrix Version", report.get("Assessment Standard", "-")),
            ("Jurisdiction Profile", report.get("Jurisdiction Profile", "-")),
            ("Risk Matrix", report.get("Risk Matrix", "-")),
            ("Prepared by", "Safety Consultant / Safety Officer"),
            ("Revision", report.get("Version", "-")),
            ("Assessment Date", report.get("Assessment Date", "-")),
            ("Next Review Date", report.get("Next Review Date", "-")),
        ]
    _add_key_value_table(doc, metadata_rows)

    _add_heading(doc, lbl["purpose"], level=2)
    doc.add_paragraph(static["purpose_body"])

    steps = report.get("Confirmed Steps") or []
    if steps:
        _add_heading(doc, lbl["sequence"], level=2)
        for idx, step in enumerate(steps, start=1):
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.25)
            paragraph.paragraph_format.first_line_indent = Inches(-0.18)
            paragraph.paragraph_format.space_after = Pt(3)
            run = paragraph.add_run(f"{idx}. {step}")
            run.font.name = "Calibri"
            run.font.size = Pt(11)

    _add_heading(doc, lbl["requirements"], level=2)
    for item in static["requirements"]:
        doc.add_paragraph(item, style="List Bullet")

    _add_heading(doc, lbl["matrix"], level=2)
    doc.add_paragraph(static["matrix_body"])
    _risk_score_tables(doc, matrix or {}, language)

    _add_heading(doc, lbl["ra_table"], level=2)
    headers = [
        lbl["item"],
        lbl["job_task"],
        lbl["hazard"],
        lbl["people"],
        lbl["cause"],
        lbl["harm"],
        lbl["existing"],
        "P",
        "IC",
        lbl["risk_level"],
        lbl["further"],
        lbl["training_ppe"],
        lbl["action_by"],
        lbl["residual"],
        lbl["actual"],
    ]
    table = doc.add_table(rows=1, cols=len(headers))
    for idx, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], header, bold=True, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    for item_no, row in enumerate(ra_rows, start=1):
        cells = table.add_row().cells
        is_weather = _is_weather_row(row)
        p_value, ic_value = _extract_probability_impact(row.get("Initial Risk"))
        residual_score = _extract_score(row.get("Residual Risk"))
        residual_code = _extract_level_code(row.get("Residual Risk"))
        actual_residual = f"{residual_score or '-'} {residual_code}".strip()
        _set_cell_text(cells[0], item_no, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        _set_cell_text(cells[1], _clean_for_main_risk_row(row.get("Work Step"), language, is_weather), size=10.0)
        _set_cell_text(cells[2], _numbered_text(_clean_for_main_risk_row(row.get("Hazard"), language, is_weather)), size=10.0)
        _set_cell_text(cells[3], _clean_for_main_risk_row(row.get("Persons at Risk"), language, is_weather), size=10.0)
        _set_cell_text(cells[4], _numbered_text(_clean_for_main_risk_row(row.get("Cause of Hazard") or row.get("Remarks") or "Cause to be confirmed against Method Statement / site condition", language, is_weather)), size=10.0)
        _set_cell_text(cells[5], _numbered_text(_clean_for_main_risk_row(row.get("Possible Consequence"), language, is_weather)), size=10.0)
        _set_cell_text(cells[6], _numbered_text(_clean_for_main_risk_row(row.get("Existing Controls"), language, is_weather)), size=10.0)
        _set_cell_text(cells[7], p_value, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        _set_cell_text(cells[8], ic_value, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        _set_cell_text(cells[9], row.get("Initial Risk"), size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        further = _clean_for_main_risk_row(row.get("Additional Controls Required"), language, is_weather)
        _set_cell_text(cells[10], _numbered_text(further), size=10.0)
        _set_cell_text(cells[11], _numbered_text(_clean_for_main_risk_row(row.get("Permit / Competent Person") or "Induction / task briefing / suitable PPE", language, is_weather)), size=10.0)
        _set_cell_text(cells[12], _clean_for_main_risk_row(row.get("Responsible Person"), language, is_weather), size=10.0)
        _set_cell_text(cells[13], row.get("Residual Risk"), size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        _set_cell_text(cells[14], actual_residual, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        initial_score = _extract_score(row.get("Initial Risk"))
        if initial_score is not None:
            _set_cell_shading(cells[7], _risk_fill(initial_score))
            _set_cell_shading(cells[8], _risk_fill(initial_score))
            _set_cell_shading(cells[9], _risk_fill(initial_score))
        if residual_score is not None:
            _set_cell_shading(cells[13], _risk_fill(residual_score))
            _set_cell_shading(cells[14], _risk_fill(residual_score))
    _style_table(table, header_fill="FFF44F")
    _set_table_widths(table, [0.32, 1.05, 1.05, 0.95, 1.2, 0.9, 1.55, 0.32, 0.32, 0.72, 1.3, 1.15, 0.95, 0.85, 0.82])

    doc.add_paragraph(static.get("minimum_acceptable_risk", "Minimum acceptable residual risk: MR or below unless specifically accepted."))
    doc.add_paragraph(static.get("pi_note", "P: probability or likelihood rating; IC: Impact Consequence rating."))
    doc.add_paragraph(static.get("remarks_note", "Remark / Actual residual RL records the final residual risk."))

    _add_heading(doc, lbl["ppe"], level=2)
    ppe_rows = static["ppe"]
    for item in ppe_rows:
        doc.add_paragraph(item, style="List Bullet")

    _add_heading(doc, lbl["checklist"], level=2)
    checklist = static["checklist"]
    for item in checklist:
        doc.add_paragraph(f"[ ] {item}")

    _add_heading(doc, lbl["approval"], level=2)
    if language in {"Traditional Chinese", "Simplified Chinese"}:
        signature_rows = [
            [lbl["role"], lbl["position"], lbl["name"], lbl["signature"], lbl["date"]],
            ["\u7de8\u88fd", "\u5b89\u5168\u9867\u554f / \u5b89\u5168\u4e3b\u4efb", "____________________", "____________________", "__________"],
            ["\u5be9\u95b1", "\u9805\u76ee\u7d93\u7406", "____________________", "____________________", "__________"],
            ["\u5be9\u95b1", "\u5de5\u5730\u76e3\u7763 / \u5de5\u982d", "____________________", "____________________", "__________"],
            ["\u78ba\u8a8d", "\u5206\u5224\u5546\u4ee3\u8868", "____________________", "____________________", "__________"],
            ["\u6838\u5be6", "\u5408\u8cc7\u683c\u4eba\u58eb", "____________________", "____________________", "__________"],
            ["\u78ba\u8a8d", "\u5ba2\u6236\u4ee3\u8868\uff08\u5982\u9700\u8981\uff09", "____________________", "____________________", "__________"],
        ]
    else:
        signature_rows = [
            [lbl["role"], lbl["position"], lbl["name"], lbl["signature"], lbl["date"]],
            ["Prepared by", "Safety Consultant / Safety Officer", "____________________", "____________________", "__________"],
            ["Reviewed by", "Project Manager", "____________________", "____________________", "__________"],
            ["Reviewed by", "Site Supervisor / Foreman", "____________________", "____________________", "__________"],
            ["Acknowledged by", "Subcontractor Representative", "____________________", "____________________", "__________"],
            ["Verified by", "Competent Person", "____________________", "____________________", "__________"],
            ["Acknowledged by", "Client Representative (if required)", "____________________", "____________________", "__________"],
        ]
    table = doc.add_table(rows=0, cols=5)
    for row_index, row in enumerate(signature_rows):
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            _set_cell_text(cells[idx], value, bold=(row_index == 0), size=11.0)
    _style_table(table, header_fill="FFF44F")
    _set_table_widths(table, [2.0, 4.0, 3.4, 3.4, 2.0])

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
