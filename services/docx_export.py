from __future__ import annotations

from io import BytesIO
import re
from typing import Any

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt, RGBColor

from services.ai_prompts import DISCLAIMER
from services.language_tools import en_term_cleanup as _shared_en_cleanup
from services.language_tools import zh_term_cleanup as _shared_zh_cleanup

# East Asian font applied to every run so Chinese text renders consistently
# instead of falling back to a default serif font.
EAST_ASIAN_FONT = "Microsoft JhengHei"
LATIN_FONT = "Calibri"

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
        "permits": "7.0 Permits & Statutory Documentation",
        "emergency": "8.0 Emergency Arrangements",
        "training": "9.0 Training & Competency Records",
        "monitoring": "10.0 Monitoring & Inspection Schedule",
        "checklist": "11.0 Mandatory Pre-start Checklist",
        "approval": "12.0 Approval / Acknowledgement",
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
        "permits": "7.0 許可證及法定文件",
        "emergency": "8.0 應急安排",
        "training": "9.0 訓練及資格紀錄",
        "monitoring": "10.0 監察及巡查時間表",
        "checklist": "11.0 開工前必要檢查清單",
        "approval": "12.0 批核 / 確認",
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
        "permits": "7.0 许可证及法定文件",
        "emergency": "8.0 应急安排",
        "training": "9.0 训练及资格纪录",
        "monitoring": "10.0 监察及巡查时间表",
        "checklist": "11.0 开工前必要检查清单",
        "approval": "12.0 批核 / 确认",
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
        "ppe": "6.0 個人防護裝備要求",
        "permits": "7.0 許可證及法定文件",
        "emergency": "8.0 應急安排",
        "training": "9.0 訓練及資格紀錄",
        "monitoring": "10.0 監察及巡查時間表",
        "checklist": "11.0 開工前必要檢查清單",
        "approval": "12.0 批核 / 確認",
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
        "ppe": "6.0 个人防护装备要求",
        "permits": "7.0 许可证及法定文件",
        "emergency": "8.0 应急安排",
        "training": "9.0 训练及资格纪录",
        "monitoring": "10.0 监察及巡查时间表",
        "checklist": "11.0 开工前必要检查清单",
        "approval": "12.0 批核 / 确认",
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
        "minimum_acceptable_risk": "Minimum acceptable residual risk: all residual risk shall be reduced to ALARP and normally LR (score 1-4) after additional controls; any residual MR requires stated ALARP justification and specific acceptance by the Registered Safety Officer / authorised management before work proceeds.",
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
        "minimum_acceptable_risk": "最低可接受剩餘風險：所有剩餘風險實施進一步控制措施後須降至 LR（1-4 分）；如仍為 MR，須列明 ALARP 理據並由註冊安全主任 / 獲授權管理層特別接受方可開工。",
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
            table = doc.add_table(rows=1 + len(value), cols=len(keys))
            table.style = "Table Grid"
            for idx, key in enumerate(keys):
                table.rows[0].cells[idx].text = str(key)
            for row_index, row in enumerate(value, start=1):
                cells = table.rows[row_index].cells
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


# Ordered subset of the CT_TblPrBase child sequence. WordprocessingML requires
# tblPr children to appear in this order; strict viewers (OpenOffice / older
# LibreOffice) silently ignore a whole tblPr whose children are out of order,
# which collapses a bordered table into a stacked list. Any element we add must
# be positioned against this sequence rather than blindly appended.
_TBLPR_ORDER = (
    "w:tblStyle",
    "w:tblpPr",
    "w:tblOverlap",
    "w:bidiVisual",
    "w:tblStyleRowBandSize",
    "w:tblStyleColBandSize",
    "w:tblW",
    "w:jc",
    "w:tblCellSpacing",
    "w:tblInd",
    "w:tblBorders",
    "w:shd",
    "w:tblLayout",
    "w:tblCellMar",
    "w:tblLook",
    "w:tblCaption",
    "w:tblDescription",
)


def _tblpr_get_or_add(tbl_pr, tag: str):
    """Find or create a tblPr child, inserting it in schema-correct order."""
    existing = tbl_pr.find(qn(tag))
    if existing is not None:
        return existing
    element = OxmlElement(tag)
    successors = _TBLPR_ORDER[_TBLPR_ORDER.index(tag) + 1:]
    anchor = None
    for succ in successors:
        anchor = tbl_pr.find(qn(succ))
        if anchor is not None:
            break
    if anchor is not None:
        anchor.addprevious(element)
    else:
        tbl_pr.append(element)
    return element


