#!/usr/bin/env python3
"""Check the local Blender, Blender MCP, and Jimeng uploader prerequisites."""

from __future__ import annotations

import json
import os
import pathlib
import sys
import re


HOME = pathlib.Path.home()
BLENDER = pathlib.Path("/Applications/Blender.app/Contents/MacOS/Blender")
BLENDER_ADDON = HOME / "Library/Application Support/Blender/5.2/scripts/addons/blender_addon"
JIMENG_ADDON = HOME / "Library/Application Support/Blender/5.2/scripts/addons/jimeng_blender_uploader"
CONFIG = HOME / ".codex/config.toml"
ROOT = pathlib.Path(os.environ.get("BLENDER_WORKSPACE", pathlib.Path.cwd()))


def check_path(path: pathlib.Path) -> dict[str, object]:
    return {"path": str(path), "exists": path.exists(), "is_dir": path.is_dir()}


def main() -> int:
    checks = {
        "blender_executable": check_path(BLENDER),
        "blender_mcp_addon": check_path(BLENDER_ADDON),
        "jimeng_uploader_addon": check_path(JIMENG_ADDON),
        "codex_launcher": check_path(ROOT / "launcher.py"),
        "codex_venv": check_path(ROOT / ".venv/bin/python"),
        "mcp_token": check_path(HOME / ".config/blender-mcp/token"),
    }
    config_ok = False
    config_error = ""
    if CONFIG.exists():
        try:
            text = CONFIG.read_text(encoding="utf-8")
            section = re.search(r"(?ms)^\[mcp_servers\.blender\]\s*(.*?)(?=^\[|\Z)", text)
            config_ok = bool(section and re.search(r"^command\s*=\s*\"[^\"]+\"", section.group(1), re.M) and re.search(r"^args\s*=", section.group(1), re.M))
        except Exception as exc:  # pragma: no cover - diagnostic path
            config_error = str(exc)
    checks["codex_blender_mcp_config"] = {"path": str(CONFIG), "valid": config_ok, "error": config_error}
    checks["volcengine_api"] = {
        "configured": bool(os.environ.get("VOLCENGINE_API_KEY") or os.environ.get("ARK_API_KEY")),
        "model_configured": bool(os.environ.get("VOLCENGINE_SEEDANCE_MODEL")),
        "note": "Optional; required only for direct Volcengine generation.",
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    required = ("blender_executable", "blender_mcp_addon", "jimeng_uploader_addon", "codex_launcher", "codex_venv")
    return 0 if all(checks[name].get("exists") for name in required) and config_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
