from __future__ import annotations

import re


PATTERNS = [
    (re.compile(r"\b[A-Z]{1,2}\d{6}\([0-9A]\)", re.I), "[HKID_REDACTED]"),
    (re.compile(r"\b(?:\+?852[- ]?)?[2-9]\d{3}[- ]?\d{4}\b"), "[PHONE_REDACTED]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b[A-Z]{1,2}\s?\d{4}\b"), "[VEHICLE_PLATE_REDACTED]"),
    (re.compile(r"\b(?:HK\$|USD|RMB)\s?\d[\d,]*(?:\.\d+)?\b", re.I), "[COMMERCIAL_REDACTED]"),
]

ADDRESS_HINT = re.compile(r"\b(?:flat|room|floor|unit|block|tower|street|road|avenue|building)\b.+", re.I)
MEDICAL_HINT = re.compile(r"\b(?:diagnosis|medical|fracture|stitches|surgery|blood|hospital|clinic)\b.+", re.I)
CLIENT_HINT = re.compile(r"\b(?:client ref|tender|quotation|contract sum|confidential)\b.+", re.I)


def redact_text(text: str) -> tuple[str, list[str]]:
    redacted = text or ""
    flags: list[str] = []
    for pattern, replacement in PATTERNS:
        if pattern.search(redacted):
            flags.append(replacement.strip("[]"))
            redacted = pattern.sub(replacement, redacted)
    for pattern, replacement in [
        (ADDRESS_HINT, "[ADDRESS_REDACTED]"),
        (MEDICAL_HINT, "[MEDICAL_DETAIL_REDACTED]"),
        (CLIENT_HINT, "[CLIENT_REDACTED]"),
    ]:
        if pattern.search(redacted):
            flags.append(replacement.strip("[]"))
            redacted = pattern.sub(replacement, redacted)
    return redacted, sorted(set(flags))
