"""JobRunner: one in-process worker thread (ThreadPoolExecutor(max_workers=1)).

The API commits the Job first, then submits its ID here. The worker opens its
own DB sessions and runs model/arXiv calls outside any write transaction.
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from sqlalchemy import select

from ..db import tx
from ..errors import AppError
from ..models import Job, Stage
from .repository import add_artifact, dumps, now, touch

log = logging.getLogger("jobs")

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job")
_futures: dict[str, Future] = {}

# Tests replace this to inject Fake/Recorder gateways (see stage_runner.LiveDeps).
live_deps_factory: Callable | None = None


def live_available() -> bool:
    from ..config import settings

    return live_deps_factory is not None or settings.live_configured


def submit(job_id: str) -> None:
    _futures[job_id] = _executor.submit(execute, job_id)


def wait(job_id: str, timeout: float = 30) -> None:
    """Test helper: block until the job's worker call returns."""
    fut = _futures.get(job_id)
    if fut is not None:
        fut.result(timeout=timeout)


def execute(job_id: str) -> None:
    from .stage_runner import generate

    with tx() as s:
        job = s.get(Job, job_id)
        if job is None or job.status != "queued":
            return
        job.status = "running"
        job.started_at = now()
        project_id, stage_no = job.project_id, job.stage_no
        snapshot = json.loads(job.input_snapshot_json)
        from ..models import Project

        mode = s.get(Project, project_id).mode

    usage = {"input_tokens": None, "output_tokens": None, "calls": 0, "estimated_cost_usd": None}
    try:
        result = generate(project_id, stage_no, snapshot, mode, usage)
    except AppError as exc:
        _fail(job_id, exc.to_dict(), usage)
        return
    except Exception as exc:  # noqa: BLE001 - never leave a job running
        log.exception("job %s crashed", job_id)
        _fail(job_id, {"code": "INTERNAL_ERROR", "message": f"내부 오류로 생성이 실패했습니다: {type(exc).__name__}",
                       "fields": [], "retryable": True}, usage)
        return

    with tx() as s:
        job = s.get(Job, job_id)
        st = s.get(Stage, (project_id, stage_no))
        art = add_artifact(s, project_id, stage_no, result.payload, snapshot, result.evidence,
                           result.created_by, result.model)
        job.status = "succeeded"
        job.result_artifact_id = art.id
        job.usage_json = dumps(usage)
        job.finished_at = now()
        st.current_artifact_id = art.id
        st.status = "needs_review"  # never auto-approve (WF-03)
        touch(s, project_id)


def _fail(job_id: str, error: dict, usage: dict) -> None:
    with tx() as s:
        job = s.get(Job, job_id)
        job.status = "failed"
        job.error_json = dumps(error)
        job.usage_json = dumps(usage)
        job.finished_at = now()
        st = s.get(Stage, (job.project_id, job.stage_no))
        st.status = "needs_review"  # previous artifacts/approval pointers are kept
        touch(s, job.project_id)


def recover_on_startup() -> int:
    """WF-12: active jobs from a previous process become interrupted. Never rerun them."""
    with tx() as s:
        rows = list(s.scalars(select(Job).where(Job.status.in_(("queued", "running")))))
        for job in rows:
            job.status = "interrupted"
            job.finished_at = now()
            job.error_json = dumps({"code": "INTERRUPTED_RESTART",
                                    "message": "서버가 다시 시작되어 작업이 중단되었습니다. 필요하면 다시 실행하세요. 유료 호출은 자동으로 재실행하지 않습니다.",
                                    "fields": [], "retryable": True})
            st = s.get(Stage, (job.project_id, job.stage_no))
            if st.status == "running":
                st.status = "needs_review"
        for st in s.scalars(select(Stage).where(Stage.status == "running")):
            st.status = "needs_review"
        return len(rows)


def sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
