bl_info = {
    "name": "Blender Precision MCP Companion",
    "author": "OPCspace",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "category": "3D View",
}

import json
import hashlib
import importlib
import math
import os
import re
import socket
import struct
import threading
import traceback
from dataclasses import dataclass, field
from mathutils import Vector

import bpy


HOST = "127.0.0.1"
PORT = int(os.getenv("PRECISION_BLENDER_PORT", "9877"))
MAX_FRAME_BYTES = 4 * 1024 * 1024
WORKDIR = os.path.realpath(
    os.path.abspath(os.path.expanduser(os.getenv("PRECISION_WORKDIR", os.getcwd())))
)
JOB_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
LEGACY_JOB_ID = "legacy-v1"
UNIT_TO_METERS = {"mm": 0.001, "cm": 0.01, "m": 1.0}
ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_server = None
_transaction_prefix = None
_transaction_preexisting = set()


@dataclass
class BlenderJob:
    job_id: str
    prefix: str
    checkpoint: str
    created_objects: set[str] = field(default_factory=set)
    state: str = "active"


_jobs = {}


def _safe_work_path(filepath):
    if not isinstance(filepath, (str, os.PathLike)) or not str(filepath):
        raise ValueError("filepath must be a non-empty path")
    candidate = os.path.expanduser(os.fspath(filepath))
    if not os.path.isabs(candidate):
        candidate = os.path.join(WORKDIR, candidate)
    path = os.path.realpath(os.path.abspath(candidate))
    try:
        contained = os.path.commonpath([path, WORKDIR]) == WORKDIR
    except ValueError:
        contained = False
    if not contained:
        raise ValueError(f"path must be inside PRECISION_WORKDIR: {WORKDIR}")
    return path


def _validate_job_id(job_id):
    if not isinstance(job_id, str) or JOB_ID_RE.fullmatch(job_id) is None:
        raise ValueError("job_id must match ^[a-z0-9][a-z0-9-]{0,63}$")
    return job_id


def _require_job(job_id, *, active=True):
    job_id = _validate_job_id(job_id)
    job = _jobs.get(job_id)
    if job is None:
        raise ValueError(f"job not found: {job_id}")
    if active and job.state != "active":
        raise ValueError(f"job is not active: {job_id} ({job.state})")
    return job


def _begin_job(job_id, *, checkpoint=None, prefix=None):
    job_id = _validate_job_id(job_id)
    existing = _jobs.get(job_id)
    if existing is not None and existing.state == "active":
        raise ValueError(f"job is already active: {job_id}")
    checkpoint = _safe_work_path(
        checkpoint or os.path.join("jobs", job_id, "before.blend")
    )
    os.makedirs(os.path.dirname(checkpoint), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=checkpoint, copy=True)
    job = BlenderJob(
        job_id=job_id,
        prefix=prefix or f"PRECISION_{job_id}_",
        checkpoint=checkpoint,
    )
    _jobs[job_id] = job
    return job


def _commit_job(job_id, filepath=None):
    job = _require_job(job_id)
    final_checkpoint = _safe_work_path(
        filepath or os.path.join("jobs", job_id, "final.blend")
    )
    os.makedirs(os.path.dirname(final_checkpoint), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=final_checkpoint, copy=True)
    job.state = "committed"
    return {
        "job_id": job.job_id,
        "state": job.state,
        "checkpoint": final_checkpoint,
    }


def _abort_job(job_id):
    job = _require_job(job_id)
    job.state = "aborted"
    restored = False
    removed = 0
    restore_error = None
    if os.path.isfile(job.checkpoint):
        try:
            bpy.ops.wm.open_mainfile(filepath=job.checkpoint)
            restored = True
        except Exception as exc:
            restore_error = str(exc)
    else:
        restore_error = f"checkpoint not found: {job.checkpoint}"
    if not restored:
        for object_name in sorted(job.created_objects):
            obj = bpy.data.objects.get(object_name)
            if obj is not None:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1
    return {
        "job_id": job.job_id,
        "state": job.state,
        "restored_checkpoint": restored,
        "removed_created_objects": removed,
        "restore_error": restore_error,
    }


