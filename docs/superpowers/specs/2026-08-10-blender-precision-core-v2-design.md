# Blender Precision Core V2 Design

Date: 2026-08-10  
Status: approved for implementation planning

## Summary

Upgrade `opcspace/blender-seedance-skills` from a first-stage primitive/CAD companion into a verifiable, commercially usable precision white-model core for dimension-driven architecture, mechanical assets, furniture and props.

The V2 workflow converts a user prompt or reference set into four machine-readable contracts, executes a job-scoped Blender transaction through typed MCP tools, compares declared targets with Blender measurements, and produces an evidence bundle. Blender is the required execution backend. CAD Sketcher remains an optional precision backend for constrained profiles. Tripo and Seedance remain optional adapters and cannot determine the precision grade.

## Chosen approach

Build a unified Precision Core V2 and add `blender-precision-modeling` as the authoritative precision Skill. Preserve the existing repository and existing Skill names as compatible entry points; route precision requests from those Skills into the new Skill and core.

This approach was chosen over incremental patches because V1 has authority split across five Skills and a companion whose specification, transaction and validation boundaries are not unified. It was chosen over a full external-service orchestrator because real Tripo and Seedance task automation is not required for the first precision release and would couple the core to credentials, quotas and changing third-party services.

## Confirmed scope

### In scope

- Dimension-driven architecture, mechanical assets, furniture and props.
- Prompt input, single reference images, multi-view references, dimensional drawings and imported GLB/FBX assets.
- A strict distinction between observed facts and inferred geometry.
- Project-specific units, required measurements and absolute tolerances.
- Parameterized Blender creation, CAD-constrained profiles where available, asset import, unit/axis normalization, naming, positioning, anchoring, parenting and targeted precision patches.
- Checkpoints, job-scoped transactions, deterministic QA, orthographic/perspective previews and evidence bundles.
- A provider-neutral optional adapter boundary for Tripo and Seedance.
- Compatibility routing from existing Skills.

### Out of scope for V2 phase one

- Real Tripo account/API job submission, polling or downloads.
- Real Seedance task submission or result downloads.
- Claiming millimeter accuracy from an uncalibrated single image.
- General high-fidelity character or creature reconstruction.
- Arbitrary Python execution through Blender MCP.
- A persistent distributed job service, database, account system or hosted API.

## Precision truth model

Precision is not inferred from a prompt, screenshot, provider name or render quality. Every required assertion must contain:

```text
target value + Blender-measured value + absolute tolerance + pass/fail result
```

The pass rule is:

```text
abs(actual - target) <= tolerance_abs
```

Relative error may be reported for context, but fit-critical measurements use an absolute tolerance in the current model unit.

Reference inputs follow these rules:

- Single and multi-view references are accepted.
- A reference must contain a known dimension, visible scale, calibrated camera, or dimensional drawing before it can support a precision grade.
- A reference without scale produces an approximate blockout and records its inferred geometry; it cannot produce an L1 or L2 result.
- Tripo output is a visual starting mesh. It must be imported, normalized and remeasured in Blender. It cannot independently satisfy a fit-critical assertion.

## Precision grades

### L0 — Blockout

- No reliable scale, or only uncalibrated visual inference.
- May communicate composition, silhouette and spatial intent.
- Must not be called high precision.

### L1 — Measured white model

- Global envelope, primary part dimensions, ground contact and declared key anchors pass their absolute tolerances.
- May contain simplified topology or unresolved non-critical visual details.

### L2 — High-precision editable model

- Every required measurement passes.
- Required anchors, contacts, gaps and collision rules pass.
- Geometry QA, checkpoint, provenance and unresolved-assumption checks pass.
- The final editable `.blend` and complete evidence bundle exist.

Any failed required assertion prevents L2. The job may preserve a failed checkpoint for correction, but the report must retain the failure.

## Architecture

### 1. `blender-precision-modeling` Skill

The new Skill is the only authoritative precision router. It:

1. Extracts known dimensions, reference calibration, constraints, required deliverables and assumptions.
2. Creates and validates `scene_spec.json` and `asset_manifest.json`.
3. Assigns each asset to a deterministic Blender/CAD route or an optional visual-shell adapter.
4. Creates `operation_plan.json`.
5. Executes the plan through Precision MCP.
6. Reads `qa_report.json` and reports the grade without upgrading it.

