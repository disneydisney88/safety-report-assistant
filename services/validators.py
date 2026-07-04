from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class RAItem(BaseModel):
    work_step: str = "To be confirmed"
    hazard: str = "To be confirmed"
    possible_consequence: str = "To be confirmed"
    persons_at_risk: str = "Workers / others nearby"
    initial_risk_rating: str = "To be confirmed"
    existing_control_measures: str = "To be confirmed"
    additional_control_measures_required: str = "To be confirmed"
    residual_risk_rating: str = "To be confirmed"
    legal_cop_reference: str = "To be verified by Safety Officer"
    permit_certificate_competent_person_required: str = "To be confirmed"
    inspection_monitoring_points: str = "To be confirmed"
    responsible_person: str = "To be confirmed"
    remarks_items_to_be_confirmed: str = "To be confirmed"


class RADraft(BaseModel):
    disclaimer: str
    overall_risk_level: str = "To be confirmed"
    items: list[RAItem] = Field(default_factory=list)


class InspectionDraft(BaseModel):
    disclaimer: str
    formal_finding_en: str
    formal_finding_zh: str
    risk_possible_consequence: str
    immediate_action: str
    corrective_action: str
    preventive_action: str
    legal_cop_reference_tag: str = "To be verified by Safety Officer"
    follow_up_checking_point: str
    status: str = "Open"


class IncidentDraft(BaseModel):
    disclaimer: str
    internal_accident_report_draft: str
    accident_chronology: list[str] = Field(default_factory=list)
    immediate_causes: list[str] = Field(default_factory=list)
    root_cause_analysis: list[str] = Field(default_factory=list)
    corrective_preventive_action_table: list[dict[str, str]] = Field(default_factory=list)
    evidence_checklist: list[str] = Field(default_factory=list)
    statutory_reporting_checklist: list[str] = Field(default_factory=list)
    items_to_be_verified_by_safety_officer: list[str] = Field(default_factory=list)
    privacy_warning: str = ""


class CheckerDraft(BaseModel):
    result: Literal["PASS FOR SO REVIEW", "REVISE REQUIRED", "CRITICAL MISSING ITEM", "LEGAL REFERENCE TO BE VERIFIED"]
    comments: list[str] = Field(default_factory=list)
    suggested_revised_wording: list[str] = Field(default_factory=list)

