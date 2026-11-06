"""Shared fixtures: a real temporary SQLite file per test, demo delay 0."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import FIXTURES_DIR, settings
from app.main import create_app
from app.services import jobs

VALID_RUN = (FIXTURES_DIR / "experiment_result.valid.json").read_bytes()
INVALID_RUN = (FIXTURES_DIR / "experiment_result.invalid.json").read_bytes()
PROJECT_INPUT = json.loads((FIXTURES_DIR / "project_input.json").read_text(encoding="utf-8"))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "demo_stage_delay_seconds", 0.0)
    monkeypatch.setattr(settings, "app_mode", "demo")
    monkeypatch.setattr(jobs, "live_deps_factory", None)
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    db.init_engine(url)
    with TestClient(create_app()) as c:
        yield c


def rid() -> str:
    return str(uuid.uuid4())


class Api:
    """Thin helper over the HTTP API used by tests."""

    def __init__(self, client: TestClient):
        self.c = client

    def create(self, name=None, idea=None) -> str:
        r = self.c.post("/api/projects", json={"name": name or PROJECT_INPUT["name"], "idea": idea or PROJECT_INPUT["idea"]})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def project(self, pid):
        return self.c.get(f"/api/projects/{pid}").json()

    def stage(self, pid, n):
        return self.c.get(f"/api/projects/{pid}/stages/{n}").json()

    def run(self, pid, n, comments="", run_id=None, request_id=None, expect=202):
        r = self.c.post(f"/api/projects/{pid}/stages/{n}/run",
                        json={"request_id": request_id or rid(), "user_comments": comments, "run_id": run_id})
        assert r.status_code == expect, r.text
        return r.json()

    def wait(self, job_id, timeout=20):
        jobs.wait(job_id, timeout)
        end = time.time() + timeout
        while time.time() < end:
            j = self.c.get(f"/api/jobs/{job_id}").json()
            if j["status"] not in ("queued", "running"):
                return j
            time.sleep(0.02)
        raise AssertionError("job did not finish")

    def run_wait(self, pid, n, **kw):
        job = self.run(pid, n, **kw)
        done = self.wait(job["id"])
        assert done["status"] == "succeeded", done
        return done

    def decide(self, pid, n, action, artifact_id, comment="", run_id=None, request_id=None, expect=200):
        r = self.c.post(f"/api/projects/{pid}/stages/{n}/decisions",
                        json={"request_id": request_id or rid(), "action": action, "artifact_id": artifact_id,
                              "comment": comment, "run_id": run_id})
        assert r.status_code == expect, r.text
        return r.json()

    def approve_current(self, pid, n, expect=200):
        cur = self.stage(pid, n)["stage"]["current_artifact_id"]
        return self.decide(pid, n, "approve", cur, expect=expect)

    def edit(self, pid, n, base_id, payload, comment="", request_id=None, expect=200):
        r = self.c.post(f"/api/projects/{pid}/stages/{n}/edits",
                        json={"request_id": request_id or rid(), "base_artifact_id": base_id, "payload": payload,
                              "comment": comment})
        assert r.status_code == expect, r.text
        return r.json()

    def upload(self, pid, raw=VALID_RUN, upload_id=None, expect=201):
        r = self.c.post(f"/api/projects/{pid}/runs", data={"client_upload_id": upload_id or rid()},
                        files={"file": ("result.json", raw, "application/json")})
        assert r.status_code == expect, r.text
        return r.json()

    def through(self, pid, last: int):
        """Run and approve S1..last (uploading the bundled valid run before S5)."""
        run_id = None
        for n in range(1, last + 1):
            if n == 5:
                run_id = self.upload(pid)["id"]
            self.run_wait(pid, n, run_id=run_id if n == 5 else None)
            self.approve_current(pid, n)
        return run_id

    def current_payload(self, pid, n):
        return self.stage(pid, n)["current_artifact"]["payload"]


@pytest.fixture()
def api(client) -> Api:
    return Api(client)
