"""AC-08 / AC-11 / AC-19 evidence boundaries on the live path and in rendering."""
import copy
import json

from app.errors import AppError
from app.services.fixtures import stage_fixture

from live_fakes import FakeVerifier, RecorderClient, install, text_response


def _search_or(stage_payload_fn):
    def responder(req):
        user = json.loads(req["messages"][0]["content"].split("\n\nYour previous output failed validation.")[0])
        props = user["expected_output_schema"].get("properties", {})
        if "search_query" in props:
            return text_response(json.dumps({"search_query": "adam optimizer"}))
        return text_response(json.dumps(stage_payload_fn(user["stage_no"]), ensure_ascii=False))
    return responder


def test_unknown_cite_from_model_is_not_adopted(api, monkeypatch):
    def payload(n):
        p = stage_fixture(n)
        if n == 2:
            p["content"]["body_md"] += "\n- {{cite:arxiv_9999_99999}} invented paper"
        return p
    client = RecorderClient(_search_or(payload))
    install(monkeypatch, client)
    pid = api.create()
    api.run_wait(pid, 1)
    api.approve_current(pid, 1)
    job = api.run(pid, 2)
    done = api.wait(job["id"])
    assert done["status"] == "failed" and done["error"]["code"] == "INVALID_MODEL_JSON"
    assert any("arxiv_9999_99999" in f["message"] for f in done["error"]["fields"])
    assert api.stage(pid, 2)["current_artifact"] is None  # not saved, no fixture fallback


def test_partial_exclusion_warnings_flow_to_s6(api, monkeypatch):
    warn = "미검증 후보 제외: A Candidate Without Authors — 메타데이터 누락(저자)"
    install(monkeypatch, RecorderClient(), FakeVerifier(warnings=[warn]))
    pid = api.create()
    for n in (1, 2, 3, 4):
        api.run_wait(pid, n)
        api.approve_current(pid, n)
    s2 = api.stage(pid, 2)["current_artifact"]
    assert s2["evidence"]["warnings"] == [warn]
    assert set(s2["evidence"]["references"]) == {"arxiv_1412_6980", "arxiv_1711_05101", "arxiv_1803_09820"}
    run = api.upload(pid)
    api.run_wait(pid, 5, run_id=run["id"])
    api.approve_current(pid, 5)
    api.run_wait(pid, 6)
    s6 = api.stage(pid, 6)["current_artifact"]
    assert warn in s6["evidence"]["warnings"]
    assert s6["evidence"]["warnings"].count(warn) == 1


def test_no_verified_references_job_fails_with_reason(api, monkeypatch):
    err = AppError("NO_VERIFIED_REFERENCES", "확인된 논문이 한 편도 없어 S2를 만들 수 없습니다.",
                   [{"path": "references", "message": "미검증 후보 제외: X — 메타데이터 누락(저자)"}], status=422)
    install(monkeypatch, RecorderClient(), FakeVerifier(error=err))
    pid = api.create()
    api.run_wait(pid, 1)
    api.approve_current(pid, 1)
    done = api.wait(api.run(pid, 2)["id"])
    assert done["status"] == "failed" and done["error"]["code"] == "NO_VERIFIED_REFERENCES"
    assert done["error"]["fields"][0]["message"].startswith("미검증 후보 제외")


def test_empty_evidence_refs_are_allowed_and_rendering_uses_own_evidence(api):
    pid = api.create()
    api.run_wait(pid, 1)
    art = api.stage(pid, 1)["current_artifact"]
    assert art["payload"]["rationale"][0]["evidence_refs"] == []  # UI shows '근거 없음: 사용자 확인 필요'
    p = copy.deepcopy(art["payload"])
    p["rationale"][0]["evidence_refs"] = [f"artifact:{art['id']}"]  # not in its own input snapshot
    assert api.edit(pid, 1, art["id"], p, expect=422)["error"]["code"] == "UNKNOWN_EVIDENCE"


def test_broken_token_rejected(api):
    pid = api.create()
    api.through(pid, 5)
    api.run_wait(pid, 6)
    s6 = api.stage(pid, 6)["current_artifact"]
    for bad in ["{{metric:m0", "{{foo:bar}}", "{{cite:nope}}"]:
        p = copy.deepcopy(s6["payload"])
        p["content"]["sections"][0]["body_md"] += " " + bad
        assert api.edit(pid, 6, s6["id"], p, expect=422)["error"]["code"] == "UNKNOWN_EVIDENCE", bad
    p = copy.deepcopy(s6["payload"])
    p["content"]["sections"] = list(reversed(p["content"]["sections"]))
    assert api.edit(pid, 6, s6["id"], p, expect=422)["error"]["code"] == "INVALID_PAYLOAD"
