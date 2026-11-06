"""Approval gate, stale propagation, back, busy lock, S3/S5 semantic rules (AC-02, 05, 16, 17, 19, 10)."""
import copy
import time

from app.config import settings
from app.models import Decision
from app.db import tx
from sqlalchemy import func, select

from conftest import rid


def test_ac02_run_blocked_until_predecessor_approved(api):
    pid = api.create()
    api.run_wait(pid, 1)
    r = api.run(pid, 2, expect=409)
    assert r["error"]["code"] == "PREDECESSOR_NOT_APPROVED"
    assert api.stage(pid, 2)["stage"]["can_run"] is False
    api.approve_current(pid, 1)
    assert api.stage(pid, 2)["stage"]["can_run"] is True
    api.run_wait(pid, 2)


def test_generation_never_auto_approves(api):
    pid = api.create()
    api.run_wait(pid, 1)
    st = api.stage(pid, 1)["stage"]
    assert st["status"] == "needs_review" and st["approved_artifact_id"] is None and st["can_approve"] is True


def test_ac05_new_s3_approval_stales_downstream_only(api):
    pid = api.create()
    api.through(pid, 6)
    before = api.project(pid)["stages"]
    s3 = api.stage(pid, 3)["current_artifact"]
    payload = copy.deepcopy(s3["payload"])
    payload["content"]["body_md"] = payload["content"]["body_md"].replace(
        "같은 split과 seed를 두 학습에 사용한다.", "같은 split과 seed를 두 학습에 사용하고, 반복 seed 확인은 후속 과제로 남긴다.")
    edited = api.edit(pid, 3, s3["id"], payload, comment="반복 seed 문구 수정")
    assert edited["stage"]["status"] == "needs_review"  # saving does not approve
    assert [s["status"] for s in api.project(pid)["stages"]][3:] == ["approved"] * 3  # not stale yet
    api.decide(pid, 3, "approve", edited["artifact"]["id"])
    after = api.project(pid)["stages"]
    assert [s["status"] for s in after] == ["approved"] * 3 + ["stale"] * 3
    for b, a in zip(before[3:], after[3:]):  # history kept
        assert a["approved_artifact_id"] == b["approved_artifact_id"]
        assert a["current_artifact_id"] == b["current_artifact_id"]
    # stale results are read-only
    s4 = api.stage(pid, 4)["current_artifact"]
    r = api.edit(pid, 4, s4["id"], s4["payload"], expect=409)
    assert r["error"]["code"] == "INVALID_STAGE_STATE"
    r = api.decide(pid, 4, "approve", s4["id"], expect=409)
    assert r["error"]["code"] == "INVALID_STAGE_STATE"
    # S5 cannot run before S4 is re-approved
    run_id = api.c.get(f"/api/projects/{pid}/runs").json()[0]["id"]
    assert api.run(pid, 5, run_id=run_id, expect=409)["error"]["code"] == "PREDECESSOR_NOT_APPROVED"
    # regenerate S4 -> input snapshot points to the new S3
    regen = api.decide(pid, 4, "regenerate", s4["id"], comment="새 S3 반영")
    api.wait(regen["job"]["id"])
    new_s4 = api.stage(pid, 4)["current_artifact"]
    assert new_s4["input_snapshot"]["upstream_artifact_ids"]["3"] == edited["artifact"]["id"]
    assert new_s4["input_snapshot"]["user_comments"] == "새 S3 반영"
    assert api.run(pid, 5, run_id=run_id, expect=409)["error"]["code"] == "PREDECESSOR_NOT_APPROVED"
    api.decide(pid, 4, "approve", new_s4["id"])
    api.run_wait(pid, 5, run_id=run_id)


def test_ac17_back_records_and_changes_nothing(api):
    pid = api.create()
    api.through(pid, 2)
    before = api.project(pid)
    s2 = before["stages"][1]["current_artifact_id"]
    r = api.decide(pid, 2, "back", s2)
    assert r["navigate_to_stage"] == 1 and r["decision"]["action"] == "back"
    after = api.project(pid)
    assert after["stages"] == before["stages"]
    assert after["project"]["current_brief_artifact_id"] == before["project"]["current_brief_artifact_id"]
    s1 = before["stages"][0]["current_artifact_id"]
    assert api.decide(pid, 1, "back", s1, expect=422)["error"]["code"] == "INVALID_PAYLOAD"


def test_ac16_project_lock(api, monkeypatch):
    monkeypatch.setattr(settings, "demo_stage_delay_seconds", 0.6)
    pid = api.create()
    other = api.create(name="다른 프로젝트")
    job = api.run(pid, 1)
    assert api.run(pid, 1, expect=409)["error"]["code"] == "PROJECT_BUSY"
    assert api.c.get(f"/api/projects/{pid}").status_code == 200  # reads still work
    assert api.project(pid)["active_job"]["id"] == job["id"]
    api.run(other, 1)  # another project is not blocked
    done = api.wait(job["id"])
    assert done["status"] == "succeeded"
    assert api.project(pid)["active_job"] is None


