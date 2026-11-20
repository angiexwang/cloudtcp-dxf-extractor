"""Tests for Week 6 batch auditing and honest success accounting."""
import json
import ezdxf

from cloudtcp_dxf.batch import run_batch
from test_pipeline import config


def make_dxf(path, *, with_line=False, with_unmapped=False):
    doc = ezdxf.new()
    doc.blocks.new("W20_1")
    if with_unmapped:
        doc.blocks.new("UNRECOGNIZED")
    space = doc.modelspace()
    space.add_blockref("W20_1", (20, 5))
    if with_unmapped:
        space.add_blockref("UNRECOGNIZED", (25, 5))
    if with_line:
        space.add_line((0, 0), (100, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def test_batch_dgn_is_not_silently_accepted(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    (source / "client.dgn").write_bytes(b"not a real DGN")
    summary = run_batch(source, output)
    assert summary["total_files"] == 1
    assert summary["successful_files"] == 0
    assert summary["files"][0]["failure_category"] == ["native_dgn_not_supported"]
    assert summary["conversion_success_rate"] == 0


def test_batch_preserves_geometry_and_reports_losses(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    make_dxf(source / "nested" / "plan.dxf", with_line=True, with_unmapped=True)
    summary = run_batch(source, output, config=config())
    row = summary["files"][0]
    assert row["status"] == "failure"
    assert row["converted_elements"] == 1
    assert "unmapped_cell_names" in row["failure_category"]
    assert "basemap_not_represented_in_if_v1" in row["failure_category"]
    assert "schema_not_validated" in row["failure_category"]
    assert (output / row["extraction_output"]).exists()
    assert (output / row["if_output"]).exists()
    assert summary["remaining_failures_ranked"][0]["affected_files"] == 1


def test_batch_no_config_keeps_extraction(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    make_dxf(source / "plan.dxf")
    summary = run_batch(source, output)
    row = summary["files"][0]
    assert row["failure_category"] == ["missing_if_config"]
    assert row["if_output"] is None
    assert json.loads((output / "conversion-log.json").read_text())["total_files"] == 1


def test_batch_empty_directory_has_no_fake_success(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    summary = run_batch(source, output)
    assert summary["total_files"] == 0
    assert summary["conversion_success_rate"] is None
    assert summary["successful_files"] == 0


def test_batch_invalid_dxf_continues(tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    (source / "broken.dxf").write_text("not dxf")
    make_dxf(source / "good.dxf")
    summary = run_batch(source, output)
    assert summary["total_files"] == 2
    failures = {r["file"]: r["failure_category"] for r in summary["files"]}
    assert failures["broken.dxf"] == ["read_or_conversion_error"]
    assert failures["good.dxf"] == ["missing_if_config"]
