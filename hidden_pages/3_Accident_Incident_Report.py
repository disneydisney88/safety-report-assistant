from uuid import uuid4

import streamlit as st

from services.ai_prompts import DISCLAIMER, INCIDENT_SYSTEM_PROMPT
from services.docx_export import build_docx
from services.google_sheets import append_row, now_iso
from services.i18n import t
from services.nvidia_client import generate_json
from services.validators import IncidentDraft

st.set_page_config(page_title="Accident / Incident Report", layout="wide")
st.title("Accident / Incident / Injury Report")
st.warning(t("draft_warning"), icon="⚠️")
st.caption("Internal draft only. Do not auto-submit to Labour Department.")


def fallback(data: dict) -> IncidentDraft:
    return IncidentDraft(
        disclaimer=DISCLAIMER,
        internal_accident_report_draft=f"Internal draft based on reported event at {data.get('location', 'To be confirmed')}. Facts and statutory reporting requirements must be verified.",
        accident_chronology=[data.get("description") or "Accident chronology to be confirmed"],
        immediate_causes=[data.get("immediate_cause") or "To be confirmed"],
        root_cause_analysis=[data.get("root_cause") or "To be confirmed"],
        corrective_preventive_action_table=[
            {"type": "Immediate", "action": data.get("immediate_action") or "Make area safe", "owner": "To be confirmed", "status": "Open"},
            {"type": "Corrective", "action": data.get("corrective_action") or "Rectify direct unsafe condition", "owner": "To be confirmed", "status": "Open"},
            {"type": "Preventive", "action": data.get("preventive_action") or "Review method and supervision", "owner": "To be confirmed", "status": "Open"},
        ],
        evidence_checklist=["Photos", "Witness reference codes", "Training records", "Permit / inspection records", "Medical certificate if applicable"],
        statutory_reporting_checklist=["Form 2 / 2A / 2B applicability: To be confirmed by Safety Officer"],
        items_to_be_verified_by_safety_officer=["Sick leave days", "Severity", "Dangerous occurrence classification", "Statutory form requirement"],
        privacy_warning="Use reference codes only. Remove personal data before external sharing.",
    )


with st.form("incident"):
    c1, c2 = st.columns(2)
    project = c1.text_input(t("project"))
    date_time = c2.text_input("Date and time of accident")
    location = c1.text_input(t("location"))
    employer = c2.text_input("Employer / subcontractor")
    injured_ref = c1.text_input("Injured person reference code only")
    trade = c2.text_input("Job title / trade")
    accident_type = c1.selectbox("Type of accident", ["injury", "dangerous occurrence", "near miss", "property damage", "occupational disease suspected"])
    severity = c2.selectbox("Injury severity", ["first aid only", "medical treatment", "sick leave <= 3 days", "sick leave > 3 days", "fatal", "permanent incapacity suspected"])
    description = st.text_area("Description of accident")
    work_activity = st.text_area("Work activity at time of accident")
    plant_equipment = st.text_area("Plant / equipment involved")
    immediate_cause = st.text_area("Immediate cause")
    underlying_cause = st.text_area("Underlying cause")
    root_cause = st.text_area("Root cause")
    immediate_action = st.text_area("Immediate action taken")
    corrective_action = st.text_area("Corrective action")
    preventive_action = st.text_area("Preventive action")
    witnesses = st.text_area("Witness reference codes")
    medical_cert = c1.selectbox("Medical certificate received", ["No", "Yes", "To be confirmed"])
    sick_leave_known = c2.selectbox("Sick leave days known", ["No", "Yes", "To be confirmed"])
    forms = st.multiselect("Potential Labour Department form checklist", ["Form 2", "Form 2A", "Form 2B", "Employee injury notice", "To be confirmed by Safety Officer"])
    submitted = st.form_submit_button(t("generate"))

if submitted:
    payload = {
        "project": project,
        "date_time": date_time,
        "location": location,
        "employer": employer,
        "injured_ref": injured_ref,
        "trade": trade,
        "accident_type": accident_type,
        "severity": severity,
        "description": description,
        "work_activity": work_activity,
        "plant_equipment": plant_equipment,
        "immediate_cause": immediate_cause,
        "underlying_cause": underlying_cause,
        "root_cause": root_cause,
        "immediate_action": immediate_action,
        "corrective_action": corrective_action,
        "preventive_action": preventive_action,
        "witnesses": witnesses,
        "medical_cert": medical_cert,
        "sick_leave_known": sick_leave_known,
        "forms": forms,
    }
    draft, flags, error = generate_json(INCIDENT_SYSTEM_PROMPT, payload, IncidentDraft)
    if draft is None:
        st.info(t("ai_unavailable") + f" ({error})")
        draft = fallback(payload)
    st.session_state["incident_draft"] = draft.model_dump()
    st.session_state["incident_payload"] = payload
    if flags:
        st.caption("Redaction flags: " + ", ".join(flags))

if "incident_draft" in st.session_state:
    draft = IncidentDraft.model_validate(st.session_state["incident_draft"])
    st.subheader("Internal accident report draft")
    st.write(draft.internal_accident_report_draft)
    for label, value in draft.model_dump().items():
        if label not in {"disclaimer", "internal_accident_report_draft"}:
            st.write(f"**{label.replace('_', ' ').title()}**")
            st.write(value)
    docx = build_docx("Accident / Incident Report Draft", draft.model_dump())
    st.download_button(t("export_word"), docx, file_name="incident_report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if st.button(t("save_record")):
        payload = st.session_state["incident_payload"]
        ok = append_row(
            "incident_reports",
            {
                "incident_id": str(uuid4()),
                "project_id": payload.get("project", ""),
                "date_time": payload.get("date_time", ""),
                "location": payload.get("location", ""),
                "employer_subcontractor": payload.get("employer", ""),
                "injured_person_ref": payload.get("injured_ref", ""),
                "trade": payload.get("trade", ""),
                "accident_type": payload.get("accident_type", ""),
                "severity": payload.get("severity", ""),
                "description": payload.get("description", ""),
                "work_activity": payload.get("work_activity", ""),
                "plant_equipment": payload.get("plant_equipment", ""),
                "immediate_cause": payload.get("immediate_cause", ""),
                "underlying_cause": payload.get("underlying_cause", ""),
                "root_cause": payload.get("root_cause", ""),
                "immediate_action": payload.get("immediate_action", ""),
                "corrective_action": payload.get("corrective_action", ""),
                "preventive_action": payload.get("preventive_action", ""),
                "statutory_form_checklist": ", ".join(payload.get("forms", [])),
                "privacy_redaction_status": "Redacted before AI call",
                "approval_status": "Draft",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        )
        st.success("Saved to Google Sheets." if ok else "Google Sheets not configured; record not persisted.")
