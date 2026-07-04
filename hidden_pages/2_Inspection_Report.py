from uuid import uuid4

import streamlit as st

from services.ai_prompts import DISCLAIMER, INSPECTION_SYSTEM_PROMPT
from services.docx_export import build_docx
from services.google_sheets import append_row, now_iso
from services.i18n import t
from services.nvidia_client import generate_json
from services.validators import InspectionDraft

st.set_page_config(page_title="Inspection Report", layout="wide")
st.title("Inspection Report")
st.warning(t("draft_warning"), icon="⚠️")


def fallback(data: dict) -> InspectionDraft:
    finding = data.get("finding") or "Unsafe condition to be confirmed"
    return InspectionDraft(
        disclaimer=DISCLAIMER,
        formal_finding_en=f"During site inspection, the following safety finding was observed: {finding}.",
        formal_finding_zh=f"巡查期間發現以下安全事項：{finding}。",
        risk_possible_consequence="Possible injury, property damage or unsafe work continuation if not rectified.",
        immediate_action=data.get("immediate_action") or "Stop affected work where necessary and make the area safe.",
        corrective_action="Rectify the unsafe condition with responsible party and completion date assigned.",
        preventive_action="Review work method, brief workers on specific controls and verify by follow-up inspection.",
        legal_cop_reference_tag="To be verified by Safety Officer",
        follow_up_checking_point="Verify rectification evidence and inspect the same location before close-out.",
        status="Open",
    )


with st.form("inspection"):
    c1, c2 = st.columns(2)
    project = c1.text_input(t("project"))
    date = c2.date_input(t("date"))
    location = c1.text_input(t("location"))
    contractor = c2.text_input(t("contractor"))
    finding = st.text_area("Finding description")
    unsafe = st.selectbox("Unsafe act / unsafe condition", ["Unsafe condition", "Unsafe act", "Both", "To be confirmed"])
    photo = st.text_area("Photo description")
    risk = st.selectbox(t("risk_level"), ["Low", "Medium", "High", "Critical", "To be confirmed"])
    immediate = st.text_area("Immediate action taken")
    responsible = c1.text_input(t("responsible"))
    target = c2.date_input(t("target_date"))
    submitted = st.form_submit_button(t("generate"))

if submitted:
    payload = {
        "project": project,
        "date": str(date),
        "location": location,
        "contractor": contractor,
        "finding": finding,
        "unsafe": unsafe,
        "photo": photo,
        "risk": risk,
        "immediate_action": immediate,
        "responsible": responsible,
        "target": str(target),
    }
    draft, flags, error = generate_json(INSPECTION_SYSTEM_PROMPT, payload, InspectionDraft)
    if draft is None:
        st.info(t("ai_unavailable") + f" ({error})")
        draft = fallback(payload)
    st.session_state["inspection_draft"] = draft.model_dump()
    st.session_state["inspection_payload"] = payload
    if flags:
        st.caption("Redaction flags: " + ", ".join(flags))

if "inspection_draft" in st.session_state:
    draft = InspectionDraft.model_validate(st.session_state["inspection_draft"])
    st.subheader("Bilingual finding")
    st.write("**English**")
    st.write(draft.formal_finding_en)
    st.write("**中文**")
    st.write(draft.formal_finding_zh)
    st.table(
        {
            "Item": ["Risk / consequence", "Immediate action", "Corrective action", "Preventive action", "Legal / CoP", "Follow-up", "Status"],
            "Draft": [draft.risk_possible_consequence, draft.immediate_action, draft.corrective_action, draft.preventive_action, draft.legal_cop_reference_tag, draft.follow_up_checking_point, draft.status],
        }
    )
    docx = build_docx("Inspection Finding Draft", draft.model_dump())
    st.download_button(t("export_word"), docx, file_name="inspection_finding.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if st.button(t("save_record")):
        payload = st.session_state["inspection_payload"]
        ok = append_row(
            "inspection_findings",
            {
                "finding_id": str(uuid4()),
                "project_id": payload.get("project", ""),
                "date": payload.get("date", ""),
                "location": payload.get("location", ""),
                "contractor": payload.get("contractor", ""),
                "finding": draft.formal_finding_en,
                "unsafe_act_condition": payload.get("unsafe", ""),
                "risk_level": payload.get("risk", ""),
                "immediate_action": draft.immediate_action,
                "corrective_action": draft.corrective_action,
                "preventive_action": draft.preventive_action,
                "responsible_party": payload.get("responsible", ""),
                "target_date": payload.get("target", ""),
                "status": draft.status,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        )
        st.success("Saved to Google Sheets." if ok else "Google Sheets not configured; record not persisted.")
