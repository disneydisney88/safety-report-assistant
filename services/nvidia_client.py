from __future__ import annotations

import json
import re
import time
from typing import Any, Type

import streamlit as st
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from services.redaction import redact_text
from services.ai_prompts import DISCLAIMER

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"


def base_url() -> str:
    return st.secrets.get("AI_BASE_URL", DEFAULT_BASE_URL)
DEFAULT_MODEL = "z-ai/glm-5.2"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 8192
MAX_ALLOWED_TOKENS = 16384
DEFAULT_TIMEOUT_SECONDS = 90.0


def has_api_key() -> bool:
    return bool(st.secrets.get("NVIDIA_API_KEY", ""))


def model_name() -> str:
    return st.secrets.get("NVIDIA_MODEL", DEFAULT_MODEL)


def _thinking_extra_body() -> dict[str, Any] | None:
    """Hybrid-reasoning models (DeepSeek V4, GLM) accept a thinking toggle via
    chat_template_kwargs. Thinking OFF by default: structured-JSON drafting
    needs speed, and long reasoning chains were causing timeouts. Set
    NVIDIA_THINKING = "true" in secrets to enable it."""
    model = model_name().lower()
    if not any(tag in model for tag in ("deepseek", "glm")):
        return None
    thinking = str(st.secrets.get("NVIDIA_THINKING", "false")).strip().lower() == "true"
    return {"chat_template_kwargs": {"thinking": thinking}}


def generation_options() -> dict[str, Any]:
    requested_max_tokens = int(st.secrets.get("NVIDIA_MAX_TOKENS", DEFAULT_MAX_TOKENS))
    options: dict[str, Any] = {
        "temperature": float(st.secrets.get("NVIDIA_TEMPERATURE", DEFAULT_TEMPERATURE)),
        "top_p": float(st.secrets.get("NVIDIA_TOP_P", DEFAULT_TOP_P)),
        "max_tokens": min(requested_max_tokens, MAX_ALLOWED_TOKENS),
    }
    seed = st.secrets.get("NVIDIA_SEED", "")
    if seed != "" and "integrate.api.nvidia.com" in base_url():
        options["seed"] = int(seed)
    extra = _thinking_extra_body()
    if extra:
        options["extra_body"] = extra
    return options


def _client(timeout_override: float | None = None) -> OpenAI:
    return OpenAI(
        base_url=base_url(),
        api_key=st.secrets["NVIDIA_API_KEY"],
        timeout=timeout_override if timeout_override is not None else float(st.secrets.get("NVIDIA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
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
        kwargs: dict[str, Any] = {"temperature": 0, "top_p": 1, "max_tokens": 64}
        extra = _thinking_extra_body()
        if extra:
            kwargs["extra_body"] = extra
        response = _client().chat.completions.create(
            model=model_name(),
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": '{"ping":"connection_test"}'},
            ],
            **kwargs,
        )
        content = _message_text(response.choices[0].message)
        return True, f"connected ({model_name()})" if content else f"connected_empty_ping ({model_name()}) - generation should still work"
    except Exception as exc:
        detail = re.sub(r"\s+", " ", str(exc))[:220]
        # Diagnose the most common cause of a 400 here: the configured model id
        # does not exist on the NVIDIA endpoint. List what the key can access.
        hint = ""
        try:
            available = [m.id for m in _client().models.list().data]
            norm = {m.split("/")[-1] for m in available}
            if model_name() in available or model_name().split("/")[-1] in norm:
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
        if any(token in detail for token in ("503", "ResourceExhausted", "Service Unavailable")):
            hint += " | Free shared endpoint is busy right now - wait 1-2 minutes and test again; generation auto-retries with backoff."
        if "429" in detail or "quota" in detail.lower() or "RateLimit" in exc.__class__.__name__:
            hint = " | Rate limit / quota hit. Wait ~60s (per-minute limit), or the model's free daily quota is used up - try NVIDIA_MODEL = gemini-1.5-flash, or enable billing on the Google project."
        return False, f"{exc.__class__.__name__}: {detail}{hint}"


def _parse_json_loose(content: str) -> Any | None:
    """Best-effort JSON extraction from a chat model reply. Handles ```json
    fences, reasoning preambles and trailing text. Returns None if nothing
    parseable is found (never raises)."""
    if not content:
        return None
    text = content.strip()
    # Strip ```json ... ``` / ``` ... ``` fences.
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    # 1) whole string.
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # 2) widest {...} or [...] span.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except (json.JSONDecodeError, ValueError):
                continue
    # 3) incrementally trim from the end (truncated / trailing text).
    start = text.find("{")
    if start >= 0:
        snippet = text[start:]
        for end in range(len(snippet), start, -1):
            if snippet[end - 1] != "}":
                continue
            try:
                return json.loads(snippet[:end])
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def _message_text(message: Any) -> str:
    """Return the model's text, falling back to reasoning_content for
    reasoning models that leave the content field empty."""
    content = getattr(message, "content", None)
    if content:
        return content
    for attr in ("reasoning_content", "reasoning"):
        value = getattr(message, attr, None)
        if value:
            return value
    return ""


def generate_json(system_prompt: str, payload: dict[str, Any], schema: Type[BaseModel], options_override: dict[str, Any] | None = None, timeout_override: float | None = None, retry_timeouts: bool = False) -> tuple[BaseModel | None, list[str], str | None]:
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
    # The free shared NVIDIA endpoint returns 503 ResourceExhausted when its
    # worker pool is saturated; that clears within seconds, so back off and
    # retry instead of dropping straight to the local template.
    busy_tokens = ("503", "429", "ResourceExhausted", "RateLimit", "InternalServerError", "Service Unavailable", "Connection")
    timeout_retries = 0
    for attempt in range(4):
        try:
            response = _client(timeout_override).chat.completions.create(
                model=model_name(),
                messages=messages,
                **options,
            )
            break
        except Exception as exc:
            detail = re.sub(r"\s+", " ", str(exc))[:180]
            last_error = f"{exc.__class__.__name__}: {detail}" if detail else exc.__class__.__name__
            # A timeout burns the full NVIDIA_TIMEOUT_SECONDS, so allow only one
            # timeout retry; busy 503/429 responses fail fast, so a few short
            # sleeps are cheap.
            if "Timeout" in last_error:
                timeout_retries += 1
                if not retry_timeouts or timeout_retries > 1 or attempt == 3:
                    return None, flags, last_error
                continue
            if attempt < 3 and any(token in last_error for token in busy_tokens):
                time.sleep(4 * (attempt + 1))  # 4s, 8s, 12s
                continue
            return None, flags, last_error
    if response is None:
        return None, flags, last_error or "no_response"
    content = _message_text(response.choices[0].message) or "{}"
    data = _parse_json_loose(content)
    if data is None:
        # Model replied but not as usable JSON (reasoning preamble, ```json
        # fences, truncated object...). Never crash the app - report and let the
        # caller fall back to the local template.
        return None, flags, "invalid_json_from_model: " + re.sub(r"\s+", " ", content)[:160]
    try:
        return schema.model_validate(data), flags, None
    except ValidationError as exc:
        repaired_data = _repair_payload_for_schema(data, schema)
        try:
            return schema.model_validate(repaired_data), flags, None
        except ValidationError:
            return None, flags, str(exc)
