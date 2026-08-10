"""Legacy category direct-socket diagnostic; this is not Precision Core V2 proof."""

import json
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def call(command, params=None):
    with socket.create_connection(("127.0.0.1", 9877), timeout=20) as sock:
        sock.sendall(json.dumps({"type": command, "params": params or {}}).encode())
        data = sock.recv(262144)
    response = json.loads(data.decode())
    if response.get("status") == "error":
        raise RuntimeError(response.get("message"))
    return response["result"]


categories = ["character", "creature", "props", "architecture", "hard_surface", "environment", "abstract"]
for category in categories:
    call("precision_begin", {"prefix": f"PRECISION_{category}_", "clean_existing": True})
    result = call("precision_build_model_spec", {"spec": {
        "category": category,
        "asset": f"{category}_contract_test",
        "dimensions": [2.0, 2.0, 2.0],
        "tolerance": 0.01,
        "parts": [
            {"name": "root", "primitive": "cube", "dimensions": [2.0, 2.0, 1.0], "location": [0, 0, 0.5]},
            {"name": "detail", "primitive": "cylinder", "dimensions": [0.5, 0.5, 1.0], "location": [0, 0, 1.5]},
        ],
    }})
    assert result["category"] == category
    assert result["part_count"] == 2
    qa = call("precision_validate_scene", {"tolerance": 0.01, "require_ground_contact": True})
    assert qa["passed"] is True, (category, qa)
    print(category, "parts=2", "qa=passed")
    call("precision_commit")
