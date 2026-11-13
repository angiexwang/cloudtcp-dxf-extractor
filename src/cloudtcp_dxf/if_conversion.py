"""Conservative DXF to CloudTCP IF v1 conversion with explicit metadata and mappings."""
from collections import Counter
from math import hypot
from pathlib import Path
import json
from .extract import extract_dxf

def station_offset(point, origin, endpoint):
    dx, dy = endpoint[0] - origin[0], endpoint[1] - origin[1]
    length = hypot(dx, dy)
    if length == 0:
        raise ValueError("centerline endpoints must differ")
    vx, vy = point[0] - origin[0], point[1] - origin[1]
    along = (vx * dx + vy * dy) / length
    signed = (dx * vy - dy * vx) / length
    return {"station": round(along, 4), "offset": round(abs(signed), 4), "side": "left" if signed > 1e-9 else "right" if signed < -1e-9 else "center"}

def convert_extraction(extraction, config):
    for key in ("site", "typical_application", "zones", "centerline"):
        if key not in config:
            raise ValueError(f"Missing required configuration: {key}")
    line = config["centerline"]
    if "origin" not in line or "endpoint" not in line:
        raise ValueError("centerline requires origin and endpoint")
    site = dict(config["site"])
    site.setdefault("source_file", extraction["source"]["filename"])
    site.setdefault("source_format", "DXF")
    mappings = {key.casefold(): val for key, val in config.get("block_mappings", {}).items()}
    elements, unmapped, skipped = [], Counter(), Counter()
    for entity in extraction["entities"]:
        if entity["type"] != "INSERT":
            continue
        block = entity.get("block_name", "")
        mapping = mappings.get(block.casefold())
        if mapping is None:
            unmapped[block] += 1
            continue
        kind = mapping.get("type")
        if kind not in ("sign", "arrow_board", "flagger"):
            skipped[f"Unsupported mapping type: {kind}"] += 1
            continue
        if kind == "sign" and not mapping.get("mutcd_code"):
            skipped["Sign missing mutcd_code"] += 1
            continue
        if kind == "arrow_board" and not mapping.get("mode"):
            skipped["Arrow board missing mode"] += 1
            continue
        data = {
            "element_id": f"CAD_{entity['handle']}",
            "type": kind,
            "position": station_offset(entity["geometry"]["insert"], line["origin"], line["endpoint"]),
            "source": {"layer": entity["layer"], "entity": "INSERT", "handle": entity["handle"], "block": block},
        }
        for field in ("mutcd_code", "legend", "size_inches", "face_direction", "mode", "controls", "zone_id"):
            if field in mapping:
                data[field] = mapping[field]
        elements.append(data)
    document = {"format_version": "1.0.0", "site": site, "typical_application": config["typical_application"], "zones": config["zones"], "elements": elements}
    report = {
        "source": extraction["source"], "converted_elements": len(elements),
        "unmapped_blocks": dict(sorted(unmapped.items())),
        "skipped_mappings": dict(sorted(skipped.items())),
        "unsupported_geometry_counts": extraction["log"]["unsupported_geometry_counts"],
        "warnings": list(extraction["log"].get("warnings", [])),
        "limitations": [
            "Only named block INSERTs mapped as sign, arrow_board or flagger are converted; flattened symbols are not detected.",
            "Stationing uses a configured straight reference line, not a curved road centerline.",
            "Cone sequences, road/basemap geometry, references and CAD round-trip are not implemented.",
            "Site traffic facts and zone boundaries are supplied by configuration rather than guessed."
        ]
    }
    if unmapped:
        report["warnings"].append("Unmapped block inserts detected")
    return document, report

def convert_dxf(path, config):
    return convert_extraction(extract_dxf(path), config)

def validate_if(document, schema_path):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)