def _track_created(job, *objects):
    for obj in objects:
        if obj is not None:
            job.created_objects.add(obj.name)


def _track_legacy_created(obj):
    job = _jobs.get(LEGACY_JOB_ID)
    if job is not None and job.state == "active":
        _track_created(job, obj)


def _validate_asset_id(asset_id):
    if not isinstance(asset_id, str) or ASSET_ID_RE.fullmatch(asset_id) is None:
        raise ValueError("asset_id contains unsupported characters")
    return asset_id


def _job_object_name(job, asset_id, suffix=None):
    asset_id = _validate_asset_id(asset_id)
    base = f"{job.prefix}{asset_id}"
    return f"{base}_{suffix}" if suffix else base


def _require_job_object(job, name):
    obj = _require_object(name)
    if name not in job.created_objects or obj.get("precision_job_id") != job.job_id:
        raise ValueError(f"object is not owned by job {job.job_id}: {name}")
    return obj


def _tag_job_object(job, obj, asset_id):
    obj["precision_job_id"] = job.job_id
    obj["precision_asset_id"] = asset_id
    _track_created(job, obj)


def _create_exact_primitive(name, primitive, dimensions, location):
    primitive = str(primitive).lower()
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"object already exists: {name}")
    if primitive == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    elif primitive == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64, radius=0.5, depth=1.0, location=location
        )
    elif primitive == "cone":
        bpy.ops.mesh.primitive_cone_add(
            vertices=64, radius1=0.5, radius2=0.0, depth=1.0, location=location
        )
    elif primitive == "uv_sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=64, ring_count=32, radius=0.5, location=location
        )
    else:
        raise ValueError("primitive must be cube, cylinder, cone or uv_sphere")
    obj = bpy.context.object
    obj.name = name
    _set_dimensions(obj, dimensions)
    return obj


def _orientation(a, b, c):
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (
        c[0] - a[0]
    )
    if abs(value) <= 1e-12:
        return 0
    return 1 if value > 0 else -1


def _point_on_segment(a, b, point):
    return (
        min(a[0], b[0]) - 1e-12 <= point[0] <= max(a[0], b[0]) + 1e-12
        and min(a[1], b[1]) - 1e-12
        <= point[1]
        <= max(a[1], b[1]) + 1e-12
    )


def _segments_intersect(a, b, c, d):
    orientations = (
        _orientation(a, b, c),
        _orientation(a, b, d),
        _orientation(c, d, a),
        _orientation(c, d, b),
    )
    if orientations[0] != orientations[1] and orientations[2] != orientations[3]:
        return True
    return any(
        orientation == 0 and _point_on_segment(start, end, point)
        for orientation, start, end, point in (
            (orientations[0], a, b, c),
            (orientations[1], a, b, d),
            (orientations[2], c, d, a),
            (orientations[3], c, d, b),
        )
    )


def _validate_simple_polygon(points):
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("profile must contain at least three 2D points")
    result = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"profile point {index} must contain X and Y")
        parsed = (float(point[0]), float(point[1]))
        if not all(math.isfinite(value) for value in parsed):
            raise ValueError(f"profile point {index} must be finite")
        result.append(parsed)
    if len(set(result)) != len(result):
        raise ValueError("profile is self-intersecting or contains repeated points")
    count = len(result)
    for first in range(count):
        first_next = (first + 1) % count
        for second in range(first + 1, count):
            second_next = (second + 1) % count
            if first in (second, second_next) or first_next in (second, second_next):
                continue
            if _segments_intersect(
                result[first],
                result[first_next],
                result[second],
                result[second_next],
            ):
                raise ValueError("profile is self-intersecting")
    signed_area = sum(
        result[index][0] * result[(index + 1) % count][1]
        - result[(index + 1) % count][0] * result[index][1]
        for index in range(count)
    )
    if abs(signed_area) <= 1e-12:
        raise ValueError("profile area must be nonzero")
    return result


