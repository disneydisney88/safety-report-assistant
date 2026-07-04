from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

WORKSHEETS = {
    "projects": ["project_id", "project_name", "client", "main_contractor", "location", "status", "created_at"],
    "ra_records": ["ra_id", "project_id", "date", "location", "trade", "subcontractor", "work_activity", "risk_level", "ai_checker_result", "approval_status", "reviewer", "approver", "drive_docx_url", "drive_pdf_url", "created_at", "updated_at"],
    "ra_items": ["item_id", "ra_id", "work_step", "hazard", "consequence", "persons_at_risk", "initial_risk_rating", "existing_controls", "additional_controls", "residual_risk_rating", "legal_reference", "permit_required", "inspection_points", "responsible_person", "remarks"],
    "inspection_findings": ["finding_id", "project_id", "date", "location", "contractor", "finding", "unsafe_act_condition", "risk_level", "immediate_action", "corrective_action", "preventive_action", "responsible_party", "target_date", "status", "drive_photo_url", "drive_report_url", "created_at", "updated_at"],
    "incident_reports": ["incident_id", "project_id", "date_time", "location", "employer_subcontractor", "injured_person_ref", "trade", "accident_type", "severity", "sick_leave_category", "description", "work_activity", "plant_equipment", "immediate_cause", "underlying_cause", "root_cause", "immediate_action", "corrective_action", "preventive_action", "statutory_form_checklist", "privacy_redaction_status", "approval_status", "drive_report_url", "created_at", "updated_at"],
    "follow_up_actions": ["action_id", "source_type", "source_id", "project_id", "action_description", "responsible_party", "target_date", "status", "completion_date", "evidence_url", "remarks", "updated_at"],
    "hazard_library": ["hazard_id", "activity", "work_step", "hazard", "consequence", "standard_controls", "permit_required", "competent_person_required", "inspection_points", "common_mistakes", "legal_reference_tags"],
    "legal_reference_library": ["reference_id", "category", "document_name", "short_requirement", "applicable_activity", "exact_clause", "verification_status", "official_source_url", "last_checked_date", "remarks"],
    "ai_generation_log": ["log_id", "timestamp", "user", "module", "model", "input_summary_redacted", "output_summary", "token_estimate", "checker_result", "warning_flags"],
    "audit_log": ["audit_id", "timestamp", "user", "action", "record_type", "record_id", "old_value_summary", "new_value_summary"],
}


def configured() -> bool:
    return bool(st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "") and st.secrets.get("GOOGLE_SHEET_ID", ""))


def _service():
    info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def append_row(sheet_name: str, row: dict[str, Any]) -> bool:
    if not configured():
        return False
    headers = WORKSHEETS[sheet_name]
    values = [[row.get(h, "") for h in headers]]
    _service().spreadsheets().values().append(
        spreadsheetId=st.secrets["GOOGLE_SHEET_ID"],
        range=f"{sheet_name}!A:Z",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    return True


def read_sheet(sheet_name: str) -> pd.DataFrame:
    if not configured():
        return pd.DataFrame(columns=WORKSHEETS.get(sheet_name, []))
    result = _service().spreadsheets().values().get(
        spreadsheetId=st.secrets["GOOGLE_SHEET_ID"],
        range=f"{sheet_name}!A:Z",
    ).execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame(columns=WORKSHEETS.get(sheet_name, []))
    headers, rows = values[0], values[1:]
    return pd.DataFrame(rows, columns=headers)


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

