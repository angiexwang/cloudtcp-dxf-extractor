"""Batch audit for client CAD files; never reports unsupported DGN as converted."""
import argparse
from collections import Counter
import json
from pathlib import Path

from .extract import extract_dxf
from .if_conversion import convert_extraction, validate_if


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def classify(extraction, report, document):
    """Conservative audit: an emitted JSON file alone is not conversion success."""
    failures = []
    lost = []
    if extraction["log"]["audit_errors"]:
        failures.append("dxf_audit_errors")
    if report["unmapped_blocks"]:
        failures.append("unmapped_cell_names")
        lost.extend(f"unmapped block {name} ({count})" for name, count in report["unmapped_blocks"].items())
    if report["skipped_mappings"]:
        failures.append("invalid_symbol_mapping")
        lost.extend(f"{name} ({count})" for name, count in report["skipped_mappings"].items())
    if report["unsupported_geometry_counts"]:
        failures.append("unsupported_cad_entities")
        lost.extend(f"unsupported {name} ({count})" for name, count in report["unsupported_geometry_counts"].items())
    if not document["elements"]:
        failures.append("no_mapped_traffic_elements")
    # IF v1 cannot represent a full basemap/road linework; preserve extraction.
    geometric = sum(extraction["entity_types"].get(t, 0) for t in (
        "LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE"
    ))
    if geometric:
        failures.append("basemap_not_represented_in_if_v1")
        lost.append(f"{geometric} CAD geometry entities retained only in extraction sidecar")
    # Cones are not a supported IF element type in the current converter.
    return list(dict.fromkeys(failures)), lost


def run_batch(input_dir, output_dir, *, config=None, schema=None):
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if not input_dir.is_dir():
        raise ValueError(f"Input directory not found: {input_dir}")
    if config is not None and not isinstance(config, dict):
        raise ValueError("config must be a JSON object")
    files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".dgn", ".dxf"))
    results = []
    for path in files:
        relative = path.relative_to(input_dir)
        base = output_dir / relative
        record = {"file": relative.as_posix(), "status": "failure", "failure_category": [],
                  "elements_lost_or_misplaced": [], "converted_elements": 0,
                  "if_output": None, "extraction_output": None}
        try:
            if path.suffix.lower() == ".dgn":
                record["failure_category"].append("native_dgn_not_supported")
                record["elements_lost_or_misplaced"].append("Native DGN contents not inspected; requires verified DGN-to-DXF conversion")
            else:
                extraction = extract_dxf(path)
                extraction_path = Path(str(base) + ".extracted.json")
                save_json(extraction_path, extraction)
                record["extraction_output"] = extraction_path.relative_to(output_dir).as_posix()
                if config is None:
                    record["failure_category"].append("missing_if_config")
                    record["elements_lost_or_misplaced"].append("IF conversion not attempted without verified site metadata and centerline")
                else:
                    doc, report = convert_extraction(extraction, config)
                    record["converted_elements"] = len(doc["elements"])
                    record["unmapped_blocks"] = report["unmapped_blocks"]
                    record["skipped_mappings"] = report["skipped_mappings"]
                    failures, lost = classify(extraction, report, doc)
                    record["failure_category"].extend(failures)
                    record["elements_lost_or_misplaced"].extend(lost)
                    if schema is None:
                        record["failure_category"].append("schema_not_validated")
                    else:
                        try:
                            validate_if(doc, schema)
                        except Exception as exc:
                            record["failure_category"].append("schema_validation_failed")
                            record["validation_error"] = str(exc)
                    if "schema_validation_failed" not in record["failure_category"]:
                        if_path = Path(str(base) + ".if.json")
                        save_json(if_path, doc)
                        record["if_output"] = if_path.relative_to(output_dir).as_posix()
                    if not record["failure_category"]:
                        record["status"] = "success"
        except Exception as exc:
            record["failure_category"].append("read_or_conversion_error")
            record["error"] = f"{type(exc).__name__}: {exc}"
        results.append(record)
    count = Counter(cat for r in results for cat in r["failure_category"])
    successes = sum(r["status"] == "success" for r in results)
    summary = {
        "total_files": len(results), "successful_files": successes,
        "conversion_success_rate": successes / len(results) if results else None,
        "conversion_success_rate_percent": round(100 * successes / len(results), 2) if results else None,
        "remaining_failures_ranked": [{"category": k, "affected_files": v}
                                      for k, v in sorted(count.items(), key=lambda item: (-item[1], item[0]))],
        "files": results,
        "notes": [
            "Success requires IF schema validation, mapped traffic elements, no known CAD loss, and no unrepresented basemap geometry.",
            "Native DGN is not parsed; any DGN files count as failures until converted and individually audited.",
            "Missing cone representation, misplaced geometry, and verifier correctness require manual inspection of real plans.",
            "The CAD extraction sidecar preserves linework even though IF v1 cannot represent a full basemap."
        ]
    }
    save_json(output_dir / "conversion-log.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Batch-audit DGN/DXF files against IF v1 requirements")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path, required=True)
    parser.add_argument("--if-config", type=Path, help="Verified site configuration JSON")
    parser.add_argument("--schema", type=Path, help="IF v1 JSON schema (required to count successful conversions)")
    args = parser.parse_args(argv)
    try:
        if args.schema and not args.if_config:
            parser.error("--schema requires --if-config")
        config = json.loads(args.if_config.read_text(encoding="utf-8")) if args.if_config else None
        summary = run_batch(args.input_dir, args.output_dir, config=config, schema=args.schema)
        print(f"Audited {summary['total_files']} files; {summary['successful_files']} fully converted. "
              f"Log: {args.output_dir / 'conversion-log.json'}")
        return 0 if summary["successful_files"] == summary["total_files"] and summary["total_files"] else 1
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Batch failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
