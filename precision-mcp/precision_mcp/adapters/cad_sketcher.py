from precision_mcp.adapters.base import AdapterStatus


class CadSketcherAdapter:
    name = "cad_sketcher"

    def __init__(self, runtime_status: AdapterStatus):
        self._runtime_status = runtime_status

    def status(self) -> AdapterStatus:
        return self._runtime_status
