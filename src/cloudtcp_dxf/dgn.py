"""Convert a DGN file to DXF with the installed GDAL ogr2ogr executable.

The conversion does not guarantee CAD cell identity or fidelity.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


class DGNConversionError(RuntimeError):
    """DGN conversion failed or produced unusable DXF."""


def convert_dgn(source, target, *, executable="ogr2ogr", timeout=180, overwrite=False):
    source, target = Path(source), Path(target)
    if not source.is_file() or source.suffix.lower() != ".dgn":
        raise DGNConversionError(f"Expected an existing .dgn file: {source}")
    if source.resolve() == target.resolve():
        raise DGNConversionError("Input and output paths must differ")
    if target.suffix.lower() != ".dxf":
        raise DGNConversionError("Output must use the .dxf extension")
    if not shutil.which(executable):
        raise DGNConversionError(
            f"Cannot find {executable}. Install GDAL ogr2ogr with a DGN driver. "
            "DGN V8 generally needs a GDAL build with ODA/DGNv8 support."
        )
    if target.exists():
        if not overwrite:
            raise DGNConversionError(f"Output already exists (use --overwrite): {target}")
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [executable, "-f", "DXF", str(target), str(source)]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        target.unlink(missing_ok=True)
        raise DGNConversionError(f"Conversion timed out after {timeout} seconds") from exc
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise DGNConversionError(f"Could not start ogr2ogr: {exc}") from exc
    if completed.returncode or not target.is_file() or target.stat().st_size == 0:
        target.unlink(missing_ok=True)
        detail = (completed.stderr or completed.stdout or "No DXF produced").strip()[-1200:]
        raise DGNConversionError(f"ogr2ogr failed (exit {completed.returncode}): {detail}")
    try:
        from .extract import extract_dxf
        extracted = extract_dxf(target)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise DGNConversionError(f"DXF produced but ezdxf cannot read it: {exc}") from exc
    entity_count = extracted["source"]["extracted_entity_count"]
    if not entity_count:
        target.unlink(missing_ok=True)
        raise DGNConversionError("Exported DXF contains no modelspace entities")
    return {
        "source_dgn": str(source),
        "output_dxf": str(target),
        "entity_count": entity_count,
        "warning": "Inspect against original DGN. GDAL may flatten cells, omit references, and change CAD entities.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert a MicroStation DGN file to DXF with GDAL ogr2ogr")
    parser.add_argument("input", type=Path, help="Path to client .dgn")
    parser.add_argument("-o", "--output", type=Path, help="Output .dxf (defaults beside input)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--ogr2ogr", default="ogr2ogr", help="Path to ogr2ogr executable")
    args = parser.parse_args(argv)
    try:
        target = args.output or args.input.with_suffix(".dxf")
        report = convert_dgn(args.input, target, executable=args.ogr2ogr, overwrite=args.overwrite)
        print(f"Created {report['output_dxf']} ({report['entity_count']} modelspace entities)")
        print(f"Warning: {report['warning']}")
        return 0
    except DGNConversionError as exc:
        print(f"DGN conversion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
