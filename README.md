# CloudTCP DXF Extractor

Reusable Python DXF modelspace extraction and **conservative** mapping of named block references to CloudTCP IF v1.

## Features

- Reads DXF modelspace using `ezdxf` and inventories layers and entity types.
- Extracts lines, polylines, arcs, circles, text, ellipses and named block inserts with DXF handles.
- Logs unsupported entities rather than silently treating them as converted.
- Optional IF v1 JSON conversion for *explicitly mapped* sign, arrow-board and flagger blocks.
- Converts insert coordinates to station/offset relative to a **user-provided straight centerline**.
- Writes per-file conversion diagnostics; optional schema validation.

## Install and test

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Inspect a DXF

```bash
cloudtcp-dxf input.dxf -o extracted.json --log extraction-log.json
```

## Map recognized named blocks to IF v1

Copy and **edit** `examples/if-config.example.json`, replacing every illustrative site, traffic, zone and centerline value with verified facts specific to the drawing.

```bash
cloudtcp-dxf input.dxf --if-config site-config.json --schema tcp-intermediate-format.schema.json -o output.if.json --log conversion-log.json
```

The schema file comes from the CloudTCP verifier project and is **not bundled**. If omitted, conversion output is not schema-validated.

## Important limitations

- **No native DGN support**. The reader only accepts DXF. A separate DGN adapter or carefully validated DGN-to-DXF export is needed.
- **No reliable classification of flattened signs or cones**. The supplied Alameda DXF has no `INSERT` entities; conversion from that file will yield no identified signs.
- No automatic road centerline discovery, curved-line stationing, sign placement/legend disambiguation, cone aggregation, basemap reconstruction, xref resolution, or CAD round-trip yet.
- Required IF fields such as posted speed, number of lanes and zones are **not inferred**. Explicit configuration is necessary.
- The IF v1 schema cannot encode complete basemap/road geometry. Raw extracted CAD data should be preserved separately.
- This project does not certify traffic-control compliance.

The example config is deliberately illustrative, **not real Alameda metadata**. Do not use example values for engineering decisions.
