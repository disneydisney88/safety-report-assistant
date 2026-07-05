from services.redaction import redact_text


def test_redacts_hkid_phone_email_but_keeps_permit_terms():
    text = "Worker A123456(7), phone 9123 4567, email a@example.com, permit PTW-ABCD1234"
    redacted, flags = redact_text(text)
    assert "A123456" not in redacted
    assert "9123" not in redacted
    assert "a@example.com" not in redacted
    assert "PTW-ABCD1234" in redacted
    assert "HKID_REDACTED" in flags
    assert "PERMIT_REDACTED" not in flags