Existing Skills remain discoverable:

- `blender-modeling` delegates dimension-driven requests to `blender-precision-modeling`.
- `blender-base-mesh-library` delegates L1/L2 requests to `blender-precision-modeling` and keeps non-precision library guidance.
- `blender-white-model-render` consumes a committed job and does not modify its precision grade.
- `seedance-white-model-video` consumes a QA-approved preview and remains an external handoff.
- `blender-seedance-modeling` remains the broad top-level router.

### 2. Precision Core

The Python core is Blender-independent and owns:

- schema validation;
- unit and coordinate normalization rules;
- deterministic operation planning;
- measurement assertion evaluation;
- job state transitions;
- evidence report generation;
- adapter interfaces.

The core is the only component allowed to issue a final precision grade.

### 3. Precision MCP server

The FastMCP server exposes typed tools and converts tool calls into framed requests for the Blender add-on. It owns path allow-listing, request validation, timeouts, error normalization and job identifiers. It exposes no arbitrary code execution tool.

### 4. Blender add-on

The add-on executes allow-listed Blender operations on Blender's main thread. It owns object creation/import, transforms, geometry queries, checkpoints, rendering and export. It returns raw measurements and operation results; it does not decide the commercial precision grade.

### 5. Optional adapters

- CAD Sketcher handles constrained 2D profiles and solver-backed geometry when installed.
- Tripo may later create `visual_shell` assets. Phase one defines the interface and validates imported GLB/FBX fixtures only.
- Seedance consumes committed white-model previews after QA. It never participates in geometry validation.

## Repository structure

Keep the existing `precision-mcp/` path for compatibility and evolve it into:

```text
skills/
└── blender-precision-modeling/
    ├── SKILL.md
    ├── agents/openai.yaml
    └── references/
        ├── precision-contract.md
        └── reference-calibration.md

precision-mcp/
├── schemas/
│   ├── scene_spec.schema.json
│   ├── asset_manifest.schema.json
│   ├── operation_plan.schema.json
│   └── qa_report.schema.json
├── precision_mcp/
│   ├── server.py
│   ├── contracts.py
│   ├── planner.py
│   ├── measurements.py
│   ├── evidence.py
│   ├── transport.py
│   └── adapters/
│       ├── base.py
│       ├── blender.py
│       ├── cad_sketcher.py
│       ├── tripo.py
│       └── seedance.py
└── blender_addon/
    └── precision_addon.py
```

Adapter modules for Tripo and Seedance contain interfaces and explicit unavailable states in phase one; they do not contain guessed endpoints or model IDs.

## Machine-readable contracts

All contracts include `spec_version` and `job_id`. Schema and Python validation must enforce the same rules.

### `scene_spec.json`

Required concepts:

- category and requested deliverable grade;
- `units` and Blender Z-up/right-handed canonical coordinate system;
- global target envelope;
- reference inputs, view types and calibration facts;
- observed geometry separated from inferred geometry;
- required measurements with stable IDs, targets and absolute tolerances;
- required contacts, gaps and collision rules;
- unresolved assumptions.

### `asset_manifest.json`

Each asset includes:

- stable `asset_id`, display name and Blender object prefix;
- role: `fit_critical`, `visual_shell` or `stage`;
- source: procedural, CAD Sketcher, imported, Tripo or user-supplied;
- target dimensions and canonical transform;
- anchor definitions and parent relationships;
- expected contacts and clearances;
- source file checksum and license/provenance note when imported;
- reference confidence and associated observations/inferences.

### `operation_plan.json`

Each step includes:

- stable operation ID;
- typed tool name and validated parameters;
- job and asset scope;
- preconditions;
- expected measurable result;
- rollback behavior;
- dependent operations.

The planner must produce deterministic output for identical normalized inputs.

### `qa_report.json`

The report includes:

- target, actual, signed/absolute error, tolerance and pass/fail for every measurement;
- global and per-asset bounds;
- contact, gap and collision results;
- non-manifold, degenerate-face, invalid-normal and unapplied-scale results;
- reference calibration and confidence status;
- unresolved assumptions;
- artifact paths and checksums;
- final L0/L1/L2 grade with explicit downgrade reasons.

