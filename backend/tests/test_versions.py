"""Versions, Decisions, request dedupe and Brief history (AC-04, AC-14)."""
import copy

from sqlalchemy import func, select

from app.db import tx
from app.models import ArtifactVersion, Decision, Job

from conftest import rid


def _count(model, **where):
    with tx() as s:
        q = select(func.count()).select_from(model)
        for k, v in where.items():
            q = q.where(getattr(model, k) == v)
        return s.scalar(q)


def test_ac04_edit_creates_version_and_needs_reapproval(api):
    pid = api.create()
    api.through(pid, 1)
    first = api.stage(pid, 1)["current_artifact"]
    p = copy.deepcopy(first["payload"])
    p["content"]["brief"]["constraints"] += " 추가 제약: 계산 예산 1시간."
    r = api.edit(pid, 1, first["id"], p, comment="제약 보강")
    new = r["artifact"]
    assert new["version"] == first["version"] + 1 and new["created_by"] == "user"
    assert new["input_snapshot"] == first["input_snapshot"] and new["evidence"] == first["evidence"]
    assert r["stage"]["status"] == "needs_review"
    assert api.project(pid)["project"]["current_brief_artifact_id"] == first["id"]  # not approved yet
    # old version unchanged
    assert api.c.get(f"/api/projects/{pid}/artifacts/{first['id']}").json()["payload"] == first["payload"]
    api.decide(pid, 1, "approve", new["id"])
    assert api.project(pid)["project"]["current_brief_artifact_id"] == new["id"]
    assert _count(ArtifactVersion, project_id=pid, stage_no=1) == 2
    assert _count(Decision, project_id=pid, action="edit") == 1
    assert _count(Decision, project_id=pid, action="approve") == 2

    # Brief history from Decisions (S1 approve), opening old versions changes nothing
    decisions = api.c.get(f"/api/projects/{pid}/decisions").json()
    approved_ids = [d["artifact_id"] for d in decisions if d["stage_no"] == 1 and d["action"] == "approve"]
    assert approved_ids == [first["id"], new["id"]]
    before = api.project(pid)
    n_dec = len(decisions)
    for aid in approved_ids:
        assert api.c.get(f"/api/projects/{pid}/artifacts/{aid}").status_code == 200
    assert api.project(pid) == before
    assert len(api.c.get(f"/api/projects/{pid}/decisions").json()) == n_dec


def test_edit_rejects_client_evidence(api):
    pid = api.create()
    api.run_wait(pid, 1)
    cur = api.stage(pid, 1)["current_artifact"]
    r = api.c.post(f"/api/projects/{pid}/stages/1/edits",
                   json={"request_id": rid(), "base_artifact_id": cur["id"], "payload": cur["payload"],
                         "comment": "", "evidence": {}})
    assert r.status_code == 422


def test_ac14_duplicate_requests(api):
    pid = api.create()
    req = rid()
    j1 = api.run(pid, 1, request_id=req)
    j2 = api.run(pid, 1, request_id=req)  # replay, even while busy
    assert j1["id"] == j2["id"]
    api.wait(j1["id"])
    assert _count(Job, project_id=pid) == 1
    assert api.run(pid, 1, comments="다른 내용", request_id=req, expect=409)["error"]["code"] == "REQUEST_ID_CONFLICT"

    cur = api.stage(pid, 1)["stage"]["current_artifact_id"]
    a_req = rid()
    d1 = api.decide(pid, 1, "approve", cur, request_id=a_req)
    d2 = api.decide(pid, 1, "approve", cur, request_id=a_req)
    assert d1["decision"]["id"] == d2["decision"]["id"]
    assert _count(Decision, project_id=pid) == 1
    assert api.decide(pid, 1, "approve", cur, comment="x", request_id=a_req, expect=409)["error"]["code"] == "REQUEST_ID_CONFLICT"

    payload = api.current_payload(pid, 1)
    payload["content"]["brief"]["constraints"] += " 수정"
    e_req = rid()
    e1 = api.edit(pid, 1, cur, payload, request_id=e_req)
    e2 = api.edit(pid, 1, cur, payload, request_id=e_req)
    assert e1["artifact"]["id"] == e2["artifact"]["id"]
    assert _count(ArtifactVersion, project_id=pid, stage_no=1) == 2

    g_req = rid()
    g1 = api.decide(pid, 1, "regenerate", e1["artifact"]["id"], comment="다시", request_id=g_req)
    g2 = api.decide(pid, 1, "regenerate", e1["artifact"]["id"], comment="다시", request_id=g_req)
    assert g1["job"]["id"] == g2["job"]["id"]
    api.wait(g1["job"]["id"])
    assert _count(Job, project_id=pid) == 2
    assert _count(ArtifactVersion, project_id=pid, stage_no=1) == 3
