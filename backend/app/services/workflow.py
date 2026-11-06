"""WorkflowService: stage state, approval pointers, Decisions, staleness, request dedupe.

Every write runs in one short BEGIN IMMEDIATE transaction that rereads state.
Network calls never happen here (jobs run them after commit).
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import compact, tx
from ..errors import AppError
from ..models import ArtifactVersion, Decision, ExperimentRun, Job, Project, Stage
from ..schemas.domain import DecisionRequest, EditRequest, ProjectCreate, RunRequest
from . import jobs
from .context import build_snapshot, snapshot_is_current, validation_context
from .repository import (EMPTY_USAGE, active_job, add_artifact, artifact_view, decision_record, dumps,
                         fingerprint, get_artifact, get_project, get_run, get_stage, get_stages, job_view,
                         new_id, now, project_summary, stage_view, touch)
from .validation import validate_payload

log = logging.getLogger("workflow")

BUSY_MSG = "이 프로젝트에서 작업이 진행 중입니다. 완료된 뒤 다시 시도하세요. 조회와 화면 이동은 가능합니다."
STALE_MSG = "상위 단계가 새로 승인되어 이 결과는 오래됨(stale) 상태입니다. 수정·승인할 수 없으니 재생성하세요."


# ---------- read-side helpers used by stage_view ----------

def _predecessor_problem(stage_no: int, stages: list[Stage]) -> str | None:
    for st in stages:
        if st.stage_no < stage_no and not (st.status == "approved" and st.approved_artifact_id):
            return f"S{st.stage_no}이(가) 승인되지 않았습니다. 이전 단계를 모두 승인해야 실행할 수 있습니다."
    return None


def run_block_reason(s: Session, st: Stage, stages: list[Stage], job: Job | None) -> str | None:
    if job is not None:
        return BUSY_MSG
    return _predecessor_problem(st.stage_no, stages)


def approval_block_reason(s: Session, st: Stage, stages: list[Stage], job: Job | None) -> str | None:
    if job is not None:
        return BUSY_MSG
    if st.status == "stale":
        return STALE_MSG
    if st.status != "needs_review":
        return {"pending": "아직 결과가 없습니다.", "running": "생성 중입니다.",
                "approved": "이미 승인되었습니다."}.get(st.status, "승인할 수 없는 상태입니다.")
    if not st.current_artifact_id:
        return "검토할 결과가 없습니다. 다시 실행하세요."
    if st.current_artifact_id == st.approved_artifact_id:
        return "기존 승인본과 다른 새 초안이 없습니다."
    pred = _predecessor_problem(st.stage_no, stages)
    if pred:
        return pred
    art = get_artifact(s, st.project_id, st.current_artifact_id)
    if not snapshot_is_current(json.loads(art.input_snapshot_json), st.stage_no, stages):
        return "이 결과의 입력 버전이 현재 승인본과 다릅니다. 재생성하세요."
    return None


# ---------- projects ----------

def create_project(body: ProjectCreate) -> dict:
    with tx() as s:
        ts = now()
        mode = body.mode or settings.app_mode
        # Only an explicit choice is checked here; an APP_MODE=live default keeps the contract (run -> 503).
        if body.mode == "live" and not jobs.live_available():
            raise AppError("LIVE_NOT_CONFIGURED", "서버에 ANTHROPIC_API_KEY 또는 LLM_MODEL이 설정되지 않아 live 프로젝트를 만들 수 없습니다.")
        p = Project(id=new_id(), name=body.name, idea=body.idea, mode=mode,
                    current_brief_artifact_id=None, created_at=ts, updated_at=ts)
        s.add(p)
        s.flush()
        for n in range(1, 7):
            s.add(Stage(project_id=p.id, stage_no=n, status="pending"))
        return project_summary(p)


def delete_project(project_id: str) -> None:
    """DEVIATIONS D-04: remove a project and every row that belongs to it.

    Refused while a job is queued or running, so the worker never writes into a deleted project.
    Pointers are cleared first because the schema has no ON DELETE CASCADE.
    """
    with tx() as s:
        p = get_project(s, project_id)
        if active_job(s, project_id):
            raise AppError("PROJECT_BUSY", "진행 중인 작업이 끝난 뒤에 삭제할 수 있습니다.")
        p.current_brief_artifact_id = None
        s.execute(update(Stage).where(Stage.project_id == project_id)
                  .values(current_artifact_id=None, approved_artifact_id=None))
        s.flush()
        for model in (Decision, Job, ArtifactVersion, ExperimentRun, Stage):
            s.execute(delete(model).where(model.project_id == project_id))
        s.delete(p)
    # The delete is committed. Clean the file so the deleted text does not stay in free pages or the WAL.
    # A failure here (e.g. the DB is busy for more than 5 s) leaves the delete in place and is only logged.
    try:
        compact()
    except Exception:  # noqa: BLE001
        log.warning("project %s deleted, but VACUUM/WAL checkpoint failed", project_id, exc_info=True)


def list_projects() -> list[dict]:
    with tx() as s:
        rows = s.scalars(select(Project).order_by(Project.updated_at.desc()).limit(100))
        return [project_summary(p) for p in rows]


def project_detail(project_id: str) -> dict:
    with tx() as s:
        p = get_project(s, project_id)
        stages = get_stages(s, project_id)
        job = active_job(s, project_id)
        brief = artifact_view(get_artifact(s, project_id, p.current_brief_artifact_id)) if p.current_brief_artifact_id else None
        return {"project": project_summary(p), "stages": [stage_view(s, st, stages, job) for st in stages],
                "brief": brief, "active_job": job_view(job) if job else None}


def stage_detail(project_id: str, stage_no: int) -> dict:
    with tx() as s:
        get_project(s, project_id)
        st = get_stage(s, project_id, stage_no)
        cur = get_artifact(s, project_id, st.current_artifact_id) if st.current_artifact_id else None
        appr = get_artifact(s, project_id, st.approved_artifact_id) if st.approved_artifact_id else None
        return {"stage": stage_view(s, st), "current_artifact": artifact_view(cur) if cur else None,
                "approved_artifact": artifact_view(appr) if appr else None}


def list_decisions(project_id: str) -> list[dict]:
    with tx() as s:
        get_project(s, project_id)
        rows = list(s.scalars(select(Decision).where(Decision.project_id == project_id)
                              .order_by(Decision.created_at.desc()).limit(100)))
        return [decision_record(d) for d in reversed(rows)]


def get_artifact_view(project_id: str, artifact_id: str) -> dict:
    with tx() as s:
        get_project(s, project_id)
        return artifact_view(get_artifact(s, project_id, artifact_id))


def get_job(job_id: str) -> dict:
    with tx() as s:
        j = s.get(Job, job_id)
        if j is None:
            raise AppError("NOT_FOUND", "작업을 찾을 수 없습니다.")
        return job_view(j)


# ---------- run / regenerate ----------

def _check_s5_run(s: Session, project_id: str, run_id: str | None, stages: list[Stage]) -> str:
    if not run_id:
        raise AppError("INVALID_RUN", "S5는 분석할 실험 결과(Run)를 선택해야 합니다.", [{"path": "run_id", "message": "필수"}])
    run = get_run(s, project_id, run_id)
    payload = json.loads(run.payload_json)
    s3 = get_artifact(s, project_id, stages[2].approved_artifact_id)
    exps = {e["id"]: e for e in json.loads(s3.payload_json)["content"]["experiments"]}
    exp = exps.get(payload["experiment_id"])
    if exp is None:
        raise AppError("INVALID_RUN", "선택한 Run의 실험 ID가 현재 승인된 S3 계획에 없습니다.",
                       [{"path": "experiment_id", "message": f"{payload['experiment_id']} 없음"}])
    names = {m["name"] for m in payload["metrics"]}
    missing = [n for n in exp["metric_names"] if n not in names]
    if missing:
        raise AppError("INVALID_RUN", "선택한 Run에 승인된 S3의 필수 지표가 없습니다.",
                       [{"path": "metrics", "message": f"누락: {', '.join(missing)}"}])
    return run_id


def _enqueue(s: Session, p: Project, st: Stage, stages: list[Stage], comments: str, run_id: str | None,
             request_id: str, request_key: str, fp: str) -> Job:
    if p.mode == "live" and not jobs.live_available():
        raise AppError("LIVE_NOT_CONFIGURED", "live 프로젝트지만 서버에 ANTHROPIC_API_KEY 또는 LLM_MODEL이 설정되지 않았습니다.")
    pred = _predecessor_problem(st.stage_no, stages)
    if pred:
        raise AppError("PREDECESSOR_NOT_APPROVED", pred)
    if st.stage_no == 5:
        run_id = _check_s5_run(s, p.id, run_id, stages)
    else:
        run_id = None
    snapshot = build_snapshot(p, st, stages, comments, run_id)
    job = Job(id=new_id(), request_id=request_id, request_key=request_key, request_fingerprint=fp,
              project_id=p.id, stage_no=st.stage_no, status="queued", input_snapshot_json=dumps(snapshot),
              result_artifact_id=None, usage_json=dumps(EMPTY_USAGE), error_json=None, created_at=now())
    s.add(job)
    try:
        s.flush()
    except IntegrityError as exc:  # partial unique index: one active job per project
        raise AppError("PROJECT_BUSY", BUSY_MSG) from exc
    st.status = "running"
    touch(s, p.id)
    return job


def run_stage(project_id: str, stage_no: int, body: RunRequest) -> dict:
    key = f"run:{project_id}:{stage_no}:{body.request_id}"
    fp = fingerprint({"op": "run", "project": project_id, "stage": stage_no, "body": body.model_dump()})
    submit = None
    with tx() as s:
        existing = s.scalars(select(Job).where(Job.request_key == key)).first()
        if existing is not None:
            if existing.request_fingerprint != fp:
                raise AppError("REQUEST_ID_CONFLICT", "같은 request_id가 다른 내용으로 이미 사용되었습니다.")
            return job_view(existing)
        p = get_project(s, project_id)
        st = get_stage(s, project_id, stage_no)
        if active_job(s, project_id) is not None:
            raise AppError("PROJECT_BUSY", BUSY_MSG)
        stages = get_stages(s, project_id)
        job = _enqueue(s, p, st, stages, body.user_comments, body.run_id, body.request_id, key, fp)
        submit = job.id
        view = job_view(job)
    jobs.submit(submit)
    return view


# ---------- decisions ----------

def _decision_response(s: Session, d: Decision) -> dict:
    st = get_stage(s, d.project_id, d.stage_no)
    job = s.get(Job, d.job_id) if d.job_id else None
    art = get_artifact(s, d.project_id, d.result_artifact_id) if d.result_artifact_id else None
    return {"decision": decision_record(d), "stage": stage_view(s, st), "job": job_view(job) if job else None,
            "artifact": artifact_view(art) if art else None, "navigate_to_stage": d.navigate_to_stage}


def _dedupe_decision(s: Session, key: str, fp: str) -> Decision | None:
    d = s.scalars(select(Decision).where(Decision.request_key == key)).first()
    if d is not None and d.request_fingerprint != fp:
        raise AppError("REQUEST_ID_CONFLICT", "같은 request_id가 다른 내용으로 이미 사용되었습니다.")
    return d


def decide(project_id: str, stage_no: int, body: DecisionRequest) -> dict:
    key = f"decision:{project_id}:{stage_no}:{body.request_id}"
    fp = fingerprint({"op": "decision", "project": project_id, "stage": stage_no, "body": body.model_dump()})
    submit = None
    with tx() as s:
        prior = _dedupe_decision(s, key, fp)
        if prior is not None:
            return _decision_response(s, prior)
        p = get_project(s, project_id)
        st = get_stage(s, project_id, stage_no)
        art = get_artifact(s, project_id, body.artifact_id)
        if art.stage_no != stage_no:
            raise AppError("NOT_FOUND", "이 단계의 산출물이 아닙니다.")
        if body.action == "back" and stage_no == 1:
            raise AppError("INVALID_PAYLOAD", "S1에는 이전 단계가 없습니다.", [{"path": "action", "message": "S1 back 불가"}])
        job = active_job(s, project_id)
        if job is not None:
            raise AppError("PROJECT_BUSY", BUSY_MSG)
        stages = get_stages(s, project_id)
        d = Decision(id=new_id(), request_id=body.request_id, request_key=key, request_fingerprint=fp,
                     project_id=project_id, stage_no=stage_no, artifact_id=art.id, action=body.action,
                     comment=body.comment, result_artifact_id=None, job_id=None, navigate_to_stage=None,
                     created_at=now())

        if body.action == "approve":
            if st.status == "stale":
                raise AppError("INVALID_STAGE_STATE", STALE_MSG)
            if st.current_artifact_id != art.id:
                raise AppError("ARTIFACT_NOT_CURRENT", "현재 검토 중인 최신 결과만 승인할 수 있습니다.")
            if st.status != "needs_review":
                raise AppError("INVALID_STAGE_STATE", f"현재 상태({st.status})에서는 승인할 수 없습니다.")
            if st.current_artifact_id == st.approved_artifact_id:
                raise AppError("INVALID_STAGE_STATE", "기존 승인본과 다른 새 초안이 없습니다.")
            pred = _predecessor_problem(stage_no, stages)
            if pred:
                raise AppError("PREDECESSOR_NOT_APPROVED", pred)
            snapshot = json.loads(art.input_snapshot_json)
            if not snapshot_is_current(snapshot, stage_no, stages):
                raise AppError("STALE_INPUT", "이 결과를 만든 입력 버전이 현재 승인본과 다릅니다. 재생성한 뒤 승인하세요.")
            evidence = json.loads(art.evidence_json)
            validate_payload(stage_no, json.loads(art.payload_json),
                             validation_context(s, project_id, stage_no, snapshot, evidence))
            st.status = "approved"
            st.approved_artifact_id = art.id
            if stage_no == 1:
                p.current_brief_artifact_id = art.id
            for other in stages:
                if other.stage_no > stage_no and other.current_artifact_id:
                    other.status = "stale"

        elif body.action == "regenerate":
            if st.current_artifact_id != art.id:
                raise AppError("ARTIFACT_NOT_CURRENT", "현재 결과를 기준으로만 재생성할 수 있습니다.")
            run_id = body.run_id
            if stage_no == 5 and not run_id:
                run_id = json.loads(art.input_snapshot_json).get("run_id")
            job = _enqueue(s, p, st, stages, body.comment, run_id, body.request_id,
                           f"regenerate-job:{project_id}:{stage_no}:{body.request_id}", fp)
            d.job_id = job.id
            submit = job.id

        else:  # back
            if st.status not in ("needs_review", "approved", "stale"):
                raise AppError("INVALID_STAGE_STATE", f"현재 상태({st.status})에서는 이전 단계로 이동할 수 없습니다.")
            d.navigate_to_stage = stage_no - 1

        s.add(d)
        s.flush()
        touch(s, project_id)
        resp = _decision_response(s, d)
    if submit:
        jobs.submit(submit)
    return resp


def edit(project_id: str, stage_no: int, body: EditRequest) -> dict:
    key = f"edit:{project_id}:{stage_no}:{body.request_id}"
    fp = fingerprint({"op": "edit", "project": project_id, "stage": stage_no, "body": body.model_dump()})
    with tx() as s:
        prior = _dedupe_decision(s, key, fp)
        if prior is not None:
            return _decision_response(s, prior)
        get_project(s, project_id)
        st = get_stage(s, project_id, stage_no)
        base = get_artifact(s, project_id, body.base_artifact_id)
        if base.stage_no != stage_no:
            raise AppError("NOT_FOUND", "이 단계의 산출물이 아닙니다.")
        if active_job(s, project_id) is not None:
            raise AppError("PROJECT_BUSY", BUSY_MSG)
        if st.status == "stale":
            raise AppError("INVALID_STAGE_STATE", STALE_MSG)
        if st.current_artifact_id != base.id:
            raise AppError("ARTIFACT_NOT_CURRENT", "최신 결과를 기준으로만 수정할 수 있습니다. 화면을 새로 고치세요.")
        if st.status not in ("needs_review", "approved"):
            raise AppError("INVALID_STAGE_STATE", f"현재 상태({st.status})에서는 수정할 수 없습니다.")
        snapshot = json.loads(base.input_snapshot_json)
        evidence = json.loads(base.evidence_json)
        payload = validate_payload(stage_no, body.payload,
                                   validation_context(s, project_id, stage_no, snapshot, evidence))
        new = add_artifact(s, project_id, stage_no, payload, snapshot, evidence, "user", None)
        st.current_artifact_id = new.id
        st.status = "needs_review"
        d = Decision(id=new_id(), request_id=body.request_id, request_key=key, request_fingerprint=fp,
                     project_id=project_id, stage_no=stage_no, artifact_id=base.id, action="edit",
                     comment=body.comment, result_artifact_id=new.id, job_id=None, navigate_to_stage=None,
                     created_at=now())
        s.add(d)
        s.flush()
        touch(s, project_id)
        return _decision_response(s, d)
