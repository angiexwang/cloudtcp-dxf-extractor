"""DXF extraction and conservative IF conversion command-line interface."""
import argparse
import json
import sys
from pathlib import Path
from .extract import extract_dxf
from .if_conversion import convert_dxf, validate_if

def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect a DXF or convert mapped block inserts to IF v1")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--max-entities", type=int)
    parser.add_argument("--if-config", type=Path, help="JSON config for IF v1 conversion; requires explicit road facts and centerline")
    parser.add_argument("--schema", type=Path, help="Optional IF v1 JSON Schema for validation")
    args = parser.parse_args(argv)
    try:
        if args.max_entities is not None and args.max_entities < 0:
            parser.error("--max-entities must be nonnegative")
        if args.if_config:
            if args.max_entities is not None:
                parser.error("--max-entities is incompatible with --if-config")
            config = json.loads(args.if_config.read_text(encoding="utf-8"))
            document, log = convert_dxf(args.input, config)
            if args.schema:
                validate_if(document, args.schema)
            output = args.output or args.input.with_suffix(".if.json")
            write_json(output, document)
        else:
            if args.schema:
                parser.error("--schema requires --if-config")
            result = extract_dxf(args.input, max_entities=args.max_entities)
            log = {"source": result["source"], "entity_types": result["entity_types"], "layers": result["layers"], "log": result["log"]}
            output = args.output or args.input.with_suffix(".extracted.json")
            write_json(output, result)
        if args.log:
            write_json(args.log, log)
        print(f"Wrote {output}")
        return 0
    except (OSError, ValueError, KeyError, Exception) as exc:
        print(f"Conversion failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
