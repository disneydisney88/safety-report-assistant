from __future__ import annotations

import json
import re
from typing import Any, Type

import streamlit as st
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from services.redaction import redact_text
from services.ai_prompts import DISCLAIMER

BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "z-ai/glm-5.2"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 8192
MAX_ALLOWED_TOKENS = 8192
DEFAULT_TIMEOUT_SECONDS = 90.0


def has_api_key() -> bool:
    return bool(st.secrets.get("NVIDIA_API_KEY", ""))


def model_name() -> str:
    return st.secrets.get("NVIDIA_MODEL", DEFAULT_MODEL)


def generation_options() -> dict[str, Any]:
    requested_max_tokens = int(st.secrets.get("NVIDIA_MAX_TOKENS", DEFAULT_MAX_TOKENS))
    options: dict[str, Any] = {
        "temperature": float(st.secrets.get("NVIDIA_TEMPERATURE", DEFAULT_TEMPERATURE)),
        "top_p": float(st.secrets.get("NVIDIA_TOP_P", DEFAULT_TOP_P)),
        "max_tokens": min(requested_max_tokens, MAX_ALLOWED_TOKENS),
    }
    seed = st.secrets.get("NVIDIA_SEED", "")
    if seed != "":
        options["seed"] = int(seed)
    return options


