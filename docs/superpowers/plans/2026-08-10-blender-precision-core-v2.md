# Blender Precision Core V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use $superpower-subagents (recommended) or $superpower-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking via update_plan.

**Goal:** Build a verifiable Precision Core V2 that turns calibrated prompts/references into job-scoped Blender models, absolute-tolerance QA, and reproducible L0/L1/L2 evidence bundles.

**Architecture:** Add a Blender-independent contract/planning/measurement/evidence core behind the existing FastMCP server, replace the mismatched socket lifecycle with one framed connection per call, and make the Blender add-on execute only allow-listed job-scoped operations. Add one authoritative `blender-precision-modeling` Skill while keeping the existing five Skills as compatible entry points; Tripo and Seedance are unavailable-by-default adapters in phase one.

**Tech Stack:** Python 3.10+, standard library dataclasses/socket/pathlib, `jsonschema`, FastMCP, Blender 5.2 Python API, CAD Sketcher optional adapter, `unittest`, JSON Schema Draft 2020-12.

---

## File map

### Create

- `precision-mcp/schemas/scene_spec.schema.json` — calibrated input and required measurement contract.
- `precision-mcp/schemas/asset_manifest.schema.json` — asset roles, transforms, anchors and provenance.
- `precision-mcp/schemas/operation_plan.schema.json` — deterministic typed operation contract.
- `precision-mcp/schemas/qa_report.schema.json` — measured assertions, geometry gates and grade.
- `precision-mcp/precision_mcp/contracts.py` — schema loading and parity validation.
- `precision-mcp/precision_mcp/measurements.py` — absolute-tolerance evaluation and L0/L1/L2 grading.
- `precision-mcp/precision_mcp/planner.py` — deterministic backend/operation planning.
- `precision-mcp/precision_mcp/evidence.py` — evidence directories, canonical JSON and checksums.
- `precision-mcp/precision_mcp/transport.py` — framed one-request-per-connection Blender bridge.
- `precision-mcp/precision_mcp/adapters/__init__.py` — adapter exports.
- `precision-mcp/precision_mcp/adapters/base.py` — adapter protocol and result types.
- `precision-mcp/precision_mcp/adapters/blender.py` — required backend availability contract.
- `precision-mcp/precision_mcp/adapters/cad_sketcher.py` — optional CAD route contract.
- `precision-mcp/precision_mcp/adapters/tripo.py` — explicit unavailable phase-one adapter.
- `precision-mcp/precision_mcp/adapters/seedance.py` — explicit unavailable phase-one adapter.
- `skills/blender-precision-modeling/SKILL.md` — authoritative precision workflow.
- `skills/blender-precision-modeling/agents/openai.yaml` — authoritative precision entry metadata.
- `skills/blender-modeling/agents/openai.yaml` — compatible modeling entry metadata.
- `skills/blender-base-mesh-library/agents/openai.yaml` — compatible BaseMesh entry metadata.
- `skills/blender-seedance-modeling/agents/openai.yaml` — broad router metadata.
- `skills/blender-white-model-render/agents/openai.yaml` — render entry metadata.
- `skills/seedance-white-model-video/agents/openai.yaml` — video handoff metadata.
- `skills/blender-precision-modeling/references/precision-contract.md` — contract field guide.
- `skills/blender-precision-modeling/references/reference-calibration.md` — calibrated-reference rules.
- `tests/test_precision_contracts.py` — schema and Python-validation parity.
- `tests/test_precision_measurements.py` — absolute-error and grade tests.
- `tests/test_precision_planner.py` — deterministic route/operation tests.
- `tests/test_precision_evidence.py` — canonical bundle and checksum tests.
- `tests/test_precision_transport.py` — partial-frame, sequential-call and error tests.
- `tests/test_precision_server_v2.py` — FastMCP-facing V2 tool tests with a fake bridge.
- `tests/test_precision_addon_source.py` — allow-list and unsafe-path source guards.
- `tests/fixtures/precision_v2/*.json` — architecture, mechanical, furniture and prop contracts.
- `tests/precision_v2_gui_test.py` — portable real-Blender end-to-end runner.

### Modify

- `precision-mcp/pyproject.toml` — add `jsonschema` and test dependency metadata.
- `precision-mcp/precision_mcp/server.py` — V2 tools, contract/core integration and compatibility wrappers.
- `precision-mcp/precision_mcp/spec.py` — retain V1 compatibility while delegating measurement logic.
- `precision-mcp/blender_addon/precision_addon.py` — framed transport, job transactions, import/assembly/QA/render commands.
- `skills/blender-modeling/SKILL.md` — delegate calibrated precision requests.
- `skills/blender-base-mesh-library/SKILL.md` — delegate L1/L2 requests.
- `skills/blender-seedance-modeling/SKILL.md` — add the V2 route.
- `skills/blender-white-model-render/SKILL.md` — require a committed job for precision claims.
- `skills/seedance-white-model-video/SKILL.md` — consume QA-approved previews only.
- `.github/workflows/precision-mcp.yml` — install dependencies and run the full portable suite.
- `README.md`, `precision-mcp/README.md`, `COMMERCIAL_USE.md`, `tests/PRECISION_MCP.md` — installation, evidence and claim boundaries.

---

### Task 1: Lock the V1 failures with regression tests

**Files:**
- Create: `tests/test_precision_transport.py`
- Create: `tests/test_precision_measurements.py`

- [ ] **Step 1: Write a failing sequential transport test**

Create a local fake Blender peer that accepts two independent framed connections and assert the future `BlenderBridge` succeeds twice:

```python
import json
import socket
import struct
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.transport import BlenderBridge


def recv_exact(sock, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class TwoCallPeer:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(2)
        self.port = self.listener.getsockname()[1]

    def run(self):
        for index in range(2):
            client, _ = self.listener.accept()
            with client:
                size = struct.unpack("!I", recv_exact(client, 4))[0]
                request = json.loads(recv_exact(client, size))
                response = json.dumps({"status": "success", "request_id": request["request_id"], "result": {"index": index}}).encode()
                client.sendall(struct.pack("!I", len(response)) + response)
        self.listener.close()


class PrecisionTransportTests(unittest.TestCase):
    def test_bridge_opens_a_fresh_connection_for_each_call(self):
        peer = TwoCallPeer()
        thread = threading.Thread(target=peer.run, daemon=True)
        thread.start()
        bridge = BlenderBridge("127.0.0.1", peer.port, timeout=1)
        self.assertEqual(bridge.call("ping")["index"], 0)
        self.assertEqual(bridge.call("ping")["index"], 1)
        thread.join(timeout=1)
```

