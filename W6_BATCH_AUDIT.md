# Week 6 batch audit

This branch adds recursive DXF/DGN inventory, per-file conversion logs, and failure-frequency ranking.

## Run

Install: python -m pip install -e ".[dev]"
Test: python -m pytest
Inventory: python -m cloudtcp_dxf.batch client-plans/ -o artifacts/w6/
Convert: python -m cloudtcp_dxf.batch exported-dxfs/ -o artifacts/w6-converted/ --if-config verified-site-config.json --schema tcp-intermediate-format.schema.json

Client files should remain local unless explicitly authorized for upload. Export native DGN using approved CAD software, then verify the resulting DXF against the original (units, coordinates, layers, xrefs, and symbols). This project does not read native DGN.

Do not use the illustrative example configuration as real site data. This version accepts one config for the batch; group files by site/config or run separate batches.

## Outputs

- conversion-log.json: total files, success rate, per-file status, failure categories, lost/unrepresented elements and frequency-ranked failures.
- *.extracted.json: raw extracted geometry inventory, retained even if IF conversion fails.
- *.if.json: best-effort converted traffic elements. A written file does NOT imply complete conversion.
- Missing schema validation, unmapped blocks, unsupported entities, absent traffic elements, and basemap linework not represented in IF all prevent a full-success classification.
- Empty input directories report null success rate instead of 100%.

## Remaining W6-2 blockers

Native DGN-to-DXF conversion is not implemented. Cone recognition, flattened sign detection, centerline inference, full basemap representation in IF, CAD position visual QA, and verifier integration still require work and real sample files.

To extend block mappings: examine real block-name frequencies in the conversion log, verify symbol semantics against the original drawing, and update block_mappings in the verified site config. Do not guess MUTCD codes.

After repairing a failure category, rerun the entire same dataset, compare before/after logs, and inspect output geometry visually. The success rate is currently measured by file, not by multi-file plan set.

## Try a single client DGN (DGN -> DXF)

First install a GDAL build containing the reader for your DGN version. Confirm which drivers your local build supports:

```bash
ogrinfo --formats | grep -i dgn
```

On Windows PowerShell use `ogrinfo --formats | Select-String DGN`. The classic GDAL DGN driver handles V7; V8 generally requires an ODA-enabled GDAL build. If GDAL lacks support, export the DGN to DXF in MicroStation/other approved CAD software and continue with the existing DXF extractor.

Place your source at `client-plans/example.dgn`, then run:

```bash
python -m cloudtcp_dxf.dgn client-plans/example.dgn -o artifacts/example.dxf
python -m cloudtcp_dxf.cli artifacts/example.dxf -o artifacts/example.extracted.json --log artifacts/example.extract-log.json
```

To attempt IF v1 as well, prepare **verified** site metadata and block mappings based on that specific drawing and supply the project verifier's IF v1 JSON schema:

```bash
python -m cloudtcp_dxf.cli artifacts/example.dxf --if-config verified-site-config.json --schema tcp-intermediate-format.schema.json -o artifacts/example.if.json --log artifacts/example.if-log.json
```

To run a folder of original DGN files automatically, including export and diagnostics:

```bash
python -m cloudtcp_dxf.batch client-plans/ -o artifacts/w6/ --if-config verified-site-config.json --schema tcp-intermediate-format.schema.json
```

The batch step stores exported DXF files as `*.dgn.dxf`. If you omit `--if-config`, it exports and extracts but does not produce IF v1. Failed DGN exports are reported as `dgn_to_dxf_failed`. Exported DGN files are categorized `dgn_export_fidelity_unverified` until the DXF has been compared against the original. **A valid DXF file alone does not prove cone/sign preservation or complete IF v1 conversion.**

Do not infer completeness from the current success percentage before you have manually confirmed the required CAD entities and their positions.
