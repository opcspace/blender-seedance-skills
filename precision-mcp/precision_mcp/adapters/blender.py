from precision_mcp.adapters.base import AdapterStatus


class BlenderAdapter:
    name = "blender"

    def status(self) -> AdapterStatus:
        return AdapterStatus(True)
