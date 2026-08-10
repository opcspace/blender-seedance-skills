from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AdapterStatus:
    available: bool
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AssetAdapter(Protocol):
    name: str

    def status(self) -> AdapterStatus: ...
