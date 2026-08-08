bl_info = {
    "name": "Blender Precision MCP Companion",
    "author": "OPCspace",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "category": "3D View",
}

import json
import math
import os
import socket
import threading
import traceback
from mathutils import Vector

import bpy


HOST = "127.0.0.1"
PORT = int(os.getenv("PRECISION_BLENDER_PORT", "9877"))
_server = None


def _owned(name: str, prefix: str) -> bool:
    return name.startswith(prefix)


def _dimensions(obj):
    return [round(float(v), 6) for v in obj.dimensions]


def _inspect(obj):
    mesh = obj.data if obj.type == "MESH" else None
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = [min(v[i] for v in bbox) for i in range(3)]
    maxs = [max(v[i] for v in bbox) for i in range(3)]
    non_manifold = 0
    if mesh:
        non_manifold = sum(1 for edge in mesh.edges if not edge.is_manifold)
    return {
        "name": obj.name,
        "type": obj.type,
        "dimensions": _dimensions(obj),
        "world_bbox_min": [round(float(v), 6) for v in mins],
        "world_bbox_max": [round(float(v), 6) for v in maxs],
        "location": [round(float(v), 6) for v in obj.location],
        "scale": [round(float(v), 6) for v in obj.scale],
        "vertices": len(mesh.vertices) if mesh else None,
        "polygons": len(mesh.polygons) if mesh else None,
        "non_manifold_edges": non_manifold,
        "ground_z": round(float(mins[2]), 6),
    }


def _require_object(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"object not found: {name}")
    return obj


def _set_dimensions(obj, dimensions):
    if len(dimensions) != 3 or any(float(v) <= 0 for v in dimensions):
        raise ValueError("dimensions must contain three positive numbers")
    current = obj.dimensions
    for axis in range(3):
        if current[axis] <= 1e-9:
            raise ValueError(f"cannot normalize zero dimension on axis {axis}")
        obj.scale[axis] *= float(dimensions[axis]) / current[axis]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def _look_at(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def execute(command):
    name = command.get("type")
    params = command.get("params", {})
    if name == "precision_begin":
        prefix = params.get("prefix", "PRECISION_")
        for obj in list(bpy.data.objects):
            if _owned(obj.name, prefix):
                bpy.data.objects.remove(obj, do_unlink=True)
        return {"ok": True, "prefix": prefix, "deleted_owned_objects": True}
    if name == "precision_create_mesh":
        mesh = bpy.data.meshes.new(params["name"] + "_Mesh")
        mesh.from_pydata(params["vertices"], [], params["faces"])
        mesh.update()
        obj = bpy.data.objects.new(params["name"], mesh)
        bpy.context.collection.objects.link(obj)
        if params.get("dimensions"):
            _set_dimensions(obj, params["dimensions"])
        return _inspect(obj)
    if name == "precision_set_dimensions":
        obj = _require_object(params["name"])
        _set_dimensions(obj, params["dimensions"])
        return _inspect(obj)
    if name == "precision_inspect_geometry":
        target = params.get("name")
        objects = [_require_object(target)] if target else [o for o in bpy.context.scene.objects if o.name.startswith("PRECISION_")]
        return {"objects": [_inspect(o) for o in objects]}
    if name == "precision_frame_camera":
        obj = _require_object(params["name"])
        camera = bpy.context.scene.camera
        if camera is None:
            data = bpy.data.cameras.new("PRECISION_Camera")
            camera = bpy.data.objects.new("PRECISION_Camera", data)
            bpy.context.collection.objects.link(camera)
            bpy.context.scene.camera = camera
        fill = max(0.3, min(float(params.get("target_fill", 0.72)), 0.9))
        radius = max(obj.dimensions) / 2.0
        fov = camera.data.angle
        distance = radius / max(math.tan(fov / 2.0) * fill, 1e-6)
        camera.location = obj.location + Vector((distance, -distance, distance * 0.55))
        _look_at(camera, obj.location)
        camera.data.lens = float(params.get("lens_mm", 50.0))
        return {"camera": camera.name, "location": list(camera.location), "target_fill": fill}
    if name == "precision_render_white_model":
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = int(params.get("resolution_x", 640))
        scene.render.resolution_y = int(params.get("resolution_y", 360))
        scene.render.resolution_percentage = 100
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "SINGLE"
        scene.display.shading.single_color = (0.72, 0.72, 0.72)
        filepath = os.path.abspath(params["filepath"])
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        return {"filepath": filepath, "exists": os.path.exists(filepath)}
    if name == "precision_commit":
        return {"ok": True}
    if name == "precision_abort":
        return {"ok": False, "message": "MVP abort has no destructive restore yet; use a saved .blend checkpoint."}
    raise ValueError(f"unsupported precision command: {name}")


def _handle(client):
    try:
        data = client.recv(4 * 1024 * 1024)
        command = json.loads(data.decode("utf-8"))
        result = execute(command)
        payload = {"status": "success", "result": result}
    except Exception as exc:
        traceback.print_exc()
        payload = {"status": "error", "message": str(exc)}
    client.sendall(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    client.close()


class PrecisionServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.sock.listen(8)
        self.running = True

    def loop(self):
        while self.running:
            try:
                client, _ = self.sock.accept()
                bpy.app.timers.register(lambda c=client: (_handle(c), None)[1], first_interval=0.0)
            except OSError:
                break

    def stop(self):
        self.running = False
        self.sock.close()


def register():
    global _server
    if _server is None:
        _server = PrecisionServer()
        threading.Thread(target=_server.loop, daemon=True).start()
        print(f"Blender Precision MCP listening on {HOST}:{PORT}")


def unregister():
    global _server
    if _server:
        _server.stop()
        _server = None


if __name__ == "__main__":
    register()
