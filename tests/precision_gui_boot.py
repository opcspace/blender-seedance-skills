"""Legacy GUI boot diagnostic; this is not Precision Core V2 proof."""
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
addon_path = ROOT / "precision-mcp" / "blender_addon" / "precision_addon.py"
namespace = runpy.run_path(addon_path)
namespace["register"]()
print("PRECISION_GUI_BOOT_OK", flush=True)
