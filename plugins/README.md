# Blender plugin and runtime status

This directory records integration contracts; it does not vendor third-party add-ons or prove that a dependency is active in the current Blender process.

| Integration | Version / endpoint | Status |
| --- | --- | --- |
| Blender MCP Server | server 1.29.0; add-on metadata 0.5.1; `127.0.0.1:8400` | Historical local initialize/modeling checks; install separately from upstream |
| Precision Core V2 add-on | repository source; framed `127.0.0.1:9877` | Source and portable tests present; current real Blender 5.2 GUI acceptance is BLOCKED when runtime is unavailable |
| CAD Sketcher | external 0.3.0 + solver | Optional GPL dependency; availability is runtime-detected, never assumed from this manifest |
| Jimeng uploader | 1.0.0 | Historical add-on load check; package not vendored and GUI upload remains manual |

Tripo and Seedance are not installed Precision Core V2 integrations. Phase-one Tripo requests remain `external_pending`; Seedance is only a downstream consumer of committed previews.

## Precision Core V2

Install `precision-mcp/blender_addon/precision_addon.py` through Blender’s add-on UI and enable it. Then start the FastMCP stdio server from the repository root:

```bash
python -m pip install "mcp>=1.3,<2" "httpx>=0.24" "jsonschema>=4.23,<5"
export PYTHONPATH="$PWD/precision-mcp"
export PRECISION_WORKDIR="$PWD/tests/assets/precision_v2"
export PRECISION_BLENDER_PORT=9877
python -m precision_mcp.server
```

The MCP client talks stdio to FastMCP. FastMCP uses a framed, request-correlated local bridge to the add-on; legacy direct-socket scripts are diagnostics, not V2 proof. `PRECISION_WORKDIR` constrains evidence, checkpoints, previews, and final model writes.

Call `precision_cad_status` in the current Blender session before choosing the CAD adapter. A missing extension or solver is `backend_unavailable`; the planner must not silently route it to Blender procedural geometry.

## Why binaries are not vendored

CAD Sketcher is GPL-3.0-or-later, the uploader has no clear standalone open-source redistribution grant, and Blender/runtime components retain their own licenses. Install each integration from an authorized source and verify its license. The repository records configuration and evidence expectations without relicensing binaries.
