from services.language_tools import (
    contains_cjk,
    has_substantial_english,
    normalize_rows_language,
    row_language_mismatch,
    zh_term_cleanup,
)


def test_zh_cleanup_translates_known_fallback_phrases():
    assert zh_term_cleanup("Fall from height") == "高處墮下"
    assert zh_term_cleanup("To be verified by Safety Officer") == "由安全主任核實"
    result = zh_term_cleanup("Pre-work briefing; Supervisor control; Suitable PPE")
    assert result == "開工前簡介; 監督人員控制; 合適個人防護裝備"


def test_zh_cleanup_prefers_longest_phrase():
    text = "Workers, supervisors, subcontractors and persons nearby"
    assert zh_term_cleanup(text) == "工人、監督人員、分判商及附近人士"


def test_abbreviations_do_not_count_as_english():
    assert not has_substantial_english("使用合適 PPE 及安全帶，P2 x S5 = 10 HR")
    assert has_substantial_english("Follow approved Method Statement and brief workers")


def test_row_language_mismatch_detection():
    zh_row = {
        "Work Step": "拆卸棚架",
        "Hazard": "高處墮下",
        "Initial Risk": "P2 x S5 = 10 HR",
    }
    mixed_row = dict(zh_row, Hazard="Fall from height during scaffold dismantling")
    assert not row_language_mismatch(zh_row, "Traditional Chinese")
    assert row_language_mismatch(mixed_row, "Traditional Chinese")
    assert row_language_mismatch({"Hazard": "高處墮下"}, "English")


def test_normalize_rows_keeps_ratings_and_original_step():
    rows = [
        {
            "Source Step Original": "Erect platform",
            "Initial Risk": "P2 x S5 = 10 HR",
            "Hazard": "Fall from height",
        }
    ]
    normalized = normalize_rows_language(rows, "Traditional Chinese")
    assert normalized[0]["Initial Risk"] == "P2 x S5 = 10 HR"
    assert normalized[0]["Source Step Original"] == "Erect platform"
    assert normalized[0]["Hazard"] == "高處墮下"
    assert contains_cjk(normalized[0]["Hazard"])
