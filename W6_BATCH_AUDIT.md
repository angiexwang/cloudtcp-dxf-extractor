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