"""Canonical evidence artifacts and explicit precision job state transitions."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TRANSITIONS = {
    "planned": {"active", "aborted"},
    "active": {"validating", "aborted", "external_pending", "external_failed"},
    "validating": {"committed", "failed_qa", "aborted"},
    "external_pending": {"active", "external_failed", "aborted"},
    "external_failed": {"active", "aborted"},
    "failed_qa": {"active", "aborted"},
    "committed": set(),
    "aborted": set(),
}

_JOB_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_CHECKPOINT_NAMES = {"before", "failed", "final"}
_PREVIEW_NAMES = {"orthographic", "perspective"}


@dataclass
class JobState:
    job_id: str
    value: str = "planned"

    def transition(self, target: str) -> None:
        if target not in TRANSITIONS[self.value]:
            raise ValueError(f"invalid transition: {self.value} -> {target}")
        self.value = target


class EvidenceBundle:
    def __init__(self, workdir: Path, job_id: str):
        if _JOB_ID.fullmatch(job_id) is None:
            raise ValueError(f"invalid job_id: {job_id!r}")
        self._workdir = workdir.resolve()
        self._evidence_parent = self._workdir / "evidence"
        self.root = self._evidence_parent / job_id
        self._ensure_evidence_root_contained()
        self.root.mkdir(parents=True, exist_ok=True)

    def _ensure_within_workdir(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self._workdir)
        except ValueError as error:
            raise ValueError(f"evidence root escapes workdir: {path}") from error

    def _ensure_evidence_root_contained(self) -> None:
        self._ensure_within_workdir(self._evidence_parent)
        self._ensure_within_workdir(self.root)

    def _contained_path(self, *parts: str) -> Path:
        self._ensure_evidence_root_contained()
        path = self.root.joinpath(*parts)
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError(f"evidence path escapes bundle root: {path}")
        return path

    def write_contract(self, name: str, document: dict[str, Any]) -> Path:
        path = self._contained_path(f"{name}.json")
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def write_assumptions(self, assumptions: list[str]) -> Path:
        path = self._contained_path("assumptions.md")
        body = "# Unresolved assumptions\n\n" + "".join(
            f"- {item}\n" for item in assumptions
        )
        path.write_text(body, encoding="utf-8")
        return path

    def checkpoint_path(self, name: str) -> Path:
        if name not in _CHECKPOINT_NAMES:
            raise ValueError(f"invalid checkpoint name: {name!r}")
        path = self._contained_path("checkpoints", f"{name}.blend")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def preview_path(self, name: str) -> Path:
        if name not in _PREVIEW_NAMES:
            raise ValueError(f"invalid preview name: {name!r}")
        path = self._contained_path("previews", f"{name}.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