def _set_table_borders(table, color: str = "000000", size: str = "6") -> None:
    """Force explicit table-level borders.

    Some viewers (OpenOffice / older LibreOffice / Google Docs) do not resolve
    borders from the ``Table Grid`` style or from cell-level ``w:tcBorders``
    alone, so a bordered table collapses into what looks like a stacked list.
    Writing ``w:tblBorders`` directly on the table guarantees a real grid
    everywhere.
    """
    tbl_pr = table._tbl.tblPr
    borders = _tblpr_get_or_add(tbl_pr, "w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
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


def _apply_fonts(run) -> None:
    """Set Latin + East Asian fonts so Chinese renders in a clean sans-serif."""
    run.font.name = LATIN_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    rfonts.set(qn("w:eastAsia"), EAST_ASIAN_FONT)


# Markers that flag content needing attention in the printed report:
# square-bracket placeholders the site team must complete, and residual risk
# still above the LR acceptance target.
_PLACEHOLDER_MARKERS = ("[To be completed by site team", "[由工地團隊填寫", "[由工地填寫")


def _is_alert_text(text: str) -> bool:
    return any(marker in str(text or "") for marker in _PLACEHOLDER_MARKERS)


def residual_above_target(text: str) -> bool:
    """True when a residual rating has not reached the LR acceptance target
    (e.g. "P1 x S5 = 5 MR"). Applied to the residual column only — a high
    INITIAL rating is normal and must not be flagged."""
    match = re.search(r"=\s*\d+\s*(LR|MR|HR)", str(text or ""))
    return bool(match and match.group(1) in {"MR", "HR"})


def _set_cell_text(cell, text: Any, bold: bool = False, size: float = 10.0, align: int | None = None) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    if align is not None:
        paragraph.alignment = align
    # Empty string stays blank (e.g. colour swatch cells); None renders "-".
    run = paragraph.add_run("" if text == "" else str(text if text is not None else "-"))
    run.bold = bold
    _apply_fonts(run)
    run.font.size = Pt(size)
    # Red-flag site-team placeholders and residual risk above the LR target so
    # reviewers cannot miss what still needs action before work starts.
    if text and _is_alert_text(str(text)):
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        run.bold = True


def _zh_term_cleanup(text: Any) -> str:
    return _shared_zh_cleanup(text)


def _en_term_cleanup(text: Any) -> str:
    return _shared_en_cleanup(text)


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
    _set_table_borders(table)
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
    dxa = [int(width * 1440) for width in widths]
    total_dxa = sum(dxa)
    tbl_pr = table._tbl.tblPr

    # Force fixed layout so Word honours the column grid instead of auto-fitting.
    tbl_layout = _tblpr_get_or_add(tbl_pr, "w:tblLayout")
    tbl_layout.set(qn("w:type"), "fixed")

    tbl_w = _tblpr_get_or_add(tbl_pr, "w:tblW")
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), str(total_dxa))

    # In fixed layout Word sizes columns from w:tblGrid, so it must be rewritten
    # to the intended widths (python-docx otherwise leaves it equal-width).
    tbl = table._tbl
    grid = tbl.find(qn("w:tblGrid"))
    if grid is None:
        grid = OxmlElement("w:tblGrid")
        tbl.insert(list(tbl).index(tbl_pr) + 1, grid)
    for existing in list(grid.findall(qn("w:gridCol"))):
        grid.remove(existing)
    for width_dxa in dxa:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width_dxa))
        grid.append(grid_col)

    for row in table.rows:
        for idx, width_dxa in enumerate(dxa):
            if idx < len(row.cells):
                row.cells[idx].width = Emu(int(width_dxa * 635))  # 1 dxa = 635 EMU
                tc_pr = row.cells[idx]._tc.get_or_add_tcPr()
                tc_w = tc_pr.find(qn("w:tcW"))
                if tc_w is None:
                    tc_w = OxmlElement("w:tcW")
                    tc_pr.append(tc_w)
                tc_w.set(qn("w:type"), "dxa")
                tc_w.set(qn("w:w"), str(width_dxa))


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(9 if level > 1 else 6)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.bold = True
    _apply_fonts(run)
    run.font.size = Pt(15 if level > 1 else 18)
    run.font.color.rgb = RGBColor(31, 77, 120) if level > 1 else RGBColor(11, 37, 69)