- [ ] **Step 2: Write failing absolute-tolerance tests**

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.measurements import evaluate_assertion


class PrecisionMeasurementTests(unittest.TestCase):
    def test_absolute_tolerance_passes_at_boundary(self):
        result = evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": 0.5, "required": True}, 1000.5)
        self.assertTrue(result["passed"])
        self.assertEqual(result["absolute_error"], 0.5)

    def test_absolute_tolerance_rejects_large_error(self):
        result = evaluate_assertion({"id": "width", "target": 1000.0, "tolerance_abs": 0.5, "required": True}, 1000.51)
        self.assertFalse(result["passed"])
```

- [ ] **Step 3: Run the two tests and verify they fail for missing modules**

Run:

```bash
python -m unittest tests.test_precision_transport tests.test_precision_measurements -v
```

Expected: both modules fail to import because `precision_mcp.transport` and `precision_mcp.measurements` do not exist.

- [ ] **Step 4: Verify the untouched V1 baseline remains green**

Run:

```bash
python -m unittest discover -s tests -p 'test_precision_spec.py' -v
```

Expected: the existing three V1 specification tests pass.

- [ ] **Step 5: Keep the two red tests uncommitted until their green tasks**

Do not add either file to Task 2 commits. Task 3 implements and commits `test_precision_measurements.py`; Task 6 implements and commits `test_precision_transport.py`. This preserves the red-green sequence without creating a commit that intentionally breaks CI.

---

### Task 2: Add versioned contract schemas and parity validation

**Files:**
- Create: `precision-mcp/schemas/scene_spec.schema.json`
- Create: `precision-mcp/schemas/asset_manifest.schema.json`
- Create: `precision-mcp/schemas/operation_plan.schema.json`
- Create: `precision-mcp/schemas/qa_report.schema.json`
- Create: `precision-mcp/precision_mcp/contracts.py`
- Create: `tests/test_precision_contracts.py`
- Modify: `precision-mcp/pyproject.toml`

- [ ] **Step 1: Write failing contract tests**

Use one compact valid document per schema and assert field-level errors:

```python
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.contracts import ContractError, validate_document


SCENE = {
    "spec_version": "2.0",
    "job_id": "desk-001",
    "category": "furniture",
    "requested_grade": "L2",
    "units": "mm",
    "coordinate_system": {"up": "Z", "handedness": "right"},
    "reference_calibrated": True,
    "measurements": [{"id": "overall_width", "kind": "dimension", "asset_id": "desk", "axis": "X", "target": 1200.0, "tolerance_abs": 1.0, "required": True, "scope": "global"}],
}

MANIFEST = {
    "spec_version": "2.0",
    "job_id": "desk-001",
    "assets": [{"asset_id": "desk", "role": "fit_critical", "source": "procedural", "target_dimensions": [1200.0, 600.0, 750.0], "location": [0, 0, 375], "rotation_deg": [0, 0, 0], "anchors": []}],
}


class PrecisionContractTests(unittest.TestCase):
    def test_valid_scene_and_manifest(self):
        validate_document("scene_spec", SCENE)
        validate_document("asset_manifest", MANIFEST)

    def test_missing_tolerance_reports_json_path(self):
        invalid = copy.deepcopy(SCENE)
        del invalid["measurements"][0]["tolerance_abs"]
        with self.assertRaisesRegex(ContractError, r"measurements/0.*tolerance_abs"):
            validate_document("scene_spec", invalid)

    def test_job_ids_must_match(self):
        invalid = copy.deepcopy(MANIFEST)
        invalid["job_id"] = "other"
        with self.assertRaisesRegex(ContractError, "job_id mismatch"):
            validate_document("asset_manifest", invalid, expected_job_id=SCENE["job_id"])
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m unittest tests.test_precision_contracts -v`  
Expected: FAIL because `precision_mcp.contracts` does not exist.

- [ ] **Step 3: Create the four Draft 2020-12 schemas**

Use these shared invariants in all four JSON files:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["spec_version", "job_id"],
  "properties": {
    "spec_version": {"const": "2.0"},
    "job_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{0,63}$"}
  },
  "additionalProperties": false
}
```

Extend `scene_spec` with the exact fields used by `SCENE`, units enum `mm|cm|m`, category enum `architecture|mechanical|furniture|props`, and measurement kind enum `dimension|distance|gap|contact|collision_clearance|global_envelope`. Extend `asset_manifest` with the exact fields used by `MANIFEST`, role enum `fit_critical|visual_shell|stage`, source enum `procedural|cad_sketcher|imported|tripo|user`, optional provenance/checksum fields, and three-number arrays for dimensions/transforms. Define `operation_plan` steps with `operation_id`, `tool`, `asset_id`, `params`, `preconditions`, `expected`, `rollback`, and `depends_on`. Define `qa_report` with assertion fields `id`, `target`, `actual`, `absolute_error`, `relative_error`, `tolerance_abs`, `passed`, `required`, and `scope`; geometry/provenance/checkpoint booleans; downgrade `reasons`; unresolved `assumptions`; artifact `path`/`sha256` entries; and final grade enum `L0|L1|L2`.

- [ ] **Step 4: Implement schema loading and validation**

```python
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).parents[1] / "schemas"
SCHEMA_NAMES = {"scene_spec", "asset_manifest", "operation_plan", "qa_report"}


class ContractError(ValueError):
    pass


@lru_cache(maxsize=4)
def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise ContractError(f"unknown contract: {name}")
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def validate_document(name: str, document: dict[str, Any], expected_job_id: str | None = None) -> None:
    if expected_job_id is not None and document.get("job_id") != expected_job_id:
        raise ContractError(f"job_id mismatch: expected {expected_job_id}")
    errors = sorted(Draft202012Validator(load_schema(name)).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        path = "/".join(str(part) for part in error.absolute_path) or "$"
        raise ContractError(f"{path}: {error.message}")
```

- [ ] **Step 5: Add `jsonschema` to project dependencies and run tests**

Add `"jsonschema>=4.23,<5"` to `dependencies`, then run:

```bash
python -m unittest tests.test_precision_contracts -v
python -c "import json, glob; [json.load(open(path)) for path in glob.glob('precision-mcp/schemas/*.json')]; print('schemas: OK')"
```

Expected: all contract tests pass and `schemas: OK` prints.

- [ ] **Step 6: Commit**

```bash
git add precision-mcp/schemas precision-mcp/precision_mcp/contracts.py precision-mcp/pyproject.toml tests/test_precision_contracts.py
git commit -m "feat: add precision v2 contracts"
```

---

### Task 3: Implement absolute measurement evaluation and grading

