"""Project deletion (DEVIATIONS D-04) and per-project mode at creation (D-05)."""
from pathlib import Path

from sqlalchemy import func, select

from app.config import settings
from app.db import tx
from app.models import ArtifactVersion, Decision, ExperimentRun, Job, Project, Stage
from app.services import jobs

from conftest import PROJECT_INPUT


def _rows(pid: str) -> dict:
    with tx() as s:
        return {m.__name__: s.scalar(select(func.count()).select_from(m).where(m.project_id == pid))
                for m in (Decision, Job, ArtifactVersion, ExperimentRun, Stage)} | {
            "Project": s.scalar(select(func.count()).select_from(Project).where(Project.id == pid))}


def test_delete_removes_project_and_all_rows(api):
    keep = api.create(name="남길 프로젝트")
    api.run_wait(keep, 1)
    pid = api.create()
    api.through(pid, 6)  # artifacts, decisions, jobs, uploaded run, brief pointer
    assert all(v > 0 for v in _rows(pid).values())

    r = api.c.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
    assert all(v == 0 for v in _rows(pid).values())
    assert api.c.get(f"/api/projects/{pid}").status_code == 404
    assert [p["id"] for p in api.c.get("/api/projects").json()] == [keep]
    # the other project is untouched
    assert api.stage(keep, 1)["stage"]["status"] == "needs_review"


def _file_bytes() -> bytes:
    db = Path(settings.database_url[len("sqlite:///"):])
    return b"".join(f.read_bytes() for f in (db, Path(str(db) + "-wal")) if f.exists())


def test_delete_also_cleans_the_sqlite_file(api):
    """After delete + VACUUM + WAL truncate, the deleted text is not left in the DB file or the WAL."""
    marker = "삭제확인-ZQXJ-7731"
    pid = api.create(name=marker, idea=f"{marker} 아이디어")
    api.run_wait(pid, 1)
    assert marker.encode() in _file_bytes()

    assert api.c.delete(f"/api/projects/{pid}").status_code == 204
    assert marker.encode() not in _file_bytes()
    wal = Path(settings.database_url[len("sqlite:///"):] + "-wal")
    assert not wal.exists() or wal.stat().st_size == 0


def test_delete_succeeds_even_if_compaction_fails(api, monkeypatch):
    from app.services import workflow

    def boom():
        raise RuntimeError("database is locked")
    monkeypatch.setattr(workflow, "compact", boom)
    pid = api.create()
    assert api.c.delete(f"/api/projects/{pid}").status_code == 204
    assert api.c.get(f"/api/projects/{pid}").status_code == 404


def test_delete_unknown_project_is_404(api):
    r = api.c.delete("/api/projects/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_delete_refused_while_job_active(api, monkeypatch):
    pid = api.create()
    monkeypatch.setattr(jobs, "submit", lambda job_id: None)  # leave the job queued
    api.run(pid, 1)
    r = api.c.delete(f"/api/projects/{pid}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "PROJECT_BUSY"
    assert api.c.get(f"/api/projects/{pid}").status_code == 200


def test_mode_defaults_to_app_mode_and_can_be_chosen(api, monkeypatch):
    assert api.project(api.create())["project"]["mode"] == "demo"
    body = {"name": PROJECT_INPUT["name"], "idea": PROJECT_INPUT["idea"]}

    monkeypatch.setattr(jobs, "live_available", lambda: True)
    r = api.c.post("/api/projects", json=body | {"mode": "live"})
    assert r.status_code == 201 and r.json()["mode"] == "live"
    r = api.c.post("/api/projects", json=body | {"mode": "demo"})
    assert r.status_code == 201 and r.json()["mode"] == "demo"


def test_live_mode_refused_without_live_settings(api, monkeypatch):
    monkeypatch.setattr(jobs, "live_available", lambda: False)
    r = api.c.post("/api/projects", json={"name": "x", "idea": "y", "mode": "live"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "LIVE_NOT_CONFIGURED"
    r = api.c.post("/api/projects", json={"name": "x", "idea": "y", "mode": "other"})
    assert r.status_code == 422