def _add_key_value_table(doc: Document, rows: list[tuple[str, Any]]) -> None:
    # Rows are created up front (not via add_row on an empty table): LibreOffice
    # / OpenOffice mis-render tables that start with rows=0 and grow by add_row.
    table = doc.add_table(rows=len(rows), cols=2)
    for row_index, (label, value) in enumerate(rows):
        cells = table.rows[row_index].cells
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
            _set_cell_text(grid.cell(1, col), str(sev.get("score", "")), bold=True, size=10)
            _set_cell_text(grid.cell(2, col), sev_label, bold=True, size=9.5)
            _set_cell_shading(grid.cell(1, col), "FFF44F")
            _set_cell_shading(grid.cell(2, col), "FFF44F")
        _set_cell_text(grid.cell(2, 0), "", size=7)
        _set_cell_text(grid.cell(2, 1), "", size=7)
        for row, like in enumerate(reversed(likelihood), start=3):
            like_score = int(like.get("score", 1))
            _set_cell_text(grid.cell(row, 0), like_score, bold=True, size=10)
            like_label = str(like.get("label_en", ""))
            if language in {"Traditional Chinese", "Simplified Chinese"}:
                like_label = likelihood_zh.get(like_label, like_label)
            _set_cell_text(grid.cell(row, 1), f"{like.get('code', '')} - {like_label}", size=9.5)
            for col, sev in enumerate(severity, start=2):
                score = like_score * int(sev.get("score", 1))
                cell = grid.cell(row, col)
                _set_cell_text(cell, score, bold=True, size=10)
                _set_cell_shading(cell, _risk_fill(score))
        _style_table(grid, header_fill="F2F4F7")
        doc.add_paragraph(static["risk_index_guide"])
        guide_headers = ["Colour", "Risk Index", "Conditions for Tolerance"]
        if language in {"Traditional Chinese", "Simplified Chinese"}:
            guide_headers = ["\u984f\u8272", "\u98a8\u96aa\u6307\u6578", "\u53ef\u5bb9\u5fcd\u689d\u4ef6"]
        # Derive the guide from the selected matrix bands so approvers can see
        # the exact score boundaries (e.g. LR 1-4 / MR 5-9 / HR 10-25).
        bands = sorted(matrix.get("risk_bands", []), key=lambda b: -int(b.get("max", 0)))
        if bands:
            guide_rows = [
                (
                    _risk_fill(int(band.get("max", 0))),
                    f"{band.get('level', '')}: {band.get('min', '')}-{band.get('max', '')}",
                    str(band.get("action", "")),
                )
                for band in bands
            ]
        else:
            guide_rows = static.get("risk_guide_rows", [])
        guide = doc.add_table(rows=1 + len(guide_rows), cols=3)
        for idx, header in enumerate(guide_headers):
            _set_cell_text(guide.rows[0].cells[idx], header, bold=True, size=10)
        for row_index, (fill, label, action) in enumerate(guide_rows, start=1):
            cells = guide.rows[row_index].cells
            _set_cell_text(cells[0], "", size=10)
            _set_cell_shading(cells[0], fill)
            _set_cell_text(cells[1], label, size=10)
            _set_cell_text(cells[2], action, size=10)
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


_SECTION_TABLE_HEADERS = {
    "permits": {
        "English": ["Permit / Form", "Category", "Legal basis / SMS ref", "Issued by", "Validity", "Status"],
        "Traditional Chinese": ["許可證 / 表格", "類別", "法律依據 / 制度參考", "簽發人", "有效期", "狀態"],
        "Simplified Chinese": ["许可证 / 表格", "类别", "法律依据 / 制度参考", "签发人", "有效期", "状态"],
    },
    "training": {
        "English": ["Role", "Required training / certificate", "Legal basis", "Expiry / renewal", "Record location"],
        "Traditional Chinese": ["角色", "所需訓練 / 證書", "法律依據", "到期 / 續期", "紀錄存放"],
        "Simplified Chinese": ["角色", "所需培训 / 证书", "法律依据", "到期 / 续期", "纪录存放"],
    },
    "monitoring": {
        "English": ["Item", "Frequency", "By whom", "Record / form"],
        "Traditional Chinese": ["項目", "頻率", "負責人", "紀錄 / 表格"],
        "Simplified Chinese": ["项目", "频率", "负责人", "纪录 / 表格"],
    },
}

