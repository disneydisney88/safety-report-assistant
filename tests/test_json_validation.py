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



def test_ra_schema_supporting_sections_and_null_tolerance():
    draft = RADraft.model_validate(
        {
            "disclaimer": DISCLAIMER,
            "items": [{"work_step": "Erect scaffold"}],
            "ppe_by_trade": ["scaffolder: full body harness (EN 361)", None],
            "permits_checklist": [
                {"permit_or_form": "Form 5", "category": "Statutory", "status": None},
            ],
            "emergency_arrangements": {"rescue_plan": "trained rescuer with rescue kit", "foreseeable_scenarios": None},
            "training_records": None,
            "inspection_schedule": [{"item": "Scaffold inspection", "frequency": "every 14 days", "by_whom": "Competent Person", "record_form": "Form 5"}],
        }
    )
    assert draft.ppe_by_trade == ["scaffolder: full body harness (EN 361)"]
    assert draft.permits_checklist[0].status == "To be confirmed"
    assert draft.emergency_arrangements.rescue_plan.startswith("trained")
    assert draft.training_records == []
    assert draft.inspection_schedule[0].frequency == "every 14 days"
    # old drafts without the new fields still validate
    old = RADraft.model_validate({"disclaimer": DISCLAIMER, "items": []})
    assert old.permits_checklist == [] and old.emergency_arrangements is None


def test_extraction_coerces_list_and_string_shapes():
    from services.validators import MethodStatementExtraction

    m = MethodStatementExtraction(
        plant_equipment=["BMU", "material hoist"],
        workforce_trades=["electrician", "signalman"],
        work_steps="connect power supply",
    )
    assert m.plant_equipment == "BMU; material hoist"
    assert m.workforce_trades == "electrician; signalman"
    assert m.work_steps == ["connect power supply"]