**Files:**
- Create: `precision-mcp/precision_mcp/measurements.py`
- Modify: `tests/test_precision_measurements.py`
- Modify: `precision-mcp/precision_mcp/spec.py`

- [ ] **Step 1: Extend failing tests for downgrade rules**

```python
from precision_mcp.measurements import derive_grade, evaluate_assertion


def passing(scope="global"):
    return {"id": scope, "scope": scope, "target": 10.0, "actual": 10.0, "absolute_error": 0.0, "tolerance_abs": 0.1, "required": True, "passed": True}


class PrecisionGradeTests(unittest.TestCase):
    def test_uncalibrated_reference_is_l0(self):
        self.assertEqual(derive_grade(False, [passing()], True, True, True)["grade"], "L0")

    def test_primary_measurements_can_issue_l1(self):
        result = derive_grade(True, [passing("global"), passing("primary")], False, True, True)
        self.assertEqual(result["grade"], "L1")

    def test_all_required_gates_issue_l2(self):
        result = derive_grade(True, [passing("global"), passing("fit")], True, True, True)
        self.assertEqual(result["grade"], "L2")

    def test_failed_required_measurement_prevents_l2(self):
        failed = {**passing("fit"), "passed": False, "absolute_error": 0.2}
        result = derive_grade(True, [passing(), failed], True, True, True)
        self.assertNotEqual(result["grade"], "L2")
        self.assertIn("failed required measurement: fit", result["reasons"])
```

- [ ] **Step 2: Run the tests and verify grade tests fail**

Run: `python -m unittest tests.test_precision_measurements -v`  
Expected: the boundary tests may import, but grade tests fail because `derive_grade` is missing.

- [ ] **Step 3: Implement measurements and grading**

```python
from __future__ import annotations

from typing import Any


def evaluate_assertion(assertion: dict[str, Any], actual: float) -> dict[str, Any]:
    target = float(assertion["target"])
    tolerance = float(assertion["tolerance_abs"])
    if tolerance < 0:
        raise ValueError("tolerance_abs must be non-negative")
    error = abs(float(actual) - target)
    relative = error / abs(target) if target else None
    return {**assertion, "actual": float(actual), "absolute_error": error, "relative_error": relative, "passed": error <= tolerance}


def derive_grade(reference_calibrated: bool, assertions: list[dict[str, Any]], geometry_ok: bool, checkpoint_ok: bool, provenance_ok: bool) -> dict[str, Any]:
    reasons: list[str] = []
    if not reference_calibrated:
        return {"grade": "L0", "reasons": ["reference is not calibrated"]}
    failed_required = [item for item in assertions if item.get("required") and not item.get("passed")]
    reasons.extend(f"failed required measurement: {item['id']}" for item in failed_required)
    primary = [item for item in assertions if item.get("scope") in {"global", "primary", "anchor"}]
    l1_ok = bool(primary) and all(item.get("passed") for item in primary)
    l2_ok = not failed_required and bool(assertions) and geometry_ok and checkpoint_ok and provenance_ok
    if l2_ok:
        return {"grade": "L2", "reasons": []}
    if not geometry_ok:
        reasons.append("geometry QA failed")
    if not checkpoint_ok:
        reasons.append("final checkpoint missing")
    if not provenance_ok:
        reasons.append("asset provenance incomplete")
    return {"grade": "L1" if l1_ok else "L0", "reasons": reasons}
```

- [ ] **Step 4: Delegate V1 relative checks without changing their public behavior**

Keep `check_measurement(actual, expected, tolerance)` for compatibility, but implement it as a loop that emits the same V1 result shape. Do not use it for V2 grading. Add a module docstring explaining that V1 uses relative tolerance and V2 uses `evaluate_assertion` with absolute tolerance.

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.test_precision_measurements tests.test_precision_spec -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add precision-mcp/precision_mcp/measurements.py precision-mcp/precision_mcp/spec.py tests/test_precision_measurements.py
git commit -m "feat: grade absolute precision evidence"
```

---

### Task 4: Add deterministic planning and explicit adapter boundaries

**Files:**
- Create: `precision-mcp/precision_mcp/planner.py`
- Create: `precision-mcp/precision_mcp/adapters/__init__.py`
- Create: `precision-mcp/precision_mcp/adapters/base.py`
- Create: `precision-mcp/precision_mcp/adapters/blender.py`
- Create: `precision-mcp/precision_mcp/adapters/cad_sketcher.py`
- Create: `precision-mcp/precision_mcp/adapters/tripo.py`
- Create: `precision-mcp/precision_mcp/adapters/seedance.py`
- Create: `tests/test_precision_planner.py`

- [ ] **Step 1: Write failing deterministic-route tests**

```python
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.planner import build_plan


class PrecisionPlannerTests(unittest.TestCase):
    def test_fit_critical_assets_use_blender(self):
        scene = {"spec_version": "2.0", "job_id": "fixture-1"}
        manifest = {"spec_version": "2.0", "job_id": "fixture-1", "assets": [{"asset_id": "panel", "role": "fit_critical", "source": "procedural"}]}
        plan = build_plan(scene, manifest, cad_available=False)
        self.assertEqual(plan["steps"][0]["tool"], "precision_create_part")

    def test_visual_shell_tripo_is_external_pending(self):
        scene = {"spec_version": "2.0", "job_id": "fixture-1"}
        manifest = {"spec_version": "2.0", "job_id": "fixture-1", "assets": [{"asset_id": "ornament", "role": "visual_shell", "source": "tripo"}]}
        plan = build_plan(scene, manifest, cad_available=False)
        self.assertEqual(plan["steps"][0]["tool"], "external_pending")

    def test_cad_request_does_not_silently_fall_back(self):
        scene = {"spec_version": "2.0", "job_id": "fixture-1"}
        manifest = {"spec_version": "2.0", "job_id": "fixture-1", "assets": [{"asset_id": "profile", "role": "fit_critical", "source": "cad_sketcher"}]}
        plan = build_plan(scene, manifest, cad_available=False)
        self.assertEqual(plan["steps"][0]["tool"], "backend_unavailable")

    def test_asset_order_does_not_change_plan(self):
        scene = {"spec_version": "2.0", "job_id": "fixture-1"}
        assets = [{"asset_id": "b", "role": "fit_critical", "source": "procedural"}, {"asset_id": "a", "role": "fit_critical", "source": "procedural"}]
        first = build_plan(scene, {"spec_version": "2.0", "job_id": "fixture-1", "assets": assets}, False)
        second = build_plan(scene, {"spec_version": "2.0", "job_id": "fixture-1", "assets": list(reversed(assets))}, False)
        self.assertEqual(first, second)
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_precision_planner -v`  
Expected: FAIL because `precision_mcp.planner` does not exist.

- [ ] **Step 3: Implement adapter result types and unavailable adapters**

```python
# adapters/base.py
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterStatus:
    available: bool
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AssetAdapter(Protocol):
    name: str
    def status(self) -> AdapterStatus: ...