_EMERGENCY_FIELD_LABELS = {
    "English": {
        "foreseeable_scenarios": "Foreseeable emergency scenarios",
        "rescue_plan": "Rescue plan",
        "first_aid": "First aid",
        "emergency_contacts": "Emergency contacts",
        "assembly_point": "Assembly point",
        "adverse_weather_arrangements": "Typhoon / rainstorm arrangements",
    },
    "Traditional Chinese": {
        "foreseeable_scenarios": "可預見緊急情況",
        "rescue_plan": "救援計劃",
        "first_aid": "急救安排",
        "emergency_contacts": "緊急聯絡",
        "assembly_point": "集合點",
        "adverse_weather_arrangements": "颱風 / 暴雨安排",
    },
    "Simplified Chinese": {
        "foreseeable_scenarios": "可预见紧急情况",
        "rescue_plan": "救援计划",
        "first_aid": "急救安排",
        "emergency_contacts": "紧急联络",
        "assembly_point": "集合点",
        "adverse_weather_arrangements": "台风 / 暴雨安排",
    },
}


def _section_headers(kind: str, language: str) -> list[str]:
    table = _SECTION_TABLE_HEADERS[kind]
    return table.get(language, table["English"])


def _add_section_table(doc: Document, kind: str, language: str, rows: list[dict[str, Any]], field_order: list[str], widths: list[float]) -> None:
    headers = _section_headers(kind, language)
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    for idx, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], header, bold=True, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    for row_index, row in enumerate(rows, start=1):
        cells = table.rows[row_index].cells
        for idx, field in enumerate(field_order):
            _set_cell_text(cells[idx], row.get(field, ""), size=10.0)
    _style_table(table, header_fill="E8EEF5")
    _set_table_widths(table, widths)


def _add_supporting_sections(doc: Document, lbl: dict[str, str], language: str, sections: dict[str, Any]) -> None:
    permits = sections.get("permits_checklist") or []
    if permits:
        _add_heading(doc, lbl["permits"], level=2)
        _add_section_table(
            doc, "permits", language, permits,
            ["permit_or_form", "category", "legal_basis_or_sms_ref", "issued_by", "validity", "status"],
            [3.0, 1.3, 3.4, 1.8, 1.5, 1.5],
        )
    emergency = sections.get("emergency_arrangements") or {}
    if any(emergency.get(key) for key in _EMERGENCY_FIELD_LABELS["English"]):
        _add_heading(doc, lbl["emergency"], level=2)
        field_labels = _EMERGENCY_FIELD_LABELS.get(language, _EMERGENCY_FIELD_LABELS["English"])
        scenarios = emergency.get("foreseeable_scenarios") or []
        if scenarios:
            para = doc.add_paragraph()
            run = para.add_run(field_labels["foreseeable_scenarios"] + ":")
            run.bold = True
            _apply_fonts(run)
            for scenario in scenarios:
                doc.add_paragraph(str(scenario), style="List Bullet")
        for key in ("rescue_plan", "first_aid", "emergency_contacts", "assembly_point", "adverse_weather_arrangements"):
            value = emergency.get(key)
            if value:
                para = doc.add_paragraph()
                run = para.add_run(field_labels[key] + ": ")
                run.bold = True
                _apply_fonts(run)
                value_run = para.add_run(str(value))
                _apply_fonts(value_run)
                if _is_alert_text(str(value)):
                    value_run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
                    value_run.bold = True
    training = sections.get("training_records") or []
    if training:
        _add_heading(doc, lbl["training"], level=2)
        _add_section_table(
            doc, "training", language, training,
            ["role", "required_training_certificate", "legal_basis", "expiry_renewal", "record_location"],
            [2.2, 4.2, 3.0, 1.6, 1.5],
        )
    schedule = sections.get("inspection_schedule") or []
    if schedule:
        _add_heading(doc, lbl["monitoring"], level=2)
        _add_section_table(
            doc, "monitoring", language, schedule,
            ["item", "frequency", "by_whom", "record_form"],
            [4.6, 2.4, 2.5, 3.0],
        )