def _object_world_bounds(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def _aggregate_bounds(objects):
    corners = [corner for obj in objects for corner in _object_world_bounds(obj)]
    if not corners:
        raise ValueError("cannot calculate bounds without objects")
    minimum = Vector(min(corner[axis] for corner in corners) for axis in range(3))
    maximum = Vector(max(corner[axis] for corner in corners) for axis in range(3))
    return minimum, maximum


def _job_asset_objects(job, asset_id, *, meshes_only=False):
    objects = []
    for name in sorted(job.created_objects):
        obj = bpy.data.objects.get(name)
        if obj is None or obj.get("precision_asset_id") != asset_id:
            continue
        if meshes_only and obj.type != "MESH":
            continue
        objects.append(obj)
    return objects


def _file_sha256(filepath):
    digest = hashlib.sha256()
    with open(filepath, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _apply_object_transform(obj, *, rotation=True, scale=True):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=rotation, scale=scale)


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


def _cad_import(module):
    for package in ("bl_ext.user_default.CAD_Sketcher", "CAD_Sketcher"):
        try:
            return importlib.import_module(package + module)
        except ModuleNotFoundError:
            continue
    raise RuntimeError("CAD Sketcher extension is not enabled in this Blender session")


def execute(command):
    global _transaction_prefix, _transaction_preexisting
    name = command.get("type")
    params = command.get("params", {})
    if name == "precision_begin_job":
        job = _begin_job(params["job_id"], checkpoint=params.get("checkpoint"))
        return {
            "job_id": job.job_id,
            "prefix": job.prefix,
            "checkpoint": job.checkpoint,
            "state": job.state,
        }
    if name == "precision_commit_job":
        return _commit_job(
            params["job_id"],
            params.get("filepath") or params.get("checkpoint"),
        )
    if name == "precision_abort_job":
        return _abort_job(params["job_id"])
    if name == "precision_create_part":
        job = _require_job(params["job_id"])
        asset_id = _validate_asset_id(params["asset_id"])
        object_name = _job_object_name(job, asset_id)
        dimensions = params.get("target_dimensions") or params.get("dimensions")
        location = params.get("location") or [0.0, 0.0, 0.0]
        obj = _create_exact_primitive(
            object_name,
            params.get("primitive", "cube"),
            dimensions,
            location,
        )
        obj.rotation_euler = [
            math.radians(float(value))
            for value in params.get("rotation_deg", [0.0, 0.0, 0.0])
        ]
        _tag_job_object(job, obj, asset_id)
        _set_metadata(obj, params.get("metadata"))
        obj["precision_anchors"] = json.dumps(
            params.get("anchors", {}), sort_keys=True, separators=(",", ":")
        )
        return {"job_id": job.job_id, "asset_id": asset_id, **_inspect(obj)}
    if name == "precision_profile_extrude":
        job = _require_job(params["job_id"])
        asset_id = _validate_asset_id(params["asset_id"])
        points = _validate_simple_polygon(params.get("points") or params.get("profile"))
        depth = float(params["depth"])
        if not math.isfinite(depth) or abs(depth) <= 1e-12:
            raise ValueError("extrusion depth must be nonzero")
        object_name = _job_object_name(job, asset_id)
        if bpy.data.objects.get(object_name) is not None:
            raise ValueError(f"object already exists: {object_name}")
        count = len(points)
        vertices = [(x, y, 0.0) for x, y in points]
        vertices.extend((x, y, depth) for x, y in points)
        faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
        faces.extend(
            (
                index,
                (index + 1) % count,
                (index + 1) % count + count,
                index + count,
            )
            for index in range(count)
        )
        mesh = bpy.data.meshes.new(object_name + "_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.validate(verbose=False)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(object_name, mesh)
        bpy.context.collection.objects.link(obj)
        _set_dimensions(
            obj,
            params.get("target_dimensions") or params.get("dimensions"),
        )
        obj.location = params.get("location") or [0.0, 0.0, 0.0]
        obj.rotation_euler = [
            math.radians(float(value))
            for value in params.get("rotation_deg", [0.0, 0.0, 0.0])
        ]
        _tag_job_object(job, obj, asset_id)
        obj["precision_anchors"] = json.dumps(
            params.get("anchors", {}), sort_keys=True, separators=(",", ":")
        )
        return {"job_id": job.job_id, "asset_id": asset_id, **_inspect(obj)}
    if name == "precision_import_asset":
        job = _require_job(params["job_id"])
        asset_id = _validate_asset_id(params["asset_id"])
        filepath = _safe_work_path(params["filepath"])
        if not os.path.isfile(filepath):
            raise ValueError(f"import file not found: {filepath}")
        extension = os.path.splitext(filepath)[1].lower()
        checksum = _file_sha256(filepath)
        expected_checksum = params.get("checksum")
        if expected_checksum:
            expected_digest = str(expected_checksum).removeprefix("sha256:").lower()
            if expected_digest != checksum:
                raise ValueError("import checksum does not match source file")
        root_name = _job_object_name(job, asset_id, "ROOT")
        if bpy.data.objects.get(root_name) is not None:
            raise ValueError(f"object already exists: {root_name}")
        before = set(bpy.data.objects)
        if extension in {".glb", ".gltf"}:
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif extension == ".fbx":
            if hasattr(bpy.ops.wm, "fbx_import"):
                bpy.ops.wm.fbx_import(filepath=filepath)
            else:
                bpy.ops.import_scene.fbx(filepath=filepath)
        else:
            raise ValueError("import format must be GLB, glTF or FBX")
        imported = sorted(
            (obj for obj in bpy.data.objects if obj not in before),
            key=lambda obj: obj.name,
        )
        if not imported:
            raise RuntimeError("import produced no Blender objects")
        root = bpy.data.objects.new(root_name, None)
        bpy.context.collection.objects.link(root)
        _tag_job_object(job, root, asset_id)
        for index, obj in enumerate(imported, start=1):
            world = obj.matrix_world.copy()
            source_name = obj.name
            obj.name = _job_object_name(job, asset_id, f"{index:03d}_{source_name}")
            obj.parent = root
            obj.matrix_world = world
            _tag_job_object(job, obj, asset_id)
        provenance = str(params.get("provenance") or f"imported:{os.path.basename(filepath)}")
        for obj in [root, *imported]:
            obj["precision_provenance"] = provenance
            obj["precision_checksum"] = f"sha256:{checksum}"
            obj["precision_source_path"] = filepath
        root["precision_anchors"] = json.dumps(
            params.get("anchors", {}), sort_keys=True, separators=(",", ":")
        )
        return {
            "job_id": job.job_id,
            "asset_id": asset_id,
            "root": root.name,
            "objects": [obj.name for obj in imported],
            "object_count": len(imported),
            "checksum": f"sha256:{checksum}",
            "provenance": provenance,
        }
    if name == "precision_normalize_asset":
        job = _require_job(params["job_id"])
        asset_id = _validate_asset_id(params["asset_id"])
        root_name = params.get("name") or _job_object_name(job, asset_id, "ROOT")
        root = _require_job_object(job, root_name)
        source_units = str(params.get("source_units", "m")).lower()
        target_units = str(params.get("target_units", "m")).lower()
        if source_units not in UNIT_TO_METERS or target_units not in UNIT_TO_METERS:
            raise ValueError("source_units and target_units must be mm, cm or m")
        source_axes = params.get("source_axes") or {}
        source_up_axis = str(
            params.get("source_up_axis") or source_axes.get("up") or "Z"
        ).upper()
        target_up_axis = str(params.get("target_up_axis", "Z")).upper()
        if source_up_axis not in {"Y", "Z"} or target_up_axis not in {"Y", "Z"}:
            raise ValueError("supported up axes are Y and Z")
        factor = UNIT_TO_METERS[source_units] / UNIT_TO_METERS[target_units]
        root.scale = (factor, factor, factor)
        # Deterministic right-handed up-axis conversion: +90° X maps Y-up to Z-up.
        if source_up_axis == "Y" and target_up_axis == "Z":
            root.rotation_euler.x = math.radians(90.0)
        elif source_up_axis == "Z" and target_up_axis == "Y":
            root.rotation_euler.x = math.radians(-90.0)
        else:
            root.rotation_euler.x = 0.0
        bpy.context.view_layer.update()
        meshes = _job_asset_objects(job, asset_id, meshes_only=True)
        if not meshes:
            raise ValueError(f"asset has no mesh objects: {asset_id}")
        minimum, maximum = _aggregate_bounds(meshes)
        current_dimensions = maximum - minimum
        target_dimensions = params.get("target_dimensions") or params.get("dimensions")
        scaling_mode = str(params.get("scaling_mode", "explicit_xyz"))
        if target_dimensions is not None:
            if len(target_dimensions) != 3 or any(float(value) <= 0 for value in target_dimensions):
                raise ValueError("target_dimensions must contain three positive numbers")
            if any(float(value) <= 1e-12 for value in current_dimensions):
                raise ValueError("cannot normalize an asset with a zero world dimension")
            ratios = [
                float(target_dimensions[index]) / float(current_dimensions[index])
                for index in range(3)
            ]
            if scaling_mode == "uniform":
                uniform_factor = min(ratios)
                root.scale = tuple(float(value) * uniform_factor for value in root.scale)
            elif scaling_mode in {"explicit", "explicit_xyz", "xyz"}:
                root.scale = tuple(
                    float(root.scale[index]) * ratios[index] for index in range(3)
                )
            else:
                raise ValueError("scaling_mode must be uniform or explicit_xyz")
        bpy.context.view_layer.update()
        world_matrices = {obj.name: obj.matrix_world.copy() for obj in meshes}
        root.rotation_euler = (0.0, 0.0, 0.0)
        root.scale = (1.0, 1.0, 1.0)
        bpy.context.view_layer.update()
        for obj in meshes:
            obj.matrix_world = world_matrices[obj.name]
            _apply_object_transform(obj)
        bpy.context.view_layer.update()
        minimum, maximum = _aggregate_bounds(meshes)
        provenance = str(
            params.get("provenance") or root.get("precision_provenance", "")
        )
        checksum = str(params.get("checksum") or root.get("precision_checksum", ""))
        for obj in [root, *meshes]:
            obj["precision_provenance"] = provenance
            obj["precision_checksum"] = checksum
            obj["precision_source_units"] = source_units
            obj["precision_target_units"] = target_units
            obj["precision_source_up_axis"] = source_up_axis
            obj["precision_target_up_axis"] = target_up_axis
            obj["precision_scaling_mode"] = scaling_mode
        return {
            "job_id": job.job_id,
            "asset_id": asset_id,
            "root": root.name,
            "source_units": source_units,
            "target_units": target_units,
            "source_up_axis": source_up_axis,
            "target_up_axis": target_up_axis,
            "scaling_mode": scaling_mode,
            "world_bbox_min": [round(float(value), 6) for value in minimum],
            "world_bbox_max": [round(float(value), 6) for value in maximum],
            "dimensions": [
                round(float(maximum[index] - minimum[index]), 6)
                for index in range(3)
            ],
            "provenance": provenance,
            "checksum": checksum,
        }
    if name == "precision_begin":
        prefix = params.get("prefix", "PRECISION_")
        existing = _jobs.get(LEGACY_JOB_ID)
        if existing is not None and existing.state == "active":
            existing.state = "superseded"
        _begin_job(LEGACY_JOB_ID, prefix=prefix)
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
        _track_legacy_created(obj)
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
        _track_legacy_created(obj)
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
    if name == "precision_build_model_spec":
        spec = params.get("spec") or {}
        category = spec.get("category")
        dimensions = spec.get("dimensions")
        parts = spec.get("parts")
        allowed_categories = {"character", "creature", "props", "architecture", "hard_surface", "environment", "abstract"}
        if category not in allowed_categories:
            raise ValueError("model_spec.category is not a supported BaseMesh category")
        if not isinstance(dimensions, list) or len(dimensions) != 3 or any(float(v) <= 0 for v in dimensions):
            raise ValueError("model_spec.dimensions must contain three positive numbers")
        if not isinstance(parts, list) or not parts:
            raise ValueError("model_spec.parts must contain at least one part")
        prefix = str(spec.get("prefix", "PRECISION_"))
        asset = str(spec.get("asset", category))
        created = []
        for index, part in enumerate(parts):
            if not isinstance(part, dict) or not part.get("name"):
                raise ValueError(f"model_spec.parts[{index}] must have a name")
            part_dims = part.get("dimensions")
            if not isinstance(part_dims, list) or len(part_dims) != 3 or any(float(v) <= 0 for v in part_dims):
                raise ValueError(f"model_spec.parts[{index}].dimensions must contain three positive numbers")
            part_name = f"{prefix}{asset}_{part['name']}"
            result = execute({"type": "precision_create_primitive", "params": {
                "name": part_name,
                "primitive": part.get("primitive", "cube"),
                "dimensions": part_dims,
                "location": part.get("location", [0.0, 0.0, float(part_dims[2]) / 2.0]),
                "metadata": {
                    "base_mesh_category": category,
                    "source_prompt": str(spec.get("source_prompt", "")),
                    "reference_confidence": float(spec.get("reference_confidence", 1.0)),
                    "model_spec_asset": asset,
                },
            }})
            created.append(result)
        return {"category": category, "asset": asset, "target_dimensions": dimensions, "parts": created, "part_count": len(created)}
    if name == "precision_cad_status":
        scene = bpy.context.scene
        has_scene_props = hasattr(scene, "sketcher")
        solver_available = False
        try:
            import slvs  # noqa: F401
            solver_available = True
        except Exception:
            solver_available = False
        sketcher_ops = getattr(bpy.ops, "sketcher", None)
        operator_available = bool(sketcher_ops and hasattr(sketcher_ops, "slvs_add_sketch"))
        registered = has_scene_props and solver_available and operator_available
        return {
            "available": registered,
            "module_available": has_scene_props,
            "scene_properties_available": has_scene_props,
            "solver_available": solver_available,
            "operator_available": operator_available,
            "solver_registered": registered,
            "blender_version": list(bpy.app.version),
            "minimum_blender_version": [5, 0, 0],
            "license": "GPL-3.0-or-later (external dependency)",
        }
    if name == "precision_create_cad_rectangle":
        width = float(params["width"])
        height = float(params["height"])
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        if not hasattr(bpy.context.scene, "sketcher"):
            raise RuntimeError("CAD Sketcher scene properties are not available")
        sketch_ref = _cad_import(".model.sketch_ref")
        curve_ref = _cad_import(".model.curve_ref")
        solver = _cad_import(".curve_solver")
        curve = bpy.data.hair_curves.new(params["name"] + "_Sketch")
        obj = bpy.data.objects.new(params["name"], curve)
        bpy.context.scene.collection.objects.link(obj)
        _track_legacy_created(obj)
        sketch_ref.stamp_sketch_props(obj)
        sketch = sketch_ref.Sketch(obj)
        bpy.context.scene.sketcher.active_sketch_object = obj
        p0 = curve_ref.PointRef.create(sketch, (0.0, 0.0), fixed=True, name="Origin")
        p1 = curve_ref.PointRef.create(sketch, (width, 0.0), name="WidthPoint")
        p2 = curve_ref.PointRef.create(sketch, (width, height), name="CornerPoint")
        p3 = curve_ref.PointRef.create(sketch, (0.0, height), name="HeightPoint")
        lines = [
            curve_ref.LineRef.create(sketch, p0, p1, name="Bottom"),
            curve_ref.LineRef.create(sketch, p1, p2, name="Right"),
            curve_ref.LineRef.create(sketch, p2, p3, name="Top"),
            curve_ref.LineRef.create(sketch, p3, p0, name="Left"),
        ]
        constraints = sketch.constraints
        constraints.add_horizontal(curve_id_1=lines[0].curve_id)
        constraints.add_vertical(curve_id_1=lines[1].curve_id)
        constraints.add_horizontal(curve_id_1=lines[2].curve_id)
        constraints.add_vertical(curve_id_1=lines[3].curve_id)
        constraints.add_distance(init=True, curve_id_1=p0.curve_id, curve_id_2=p1.curve_id, value=width, align="HORIZONTAL", flip=False)
        constraints.add_distance(init=True, curve_id_1=p0.curve_id, curve_id_2=p3.curve_id, value=height, align="VERTICAL", flip=False)
        solved = bool(solver.solve_system(bpy.context, sketch=sketch))
        sketch.geometry_solved = solved
        return {
            "name": obj.name,
            "solved": solved,
            "solver_state": sketch.solver_state,
            "dof": sketch.dof,
            "entity_count": len(curve.curves),
            "constraint_count": sum(1 for _ in constraints.all),
            "target_dimensions": [width, height],
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
        if _jobs.get(LEGACY_JOB_ID) is not None and _jobs[LEGACY_JOB_ID].state == "active":
            _commit_job(LEGACY_JOB_ID)
        _transaction_prefix = None
        _transaction_preexisting = set()
        return {"ok": True}
    if name == "precision_abort":
        job = _jobs.get(LEGACY_JOB_ID)
        if job is not None and job.state == "active":
            abort_result = _abort_job(LEGACY_JOB_ID)
            removed = abort_result["removed_created_objects"]
            restored = abort_result["restored_checkpoint"]
        else:
            removed = 0
            restored = False
        _transaction_prefix = None
        _transaction_preexisting = set()
        return {"ok": True, "removed_new_objects": removed, "restored_preexisting_objects": restored}
    raise ValueError(f"unsupported precision command: {name}")


def _recv_exact(client, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = client.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _send_response(client, payload):
    body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        body = json.dumps(
            {
                "status": "error",
                "request_id": payload.get("request_id"),
                "message": "response exceeds maximum frame size",
                "error_type": "ProtocolError",
            },
            separators=(",", ":"),
        ).encode("utf-8")
    client.sendall(struct.pack("!I", len(body)) + body)


def _error_payload(request_id, exc):
    return {
        "status": "error",
        "request_id": request_id,
        "message": str(exc),
        "error_type": type(exc).__name__,
    }


def _execute_queued(client, request):
    try:
        result = execute(request)
        payload = {
            "status": "success",
            "request_id": request["request_id"],
            "result": result,
        }
    except Exception as exc:
        traceback.print_exc()
        payload = _error_payload(request.get("request_id"), exc)
    try:
        _send_response(client, payload)
    finally:
        client.close()
    return None


def _handle(client):
    request_id = None
    try:
        frame_size = struct.unpack("!I", _recv_exact(client, 4))[0]
        if frame_size == 0:
            raise ValueError("request frame is empty")
        if frame_size > MAX_FRAME_BYTES:
            raise ValueError("request exceeds maximum frame size")
        body = _recv_exact(client, frame_size)
        request = json.loads(body.decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(request.get("type"), str):
            raise ValueError("request type must be a string")
        if not isinstance(request.get("params", {}), dict):
            raise ValueError("request params must be a JSON object")
        bpy.app.timers.register(
            lambda c=client, r=request: _execute_queued(c, r),
            first_interval=0.0,
        )
    except Exception as exc:
        traceback.print_exc()
        try:
            _send_response(client, _error_payload(request_id, exc))
        finally:
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
                _handle(client)
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
