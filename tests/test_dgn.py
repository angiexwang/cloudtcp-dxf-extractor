"""Unit tests for the external DGN converter without requiring real client files."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from cloudtcp_dxf.dgn import DGNConversionError, convert_dgn


def test_missing_gdal_does_not_create_output(tmp_path, monkeypatch):
    source = tmp_path / "client.dgn"
    source.write_bytes(b"sample")
    monkeypatch.setattr("cloudtcp_dxf.dgn.shutil.which", lambda _: None)
    with pytest.raises(DGNConversionError, match="Cannot find"):
        convert_dgn(source, tmp_path / "client.dxf")


def test_gdal_failure_is_explicit(tmp_path, monkeypatch):
    source = tmp_path / "client.dgn"
    source.write_bytes(b"sample")
    monkeypatch.setattr("cloudtcp_dxf.dgn.shutil.which", lambda _: "/usr/bin/ogr2ogr")
    monkeypatch.setattr("cloudtcp_dxf.dgn.subprocess.run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stderr="DGN driver unavailable", stdout=""))
    with pytest.raises(DGNConversionError, match="DGN driver unavailable"):
        convert_dgn(source, tmp_path / "client.dxf")


def test_successful_export_is_read_back(tmp_path, monkeypatch):
    import ezdxf
    source = tmp_path / "client.dgn"
    target = tmp_path / "client.dxf"
    source.write_bytes(b"sample")
    monkeypatch.setattr("cloudtcp_dxf.dgn.shutil.which", lambda _: "/usr/bin/ogr2ogr")
    def fake_ogr(cmd, **kwargs):
        document = ezdxf.new()
        document.modelspace().add_line((0, 0), (10, 0))
        document.saveas(cmd[3])
        return SimpleNamespace(returncode=0, stderr="", stdout="")
    monkeypatch.setattr("cloudtcp_dxf.dgn.subprocess.run", fake_ogr)
    report = convert_dgn(source, target)
    assert report["entity_count"] == 1
    assert target.exists()
    assert "Inspect" in report["warning"]