```

`TripoAdapter.status()` and `SeedanceAdapter.status()` return `AdapterStatus(False, "online integration is deferred in Precision Core V2 phase one")`. `BlenderAdapter.status()` returns available. `CadSketcherAdapter` accepts an injected runtime status and reports it without guessing.

- [ ] **Step 4: Implement deterministic planning**

```python
from __future__ import annotations

from typing import Any


def build_plan(scene_spec: dict[str, Any], manifest: dict[str, Any], cad_available: bool) -> dict[str, Any]:
    job_id = scene_spec["job_id"]
    if manifest["job_id"] != job_id:
        raise ValueError("job_id mismatch")
    steps = []
    for index, asset in enumerate(sorted(manifest["assets"], key=lambda item: item["asset_id"])):
        source = asset["source"]
        if source == "tripo":
            tool = "external_pending"
        elif source == "cad_sketcher":
            tool = "precision_create_cad_part" if cad_available else "backend_unavailable"
        elif source in {"imported", "user"}:
            tool = "precision_import_asset"
        else:
            tool = "precision_create_part"
        steps.append({"operation_id": f"{index + 1:03d}-{asset['asset_id']}", "tool": tool, "asset_id": asset["asset_id"], "params": asset, "preconditions": [], "expected": {"asset_id": asset["asset_id"]}, "rollback": "remove_job_asset", "depends_on": []})
    return {"spec_version": "2.0", "job_id": job_id, "steps": steps}
```

- [ ] **Step 5: Run tests and commit**

```bash
python -m unittest tests.test_precision_planner -v
git add precision-mcp/precision_mcp/planner.py precision-mcp/precision_mcp/adapters tests/test_precision_planner.py
git commit -m "feat: plan precision backend operations"
```

Expected: planner tests pass.

---

### Task 5: Build canonical evidence bundles and job states

**Files:**
- Create: `precision-mcp/precision_mcp/evidence.py`
- Create: `tests/test_precision_evidence.py`

- [ ] **Step 1: Write failing evidence tests**

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.evidence import EvidenceBundle, JobState


class PrecisionEvidenceTests(unittest.TestCase):
    def test_bundle_writes_canonical_json_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = EvidenceBundle(Path(directory), "desk-001")
            path = bundle.write_contract("scene_spec", {"b": 2, "a": 1})
            self.assertEqual(path.read_text(), '{\n  "a": 1,\n  "b": 2\n}\n')
            self.assertEqual(len(bundle.sha256(path)), 64)

    def test_invalid_state_transition_is_rejected(self):
        state = JobState("desk-001")
        with self.assertRaisesRegex(ValueError, "planned -> committed"):
            state.transition("committed")

    def test_bundle_writes_assumptions(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = EvidenceBundle(Path(directory), "desk-001")
            path = bundle.write_assumptions(["hidden rear fasteners inferred from the front view"])
            self.assertIn("hidden rear fasteners", path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_precision_evidence -v`  
Expected: FAIL because `precision_mcp.evidence` does not exist.

- [ ] **Step 3: Implement canonical writes, checksums and transitions**

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TRANSITIONS = {
    "planned": {"active", "aborted"},
    "active": {"validating", "aborted", "external_pending", "external_failed"},
    "validating": {"committed", "failed_qa", "aborted"},
    "external_pending": {"active", "external_failed", "aborted"},
    "external_failed": {"active", "aborted"},
    "failed_qa": {"active", "aborted"},
    "committed": set(),
    "aborted": set(),
}


@dataclass
class JobState:
    job_id: str
    value: str = "planned"

    def transition(self, target: str) -> None:
        if target not in TRANSITIONS[self.value]:
            raise ValueError(f"invalid transition: {self.value} -> {target}")
        self.value = target


class EvidenceBundle:
    def __init__(self, workdir: Path, job_id: str):
        self.root = workdir.resolve() / "evidence" / job_id
        self.root.mkdir(parents=True, exist_ok=True)

    def write_contract(self, name: str, document: dict[str, Any]) -> Path:
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def write_assumptions(self, assumptions: list[str]) -> Path:
        path = self.root / "assumptions.md"
        body = "# Unresolved assumptions\n\n" + "".join(f"- {item}\n" for item in assumptions)
        path.write_text(body, encoding="utf-8")
        return path

    @staticmethod
    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
```

- [ ] **Step 4: Add directory helpers**

Add `checkpoint_path(name)` restricted to `before|failed|final` and `preview_path(name)` restricted to `orthographic|perspective`. Validate the resolved child remains inside `self.root` before returning it.

- [ ] **Step 5: Run tests and commit**

```bash
python -m unittest tests.test_precision_evidence -v
git add precision-mcp/precision_mcp/evidence.py tests/test_precision_evidence.py
git commit -m "feat: build precision evidence bundles"
```

---

### Task 6: Replace the broken socket lifecycle with framed transport

**Files:**
- Create: `precision-mcp/precision_mcp/transport.py`
- Modify: `tests/test_precision_transport.py`
- Modify: `precision-mcp/precision_mcp/server.py`

- [ ] **Step 1: Add failing partial-frame and error tests**

Add tests that send the four-byte header and JSON payload in multiple chunks, reject a declared size over `MAX_MESSAGE_BYTES`, and verify a response with a mismatched `request_id` raises `BridgeProtocolError`.

```python
def test_oversized_frame_is_rejected(self):
    bridge = BlenderBridge("127.0.0.1", 9, max_message_bytes=8)
    with self.assertRaisesRegex(ValueError, "max_message_bytes"):
        bridge._encode({"payload": "too large"})
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_precision_transport -v`  
Expected: FAIL because the transport module is still missing.

- [ ] **Step 3: Implement one-connection-per-call framed transport**

```python
from __future__ import annotations

import json
import socket
import struct
import uuid
from typing import Any

MAX_MESSAGE_BYTES = 4 * 1024 * 1024


class BridgeProtocolError(RuntimeError):
    pass


