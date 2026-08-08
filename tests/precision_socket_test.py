"""Black-box test for the running GUI precision addon."""
import json
import socket
from pathlib import Path


ROOT = Path("/Users/jiangye/project/blender/blender-seedance-skills-repo")


def call(command, params=None):
    with socket.create_connection(("127.0.0.1", 9877), timeout=10) as sock:
        sock.sendall(json.dumps({"type": command, "params": params or {}}).encode())
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError("precision addon closed connection")
            chunks.append(chunk)
            try:
                response = json.loads(b"".join(chunks).decode())
                break
            except json.JSONDecodeError:
                continue
    if response.get("status") == "error":
        raise RuntimeError(response.get("message"))
    return response["result"]


print("CAD_STATUS", call("precision_cad_status"))
print("BEGIN", call("precision_begin", {"prefix": "PRECISION_", "clean_existing": True}))
print("PRIMITIVE", call("precision_create_primitive", {"name": "PRECISION_TestBlock", "primitive": "cube", "dimensions": [2.0, 4.0, 1.0], "location": [0.0, 0.0, 0.5], "metadata": {"base_mesh_category": "architecture", "source_prompt": "precision integration test"}}))
print("INSPECT", call("precision_inspect_geometry", {"name": "PRECISION_TestBlock"}))
print("QA", call("precision_validate_scene", {"tolerance": 0.01, "require_ground_contact": True}))
print("CAMERA", call("precision_frame_camera", {"name": "PRECISION_TestBlock", "target_fill": 0.72, "lens_mm": 50.0}))
checkpoint = ROOT / "tests" / "assets" / "precision_mcp" / "precision_checkpoint.blend"
preview = ROOT / "tests" / "assets" / "precision_mcp" / "precision_preview.png"
print("CHECKPOINT", call("precision_save_checkpoint", {"filepath": str(checkpoint)}))
print("RENDER", call("precision_render_white_model", {"filepath": str(preview), "resolution_x": 320, "resolution_y": 240}))
print("COMMIT", call("precision_commit"))
print("ABORT_BEGIN", call("precision_begin", {"prefix": "PRECISION_ABORT_", "clean_existing": False}))
print("ABORT_CREATE", call("precision_create_primitive", {"name": "PRECISION_ABORT_Temporary", "primitive": "cube", "dimensions": [1.0, 1.0, 1.0], "location": [0.0, 0.0, 0.5]}))
print("ABORT", call("precision_abort"))
remaining = call("precision_inspect_geometry", {"name": None})
print("ABORT_REMAINING", remaining)
assert all(item["name"] != "PRECISION_ABORT_Temporary" for item in remaining["objects"])
print("ARTIFACTS", checkpoint.exists(), preview.exists(), checkpoint.stat().st_size if checkpoint.exists() else 0, preview.stat().st_size if preview.exists() else 0)
