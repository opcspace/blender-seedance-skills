from precision_mcp.adapters.base import AdapterStatus


DEFERRED_REASON = "online integration is deferred in Precision Core V2 phase one"


class TripoAdapter:
    name = "tripo"

    def status(self) -> AdapterStatus:
        return AdapterStatus(False, DEFERRED_REASON)