def _renumber_section_labels(lbl: dict[str, str], sections: dict[str, Any]) -> dict[str, str]:
    """Renumber the tail sections so headings stay consecutive.

    The label tables carry default numbers assuming every supporting section
    is present; when the AI omitted one, the report used to jump straight
    from "6.0 PPE" to "11.0 checklist". Assign numbers by what will actually
    render instead.
    """
    emergency = sections.get("emergency_arrangements") or {}
    present = {
        "ppe": True,
        "permits": bool(sections.get("permits_checklist")),
        "emergency": any(emergency.get(key) for key in _EMERGENCY_FIELD_LABELS["English"]),
        "training": bool(sections.get("training_records")),
        "monitoring": bool(sections.get("inspection_schedule")),
        "checklist": True,
        "approval": True,
    }
    renumbered = dict(lbl)
    number = 6
    for key in ("ppe", "permits", "emergency", "training", "monitoring", "checklist", "approval"):
        if present[key]:
            renumbered[key] = re.sub(r"^\d+\.0\s*", f"{number}.0 ", lbl[key])
            number += 1
    return renumbered


def build_ra_docx(report: dict[str, Any], ra_rows: list[dict[str, Any]], matrix: dict[str, Any] | None = None, sections: dict[str, Any] | None = None) -> BytesIO:
    language = str(report.get("Report Language", "English"))
    lbl = _renumber_section_labels(_labels(language), sections or {})
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
    styles["Normal"].font.name = LATIN_FONT
    styles["Normal"].font.size = Pt(11)
    # Document-level East Asian font so body paragraphs render Chinese cleanly.
    style_rpr = styles["Normal"].element.get_or_add_rPr()
    style_rfonts = style_rpr.find(qn("w:rFonts"))
    if style_rfonts is None:
        style_rfonts = OxmlElement("w:rFonts")
        style_rpr.append(style_rfonts)
    style_rfonts.set(qn("w:ascii"), LATIN_FONT)
    style_rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    style_rfonts.set(qn("w:eastAsia"), EAST_ASIAN_FONT)

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
            ("生成方式", report.get("Generated By", "-")),
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
            ("Generated By", report.get("Generated By", "-")),
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
    # Activity-specific statutory references (e.g. Cap. 59AC + SWP CoP + Form
    # 1/2/3 for BMU work) supplied by the app based on the confirmed flags.
    for item in report.get("Statutory Extra") or []:
        doc.add_paragraph(str(item), style="List Bullet")

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
    # All rows created up front; add_row-on-empty tables mis-render in OpenOffice.
    table = doc.add_table(rows=1 + len(ra_rows), cols=len(headers))
    for idx, header in enumerate(headers):
        _set_cell_text(table.rows[0].cells[idx], header, bold=True, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    previous_step = None
    for item_no, row in enumerate(ra_rows, start=1):
        cells = table.rows[item_no].cells
        is_weather = _is_weather_row(row)
        p_value, ic_value = _extract_probability_impact(row.get("Initial Risk"))
        residual_score = _extract_score(row.get("Residual Risk"))
        residual_code = _extract_level_code(row.get("Residual Risk"))
        actual_residual = f"{residual_score or '-'} {residual_code}".strip()
        _set_cell_text(cells[0], item_no, size=10.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        # Every row prints its job task, including repeats within a
        # multi-hazard group — a blank Job Task cell fails formal RA QA.
        step_text = _clean_for_main_risk_row(row.get("Work Step"), language, is_weather)
        _set_cell_text(cells[1], step_text or "To be confirmed", size=10.0)
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
        # Residual not yet at the LR acceptance target: bold red so the
        # reviewer must either strengthen controls or record management
        # acceptance before work proceeds.
        if residual_above_target(str(row.get("Residual Risk") or "")):
            for cell_idx in (13, 14):
                for paragraph in cells[cell_idx].paragraphs:
                    for run in paragraph.runs:
                        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
                        run.bold = True
        initial_score = _extract_score(row.get("Initial Risk"))
        if initial_score is not None:
            _set_cell_shading(cells[7], _risk_fill(initial_score))
            _set_cell_shading(cells[8], _risk_fill(initial_score))
            _set_cell_shading(cells[9], _risk_fill(initial_score))
        if residual_score is not None:
            _set_cell_shading(cells[13], _risk_fill(residual_score))
            _set_cell_shading(cells[14], _risk_fill(residual_score))
    _style_table(table, header_fill="FFF44F")
    # Widths tuned to sit comfortably inside the A3 landscape text column (~14.5",
    # leaving margin so no viewer collapses the table): narrow P/IC/Item, generous
    # control-measure columns, all trailing columns kept visible.
    _set_table_widths(table, [0.35, 1.2, 1.2, 0.9, 1.3, 0.95, 1.7, 0.35, 0.35, 0.78, 1.5, 1.3, 0.9, 0.85, 0.85])

    doc.add_paragraph(static.get("minimum_acceptable_risk", "Minimum acceptable residual risk: MR or below unless specifically accepted."))
    doc.add_paragraph(static.get("pi_note", "P: probability or likelihood rating; IC: Impact Consequence rating."))
    doc.add_paragraph(static.get("remarks_note", "Remark / Actual residual RL records the final residual risk."))

    sections = sections or {}

    _add_heading(doc, lbl["ppe"], level=2)
    # Prefer trade/step-specific PPE from the AI draft; fall back to the
    # generic static list when not provided.
    ppe_rows = sections.get("ppe_by_trade") or static["ppe"]
    for item in ppe_rows:
        doc.add_paragraph(str(item), style="List Bullet")

    _add_supporting_sections(doc, lbl, language, sections)

    _add_heading(doc, lbl["checklist"], level=2)
    checklist = static["checklist"]
    for item in checklist:
        doc.add_paragraph(f"[ ] {item}")

    _add_heading(doc, lbl["approval"], level=2)
    if language in {"Traditional Chinese", "Simplified Chinese"}:
        approval_header = [lbl["role"], lbl["position"], lbl["name"], lbl["signature"], lbl["date"]]
        approval_body = [
            ["\u7de8\u88fd", "\u5b89\u5168\u9867\u554f / \u5b89\u5168\u4e3b\u4efb"],
            ["\u5be9\u95b1", "\u9805\u76ee\u7d93\u7406"],
            ["\u5be9\u95b1", "\u5de5\u5730\u76e3\u7763 / \u5de5\u982d"],
            ["\u78ba\u8a8d", "\u5206\u5224\u5546\u4ee3\u8868"],
            ["\u6838\u5be6", "\u5408\u8cc7\u683c\u4eba\u58eb"],
            ["\u78ba\u8a8d", "\u5ba2\u6236\u4ee3\u8868\uff08\u5982\u9700\u8981\uff09"],
        ]
    else:
        approval_header = [lbl["role"], lbl["position"], lbl["name"], lbl["signature"], lbl["date"]]
        approval_body = [
            ["Prepared by", "Safety Consultant / Safety Officer"],
            ["Reviewed by", "Project Manager"],
            ["Reviewed by", "Site Supervisor / Foreman"],
            ["Acknowledged by", "Subcontractor Representative"],
            ["Verified by", "Competent Person"],
            ["Acknowledged by", "Client Representative (if required)"],
        ]
    # Fixed row count up front so OpenOffice / LibreOffice render a real grid.
    table = doc.add_table(rows=1 + len(approval_body), cols=5)
    for idx, value in enumerate(approval_header):
        _set_cell_text(table.rows[0].cells[idx], value, bold=True, size=11.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    for row_index, (role, position) in enumerate(approval_body, start=1):
        cells = table.rows[row_index].cells
        _set_cell_text(cells[0], role, bold=True, size=10.5)
        _set_cell_text(cells[1], position, size=10.5)
        # Name / Signature / Date left blank as write-in boxes.
        for idx in (2, 3, 4):
            _set_cell_text(cells[idx], "", size=10.5)
        table.rows[row_index].height = Inches(0.42)
        table.rows[row_index].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    _style_table(table, header_fill="FFF44F")
    # Shade the role column lightly so the sheet reads as a proper approval grid.
    for body_row in table.rows[1:]:
        _set_cell_shading(body_row.cells[0], "F2F4F7")
    # Kept well under the page width (~12") and centred; a 5-column signature
    # block does not need the full A3 span and narrow tables render reliably
    # across Word, WPS and LibreOffice.
    _set_table_widths(table, [1.6, 3.2, 2.8, 2.8, 1.6])

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
