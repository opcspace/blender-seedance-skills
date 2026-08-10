# Precision Core V2 Contract

Use these four JSON contract files as the job record. Validate them before executing geometry and preserve them unchanged in the final evidence bundle except through named contract revisions.

## 1. `scene-spec.json` (`SceneSpec`)

Required fields:

- `schema_version`: `"2.0"`
- `job_id`, `scene_id`, `units`
- `requested_grade`: `L0`, `L1`, or `L2`
- `backend`: `blender` or `cad`
- `coordinate_system`, `origin`, `global_envelope`
- `parts`, `interfaces`, `contacts`, `anchors`
- `measurements`, `assertions`
- `assumptions`, `reasons`

Use absolute scene units. Every fit-critical target must have an explicit absolute `tolerance`; never substitute percentages or visual similarity.

## 2. `asset-manifest.json` (`AssetManifest`)

Required fields:

- `schema_version`, `job_id`, `assets`
- For each asset: `asset_id`, `role`, `source`, `uri`, `checksum`, `units`, `scale`, `provenance`, `assumptions`, `reasons`

Asset `role` is one of `reference`, `dimensional_drawing`, `calibration`, `visual_shell`, `source_geometry`, or `deliverable`. Asset `source` is one of `user`, `generated`, `imported`, `library`, `tripo`, or `derived`. A Tripo asset must use `role: visual_shell`; it supplies visual guidance only and never measurement authority.

## 3. `operation-plan.json` (`OperationPlan`)

Required fields:

- `schema_version`, `job_id`, `backend`, `operations`, `assumptions`, `reasons`
- For each operation: `operation_id`, `operation_type`, `target_ids`, `parameters`, `depends_on`, `expected_outputs`, `checkpoint`

Order operations deterministically by dependency and stable `operation_id`. Use only registered typed operations. Do not embed Python, expressions, shell, Blender console text, or other raw executable code. Apply corrections as named typed patch operations that cite the failed inspection/assertion and their parent checkpoint.

## 4. `precision-report.json` (`PrecisionReport`)

Required fields:

- `schema_version`, `job_id`, `status`, `grade`, `backend`
- `measurements`, `assertions`, `geometry_checks`, `checkpoints`, `provenance`
- `operation_history`, `patch_history`, `evidence`
- `assumptions`, `reasons`

`status` is `prepared`, `inspected`, `validated`, `failed`, `backend_unavailable`, or `finalized`. Measurement `kind` is `global_envelope`, `primary`, `contact`, `anchor`, `clearance`, `alignment`, `interface`, `angle`, `radius`, or `custom`. Each measurement records `measurement_id`, `kind`, `target`, `actual`, `tolerance`, `unit`, `required`, `passed`, and `evidence_ids`.

## Exact grade gates

- **L0:** Use whenever input lacks a known dimension or scale and either a calibrated camera or a dimensional drawing; when required calibration is inferred; when a requested backend is unavailable; or when any higher gate is incomplete. One image or several images alone do not raise L0.
- **L1:** Require passing required `global_envelope`, `primary`, `contact`, and `anchor` measurements and their assertions. Missing any category, failure, or absent evidence is L0.
- **L2:** Require every required measurement and assertion to pass; all geometry checks and checkpoints to pass; complete provenance; no unresolved `assumptions`; and the full evidence set. A failed required assertion prevents commit and L2.

Only `precision_validate_job` may determine a passing grade. Only `precision_finalize_job` may commit a passing report/evidence bundle.

## Evidence contents

Include all four contract files; the committed `.blend` and normalized import/export artifacts; checksums; backend/tool versions; calibrated reference and dimensional sources; deterministic operation and named-patch histories; before/after checkpoints; measurement values with absolute tolerances; assertion and geometry-check results; object/part identifiers and transforms; provenance; and neutral renders sufficient to identify measured targets. Rendered appearance and Seedance output are supporting previews, never grade evidence.
