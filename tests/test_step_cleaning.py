from services.file_extract import clean_extracted_steps


def test_rejects_document_title_and_headings():
    raw = [
        "拆棚施工方案",
        "安全程序及措施",
        "拆棚之程序",
        "準備工作",
        "先拆斜棚，其中先拆除尼龍網/鋅鐵片/帆布，繼而拆橫杆，再拆支撐點之竹杆。",
    ]
    steps = clean_extracted_steps(raw, titles=["拆棚施工方案"])
    assert steps == ["先拆斜棚，其中先拆除尼龍網/鋅鐵片/帆布，繼而拆橫杆，再拆支撐點之竹杆。"]


def test_rejects_safety_rules_and_controls():
    raw = [
        "必須佩戴安全帶及安全帽",
        "嚴禁拋擲竹枝",
        "如遇天氣惡劣須即時停工",
        "拆除橫杆並傳遞至下層工人收集",
    ]
    steps = clean_extracted_steps(raw)
    assert steps == ["拆除橫杆並傳遞至下層工人收集"]


def test_keeps_english_action_steps():
    raw = [
        "Method Statement",
        "Table of Contents",
        "Erect working platform and install guardrails",
        "Dismantle scaffold members from top level downwards",
    ]
    steps = clean_extracted_steps(raw, titles=["Method Statement"])
    assert steps == [
        "Erect working platform and install guardrails",
        "Dismantle scaffold members from top level downwards",
    ]


def test_deduplicates_and_caps_steps():
    raw = [f"安裝第{i}段棚架構件" for i in range(1, 20)] + ["安裝第1段棚架構件"]
    steps = clean_extracted_steps(raw, max_steps=14)
    assert len(steps) == 14
    assert len(set(steps)) == 14


def test_rejects_concatenated_labels_and_buttons():
    junk = [
        "T&CProcedureof",
        "MethodofSiteTestingofBMU",
        "Tractionhoistsselectorswitch",
        "Cageupbutton",
        "Emergencystop",
    ]
    real = [
        "接駁 380V、三相、16A、5-pin 臨時電源或永久電源。",
        "測試控制箱所有按鈕，確認各摩打運行方向正確。",
        "Test all limit switches and confirm operation",
    ]
    steps = clean_extracted_steps(junk + real)
    assert steps == real


def test_repairs_spaceless_pdf_steps():
    from services.file_extract import clean_extracted_steps, repair_concatenated_english

    broken = [
        "Bypassbutton(bypassslackropelimit,downlimitsocagecanlandonground",
        "Visualcheckallstructuralmembers,connections,",
        "Visualcheckgondolaconnections,allnets&bolts",
        "MethodofSiteTestingofBMU",  # heading, must be rejected even after repair
    ]
    steps = clean_extracted_steps(broken)
    assert steps == [
        "Bypass button (bypass slack rope limit, down limit so cage can land on ground",
        "Visual check all structural members, connections,",
        "Visual check gondola connections, all nets&bolts",
    ]
    # Healthy text must survive repair untouched.
    ok = "Carry out static load test of the cage at 150% SWL witnessed by RPE."
    assert repair_concatenated_english(ok) == ok