def _s3_with(api, pid, mutate):
    s3 = api.stage(pid, 3)["current_artifact"]
    payload = copy.deepcopy(s3["payload"])
    mutate(payload)
    return s3, payload


def test_ac19_s3_requires_all_hypotheses_and_ablation(api):
    pid = api.create()
    # make the Brief have H1 and H2
    api.run_wait(pid, 1)
    s1 = api.stage(pid, 1)["current_artifact"]
    p1 = copy.deepcopy(s1["payload"])
    p1["content"]["brief"]["hypotheses"].append({"id": "H2", "statement": "macro F1도 같은 방향을 보인다."})
    e = api.edit(pid, 1, s1["id"], p1)
    api.decide(pid, 1, "approve", e["artifact"]["id"])
    api.run_wait(pid, 2)
    api.approve_current(pid, 2)
    # the fixed demo S3 only maps H1 -> generation fails validation, no artifact created
    job = api.run(pid, 3)
    done = api.wait(job["id"])
    assert done["status"] == "failed"
    assert done["error"]["code"] == "INVALID_PAYLOAD"
    assert any("H2" in f["message"] for f in done["error"]["fields"])
    assert api.stage(pid, 3)["stage"]["current_artifact_id"] is None


def test_s3_edit_rules(api):
    pid = api.create()
    api.through(pid, 2)
    api.run_wait(pid, 3)
    base, p = _s3_with(api, pid, lambda p: p["content"].__setitem__(
        "body_md", p["content"]["body_md"].split("## Ablation 계획")[0]))
    r = api.edit(pid, 3, base["id"], p, expect=422)
    assert any("Ablation" in f["message"] for f in r["error"]["fields"])
    base, p = _s3_with(api, pid, lambda p: p["content"]["experiments"][0]["hypothesis_ids"].append("H1"))
    assert api.edit(pid, 3, base["id"], p, expect=422)["error"]["code"] == "INVALID_PAYLOAD"
    base, p = _s3_with(api, pid, lambda p: p["content"]["experiments"][0]["hypothesis_ids"].__setitem__(0, "H9"))
    assert api.edit(pid, 3, base["id"], p, expect=422)["error"]["code"] == "INVALID_PAYLOAD"
    base, p = _s3_with(api, pid, lambda p: p["rationale"][0]["evidence_refs"].append("ref:arxiv_0000_00000"))
    assert api.edit(pid, 3, base["id"], p, expect=422)["error"]["code"] == "UNKNOWN_EVIDENCE"


def test_ac10_s5_verdict_rules(api):
    pid = api.create()
    api.through(pid, 4)
    run_id = api.upload(pid)["id"]
    api.run_wait(pid, 5, run_id=run_id)
    s5 = api.stage(pid, 5)["current_artifact"]
    p = copy.deepcopy(s5["payload"])
    p["content"]["hypothesis_verdicts"].append(dict(p["content"]["hypothesis_verdicts"][0]))
    assert api.edit(pid, 5, s5["id"], p, expect=422)["error"]["code"] == "INVALID_PAYLOAD"
    p = copy.deepcopy(s5["payload"])
    p["content"]["hypothesis_verdicts"] = [{"hypothesis_id": "H2", "verdict": "inconclusive", "reason": "x"}]
    assert api.edit(pid, 5, s5["id"], p, expect=422)["error"]["code"] == "INVALID_PAYLOAD"
    p = copy.deepcopy(s5["payload"])
    p["content"]["body_md"] += " {{metric:m99}}"
    assert api.edit(pid, 5, s5["id"], p, expect=422)["error"]["code"] == "UNKNOWN_EVIDENCE"


def test_approve_requires_new_draft(api):
    pid = api.create()
    api.through(pid, 1)
    cur = api.stage(pid, 1)["stage"]["current_artifact_id"]
    r = api.decide(pid, 1, "approve", cur, expect=409)
    assert r["error"]["code"] == "INVALID_STAGE_STATE"
    with tx() as s:
        assert s.scalar(select(func.count()).select_from(Decision).where(Decision.action == "approve")) == 1


def test_other_project_artifact_is_404(api):
    a, b = api.create(), api.create(name="b")
    api.run_wait(a, 1)
    art = api.stage(a, 1)["stage"]["current_artifact_id"]
    assert api.c.get(f"/api/projects/{b}/artifacts/{art}").status_code == 404
    api.run_wait(b, 1)
    assert api.decide(b, 1, "approve", art, expect=404)["error"]["code"] == "NOT_FOUND"


def test_error_shape_for_bad_body(client):
    r = client.post("/api/projects", json={"name": ""})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "INVALID_PAYLOAD" and err["fields"] and set(err) == {"code", "message", "fields", "retryable"}
    _ = time
    _ = rid
