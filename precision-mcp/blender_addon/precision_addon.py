bl_info = {
    "name": "Blender Precision MCP Companion",
    "author": "OPCspace",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "category": "3D View",
}

import json
import importlib.util
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
_transaction_prefix = None
_transaction_preexisting = set()


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
        edge_face_counts = {}
        for polygon in mesh.polygons:
            for edge_key in polygon.edge_keys:
                key = tuple(sorted(edge_key))
                edge_face_counts[key] = edge_face_counts.get(key, 0) + 1
        non_manifold = sum(1 for edge in mesh.edges if edge_face_counts.get(tuple(sorted(edge.vertices)), 0) != 2)
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


def _set_metadata(obj, metadata):
    for key, value in (metadata or {}).items():
        if isinstance(value, (str, int, float, bool)):
            obj[key] = value


def _look_at(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def execute(command):
    global _transaction_prefix, _transaction_preexisting
    name = command.get("type")
    params = command.get("params", {})
    if name == "precision_begin":
        prefix = params.get("prefix", "PRECISION_")
        _transaction_prefix = prefix
        _transaction_preexisting = {obj.name for obj in bpy.data.objects if _owned(obj.name, prefix)}
        deleted = 0
        if params.get("clean_existing", False):
            for obj in list(bpy.data.objects):
                if _owned(obj.name, prefix):
                    bpy.data.objects.remove(obj, do_unlink=True)
                    deleted += 1
            _transaction_preexisting = set()
        return {"ok": True, "prefix": prefix, "clean_existing": bool(params.get("clean_existing", False)), "deleted_owned_objects": deleted}
    if name == "precision_create_mesh":
        mesh = bpy.data.meshes.new(params["name"] + "_Mesh")
        mesh.from_pydata(params["vertices"], [], params["faces"])
        mesh.update()
        obj = bpy.data.objects.new(params["name"], mesh)
        bpy.context.collection.objects.link(obj)
        if params.get("dimensions"):
            _set_dimensions(obj, params["dimensions"])
        return _inspect(obj)
    if name == "precision_create_primitive":
        primitive = params["primitive"].lower()
        location = params.get("location") or [0.0, 0.0, 0.0]
        if primitive == "cube":
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
        elif primitive == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.5, depth=1.0, location=location)
        elif primitive == "cone":
            bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=0.5, radius2=0.0, depth=1.0, location=location)
        elif primitive == "uv_sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.5, location=location)
        elif primitive == "plane":
            bpy.ops.mesh.primitive_plane_add(size=1.0, location=location)
        else:
            raise ValueError("primitive must be cube, cylinder, cone, uv_sphere or plane")
        obj = bpy.context.object
        obj.name = params["name"]
        if primitive == "plane":
            dims = params["dimensions"]
            if len(dims) != 3 or dims[0] <= 0 or dims[1] <= 0:
                raise ValueError("plane dimensions must contain positive X and Y values")
            obj.scale.x = float(dims[0])
            obj.scale.y = float(dims[1])
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        else:
            _set_dimensions(obj, params["dimensions"])
        _set_metadata(obj, params.get("metadata"))
        return _inspect(obj)
    if name == "precision_cad_status":
        scene = bpy.context.scene
        has_scene_props = hasattr(scene, "sketcher")
        module_available = importlib.util.find_spec("CAD_Sketcher") is not None
        registered = False
        if module_available:
            try:
                cad_module = __import__("CAD_Sketcher")
                registered = bool(getattr(getattr(cad_module, "global_data", None), "registered", False))
            except Exception:
                registered = False
        return {
            "available": module_available and has_scene_props,
            "module_available": module_available,
            "scene_properties_available": has_scene_props,
            "solver_registered": registered,
            "blender_version": list(bpy.app.version),
            "minimum_blender_version": [5, 0, 0],
            "license": "GPL-3.0-or-later (external dependency)",
        }
    if name == "precision_set_dimensions":
        obj = _require_object(params["name"])
        _set_dimensions(obj, params["dimensions"])
        return _inspect(obj)
    if name == "precision_inspect_geometry":
        target = params.get("name")
        objects = [_require_object(target)] if target else [o for o in bpy.context.scene.objects if o.name.startswith("PRECISION_")]
        return {"objects": [_inspect(o) for o in objects]}
    if name == "precision_validate_scene":
        tolerance = float(params.get("tolerance", 0.01))
        if tolerance <= 0 or tolerance >= 1:
            raise ValueError("tolerance must be between 0 and 1")
        objects = [o for o in bpy.context.scene.objects if o.name.startswith("PRECISION_") and o.type == "MESH"]
        issues = []
        for obj in objects:
            report = _inspect(obj)
            if params.get("require_ground_contact", True) and report["ground_z"] < -tolerance:
                issues.append({"object": obj.name, "code": "below_ground", "ground_z": report["ground_z"]})
            if report["non_manifold_edges"] and obj.get("allow_non_manifold") is not True:
                issues.append({"object": obj.name, "code": "non_manifold_edges", "count": report["non_manifold_edges"]})
        return {"passed": not issues, "tolerance": tolerance, "object_count": len(objects), "issues": issues}
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
    if name == "precision_save_checkpoint":
        filepath = os.path.abspath(params["filepath"])
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=True)
        return {"filepath": filepath, "exists": os.path.exists(filepath)}
    if name == "precision_commit":
        _transaction_prefix = None
        _transaction_preexisting = set()
        return {"ok": True}
    if name == "precision_abort":
        removed = 0
        if _transaction_prefix:
            for obj in list(bpy.data.objects):
                if _owned(obj.name, _transaction_prefix) and obj.name not in _transaction_preexisting:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed += 1
        _transaction_prefix = None
        _transaction_preexisting = set()
        return {"ok": True, "removed_new_objects": removed, "restored_preexisting_objects": False}
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
