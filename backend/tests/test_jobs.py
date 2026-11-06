"""Restart recovery and failure handling (AC-07, AC-06 server side)."""
import json

from app.db import tx
from app.models import Job, Stage
from app.services import jobs
from app.services.repository import EMPTY_USAGE, dumps, new_id, now

from conftest import rid


def test_ac07_restart_marks_interrupted_and_keeps_artifacts(api):
    pid = api.create()
    api.through(pid, 1)
    approved = api.stage(pid, 1)["stage"]["approved_artifact_id"]
    # simulate a job that was running when the server died
    with tx() as s:
        st = s.get(Stage, (pid, 1))
        st.status = "running"
        s.add(Job(id=new_id(), request_id=rid(), request_key=f"run:{pid}:1:x", request_fingerprint="f",
                  project_id=pid, stage_no=1, status="running", input_snapshot_json=dumps({}),
                  result_artifact_id=None, usage_json=dumps(EMPTY_USAGE), error_json=None, created_at=now()))
    assert jobs.recover_on_startup() == 1
    with tx() as s:
        job = s.query(Job).filter(Job.project_id == pid, Job.status == "interrupted").one()
        assert json.loads(job.error_json)["code"] == "INTERRUPTED_RESTART"
    st = api.stage(pid, 1)["stage"]
    assert st["status"] == "needs_review" and st["approved_artifact_id"] == approved
    assert api.project(pid)["active_job"] is None
    # manual retry works and nothing reran automatically
    cur = st["current_artifact_id"]
    regen = api.decide(pid, 1, "regenerate", cur, comment="재시도")
    assert api.wait(regen["job"]["id"])["status"] == "succeeded"


def test_job_view_usage_for_demo(api):
    pid = api.create()
    done = api.run_wait(pid, 1)
    assert done["usage"] == {"input_tokens": None, "output_tokens": None, "calls": 0, "estimated_cost_usd": None}
    assert done["started_at"] and done["finished_at"]


def test_ac06_reconnect_sees_same_job(api, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "demo_stage_delay_seconds", 0.4)
    pid = api.create()
    job = api.run(pid, 1)
    # "browser closed and reopened": only the project detail is re-read
    again = api.project(pid)["active_job"]
    assert again["id"] == job["id"]
    api.wait(job["id"])
    with tx() as s:
        assert s.query(Job).filter(Job.project_id == pid).count() == 1
    assert api.stage(pid, 1)["current_artifact"]["version"] == 1
