import json
import os
import socket
import threading
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


HOST = os.getenv("PRECISION_BLENDER_HOST", "127.0.0.1")
PORT = int(os.getenv("PRECISION_BLENDER_PORT", "9877"))
WORKDIR = Path(os.getenv("PRECISION_WORKDIR", os.getcwd())).resolve()


class BlenderBridge:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.lock = threading.Lock()

    def call(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.lock:
            if self.sock is None:
                self.sock = socket.create_connection((self.host, self.port), timeout=10)
            payload = json.dumps({"type": command, "params": params or {}}).encode("utf-8")
            try:
                self.sock.sendall(payload)
                self.sock.settimeout(180)
                chunks: list[bytes] = []
                while True:
                    chunk = self.sock.recv(65536)
                    if not chunk:
                        raise ConnectionError("precision addon closed the socket")
                    chunks.append(chunk)
                    try:
                        response = json.loads(b"".join(chunks).decode("utf-8"))
                        break
                    except json.JSONDecodeError:
                        continue
                if response.get("status") == "error":
                    raise RuntimeError(response.get("message", "Blender precision command failed"))
                return response.get("result", response)
            except Exception:
                self.sock.close()
                self.sock = None
                raise


bridge = BlenderBridge(HOST, PORT)
mcp = FastMCP("BlenderPrecisionMCP")


def _call(name: str, params: dict[str, Any] | None = None) -> str:
    return json.dumps(bridge.call(name, params), ensure_ascii=False, indent=2)


def _safe_path(filepath: str) -> str:
    path = Path(filepath).expanduser().resolve()
    if path != WORKDIR and WORKDIR not in path.parents:
        raise ValueError(f"path must be inside PRECISION_WORKDIR: {WORKDIR}")
    return str(path)


@mcp.tool()
def precision_begin(prefix: str = "PRECISION_", clean_existing: bool = False) -> str:
    """Start a transaction; existing objects are preserved unless clean_existing is explicitly true."""
    return _call("precision_begin", {"prefix": prefix, "clean_existing": clean_existing})


@mcp.tool()
def precision_create_mesh(name: str, vertices: list[list[float]], faces: list[list[int]], dimensions: list[float] | None = None, prefix: str = "PRECISION_") -> str:
    """Create a mesh from explicit vertices/faces, optionally normalized to exact XYZ dimensions."""
    return _call("precision_create_mesh", {"name": name, "vertices": vertices, "faces": faces, "dimensions": dimensions, "prefix": prefix})


@mcp.tool()
def precision_create_primitive(name: str, primitive: str, dimensions: list[float], location: list[float] | None = None, metadata: dict[str, Any] | None = None) -> str:
    """Create a named cube, cylinder, cone, UV sphere or plane with exact dimensions."""
    return _call("precision_create_primitive", {"name": name, "primitive": primitive, "dimensions": dimensions, "location": location, "metadata": metadata or {}})


@mcp.tool()
def precision_cad_status() -> str:
    """Report whether CAD Sketcher and its solver are available in the connected Blender session."""
    return _call("precision_cad_status")


@mcp.tool()
def precision_set_dimensions(name: str, dimensions: list[float], apply_scale: bool = True) -> str:
    """Set exact world dimensions and optionally apply scale."""
    return _call("precision_set_dimensions", {"name": name, "dimensions": dimensions, "apply_scale": apply_scale})


@mcp.tool()
def precision_inspect_geometry(name: str | None = None) -> str:
    """Return measurable geometry QA for one object or all precision objects."""
    return _call("precision_inspect_geometry", {"name": name})


@mcp.tool()
def precision_validate_scene(tolerance: float = 0.01, require_ground_contact: bool = True) -> str:
    """Run measurable scene QA; tolerance is relative dimension error, e.g. 0.01 = 1%."""
    return _call("precision_validate_scene", {"tolerance": tolerance, "require_ground_contact": require_ground_contact})


@mcp.tool()
def precision_frame_camera(name: str, target_fill: float = 0.72, lens_mm: float = 50.0) -> str:
    """Frame a camera from the object world bounding box at a target occupancy."""
    return _call("precision_frame_camera", {"name": name, "target_fill": target_fill, "lens_mm": lens_mm})


@mcp.tool()
def precision_render_white_model(filepath: str, resolution_x: int = 640, resolution_y: int = 360) -> str:
    """Render a neutral Workbench white-model preview to an explicit path."""
    return _call("precision_render_white_model", {"filepath": _safe_path(filepath), "resolution_x": resolution_x, "resolution_y": resolution_y})


@mcp.tool()
def precision_save_checkpoint(filepath: str) -> str:
    """Save a Blender checkpoint inside PRECISION_WORKDIR before destructive edits."""
    return _call("precision_save_checkpoint", {"filepath": _safe_path(filepath)})


@mcp.tool()
def precision_commit() -> str:
    """Commit the current modeling transaction."""
    return _call("precision_commit")


@mcp.tool()
def precision_abort() -> str:
    """Stop the current modeling transaction; restore from the Skill checkpoint if needed."""
    return _call("precision_abort")


if __name__ == "__main__":
    mcp.run()
