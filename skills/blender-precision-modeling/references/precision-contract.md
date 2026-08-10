# Precision Core V2 Contract

Use the four schema-valid JSON files below as the canonical job record. Every root requires `spec_version: "2.0"` and the same `job_id`. Precision Core V2 rejects extra fields.

## `scene_spec.json` (`SceneSpec`)

Required root fields:

- `spec_version`, `job_id`
- `category`: `architecture`, `mechanical`, `furniture`, or `props`
- `requested_grade`: `L0`, `L1`, or `L2`
- `units`: `mm`, `cm`, or `m`
- `coordinate_system`: object containing `up` (`X`, `Y`, or `Z`) and `handedness` (`left` or `right`)
- `reference_calibrated`: boolean
- `measurements`: array

Each measurement requires `id`, `kind`, `asset_id`, `target`, `tolerance_abs`, `required`, and `scope`; `axis` (`X`, `Y`, or `Z`) is optional. `kind` is exactly `dimension`, `distance`, `gap`, `contact`, `collision_clearance`, or `global_envelope`. Use `scope` values `global`, `primary`, `contact`, and `anchor` to supply the four L1 gates. Express every fit-critical tolerance as the absolute `tolerance_abs` in `units`.

## `asset_manifest.json` (`AssetManifest`)

Require `spec_version`, `job_id`, and `assets`. Each asset requires:

- `asset_id`
- `role`: `fit_critical`, `visual_shell`, or `stage`
- `source`: `procedural`, `cad_sketcher`, `imported`, `tripo`, or `user`
- `target_dimensions`, `location`, `rotation_deg`: three-number vectors
- `anchors`: string array

`provenance` and `checksum` are optional schema fields, but complete provenance is required for L2. Tripo must remain a `visual_shell` and cannot provide fit-critical evidence.

Represent CAD intent only with asset `source: cad_sketcher`. Pass runtime `cad_available` to the planner; never encode a CAD selector in `SceneSpec`. The deterministic source routes are:

| Asset source | Planned step `tool` |
|---|---|
| `procedural` | `precision_create_part` |
| `imported`, `user` | `precision_import_asset` |
| `tripo` | `external_pending` |
| `cad_sketcher` with `cad_available: true` | `precision_create_cad_part` |
| `cad_sketcher` with `cad_available: false` | `backend_unavailable` |

Never silently replace an unavailable CAD route.

## `operation_plan.json` (`OperationPlan`)

Require `spec_version`, `job_id`, and `steps`. Each step requires `operation_id`, `tool`, `asset_id`, `params`, `preconditions`, `expected`, `rollback`, and `depends_on`. The four object fields are `params`, `preconditions`, `expected`, and `rollback`; `depends_on` is a string array.

Sort assets by stable `asset_id`, assign stable `operation_id` values, and honor dependencies. Execute registered typed tools only. Never embed Python, shell, expressions, Blender-console text, or other raw code. Apply corrections through named typed patch tools and re-inspect.

## `qa_report.json` (`QAReport`)

Required root fields are `spec_version`, `job_id`, `assertions`, `geometry`, `provenance`, `checkpoint`, `reasons`, `assumptions`, `artifacts`, and `final_grade` (`L0`, `L1`, or `L2`). `geometry`, `provenance`, and `checkpoint` are booleans; `reasons` and `assumptions` are string arrays.

Each assertion requires exactly `id`, `target`, `actual`, `absolute_error`, `relative_error`, `tolerance_abs`, `passed`, `required`, and `scope`. `relative_error` may be null for a zero target. Each artifact requires `path` and a 64-hex-character `sha256`.

## Input-insufficient L0

Encode uncalibrated input with `reference_calibrated: false`. Preserve the user's `requested_grade`, but validation must derive `final_grade: L0`. `measurements` may be empty when no calibrated target exists. Record missing dimensions, scale, camera calibration, or drawing data in QA `assumptions` and `reasons` and in `assumptions.md`. Do not invoke finalization or claim L2.

## Grade gates

- **L0:** Require when `reference_calibrated` is false or any L1 gate is missing or failed. Single or multiple uncalibrated views remain L0.
- **L1:** Require at least one passing assertion for each `global`, `primary`, `contact`, and `anchor` gate, and require every assertion contributing to those gates to pass. `kind: global_envelope` can supply the global gate; `kind: contact` can supply the contact gate.
- **L2:** Require L1, every required assertion passing, `geometry: true`, `checkpoint: true`, `provenance: true`, and an empty `assumptions` array.

Only `precision_validate_job` derives `final_grade`. `precision_finalize_job` commits only a strict L2 report with no failed required assertion.

## Evidence bundle

Preserve `scene_spec.json`, `asset_manifest.json`, `operation_plan.json`, and `qa_report.json`; `assumptions.md`; `checkpoints/before.blend` and either `checkpoints/failed.blend` or `checkpoints/final.blend`; and, for committed L2, `previews/orthographic.png` and `previews/perspective.png`. List final checkpoints/previews in QA `artifacts` with their SHA-256 digests. Seedance output and visual appearance are previews, never measurement authority.