def read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("Blender bridge closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class BlenderBridge:
    def __init__(self, host: str, port: int, timeout: float = 180, max_message_bytes: int = MAX_MESSAGE_BYTES):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_message_bytes = max_message_bytes

    def _encode(self, payload: dict[str, Any]) -> bytes:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(body) > self.max_message_bytes:
            raise ValueError("payload exceeds max_message_bytes")
        return struct.pack("!I", len(body)) + body

    def call(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        request = {"request_id": request_id, "type": command, "params": params or {}}
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(self._encode(request))
            size = struct.unpack("!I", read_exact(sock, 4))[0]
            if size > self.max_message_bytes:
                raise BridgeProtocolError("response exceeds max_message_bytes")
            response = json.loads(read_exact(sock, size).decode("utf-8"))
        if response.get("request_id") != request_id:
            raise BridgeProtocolError("response request_id mismatch")
        if response.get("status") == "error":
            raise RuntimeError(response.get("message", "Blender precision command failed"))
        return response.get("result", response)
```

- [ ] **Step 4: Replace `BlenderBridge` in `server.py`**

Delete the persistent socket and lock implementation, import `BlenderBridge` from `precision_mcp.transport`, and instantiate it with environment-derived host/port. Keep `_safe_path` and existing tool names temporarily.

- [ ] **Step 5: Run transport and compile tests**

```bash
python -m unittest tests.test_precision_transport -v
python -m py_compile precision-mcp/precision_mcp/transport.py precision-mcp/precision_mcp/server.py
```

Expected: transport tests pass and compilation succeeds.

- [ ] **Step 6: Commit**

```bash
git add precision-mcp/precision_mcp/transport.py precision-mcp/precision_mcp/server.py tests/test_precision_transport.py
git commit -m "fix: frame precision blender transport"
```

---

### Task 7: Implement job-scoped Blender transactions and framed add-on handling

**Files:**
- Modify: `precision-mcp/blender_addon/precision_addon.py`
- Create: `tests/test_precision_addon_source.py`

- [ ] **Step 1: Write source-level guard tests before importing `bpy`**

```python
import ast
import unittest
from pathlib import Path

ADDON = Path(__file__).parents[1] / "precision-mcp" / "blender_addon" / "precision_addon.py"


class PrecisionAddonSourceTests(unittest.TestCase):
    def test_addon_has_no_arbitrary_execution_command(self):
        source = ADDON.read_text(encoding="utf-8")
        self.assertNotIn("execute_blender_code", source)
        self.assertNotIn("exec(", source)

    def test_addon_parses_and_defines_v2_job_commands(self):
        tree = ast.parse(ADDON.read_text(encoding="utf-8"))
        source = ADDON.read_text(encoding="utf-8")
        self.assertIsNotNone(tree)
        for command in ("precision_begin_job", "precision_abort_job", "precision_commit_job"):
            self.assertIn(command, source)
```

- [ ] **Step 2: Run and verify the command test fails**

Run: `python -m unittest tests.test_precision_addon_source -v`  
Expected: FAIL because the V2 job commands are absent.

- [ ] **Step 3: Add job state and safe work paths**

Inside the add-on, add:

```python
import re
import struct
from dataclasses import dataclass, field

WORKDIR = os.path.abspath(os.getenv("PRECISION_WORKDIR", os.getcwd()))
JOB_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass
class BlenderJob:
    job_id: str
    prefix: str
    checkpoint: str
    created_objects: set[str] = field(default_factory=set)
    state: str = "active"


_jobs = {}


def _safe_work_path(filepath):
    path = os.path.abspath(os.path.expanduser(filepath))
    if os.path.commonpath([path, WORKDIR]) != WORKDIR:
        raise ValueError(f"path must be inside PRECISION_WORKDIR: {WORKDIR}")
    return path
```

- [ ] **Step 4: Add begin/commit/abort commands**

`precision_begin_job` validates `job_id`, rejects an already-active job, saves `before.blend` with `copy=True`, and registers prefix `PRECISION_<job_id>_`. `precision_commit_job` marks the job committed and saves the requested final checkpoint. `precision_abort_job` attempts `bpy.ops.wm.open_mainfile(filepath=checkpoint)` when the checkpoint exists; if Blender cannot restore it, remove only `created_objects` and return `restored_checkpoint: false` with the exception text.

Use this result shape:

```python
{"job_id": job_id, "state": "aborted", "restored_checkpoint": restored, "removed_created_objects": removed, "restore_error": restore_error}
```

- [ ] **Step 5: Replace single `recv` with framed reads and structured response IDs**

Implement `_recv_exact`, read a four-byte `!I` size, enforce 4 MiB, parse `request_id`, and send a framed response containing the same ID. Keep one request per accepted connection. The listener thread should only read frames; register `_execute_queued(client, request)` with `bpy.app.timers` so `execute()` stays on Blender's main thread.

- [ ] **Step 6: Preserve V1 wrappers through a compatibility job**

Map `precision_begin`, `precision_commit` and `precision_abort` to an internal `legacy-v1` job without changing their public result keys. Do not route V2 validation through V1 prefix-wide scene scans.

- [ ] **Step 7: Run static tests and compile**

```bash
python -m unittest tests.test_precision_addon_source -v
python -m py_compile precision-mcp/blender_addon/precision_addon.py
```

Expected: tests pass and compilation succeeds without Blender installed.

- [ ] **Step 8: Commit**

```bash
git add precision-mcp/blender_addon/precision_addon.py tests/test_precision_addon_source.py
git commit -m "feat: scope blender precision transactions"
```

---

### Task 8: Add precise asset creation and GLB/FBX intake

**Files:**
- Modify: `precision-mcp/blender_addon/precision_addon.py`
- Modify: `tests/test_precision_addon_source.py`
- Create: `tests/fixtures/precision_v2/import-cube.glb`
- Create: `tests/fixtures/precision_v2/import-cube.fbx`

- [ ] **Step 1: Add failing command-presence tests**

Extend the source test to require:

```python
for command in ("precision_create_part", "precision_import_asset", "precision_normalize_asset", "precision_profile_extrude"):
    self.assertIn(command, source)
```

Run: `python -m unittest tests.test_precision_addon_source -v`  
Expected: FAIL because the commands are absent.

- [ ] **Step 2: Add exact primitive and profile creation**

Implement `precision_create_part` using existing exact-dimension primitives and enforce the current job prefix. Implement `precision_profile_extrude` from a simple non-self-intersecting 2D polygon: create front/back vertices, front/back faces and side quads, then validate target XYZ dimensions with `_set_dimensions`. Reject fewer than three profile points and zero extrusion depth.

- [ ] **Step 3: Add imported-asset root isolation**

For GLB use `bpy.ops.import_scene.gltf(filepath=...)`. For FBX, prefer `bpy.ops.wm.fbx_import(filepath=...)` when present and fall back to `bpy.ops.import_scene.fbx(filepath=...)`. Record the object names that appeared after import, create an empty root named `PRECISION_<job_id>_<asset_id>_ROOT`, and parent imported objects while preserving world transforms.

- [ ] **Step 4: Normalize units and axes**

Use explicit unit factors:

```python
UNIT_TO_METERS = {"mm": 0.001, "cm": 0.01, "m": 1.0}
factor = UNIT_TO_METERS[source_units] / UNIT_TO_METERS[target_units]
root.scale = (factor, factor, factor)
```

Apply a documented rotation for source up axes `Y` or `Z`, update the view layer, compute aggregate world bounds, then apply either uniform scaling or explicit XYZ scaling according to manifest `scaling_mode`. Apply transforms and store provenance, checksum and source axes as custom properties.

- [ ] **Step 5: Generate deterministic cube fixtures through Blender GUI**

Use Blender once to create one 1 m cube and export it to both files under `tests/fixtures/precision_v2/`. These are test fixtures, not product assets. Record their SHA-256 values in the fixture manifests created in Task 12.

- [ ] **Step 6: Run static tests and commit**

```bash
python -m unittest tests.test_precision_addon_source -v
python -m py_compile precision-mcp/blender_addon/precision_addon.py
git add precision-mcp/blender_addon/precision_addon.py tests/test_precision_addon_source.py tests/fixtures/precision_v2/import-cube.glb tests/fixtures/precision_v2/import-cube.fbx
git commit -m "feat: import and normalize precision assets"
```

---

### Task 9: Add anchor assembly, targeted patches and raw geometry QA

**Files:**
- Modify: `precision-mcp/blender_addon/precision_addon.py`
- Modify: `tests/test_precision_addon_source.py`

- [ ] **Step 1: Require assembly and inspection commands**

```python
for command in ("precision_set_transform", "precision_align_anchors", "precision_patch_feature", "precision_inspect_job"):
    self.assertIn(command, source)
```

Run the source test and expect failure.

- [ ] **Step 2: Implement canonical transforms and anchors**

`precision_set_transform` accepts explicit location, Euler degrees and target scale. `precision_align_anchors` computes world points using `obj.matrix_world @ Vector(local_anchor)` and translates the moving root by `target_world - moving_world`. Reject anchors that are missing or belong to another job.

- [ ] **Step 3: Implement named precision patches**

Support a closed phase-one patch allow-list:

```python
PATCHES = {"dimensions", "location", "rotation_deg", "hole_diameter", "array_spacing"}
```

Dimensions and transforms update the named asset. Hole and array patches look up modifiers tagged with `precision_feature_id`; if the feature is absent, return a structured error rather than rebuilding the object.

- [ ] **Step 4: Implement job-wide raw QA**

Return a stable report containing aggregate and per-object bounds, applied scale state, non-manifold edge count, degenerate polygons, invalid normals, ground Z, anchor world positions, contact distances and collision pairs. Use `BVHTree.FromObject` for mesh collision checks; AABB is allowed only as a broad-phase filter and must not be reported as a confirmed collision.

- [ ] **Step 5: Fix camera prerequisites while bounds helpers are centralized**

Move aggregate bound calculation into one helper shared by QA and camera framing. Set the requested lens before calculating perspective distance, use aggregate center rather than object origin, and account for render aspect ratio.

- [ ] **Step 6: Run static tests and commit**

```bash
python -m unittest tests.test_precision_addon_source -v
python -m py_compile precision-mcp/blender_addon/precision_addon.py
git add precision-mcp/blender_addon/precision_addon.py tests/test_precision_addon_source.py
git commit -m "feat: assemble and inspect precision jobs"
```

---

### Task 10: Wire V2 MCP tools, QA evaluation and evidence finalization

**Files:**
- Modify: `precision-mcp/precision_mcp/server.py`
- Create: `tests/test_precision_server_v2.py`

- [ ] **Step 1: Write failing server tests with an injected fake bridge**

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

import precision_mcp.server as server


SCENE = {
    "spec_version": "2.0", "job_id": "desk-001", "category": "furniture", "requested_grade": "L2", "units": "mm",
    "coordinate_system": {"up": "Z", "handedness": "right"}, "reference_calibrated": True,
    "measurements": [{"id": "overall_width", "kind": "dimension", "asset_id": "desk", "axis": "X", "target": 1200.0, "tolerance_abs": 1.0, "required": True, "scope": "global"}],
}
MANIFEST = {
    "spec_version": "2.0", "job_id": "desk-001",
    "assets": [{"asset_id": "desk", "role": "fit_critical", "source": "procedural", "target_dimensions": [1200.0, 600.0, 750.0], "location": [0, 0, 375], "rotation_deg": [0, 0, 0], "anchors": []}],
}


class FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, command, params=None):
        self.calls.append((command, params or {}))
        if command == "precision_inspect_job":
            return {"measurements": {"overall_width": 1200.4}, "geometry_ok": True, "provenance_ok": True}
        return {"ok": True}


class PrecisionServerV2Tests(unittest.TestCase):
    def test_prepare_job_validates_and_persists_plan(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory, patch.object(server, "bridge", fake), patch.object(server, "WORKDIR", Path(directory)):
            result = json.loads(server.precision_prepare_job(SCENE, MANIFEST))
            self.assertEqual(result["job_id"], "desk-001")
            self.assertTrue((Path(directory) / "evidence" / "desk-001" / "operation_plan.json").exists())

    def test_validate_job_uses_blender_measurements(self):
        fake = FakeBridge()
        with tempfile.TemporaryDirectory() as directory, patch.object(server, "bridge", fake), patch.object(server, "WORKDIR", Path(directory)):
            result = json.loads(server.precision_validate_job(SCENE, MANIFEST, checkpoint_exists=True))
            self.assertEqual(result["assertions"][0]["actual"], 1200.4)
            self.assertEqual(result["grade"], "L2")
```

Keep fixture dictionaries in the test file rather than production `server.py`.

- [ ] **Step 2: Run and verify failure**

Run: `python -m unittest tests.test_precision_server_v2 -v`  
Expected: FAIL because `precision_prepare_job` and `precision_validate_job` do not exist.

- [ ] **Step 3: Add V2 preparation and typed execution tools**

Implement `precision_prepare_job(scene_spec, asset_manifest)` to validate both contracts, build and validate the plan, write the three contracts to `EvidenceBundle`, call `precision_begin_job`, and return the plan. Add typed wrappers for `precision_create_part`, `precision_profile_extrude`, `precision_import_asset`, `precision_normalize_asset`, `precision_set_transform`, `precision_align_anchors`, `precision_patch_feature`, and `precision_inspect_job`. Every wrapper requires `job_id`.

- [ ] **Step 4: Add V2 QA and finalization**

`precision_validate_job` calls `precision_inspect_job`, maps every SceneSpec measurement ID to a returned raw value, calls `evaluate_assertion`, derives the grade, validates `qa_report`, writes assumptions, and transitions `JobState` to `validating`; a failed result then transitions to `failed_qa`, while a passing result remains `validating` until finalization. `precision_finalize_job` renders both previews, saves `final.blend` only after QA, computes artifact checksums, inserts paths and checksums into the report, validates and rewrites the final report, commits the job, and transitions to `committed`. A failed required assertion saves `failed.blend`, leaves the report at L0/L1, and must not call `precision_commit_job`.

- [ ] **Step 5: Retain V1 tools as wrappers**

Keep existing MCP tool names and response formats, but route their bridge calls through the new transport. Update docstrings to state that V1 relative QA is compatibility-only and cannot issue V2 L2.

- [ ] **Step 6: Run server, contract and measurement tests**

```bash
python -m unittest tests.test_precision_server_v2 tests.test_precision_contracts tests.test_precision_measurements tests.test_precision_planner tests.test_precision_evidence -v
python -m py_compile precision-mcp/precision_mcp/*.py
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add precision-mcp/precision_mcp/server.py tests/test_precision_server_v2.py
git commit -m "feat: expose precision core v2 tools"
```

---

### Task 11: Create the authoritative precision Skill and compatibility routes

**Files:**
- Create: `skills/blender-precision-modeling/SKILL.md`
- Create: `skills/blender-precision-modeling/agents/openai.yaml`
- Create: `skills/blender-modeling/agents/openai.yaml`
- Create: `skills/blender-base-mesh-library/agents/openai.yaml`
- Create: `skills/blender-seedance-modeling/agents/openai.yaml`
- Create: `skills/blender-white-model-render/agents/openai.yaml`
- Create: `skills/seedance-white-model-video/agents/openai.yaml`
- Create: `skills/blender-precision-modeling/references/precision-contract.md`
- Create: `skills/blender-precision-modeling/references/reference-calibration.md`
- Modify: `skills/blender-modeling/SKILL.md`
- Modify: `skills/blender-base-mesh-library/SKILL.md`
- Modify: `skills/blender-seedance-modeling/SKILL.md`
- Modify: `skills/blender-white-model-render/SKILL.md`
- Modify: `skills/seedance-white-model-video/SKILL.md`

- [ ] **Step 1: Write the new Skill trigger and concise workflow**

Use this frontmatter exactly:

```yaml
---
name: blender-precision-modeling
description: Build, import, assemble, patch, measure, validate, and deliver dimension-driven Blender white models through Precision Core V2. Use for calibrated prompt/reference modeling, architecture, mechanical assets, furniture, props, GLB/FBX normalization, absolute tolerances, CAD-constrained profiles, commercial evidence bundles, or any request claiming high precision.
---
```

The body must route in this order: calibrate input → write contracts → prepare job → execute typed operations → inspect and patch → validate → finalize evidence. It must explicitly demote uncalibrated references to L0 and forbid Tripo/Seedance from issuing a precision grade.

- [ ] **Step 2: Add focused references**

`precision-contract.md` documents the four contract files, measurement kinds, asset roles and L0/L1/L2 gates. `reference-calibration.md` documents accepted calibration sources, observed-versus-inferred separation, camera/view labels, and the single-image L0 rule. Do not duplicate the full reference text in `SKILL.md`.

- [ ] **Step 3: Generate `agents/openai.yaml`**

Read `/Users/a/.codex/skills/.system/skill-creator/references/openai_yaml.md`, then generate the new Skill metadata:

```bash
python3 /Users/a/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py skills/blender-precision-modeling \
  --interface 'display_name=Blender Precision Modeling' \
  --interface 'short_description=Build and verify dimension-driven Blender white models' \
  --interface 'default_prompt=Use $blender-precision-modeling to turn this calibrated brief into a measured Blender model and evidence bundle.'
```

Generate matching metadata for the existing Skills:

```bash
python3 /Users/a/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py skills/blender-modeling --interface 'display_name=Blender Modeling' --interface 'short_description=Build and edit Blender scenes from prompts or references' --interface 'default_prompt=Use $blender-modeling to build or revise this editable Blender scene.'
python3 /Users/a/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py skills/blender-base-mesh-library --interface 'display_name=Blender BaseMesh Library' --interface 'short_description=Create and organize reusable Blender BaseMeshes' --interface 'default_prompt=Use $blender-base-mesh-library to select or build this reusable white-model asset.'
python3 /Users/a/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py skills/blender-seedance-modeling --interface 'display_name=Blender Seedance Modeling' --interface 'short_description=Route Blender white-model and Seedance workflows' --interface 'default_prompt=Use $blender-seedance-modeling to route this Blender-to-Seedance production request.'
python3 /Users/a/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py skills/blender-white-model-render --interface 'display_name=Blender White Model Render' --interface 'short_description=Render neutral Blender white-model previews' --interface 'default_prompt=Use $blender-white-model-render to render this committed white-model scene.'
python3 /Users/a/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py skills/seedance-white-model-video --interface 'display_name=Seedance White Model Video' --interface 'short_description=Prepare verified white models for Seedance video' --interface 'default_prompt=Use $seedance-white-model-video to prepare this QA-approved white model for Seedance.'
```

- [ ] **Step 4: Update existing Skill routes**

Add one short delegation rule to each relevant Skill. Precision claims, dimensions, calibrated references and commercial evidence route to `blender-precision-modeling`; render/video Skills only consume committed artifacts. Keep existing non-precision workflows intact.

- [ ] **Step 5: Validate every Skill**

```bash
for skill in skills/*; do python3 /Users/a/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"; done
```

Expected: every Skill prints `Skill is valid!`.

- [ ] **Step 6: Commit**

```bash
git add skills
git commit -m "feat: add blender precision modeling skill"
```

---

### Task 12: Add portable four-category fixtures and real GUI acceptance

**Files:**
- Create: `tests/fixtures/precision_v2/architecture-scene.json`
- Create: `tests/fixtures/precision_v2/architecture-manifest.json`
- Create: `tests/fixtures/precision_v2/mechanical-scene.json`
- Create: `tests/fixtures/precision_v2/mechanical-manifest.json`
- Create: `tests/fixtures/precision_v2/furniture-scene.json`
- Create: `tests/fixtures/precision_v2/furniture-manifest.json`
- Create: `tests/fixtures/precision_v2/prop-scene.json`
- Create: `tests/fixtures/precision_v2/prop-manifest.json`
- Create: `tests/precision_v2_gui_test.py`
- Modify: `tests/PRECISION_MCP.md`

- [ ] **Step 1: Create calibrated fixtures with concrete assertions**

Use these acceptance subjects:

```text
architecture: 4000×200×2800 mm wall, 900×2000 mm opening, 1 mm tolerance
mechanical: 600×400×250 mm enclosure, four 8 mm holes, 0.5 mm tolerance
furniture: 1200×600×750 mm table, four leg anchors, 1 mm tolerance
prop: imported 1000 mm handled tool, Z-up normalization, 1 mm tolerance
```

Every SceneSpec is calibrated and contains required global/primary/anchor assertions. Every manifest uses stable asset IDs, explicit transforms and provenance for imported fixtures.

- [ ] **Step 2: Write a portable GUI runner**

Resolve all paths from the test file:

```python
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "precision_v2"
OUTPUT = ROOT / "tests" / "assets" / "precision_v2"
```

The runner launches the real stdio Precision MCP server and calls it through the MCP SDK:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "precision_mcp.server"],
    env={**os.environ, "PRECISION_WORKDIR": str(OUTPUT), "PYTHONPATH": str(ROOT / "precision-mcp")},
)
async with stdio_client(params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        prepared = await session.call_tool("precision_prepare_job", {"scene_spec": scene, "asset_manifest": manifest})
```

Continue through the same session to execute each plan step, apply one named patch, call `precision_validate_job`, and finalize. Assert the expected grade and that contracts, report, checkpoint and two previews exist. Never open a direct raw socket in this runner.

- [ ] **Step 3: Add negative acceptance cases**

Run an uncalibrated copy and assert L0, corrupt an imported unit declaration and assert normalization repairs it, change a required dimension beyond tolerance and assert no L2, attempt a workdir escape and assert rejection, and stop the Blender listener mid-call to assert a structured connection error.

- [ ] **Step 4: Run the GUI tests on Blender 5.2**

Start Blender with the add-on enabled on port 9877, start the MCP server with an explicit repo-local workdir, then run:

```bash
PRECISION_WORKDIR="$PWD/tests/assets/precision_v2" python tests/precision_v2_gui_test.py
```

Expected summary:

```text
architecture L2 PASS
mechanical L2 PASS
furniture L2 PASS
prop L2 PASS
uncalibrated L0 PASS
failed-required-dimension NOT-L2 PASS
path-escape REJECTED PASS
```

- [ ] **Step 5: Record evidence without overstating it**

Update `tests/PRECISION_MCP.md` with Blender/add-on/Python versions, exact command, result summary and relative artifact links. If any GUI case cannot run, record it as blocked and do not claim V2 runtime validation.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/precision_v2 tests/precision_v2_gui_test.py tests/assets/precision_v2 tests/PRECISION_MCP.md
git commit -m "test: verify precision v2 blender workflow"
```

---

### Task 13: Update installation, commercial claims, CI and final verification

**Files:**
- Modify: `README.md`
- Modify: `precision-mcp/README.md`
- Modify: `COMMERCIAL_USE.md`
- Modify: `plugins/README.md`
- Modify: `plugins/manifest.json`
- Modify: `.github/workflows/precision-mcp.yml`
- Modify: `tests/precision_socket_test.py`
- Modify: `tests/precision_cad_socket_test.py`
- Modify: `tests/precision_seven_category_socket_test.py`
- Modify: `tests/precision_gui_boot.py`

- [ ] **Step 1: Remove hard-coded developer paths**

Replace `/Users/jiangye/...` constants with `Path(__file__).resolve().parents[1]`. Make legacy direct-socket scripts explicitly `legacy diagnostic` and keep them out of the V2 proof path.

- [ ] **Step 2: Document installation and configuration**

Document the new Skill, `PRECISION_WORKDIR`, framed add-on port, FastMCP start command, phase-one adapter states and evidence directory. Add Precision MCP and CAD Sketcher status fields to `plugins/manifest.json`; do not list Tripo or Seedance as installed integrations.

- [ ] **Step 3: Tighten commercial claim language**

Define L0/L1/L2 using the V2 gates, require `qa_report.json` and checksummed `.blend`, and state that Tripo visual meshes, uncalibrated references and blocked GUI tests cannot support L2.

- [ ] **Step 4: Finish CI**

CI must install dependencies, discover all `test_precision_*.py` portable tests, compile all Python/add-on files, parse every schema, and run Skill validation. Do not run graphical Blender in Ubuntu CI unless a proven runner is added separately.

- [ ] **Step 5: Run the complete portable verification**

```bash
python -m unittest discover -s tests -p 'test_precision_*.py' -v
python -m py_compile precision-mcp/precision_mcp/*.py precision-mcp/precision_mcp/adapters/*.py precision-mcp/blender_addon/precision_addon.py
python -c "import json, glob; [json.load(open(path)) for path in glob.glob('precision-mcp/schemas/*.json')]; print('schemas: OK')"
for skill in skills/*; do python3 /Users/a/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"; done
git diff --check
```

Expected: all unit tests pass, compilation succeeds, `schemas: OK` prints, every Skill is valid, and `git diff --check` is silent.

- [ ] **Step 6: Re-run the real GUI acceptance after documentation changes**

Run the Task 12 GUI command again. Confirm the evidence checksums still match the final `.blend` and previews.

- [ ] **Step 7: Commit final integration**

```bash
git add README.md precision-mcp/README.md COMMERCIAL_USE.md plugins .github/workflows/precision-mcp.yml tests
git commit -m "docs: publish precision core v2 workflow"
```

- [ ] **Step 8: Inspect final history and status**

```bash
git status --short --branch
git log --oneline --decorate -15
```

Expected: working tree clean and the V2 commits appear in task order.

---

## Verification summary

The implementation is complete only when all of these are true:

1. Portable contract, measurement, planner, evidence, transport, server and source-guard tests pass.
2. The FastMCP bridge handles sequential calls and partial frames with no stale socket.
3. V2 QA compares SceneSpec targets with Blender measurements using absolute tolerances.
4. Job scoping prevents unrelated `PRECISION_` objects from influencing validation.
5. Architecture, mechanical, furniture and prop fixtures pass the real MCP-to-Blender GUI path.
6. Uncalibrated and failed-measurement cases cannot issue L2.
7. Every evidence bundle contains validated contracts, checksummed `.blend`, two previews and a QA report.
8. Existing Skill names still work and delegate precision claims to `blender-precision-modeling`.
9. Tripo and Seedance remain optional, explicit unavailable adapters in phase one.
10. No hard-coded developer home paths remain.

## Next skill

- Recommended: `$superpower-subagents` for task-by-task execution with review after each commit.
- Alternative: `$superpower-executing-plans` for inline execution in this task with review checkpoints.
