import json
import ezdxf
import pytest
from cloudtcp_dxf.extract import extract_dxf
from cloudtcp_dxf.if_conversion import convert_dxf, station_offset
from cloudtcp_dxf.cli import main

def config():
    return {
        "site": {"name": "Synthetic", "coordinate_system": "local", "units": "feet", "road_name": "Example Rd", "state": "CA"},
        "typical_application": {"type": "lane_closure", "direction": "NB", "posted_speed_mph": 35, "lanes_total": 2},
        "zones": [{"zone_id": "Z1", "type": "work", "start_station": 0, "end_station": 100}],
        "centerline": {"origin": [0, 0], "endpoint": [100, 0]},
        "block_mappings": {"W20_1": {"type": "sign", "mutcd_code": "W20-1", "zone_id": "Z1"}}
    }

def fixture(tmp_path):
    doc = ezdxf.new()
    doc.blocks.new("W20_1")
    doc.blocks.new("OTHER")
    m = doc.modelspace()
    m.add_line((0, 0), (100, 0), dxfattribs={"layer": "Road"})
    m.add_blockref("W20_1", (20, 5), dxfattribs={"layer": "Signs"})
    m.add_blockref("OTHER", (30, 6))
    path = tmp_path / "fixture.dxf"
    doc.saveas(path)
    return path

def test_extract(tmp_path):
    data = extract_dxf(fixture(tmp_path))
    assert data["source"]["extracted_entity_count"] == 3
    assert data["entity_types"]["INSERT"] == 2
    assert data["log"]["audit_errors"] == 0

def test_positions():
    assert station_offset([20, 5], [0, 0], [100, 0])["side"] == "left"
    assert station_offset([20, -5], [0, 0], [100, 0])["side"] == "right"
    with pytest.raises(ValueError):
        station_offset([1, 2], [0, 0], [0, 0])

def test_conversion(tmp_path):
    document, log = convert_dxf(fixture(tmp_path), config())
    assert len(document["elements"]) == 1
    assert document["elements"][0]["mutcd_code"] == "W20-1"
    assert document["elements"][0]["position"]["station"] == 20
    assert log["unmapped_blocks"] == {"OTHER": 1}

def test_missing_facts_not_fabricated(tmp_path):
    with pytest.raises(ValueError, match="centerline"):
        convert_dxf(fixture(tmp_path), {"site": {}, "typical_application": {}, "zones": []})

def test_cli(tmp_path):
    path = fixture(tmp_path)
    output, log = tmp_path / "out.json", tmp_path / "log.json"
    assert main([str(path), "-o", str(output), "--log", str(log)]) == 0
    assert json.loads(output.read_text())["source"]["extracted_entity_count"] == 3
