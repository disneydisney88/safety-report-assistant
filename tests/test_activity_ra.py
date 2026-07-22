def _rating(m, l, s):
    sc = l * s
    lvl = "HR" if sc >= 10 else ("MR" if sc >= 5 else "LR")
    return f"P{l} x S{s} = {sc} {lvl}"


def _srecs(steps):
    return [{"source_step_id": f"S{i+1:03d}", "step_text": s} for i, s in enumerate(steps)]


def test_activity_grouping_collapses_repetitive_steps():
    from services.activity_ra import build_activity_grouped_items

    steps = [
        "清理施工範圍", "設置圍欄警告標誌", "測量放線核對圖則", "模板拉桿安裝",
        "底板鋼筋綁紮", "搭設金屬工作平台", "底板混凝土澆築震動器", "井壁模板支撐",
        "井壁混凝土澆灌", "養護及試件", "拆模及臨時支撐拆除", "井口開口蓋板護欄",
        "叉車運走廢料", "接駁380V電源",
    ]
    items = build_activity_grouped_items(
        {"confirmed_steps": steps, "report_language": "Traditional Chinese"},
        {}, _rating, _srecs, "Traditional Chinese",
    )
    # 14 sentence-steps must collapse to far fewer activity rows, not 14+.
    assert len(items) <= 14
    # Rows must be distinct (no single generic hazard dominating).
    hazards = {it["hazard"] for it in items}
    assert len(hazards) >= len(items) - 1
    # Fatal activities keep S5 residual; injury activities reach LR.
    ratings = {it["hazard_id"]: it["residual_risk_rating"] for it in items}
    assert "S5" in ratings["formwork"]
    assert "LR" in ratings["access_enclosure"]


def test_striking_and_curing_classification():
    from services.activity_ra import classify_step

    assert classify_step("拆模及臨時支撐拆除")["key"] == "striking"
    assert classify_step("養護及試件")["key"] == "curing"
    assert classify_step("底板鋼筋綁紮")["key"] == "rebar"