## End-to-end data flow

1. Accept prompt and references.
2. Separate observed facts, supplied dimensions and inferred geometry.
3. Validate `scene_spec.json`. Invalid input stops before Blender mutation.
4. Build `asset_manifest.json` and classify fit-critical versus visual-shell assets.
5. Build deterministic `operation_plan.json`.
6. Start a Blender job and save `before.blend`.
7. Create or import each asset into the job namespace.
8. Normalize units, source axes, transforms, origins, names and provenance.
9. Assemble by explicit transforms and anchors.
10. Measure, compare and apply targeted patches by `asset_id` or `feature_id`.
11. Run full geometry, assembly and reference QA.
12. Save `final.blend`, previews and `qa_report.json`.
13. Commit the job or preserve a failed checkpoint without issuing L2.
14. Optionally hand a committed preview to Seedance.

## Typed Blender tool families

### Specification and transactions

- load validated job contracts;
- begin job;
- save checkpoint;
- commit job;
- abort and restore job.

### Precision creation

- native primitives with exact dimensions;
- profile extrusion;
- holes/cuts and controlled booleans;
- arrays and repeated modules;
- CAD Sketcher constraint operations when available.

### Asset intake

- import GLB/FBX;
- detect or accept source units;
- normalize axes;
- apply transforms;
- set origin and stable names;
- attach provenance metadata.

### Assembly and patching

- set canonical transform;
- define and align anchors;
- set parent relationships;
- patch a named dimension or feature without rebuilding unrelated objects.

### Measurement and QA

- measure world bounds and distances;
- measure anchor/contact/gap relationships;
- detect collisions;
- inspect topology, normals, degeneracy and transforms;
- validate only the current job, then run a full final scene check.

### Presentation and export

- frame aggregate job bounds, not one object;
- render orthographic and perspective previews;
- save `.blend` checkpoints;
- export approved assets.

## Transaction model

Every job has a stable `job_id`. Owned collections, objects and files are scoped to that ID. Beginning a job never deletes unrelated objects. Operations are idempotent where practical: re-running an operation updates or verifies its named target instead of creating a duplicate.

The states are:

```text
planned -> active -> validating -> committed
                    -> failed_qa
         -> aborted
         -> external_pending / external_failed
```

`abort_job` restores the saved checkpoint when available. If checkpoint restore is impossible, it removes only objects created by the job and reports that pre-existing edits could not be restored. The Skill must not claim rollback succeeded when it did not.

## Transport and main-thread safety

Replace the current ambiguous socket lifecycle with a documented framed protocol containing request length, request ID, command and parameters. Phase one should use one local connection per MCP tool call; the overhead is negligible and it avoids stale half-closed connections. Both sides must support partial reads, maximum message size, timeout and structured errors.

The socket listener receives and validates frames off the Blender main thread. Blender operations run through a main-thread queue/timer. The main thread must not block while waiting for an incomplete client payload.

## Error handling and degradation

- Invalid contract: return field-level errors and do not modify Blender.
- Blender operation failure: record the operation ID, abort the job and restore the checkpoint.
- QA failure: save `failed.blend` and the failed report; do not issue L2.
- Uncalibrated references: continue as L0 and list all inferences.
- Optional adapter failure: mark `external_pending` or `external_failed`; preserve the committed Blender result.
- Unsafe path or unknown command: reject before Blender execution.
- Imported asset without provenance: allow L0/L1 editing but prevent L2 until provenance is recorded.

## Security boundaries

- Bind locally by default.
- Expose typed allow-listed tools only.
- Reject work paths outside `PRECISION_WORKDIR` on both the MCP server and add-on sides.
- Enforce request size, timeout and supported file extensions.
- Never log credentials or reference contents unnecessarily.
- Do not guess Tripo/Seedance endpoints, model IDs or credentials.

## Evidence bundle

Each job produces:

