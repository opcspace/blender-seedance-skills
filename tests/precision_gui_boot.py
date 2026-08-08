"""Launch helper for a real GUI Blender precision-MCP integration test."""
import runpy

addon_path = "/Users/jiangye/project/blender/blender-seedance-skills-repo/precision-mcp/blender_addon/precision_addon.py"
namespace = runpy.run_path(addon_path)
namespace["register"]()
print("PRECISION_GUI_BOOT_OK", flush=True)
