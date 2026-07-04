from services.ai_prompts import DISCLAIMER
from services.validators import RADraft


def test_ra_schema_accepts_required_table_items():
    draft = RADraft.model_validate(
        {
            "disclaimer": DISCLAIMER,
            "overall_risk_level": "High",
            "items": [
                {
                    "work_step": "Set up platform",
                    "hazard": "Fall from height",
                    "possible_consequence": "Serious injury",
                    "persons_at_risk": "Workers",
                    "initial_risk_rating": "High",
                    "existing_control_measures": "Guardrails",
                    "additional_control_measures_required": "Pre-use inspection",
                    "residual_risk_rating": "Medium",
                    "legal_cop_reference": "To be verified by Safety Officer",
                    "permit_certificate_competent_person_required": "To be confirmed",
                    "inspection_monitoring_points": "Check access",
                    "responsible_person": "Supervisor",
                    "remarks_items_to_be_confirmed": "Confirm site condition"
                }
            ],
        }
    )
    assert draft.items[0].hazard == "Fall from height"