def _client() -> OpenAI:
    return OpenAI(
        base_url=BASE_URL,
        api_key=st.secrets["NVIDIA_API_KEY"],
        timeout=float(st.secrets.get("NVIDIA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        max_retries=0,
    )


def _repair_payload_for_schema(data: Any, schema: Type[BaseModel]) -> Any:
    if getattr(schema, "__name__", "") != "RADraft" or not isinstance(data, dict):
        return data
    if "disclaimer" in data and "items" in data:
        return data

    source = data.get("risk_assessment") or data.get("riskAssessment") or data
    if not isinstance(source, dict):
        source = data

    possible_item_keys = ["items", "ra_items", "risk_items", "risk_assessment_items", "table", "risk_table"]
    raw_items = []
    for key in possible_item_keys:
        value = source.get(key) if isinstance(source, dict) else None
        if isinstance(value, list):
            raw_items = value
            break

    repaired_items = []
    def text_value(value: Any, default: str) -> str:
        if value is None or value == "":
            return default
        if isinstance(value, list):
            return "; ".join(str(v) for v in value)
        if isinstance(value, dict):
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        return str(value)

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        repaired_items.append(
            {
                "source_step_id": text_value(item.get("source_step_id") or item.get("sourceStepId") or item.get("step_id") or item.get("stepId"), ""),
                "source_step_text_original": text_value(item.get("source_step_text_original") or item.get("sourceStepTextOriginal") or item.get("original_step") or item.get("originalStep"), ""),
                "source_step_text_translated": text_value(item.get("source_step_text_translated") or item.get("sourceStepTextTranslated") or item.get("translated_step") or item.get("translatedStep"), ""),
                "hazard_id": text_value(item.get("hazard_id") or item.get("hazardId"), ""),
                "hazard_category": text_value(item.get("hazard_category") or item.get("hazardCategory"), ""),
                "work_step": text_value(item.get("work_step") or item.get("workStep") or item.get("step") or item.get("activity") or source.get("activity"), "To be confirmed"),
                "hazard": text_value(item.get("hazard") or item.get("hazards"), "To be confirmed"),
                "cause_of_hazard": text_value(item.get("cause_of_hazard") or item.get("causeOfHazard") or item.get("cause") or item.get("hazard_cause") or item.get("hazardCause"), "To be confirmed"),
                "possible_consequence": text_value(item.get("possible_consequence") or item.get("possibleConsequence") or item.get("consequence") or item.get("possible_consequences") or item.get("possibleConsequences"), "To be confirmed"),
                "persons_at_risk": text_value(item.get("persons_at_risk") or item.get("personsAtRisk") or item.get("people_at_risk") or item.get("peopleAtRisk"), "Workers / others nearby"),
                "initial_risk_rating": text_value(item.get("initial_risk_rating") or item.get("initialRiskRating") or item.get("initial_risk") or item.get("initialRisk") or item.get("risk_rating") or item.get("riskLevel"), "To be confirmed"),
                "existing_control_measures": text_value(item.get("existing_control_measures") or item.get("existingControlMeasures") or item.get("existing_controls") or item.get("existingControls") or item.get("controls"), "To be confirmed"),
                "additional_control_measures_required": text_value(item.get("additional_control_measures_required") or item.get("additionalControlMeasuresRequired") or item.get("additional_controls") or item.get("additionalControls"), "To be confirmed"),
                "residual_risk_rating": text_value(item.get("residual_risk_rating") or item.get("residualRiskRating") or item.get("residual_risk") or item.get("residualRisk"), "To be confirmed"),
                "legal_cop_reference": text_value(item.get("legal_cop_reference") or item.get("legalCopReference") or item.get("legal_reference") or item.get("legalReference") or item.get("legal_ref_tags") or item.get("legalRefTags"), "To be verified by Safety Officer"),
                "permit_certificate_competent_person_required": text_value(item.get("permit_certificate_competent_person_required") or item.get("permitCertificateCompetentPersonRequired") or item.get("permit_required") or item.get("permitRequired") or item.get("competent_person_required") or item.get("competentPersonRequired"), "To be confirmed"),
                "inspection_monitoring_points": text_value(item.get("inspection_monitoring_points") or item.get("inspectionMonitoringPoints") or item.get("inspection_points") or item.get("inspectionPoints") or item.get("monitoring_points") or item.get("monitoringPoints"), "To be confirmed"),
                "responsible_person": text_value(item.get("responsible_person") or item.get("responsiblePerson") or item.get("responsible_party") or item.get("responsibleParty"), "To be confirmed"),
                "remarks_items_to_be_confirmed": text_value(item.get("remarks_items_to_be_confirmed") or item.get("remarksItemsToBeConfirmed") or item.get("remarks") or item.get("items_to_confirm") or item.get("itemsToConfirm"), "To be confirmed"),
            }
        )

    return {
        "disclaimer": data.get("disclaimer") or source.get("disclaimer") or DISCLAIMER,
        "overall_risk_level": data.get("overall_risk_level") or source.get("overall_risk_level") or source.get("risk_level") or "To be confirmed",
        "items": repaired_items,
    }


def test_connection() -> tuple[bool, str]:
    if not has_api_key():
        return False, "missing_api_key"
    try:
        response = _client().chat.completions.create(
            model=model_name(),
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": '{"ping":"connection_test"}'},
            ],
            temperature=0,
            top_p=1,
            max_tokens=64,
        )
        content = response.choices[0].message.content or ""
        return True, f"connected ({model_name()})" if content else "connected_empty_response"
    except Exception as exc:
        detail = re.sub(r"\s+", " ", str(exc))[:220]
        # Diagnose the most common cause of a 400 here: the configured model id
        # does not exist on the NVIDIA endpoint. List what the key can access.
        hint = ""
        try:
            available = [m.id for m in _client().models.list().data]
            if model_name() in available:
                hint = f" | model '{model_name()}' exists on the endpoint"
            else:
                similar = [m for m in available if any(t in m.lower() for t in ("glm", "z-ai", "zai", "zhipu"))][:6]
                fallbacks = [m for m in available if "instruct" in m.lower()][:3]
                suggestion = ", ".join(similar or fallbacks) or "see build.nvidia.com model catalog"
                hint = (
                    f" | model '{model_name()}' NOT FOUND on this endpoint. "
                    f"Set NVIDIA_MODEL in Streamlit Secrets to a valid id, e.g.: {suggestion}"
                )
        except Exception:
            pass
        return False, f"{exc.__class__.__name__}: {detail}{hint}"


def generate_json(system_prompt: str, payload: dict[str, Any], schema: Type[BaseModel], options_override: dict[str, Any] | None = None) -> tuple[BaseModel | None, list[str], str | None]:
    hidden_prompt = str(payload.get("hidden_report_prompt", "") or "")
    # The hidden prompt is sent as its own message; remove it from the payload
    # dump so it is not transmitted twice (doubling input tokens caused
    # BadRequestError context overflows on long Method Statements).
    slim_payload = {k: v for k, v in payload.items() if k != "hidden_report_prompt"}
    raw_payload = json.dumps(slim_payload, ensure_ascii=False, indent=2)
    redacted_payload, flags = redact_text(raw_payload)
    redacted_hidden_prompt, hidden_flags = redact_text(hidden_prompt)
    flags = list(dict.fromkeys(flags + hidden_flags))
    if not has_api_key():
        return None, flags, "missing_api_key"

    options = generation_options()
    if options_override:
        options.update(options_override)
    messages = [{"role": "system", "content": system_prompt + "\nReturn valid JSON only."}]
    if redacted_hidden_prompt:
        messages.append({"role": "user", "content": "HIDDEN REPORT PROMPT / CONTROLLING BRIEF:\n" + redacted_hidden_prompt})
    messages.append({"role": "user", "content": "STRUCTURED INPUT DATA:\n" + redacted_payload})
    response = None
    last_error = ""
    for attempt in range(2):  # one automatic retry on timeout / connection errors
        try:
            response = _client().chat.completions.create(
                model=model_name(),
                messages=messages,
                **options,
            )
            break
        except Exception as exc:
            detail = re.sub(r"\s+", " ", str(exc))[:180]
            last_error = f"{exc.__class__.__name__}: {detail}" if detail else exc.__class__.__name__
            if attempt == 0 and ("Timeout" in last_error or "Connection" in last_error):
                continue
            return None, flags, last_error
    if response is None:
        return None, flags, last_error or "no_response"
    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        data = json.loads(content[start : end + 1]) if start >= 0 and end > start else {}
    try:
        return schema.model_validate(data), flags, None
    except ValidationError as exc:
        repaired_data = _repair_payload_for_schema(data, schema)
        try:
            return schema.model_validate(repaired_data), flags, None
        except ValidationError:
            return None, flags, str(exc)
