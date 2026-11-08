"""DEVIATIONS D-07: bundle upload (several experiments in one file) and S5 over several runs."""
import copy
import json

from app.services.fixtures import stage_fixture
from live_fakes import RecorderClient, default_responder, install, text_response

from conftest import VALID_RUN, rid


def _run(exp_id: str, shift: float = 0.0) -> dict:
    d = json.loads(VALID_RUN)
    d["experiment_id"] = exp_id
    for m in d["metrics"]:
        m["value"] = round(m["value"] - shift, 6)
    return d


def _bundle(*runs: dict) -> bytes:
    return json.dumps({"schema_version": "1.1", "runs": list(runs)}).encode()


def _s3_two_experiments() -> dict:
    s3 = copy.deepcopy(stage_fixture(3))
    e2 = copy.deepcopy(s3["content"]["experiments"][0])
    e2["id"], e2["label"] = "E2", "E1 설정의 학습률 변형"
    s3["content"]["experiments"].append(e2)
    return s3


def _s5_multi() -> dict:
    s5 = copy.deepcopy(stage_fixture(5))
    s5["content"]["body_md"] = (
        "## E1 기본 설정\nSGD accuracy {{metric:E1.m0}}, Adam accuracy {{metric:E1.m2}}.\n\n"
        "## E2 학습률 변형\nSGD accuracy {{metric:E2.m0}}, Adam accuracy {{metric:E2.m2}}.\n\n"
        "## 전체 요약\n두 실험 모두 단일 seed라 일반적 우위를 판단할 수 없다."
    )
    s5["rationale"][0]["evidence_refs"] = ["metric:E1.m0", "metric:E2.m0"]
    return s5


def _responder(s5_payload: dict):
    def respond(req: dict):
        user = json.loads(req["messages"][0]["content"].split("\n\nYour previous output failed validation.")[0])
        if user.get("stage_no") == 3 and "content" in user["expected_output_schema"].get("properties", {}):
            return text_response(json.dumps(_s3_two_experiments(), ensure_ascii=False))
        if user.get("stage_no") == 5:
            return text_response(json.dumps(s5_payload, ensure_ascii=False))
        if user.get("stage_no") == 6 and any("." in k for k in user["metric_bindings"]):
            # the fixture uses single-run IDs (m0); with several runs the allowed IDs are E1.m0, ...
            s6 = json.dumps(stage_fixture(6), ensure_ascii=False).replace("metric:m", "metric:E1.m")
            return text_response(s6)
        return default_responder(req)
    return respond


def _live_through_s4(api, monkeypatch, s5_payload=None) -> tuple[str, RecorderClient]:
    client = RecorderClient(_responder(s5_payload or _s5_multi()))
    install(monkeypatch, client)
    pid = api.create()
    api.through(pid, 4)
    return pid, client


def test_bundle_upload_stores_one_run_per_experiment(api, monkeypatch):
    pid, _ = _live_through_s4(api, monkeypatch)
    upload_id = rid()
    raw = _bundle(_run("E1"), _run("E2", 0.1))
    r = api.upload(pid, raw, upload_id=upload_id)
    assert r["bundle"] is True and [x["payload"]["experiment_id"] for x in r["runs"]] == ["E1", "E2"]
    assert len(api.c.get(f"/api/projects/{pid}/runs").json()) == 2
    # same id + same content is idempotent; same id + other content conflicts
    again = api.upload(pid, raw, upload_id=upload_id)
    assert [x["id"] for x in again["runs"]] == [x["id"] for x in r["runs"]]
    assert api.upload(pid, _bundle(_run("E1"), _run("E2", 0.2)), upload_id=upload_id,
                      expect=409)["error"]["code"] == "REQUEST_ID_CONFLICT"
    # a single-run file still works as before
    assert api.upload(pid, VALID_RUN)["payload"]["experiment_id"] == "E1"


def test_bundle_errors_point_into_runs(api, monkeypatch):
    pid, _ = _live_through_s4(api, monkeypatch)
    bad_value = _run("E2")
    bad_value["metrics"][0]["value"] = 1.5
    paths = {f["path"] for f in api.upload(pid, _bundle(_run("E1"), bad_value), expect=422)["error"]["fields"]}
    assert "runs.1.metrics.0.value" in paths
    paths = {f["path"] for f in api.upload(pid, _bundle(_run("E1"), _run("E9")), expect=422)["error"]["fields"]}
    assert "runs.1.experiment_id" in paths
    assert api.upload(pid, _bundle(_run("E1"), _run("E1")), expect=422)["error"]["code"] == "INVALID_RUN"
    assert len(api.c.get(f"/api/projects/{pid}/runs").json()) == 0  # nothing stored on failure


def test_s5_analyses_several_runs_and_s6_gets_all_metrics(api, monkeypatch):
    pid, client = _live_through_s4(api, monkeypatch)
    runs = api.upload(pid, _bundle(_run("E1"), _run("E2", 0.1)))["runs"]
    ids = [x["id"] for x in runs]
    r = api.c.post(f"/api/projects/{pid}/stages/5/run",
                   json={"request_id": rid(), "user_comments": "", "run_id": None, "run_ids": list(reversed(ids))})
    assert r.status_code == 202, r.text
    assert api.wait(r.json()["id"])["status"] == "succeeded"
    art = api.stage(pid, 5)["current_artifact"]
    assert art["input_snapshot"]["run_ids"] == ids  # stored in S3 experiment order
    assert {"E1.m0", "E2.m0"} <= set(art["evidence"]["metrics"])
    assert art["evidence"]["metrics"]["E2.m0"]["experiment_id"] == "E2"
    assert "| 실험 |" in art["rendered_markdown"] and "## E2 학습률 변형" in art["rendered_markdown"]
    sent = client.user_inputs()[-1]
    assert [x["experiment_id"] for x in sent["selected_experiment_runs"]] == ["E1", "E2"]

    api.approve_current(pid, 5)
    api.run_wait(pid, 6)
    s6 = api.stage(pid, 6)["current_artifact"]
    assert {"E1.m0", "E2.m0"} <= set(s6["evidence"]["metrics"])


def test_s5_with_several_runs_needs_a_section_per_experiment(api, monkeypatch):
    missing_e2 = _s5_multi()
    missing_e2["content"]["body_md"] = missing_e2["content"]["body_md"].replace("## E2 학습률 변형", "## 두 번째 실험")
    pid, _ = _live_through_s4(api, monkeypatch, missing_e2)
    ids = [x["id"] for x in api.upload(pid, _bundle(_run("E1"), _run("E2", 0.1)))["runs"]]
    r = api.c.post(f"/api/projects/{pid}/stages/5/run",
                   json={"request_id": rid(), "user_comments": "", "run_id": None, "run_ids": ids})
    done = api.wait(r.json()["id"])
    assert done["status"] == "failed"
    assert "## E2" in json.dumps(done["error"], ensure_ascii=False)


def test_s5_rejects_two_runs_of_one_experiment(api, monkeypatch):
    pid, _ = _live_through_s4(api, monkeypatch)
    a = api.upload(pid, VALID_RUN)["id"]
    b = api.upload(pid, json.dumps(_run("E1", 0.1)).encode())["id"]
    r = api.c.post(f"/api/projects/{pid}/stages/5/run",
                   json={"request_id": rid(), "user_comments": "", "run_id": None, "run_ids": [a, b]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_RUN"
