# Precision MCP MVP verification

Date: 2026-08-09

## Passed

- `precision_mcp/server.py` and `precision_addon.py` pass Python AST parsing.
- Both files pass compilation with `PYTHONPYCACHEPREFIX=/tmp/precision-mcp-pycache python3 -m py_compile ...`.
- Blender executable was found at `/Applications/Blender.app/Contents/MacOS/Blender` and reports Blender 5.2.0 LTS.
- The implementation exposes only typed precision commands: mesh creation, exact dimensions, geometry inspection, camera framing, Workbench render, commit and abort.

## Blocked runtime check

The headless Blender process crashes during Blender GPU backend initialization before executing the test script. The crash backtrace points to `gpu::MTLBackend::metal_is_supported`, not to the precision addon. Therefore this is not recorded as a passed Blender integration test.

The next runtime test must load the addon in the existing GUI Blender session, enable it on port `9877`, and then call the MCP tools against that port. Until that is done, the repo must not claim that the precision MCP is installed or runtime-validated.

## Known MVP boundary

`precision_abort` removes only objects created after the current transaction begins. It does not restore an external `.blend` file; the higher-level Skill should still create a checkpoint before destructive operations.

## GUI integration attempt

- The existing 8400 listener was checked, but it was no longer reachable when the isolated test was started.
- A separate GUI Blender launch was attempted with `precision_gui_boot.py`.
- Blender exited before Python startup with a Metal backend crash in `gpu::MTLBackend::metal_is_supported`.
- `--gpu-backend opengl` is unavailable in this Blender build; the executable reports only `[metal]`.
- Result: addon runtime and `9877` socket behavior remain unverified on this machine.

## GUI integration passed

On the same machine, the test was retried by launching Blender through macOS GUI permissions:

```text
Blender 5.2.0 LTS
127.0.0.1:9877 listening
CAD status: module_available=false (CAD Sketcher not installed)
dimensions: [2.0, 4.0, 1.0]
non_manifold_edges: 0
ground_z: 0.0
QA: passed=true, tolerance=0.01, issues=[]
checkpoint: exists=true, 99626 bytes
white-model preview: exists=true, 53874 bytes
commit: ok=true
abort: removed_new_objects=1
```

Preview artifact: [`precision_preview.png`](assets/precision_mcp/precision_preview.png).
Checkpoint artifact: [`precision_checkpoint.blend`](assets/precision_mcp/precision_checkpoint.blend).

This proves the typed precision runtime path on Blender 5.2. The CAD constraint result is recorded below.

## CAD Sketcher solver verification

CAD Sketcher 0.3.0 was installed from its official extension source and its bundled macOS ARM64
CPython 3.13 `slvs` wheel was installed into Blender's user Python site-packages. After restarting
the GUI session, `precision_cad_status` returned:

```text
available=true
scene_properties_available=true
solver_available=true
operator_available=true
solver_registered=true
```

The next verification is `tests/precision_cad_socket_test.py`, which creates a 3.0 x 2.0 rectangle,
adds horizontal/vertical and width/height constraints, and requires a successful solver result.

The CAD test was executed successfully:

```text
CAD_STATUS: available=true, solver_available=true, operator_available=true, solver_registered=true
CAD_RECTANGLE: solved=true, solver_state=OKAY, dof=0, entity_count=8, constraint_count=6
target_dimensions: [3.0, 2.0]
```

Together, the two tests prove the dimension-driven mesh path and a real constraint-solved sketch path.

`tests/precision_seven_category_socket_test.py` also submits a repeatable `model_spec` through the
MCP for all seven BaseMesh categories. Each category creates two named parameterized parts and passes
the same geometry/ground QA contract. This verifies category routing and reproducibility; it does not
claim that two primitive parts are a finished character, creature or environment asset.

The live Blender 5.2 output was:

```text
character parts=2 qa=passed
creature parts=2 qa=passed
props parts=2 qa=passed
architecture parts=2 qa=passed
hard_surface parts=2 qa=passed
environment parts=2 qa=passed
abstract parts=2 qa=passed
```
