def _rating(m, l, s):
    sc = l * s
    lvl = "HR" if sc >= 10 else ("MR" if sc >= 5 else "LR")
    return f"P{l} x S{s} = {sc} {lvl}"


def _srecs(steps):
    return [{"source_step_id": f"S{i+1:03d}", "step_text": s} for i, s in enumerate(steps)]


def test_activity_grouping_collapses_repetitive_steps():
    from services.activity_ra import are_activity_grouped_rows, build_activity_grouped_items

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
    assert are_activity_grouped_rows(items)
    # 14 sentence-steps must collapse to far fewer activity rows, not 14+.
    assert len(items) <= 14
    # Rows must be distinct (no single generic hazard dominating).
    hazards = {it["hazard"] for it in items}
    assert len(hazards) >= len(items) - 1
    # Fatal activities keep S5 residual; injury activities reach LR.
    ratings = {it["hazard_id"]: it["residual_risk_rating"] for it in items}
    assert "S5" in ratings["formwork"]
    assert "LR" in ratings["access_enclosure"]


def test_activity_grouped_rows_are_identified_for_post_processing():
    from services.activity_ra import are_activity_grouped_rows

    assert are_activity_grouped_rows([
        {"Hazard ID": "formwork"},
        {"Hazard ID": "scaffold_platform"},
        {"Hazard ID": "weather_emergency"},
    ])
    assert not are_activity_grouped_rows([{"Hazard ID": "generic-hazard"}])
    assert not are_activity_grouped_rows([])


def test_striking_and_curing_classification():
    from services.activity_ra import classify_step

    assert classify_step("拆模及臨時支撐拆除")["key"] == "striking"
    assert classify_step("養護及試件")["key"] == "curing"
    assert classify_step("底板鋼筋綁紮")["key"] == "rebar"


def test_step_type_classifier_filters_non_activities():
    from services.activity_ra import classify_step_type

    assert classify_step_type("模板施工前準備") == "heading"
    assert classify_step_type("〔控制點／Hold Point〕") == "heading"
    assert classify_step_type("相片記錄存檔") == "record_only"
    assert classify_step_type("取得書面批准後方可進行下一工序") == "permit_or_approval"
    assert classify_step_type("全面檢查模板、鋼筋及開口，取得T4批准後方可澆灌混凝土") == "work_activity"
    assert classify_step_type("底板混凝土澆築") == "work_activity"
    assert classify_step_type("底板鋼筋檢查") == "work_activity"  # T4 / hold-point bucket


def test_manhole_steps_keep_safety_critical_secondary_activities():
    from services.activity_ra import build_activity_grouped_items

    def rating(m, l, s):
        score = l * s
        level = "HR" if score >= 10 else ("MR" if score >= 5 else "LR")
        return f"P{l} x S{s} = {score} {level}"

    steps = [
        "清理及整理施工範圍，確保照明、通風及安全通道。",
        "檢查所有電動工具、起重設備、吊具、工作平台及梯具。",
        "由測量人員按批准圖紙放出井的位置及標高。",
        "按批准圖紙吊運及安放鋼筋，然後綁紮及固定底板鋼筋。",
        "安裝井壁內外模板、拉桿及臨時支撐。",
        "全面檢查模板、鋼筋、開口及標高，取得T4批准後方可澆灌混凝土。",
        "將混凝土運送至指定位置並利用混凝土泵進行澆灌。",
        "使用膠膜保濕養護並安排混凝土試件測試。",
        "按次序拆模板及臨時支撐。",
    ]
    items = build_activity_grouped_items(
        {"confirmed_steps": steps, "report_language": "English"},
        {}, rating, _srecs, "English",
    )
    hazard_ids = {item["hazard_id"] for item in items}
    assert {"t4_holdpoint", "lifting", "electrical", "transport_waste", "openings"} <= hazard_ids
    assert 12 <= len(items) <= 16


def test_duplicate_killer_removes_generic_and_collapses_repeats():
    from services.activity_ra import count_generic_rows, remove_generic_and_duplicate_rows

    generic = {
        "Work Step": "Confirmed work step requiring risk assessment",
        "Hazard": "Fall, falling object, unsafe access or unsafe working platform related to the confirmed work step",
        "Cause of Hazard": "x", "Existing Controls": "Follow approved Method Statement",
    }
    zh_generic = {"Work Step": "步驟9", "Hazard": "與工序相關的高處墮下、物料墮下、通道或作業面不安全", "Cause of Hazard": "y", "Existing Controls": "按 MS"}
    specific = {"Work Step": "混凝土澆築", "Hazard": "爆模", "Cause of Hazard": "側壓過大", "Existing Controls": "控制澆灌速度"}
    repeat = {"Work Step": "步驟A", "Hazard": "同一危害", "Cause of Hazard": "同一成因", "Existing Controls": "同一措施"}
    rows = [generic] * 5 + [zh_generic] * 3 + [specific] + [dict(repeat, **{"Work Step": f"步驟{i}"}) for i in range(4)]
    assert count_generic_rows(rows) == 8
    cleaned = remove_generic_and_duplicate_rows(rows)
    assert count_generic_rows(cleaned) == 0
    texts = [r["Hazard"] for r in cleaned]
    assert all("Confirmed work step" not in r["Work Step"] for r in cleaned)
    assert all("與工序相關的高處墮下" not in h for h in texts)
    assert texts.count("同一危害") == 2  # collapsed from 4 to max 2
    assert any(h == "爆模" for h in texts)


def test_gap_grouping_skips_headings_and_merges(monkeypatch=None):
    from services.activity_ra import build_activity_grouped_items

    def rating(m, l, s):
        sc = l * s
        lvl = "HR" if sc >= 10 else ("MR" if sc >= 5 else "LR")
        return f"P{l} x S{s} = {sc} {lvl}"

    def srecs(steps):
        return [{"source_step_id": f"S{i+1:03d}", "step_text": s} for i, s in enumerate(steps)]

    uncovered = ["模板施工前準備", "底板鋼筋檢查", "井壁鋼筋安裝", "井頂板混凝土澆灌", "相片記錄存檔"]
    items = build_activity_grouped_items(
        {"confirmed_steps": uncovered, "report_language": "English"},
        {}, rating, srecs, "English", include_weather=False, include_general=False,
    )
    # 5 lines -> 2 rows (rebar incl. its inspection, concreting); heading +
    # record-only lines dropped.
    assert len(items) == 2
    assert {it["hazard_id"] for it in items} == {"rebar", "concreting"}
    assert not any("weather" in it["hazard_id"] for it in items)
