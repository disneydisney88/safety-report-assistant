from services.ai_prompts import DISCLAIMER, RA_SYSTEM_PROMPT


def test_prompts_contain_no_legal_approval_claim():
    assert "Do not invent" in RA_SYSTEM_PROMPT
    assert "reviewed and approved by Safety Officer" in DISCLAIMER

