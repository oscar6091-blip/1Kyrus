"""DB lookups and contract-shaped response views."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import AppError, not_found
from ..models import ArtifactVersion, Decision, ExperimentRun, Job, Project, Stage

ACTIVE_JOB_STATES = ("queued", "running")
EMPTY_USAGE = {"input_tokens": None, "output_tokens": None, "calls": 0, "estimated_cost_usd": None}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(obj: Any) -> str:
    return hashlib.sha256(dumps(obj).encode("utf-8")).hexdigest()


# ---------- lookups ----------

def get_project(s: Session, project_id: str) -> Project:
    p = s.get(Project, project_id)
    if p is None:
        raise not_found("프로젝트")
    return p


def get_stage(s: Session, project_id: str, stage_no: int) -> Stage:
    if not 1 <= stage_no <= 6:
        raise not_found("단계")
    st = s.get(Stage, (project_id, stage_no))
    if st is None:
        raise not_found("단계")
    return st


def get_stages(s: Session, project_id: str) -> list[Stage]:
    return list(s.scalars(select(Stage).where(Stage.project_id == project_id).order_by(Stage.stage_no)))


def get_artifact(s: Session, project_id: str, artifact_id: str) -> ArtifactVersion:
    a = s.get(ArtifactVersion, artifact_id)
    if a is None or a.project_id != project_id:
        raise not_found("산출물")
    return a


def get_run(s: Session, project_id: str, run_id: str) -> ExperimentRun:
    r = s.get(ExperimentRun, run_id)
    if r is None or r.project_id != project_id:
        raise AppError("INVALID_RUN", "이 프로젝트에 저장된 실험 결과가 아닙니다.", [{"path": "run_id", "message": "다른 프로젝트이거나 없는 Run"}])
    return r


def active_job(s: Session, project_id: str) -> Job | None:
    return s.scalars(select(Job).where(Job.project_id == project_id, Job.status.in_(ACTIVE_JOB_STATES))).first()


def next_version(s: Session, project_id: str, stage_no: int) -> int:
    cur = s.scalar(select(func.max(ArtifactVersion.version)).where(
        ArtifactVersion.project_id == project_id, ArtifactVersion.stage_no == stage_no))
    return (cur or 0) + 1


def add_artifact(s: Session, project_id: str, stage_no: int, payload: dict, snapshot: dict, evidence: dict,
                 created_by: str, model: str | None) -> ArtifactVersion:
    a = ArtifactVersion(
        id=new_id(), project_id=project_id, stage_no=stage_no, version=next_version(s, project_id, stage_no),
        payload_json=dumps(payload), input_snapshot_json=dumps(snapshot), evidence_json=dumps(evidence),
        created_by=created_by, model=model, created_at=now(),
    )
    s.add(a)
    s.flush()
    return a


def touch(s: Session, project_id: str) -> None:
    p = s.get(Project, project_id)
    if p is not None:
        p.updated_at = now()


# ---------- views ----------

def project_summary(p: Project) -> dict:
    return {"id": p.id, "name": p.name, "idea": p.idea, "mode": p.mode,
            "current_brief_artifact_id": p.current_brief_artifact_id,
            "created_at": p.created_at, "updated_at": p.updated_at}


def artifact_view(a: ArtifactVersion) -> dict:
    from .rendering import render_markdown

    payload = json.loads(a.payload_json)
    evidence = json.loads(a.evidence_json)
    return {
        "id": a.id, "project_id": a.project_id, "stage_no": a.stage_no, "version": a.version,
        "payload": payload, "input_snapshot": json.loads(a.input_snapshot_json), "evidence": evidence,
        "rendered_markdown": render_markdown(a.stage_no, payload, evidence),
        "created_by": a.created_by, "created_at": a.created_at, "model": a.model,
    }


def job_view(j: Job) -> dict:
    return {
        "id": j.id, "project_id": j.project_id, "stage_no": j.stage_no, "status": j.status,
        "result_artifact_id": j.result_artifact_id,
        "error": json.loads(j.error_json) if j.error_json else None,
        "usage": json.loads(j.usage_json), "started_at": j.started_at, "finished_at": j.finished_at,
    }


def decision_record(d: Decision) -> dict:
    return {"id": d.id, "request_id": d.request_id, "project_id": d.project_id, "stage_no": d.stage_no,
            "artifact_id": d.artifact_id, "action": d.action, "comment": d.comment, "created_at": d.created_at}


def run_view(r: ExperimentRun) -> dict:
    return {"id": r.id, "project_id": r.project_id, "client_upload_id": r.client_upload_id,
            "payload": json.loads(r.payload_json), "created_at": r.created_at}


def stage_view(s: Session, st: Stage, stages: list[Stage] | None = None, job: Job | None | bool = False) -> dict:
    from .workflow import approval_block_reason, run_block_reason

    if job is False:
        job = active_job(s, st.project_id)
    stages = stages or get_stages(s, st.project_id)
    run_reason = run_block_reason(s, st, stages, job)
    approve_reason = approval_block_reason(s, st, stages, job)
    if st.status == "stale":
        disabled = "상위 단계가 새로 승인되어 이 결과는 오래됨(stale) 상태입니다. 읽기 전용이며 재생성해야 합니다."
    else:
        disabled = run_reason if (run_reason and approve_reason) else None
    return {
        "stage_no": st.stage_no, "status": st.status,
        "current_artifact_id": st.current_artifact_id, "approved_artifact_id": st.approved_artifact_id,
        "can_run": run_reason is None, "can_approve": approve_reason is None,
        "disabled_reason": disabled,
        "active_job_id": job.id if (job and job.stage_no == st.stage_no) else None,
    }
