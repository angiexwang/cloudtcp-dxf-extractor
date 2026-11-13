"""Reusable DXF modelspace extraction; unsupported entities stay in the report."""
from collections import Counter
from pathlib import Path
import ezdxf

def xyz(value):
    return [float(value[0]), float(value[1]), float(value[2]) if len(value) > 2 else 0.0]

def entity_data(entity):
    kind = entity.dxftype()
    result = {"handle": entity.dxf.get("handle"), "type": kind, "layer": entity.dxf.get("layer", "0")}
    if kind == "LINE":
        result["geometry"] = {"start": xyz(entity.dxf.start), "end": xyz(entity.dxf.end)}
    elif kind == "LWPOLYLINE":
        result["geometry"] = {"vertices": [[float(x), float(y), float(b)] for x, y, _, _, b in entity.get_points("xyseb")], "closed": bool(entity.closed)}
    elif kind == "POLYLINE":
        result["geometry"] = {"vertices": [xyz(v.dxf.location) for v in entity.vertices], "closed": bool(entity.is_closed)}
    elif kind == "ARC":
        result["geometry"] = {"center": xyz(entity.dxf.center), "radius": float(entity.dxf.radius), "start_angle": float(entity.dxf.start_angle), "end_angle": float(entity.dxf.end_angle)}
    elif kind == "CIRCLE":
        result["geometry"] = {"center": xyz(entity.dxf.center), "radius": float(entity.dxf.radius)}
    elif kind == "POINT":
        result["geometry"] = {"position": xyz(entity.dxf.location)}
    elif kind in ("TEXT", "MTEXT"):
        result["text"] = entity.dxf.text if kind == "TEXT" else entity.plain_text()
        result["geometry"] = {"insert": xyz(entity.dxf.insert), "rotation": float(entity.dxf.get("rotation", 0))}
    elif kind == "INSERT":
        result["block_name"] = entity.dxf.name
        result["geometry"] = {"insert": xyz(entity.dxf.insert), "rotation": float(entity.dxf.get("rotation", 0)), "scale": [float(entity.dxf.get(k, 1)) for k in ("xscale", "yscale", "zscale")]}
        result["attributes"] = {a.dxf.tag: a.dxf.text for a in entity.attribs}
    elif kind == "ELLIPSE":
        result["geometry"] = {"center": xyz(entity.dxf.center), "major_axis": xyz(entity.dxf.major_axis), "ratio": float(entity.dxf.ratio), "start_param": float(entity.dxf.start_param), "end_param": float(entity.dxf.end_param)}
    return result

def extract_dxf(path, *, max_entities=None):
    path = Path(path)
    if max_entities is not None and max_entities < 0:
        raise ValueError("max_entities must be nonnegative")
    document = ezdxf.readfile(path)
    audit = document.audit()
    entities = []
    types, layers, unsupported = Counter(), Counter(), Counter()
    for item in document.modelspace():
        if max_entities is not None and len(entities) >= max_entities:
            break
        record = entity_data(item)
        entities.append(record)
        types[record["type"]] += 1
        layers[record["layer"]] += 1
        if "geometry" not in record:
            unsupported[record["type"]] += 1
    warnings = []
    if len(entities) < len(document.modelspace()):
        warnings.append("Partial extraction: max_entities reached")
    if types["INSERT"] == 0:
        warnings.append("No INSERT entities: block-name symbol mapping cannot identify flattened symbols")
    return {
        "extraction_format": "cloudtcp-cad-extraction/0.1.0",
        "source": {"filename": path.name, "format": "DXF", "drawing_units_code": int(document.header.get("$INSUNITS", 0)), "modelspace_entity_count": len(document.modelspace()), "extracted_entity_count": len(entities)},
        "layers": [{"name": name, "count": n} for name, n in sorted(layers.items())],
        "entity_types": dict(sorted(types.items())),
        "entities": entities,
        "log": {"audit_errors": len(audit.errors), "audit_fixes": len(audit.fixes), "unsupported_geometry_counts": dict(sorted(unsupported.items())), "warnings": warnings, "scope": "DXF modelspace only; no native DGN reading, external reference resolution or CAD round-trip."}
    }