```text
evidence/<job_id>/
├── scene_spec.json
├── asset_manifest.json
├── operation_plan.json
├── qa_report.json
├── assumptions.md
├── checkpoints/
│   ├── before.blend
│   ├── failed.blend        # only when applicable
│   └── final.blend         # committed jobs
└── previews/
    ├── orthographic.png
    └── perspective.png
```

The report records file checksums so a reviewer can determine which files were measured.

## Test strategy

### Schema and core tests

- JSON Schema and Python validation parity.
- Unit and coordinate conversion.
- Absolute tolerance evaluation.
- Deterministic planner output.
- Precision grade and downgrade reasons.
- Uncalibrated single-image input producing L0.

### Transport and security tests

- Real FastMCP entry point through the framed bridge, using a deterministic fake Blender peer.
- Multiple sequential tool calls.
- Partial frames, disconnects, timeouts and malformed/oversized requests.
- Unknown commands and path traversal.
- No arbitrary code execution tool.

### Real Blender GUI integration tests

Run through the actual Precision MCP server and Blender add-on, not a direct socket-only test. Verify:

- GLB and FBX intake;
- unit and axis normalization;
- parameterized creation and CAD status;
- checkpoint, failed transaction and abort restore;
- targeted patch and remeasurement;
- aggregate scene framing and Workbench rendering;
- final evidence bundle.

### End-to-end acceptance fixtures

1. Architecture: wall, dimensional opening, repeated module and stair/level relationship.
2. Mechanical: enclosure, panel, hole locations and specified clearances.
3. Furniture: table or chair components, leg anchors, symmetry and ground contact.
4. Prop: handled tool or container, explicit orientation, import normalization and targeted modification.

Negative cases include an unscaled single image, an imported mesh with incorrect units, a failed required dimension, a path escape and a dropped Blender connection.

## Release gates

- All Skills pass `quick_validate.py` and have matching `agents/openai.yaml` metadata.
- Core, schema, transport and security tests pass in CI.
- Four real Blender GUI fixtures pass through the full MCP path.
- Each real fixture contains contracts, report, `.blend` checkpoint and previews.
- No test or runtime file contains a hard-coded developer home path.
- README and commercial policy claim only evidence-backed capabilities.

## Migration sequence

1. Capture V1 behavior and add failing regression tests for the known issues.
2. Add the four schemas, contract validator, planner and evidence builder.
3. Replace the transport and implement job-scoped transactions.
4. Implement precise creation, intake, normalization, assembly, measurement and patch tools.
5. Add `blender-precision-modeling` and update existing Skills to delegate precision requests.
6. Add metadata, installation configuration and compatibility documentation.
7. Run the four Blender GUI acceptance fixtures.
8. Update capability claims only after the evidence is committed.

## V1 issues that the implementation must close

- The MCP bridge retains a socket while the Blender add-on closes each connection after one response.
- `precision_validate_scene` accepts a tolerance but does not compare target dimensions with actual dimensions.
- Top-level `model_spec.dimensions` does not participate in aggregate scene validation.
- Transaction prefixes, created object names and whole-scene `PRECISION_` queries do not share one authoritative job scope.
- Existing socket tests create a new direct connection for every request, bypass the FastMCP path and include hard-coded local paths.
- Current category tests prove routing and primitive creation, not finished precision assets.
- Camera framing uses one object, computes distance before applying the requested lens, and does not validate aggregate framing.

## Open risks accepted for phase one

- CAD Sketcher remains an external dependency with separate licensing and version compatibility.
- Real Blender GUI tests may require a local machine until a reliable graphical CI runner is available.
- Imported visual meshes may need manual topology repair; the report must expose this rather than hiding it.
- Reference-image silhouette comparison can indicate visual agreement but cannot replace dimensional calibration.
- Tripo and Seedance online integration is deferred; adapter contracts must remain stable enough for a later implementation.

## Acceptance criteria

The design is implemented when a user can supply a calibrated prompt/reference brief for one of the four scoped asset classes, receive validated contracts, run a job through Precision MCP and Blender, make a named precision patch, rerun QA, and receive a reproducible L0/L1/L2 evidence bundle. A failed required measurement must prevent L2, and the same core workflow must succeed without Tripo or Seedance credentials.

## Next skill

Use `$superpower-writing-plans` after the user reviews this committed specification.
