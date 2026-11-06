"""StageRunner: produce (payload, evidence) for a job from its frozen snapshot.

demo: pre-written fixtures, saved through the same validation and storage path.
live: app/stages/* via the LLMGateway. Live failures never fall back to fixtures (WF-13).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..db import tx
from . import jobs
from .context import build_evidence, validation_context
from .fixtures import reference_snapshot, stage_fixture
from .validation import validate_payload


@dataclass
class GenerationResult:
    payload: dict
    evidence: dict
    created_by: str
    model: str | None


def generate(project_id: str, stage_no: int, snapshot: dict, mode: str, usage: dict) -> GenerationResult:
    if mode == "demo":
        return _demo(project_id, stage_no, snapshot)
    from ..stages import generate_live

    return generate_live(project_id, stage_no, snapshot, usage)


def _demo(project_id: str, stage_no: int, snapshot: dict) -> GenerationResult:
    jobs.sleep(settings.demo_stage_delay_seconds)
    with tx() as s:
        refs = {r["id"]: r for r in reference_snapshot()} if stage_no == 2 else None
        evidence = build_evidence(s, project_id, stage_no, snapshot, s2_references=refs)
        ctx = validation_context(s, project_id, stage_no, snapshot, evidence)
        payload = validate_payload(stage_no, stage_fixture(stage_no), ctx)
    return GenerationResult(payload=payload, evidence=evidence, created_by="fixture", model=None)
