# Precision Core V2 verification record

Date: 2026-08-10

## Portable verification

The portable acceptance layer is separate from Blender runtime acceptance. It validates all four calibrated SceneSpec/AssetManifest pairs, matching job IDs, deterministic contract-valid plans, required L1 gate categories, exact subject dimensions/tolerances, and the imported prop route:

```bash
python -m unittest tests.test_precision_fixtures -v
python -m py_compile tests/precision_v2_gui_test.py
python -c "import glob,json; paths=glob.glob('tests/fixtures/precision_v2/*.json'); [json.load(open(path, encoding='utf-8')) for path in paths]; print(f'fixtures: {len(paths)} OK')"
```

Result: **PASS** — 4 fixture tests passed, the manual runner compiled, and 8 fixture JSON documents parsed. This result does not prove that Blender created, measured, rendered, or saved any asset.

Portable subjects:

- Architecture: calibrated 4000 × 200 × 2800 mm wall, 900 × 2000 mm opening, 1 mm tolerance.
- Mechanical: calibrated 600 × 400 × 250 mm enclosure, four 8 mm hole guides, 0.5 mm tolerance.
- Furniture: calibrated 1200 × 600 × 750 mm table with four leg anchors, 1 mm tolerance.
- Props: calibrated imported 1000 mm handled tool with declared Z-up target, 1 mm tolerance.

## Real Blender 5.2 GUI acceptance

**BLOCKED: Blender executable/runtime unavailable; GLB/FBX fixtures not generated**

No `.blend`, GLB/FBX, preview, checksum, or L2 runtime result was fabricated. In particular, `tests/assets/precision_v2/import-cube.glb` is absent and is a required user-supplied input for the imported prop acceptance.

The intended command, after enabling `precision-mcp/blender_addon/precision_addon.py` in a real Blender 5.2 GUI session on framed port 9877, is:

```bash
PRECISION_WORKDIR="$PWD/tests/assets/precision_v2" python tests/precision_v2_gui_test.py
```

The runner starts the FastMCP stdio server and keeps one MCP SDK `ClientSession` for preparation, typed plan execution, an allow-listed patch, validation, and finalization. It never opens a raw socket. A successful future run must print and substantiate:

```text
architecture L2 PASS
mechanical L2 PASS
furniture L2 PASS
props L2 PASS
uncalibrated L0 PASS
failed-required-dimension NOT-L2 PASS
path-escape REJECTED PASS
```

It must also leave validated contracts, `qa_report.json`, `before.blend`, a checksummed `final.blend`, and orthographic/perspective previews under each `evidence/<job-id>/`. Until those files and hashes exist from the real runtime, V2 GUI acceptance remains blocked.

Stopping the Blender listener mid-call is a manual negative case: the MCP result must be a structured connection error, not a hang or raw-socket traceback. It was not executed in the unavailable runtime.

## Historical diagnostics are not V2 proof

Earlier Blender 5.2 MVP diagnostics exercised primitive creation, CAD Sketcher, seven-category routing, transaction abort, and preview/checkpoint output. The scripts `precision_socket_test.py`, `precision_cad_socket_test.py`, `precision_seven_category_socket_test.py`, and `precision_gui_boot.py` are retained as legacy diagnostics. They use the direct add-on path and do not establish the V2 contract, evidence, grade, or same-session FastMCP workflow described above.
