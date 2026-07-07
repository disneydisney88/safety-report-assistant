from services.pre_ra import (
    build_pre_ra_sheet,
    detect_flags,
    detect_permits,
    format_pre_ra_for_prompt,
    load_master_db,
    missing_information,
)

DB = load_master_db()


def test_master_db_loaded():
    assert DB.get("keyword_map"), "master database missing keyword_map"
    assert DB.get("permit_rules"), "master database missing permit_rules"


def test_scaffold_dismantling_flags_and_permits():
    text = "先拆斜棚，拆除連牆器，工人於外牆竹棚以人手傳竹料到地面，鄰近行人路"
    flags = detect_flags(text, DB)
    assert flags["scaffolding"] == "Yes"
    assert flags["work_at_height"] == "Yes"
    assert flags["public_interface"] == "Yes"
    assert flags["hot_work"] == "Unknown"


def test_hot_work_triggers_permit():
    permits = detect_permits("需要燒焊及氣割工序", DB)
    names = [p["permit_name"] for p in permits]
    assert "Hot Work Permit" in names


def test_missing_info_for_lifting_without_route():
    flags = {"lifting": "Yes"}
    missing = missing_information("使用吊機吊運物料", flags)
    assert any("route" in item.lower() or "路線" in item for item in missing)


def test_sheet_assembly_and_prompt_block():
    data = {"activity": "拆棚", "equipment": "打磨機", "location": "外牆", "confined_space": "No"}
    sheet = build_pre_ra_sheet("外牆竹棚拆卸，使用打磨機，鄰近行人路", ["拆斜棚"], data, DB)
    assert sheet["flags"]["scaffolding"] == "Yes"
    assert any("Grinder" in item for item in sheet["plant_tools"])
    assert sheet["competency"], "competency should follow Yes flags"
    block = format_pre_ra_for_prompt(sheet)
    assert "Confirmed Pre-RA factual basis" in block
    assert "Permits / certificates triggered" in block
