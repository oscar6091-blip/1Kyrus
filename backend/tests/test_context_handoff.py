"""AC-03: the edited+approved S3 and the user comment really reach the next model request."""
import copy

from live_fakes import RecorderClient, install


def test_ac03_new_s3_content_ids_and_comment_reach_s4_prompt(api, monkeypatch):
    client = RecorderClient()
    install(monkeypatch, client)
    pid = api.create()
    run_id = None
    for n in (1, 2, 3):
        api.run_wait(pid, n)
        api.approve_current(pid, n)

    s3 = api.stage(pid, 3)["current_artifact"]
    p = copy.deepcopy(s3["payload"])
    marker = "반복 seed 3개(0, 1, 2)로 확인한다."
    p["content"]["body_md"] = p["content"]["body_md"].replace("## Ablation 계획", f"## 반복\n{marker}\n\n## Ablation 계획")
    new_s3 = api.edit(pid, 3, s3["id"], p, comment="반복 seed 추가")["artifact"]
    api.decide(pid, 3, "approve", new_s3["id"])

    client.calls.clear()
    api.run_wait(pid, 4, comments="seed 반복 루프를 코드에 넣어 주세요")
    (sent,) = client.user_inputs()
    assert sent["stage_no"] == 4
    ups = {u["stage_no"]: u for u in sent["approved_upstream_artifacts"]}
    assert ups[3]["artifact_id"] == new_s3["id"]
    assert marker in ups[3]["payload"]["content"]["body_md"]
    assert sent["user_comments"] == "seed 반복 루프를 코드에 넣어 주세요"
    assert f"artifact:{new_s3['id']}" in sent["allowed_evidence_refs"]
    assert sent["approved_brief"]["hypotheses"][0]["id"] == "H1"
    assert "Stage4" not in str(sent["expected_output_schema"]) and "files" in sent["expected_output_schema"]["properties"]["content"]["properties"]

    # regenerate: previous artifact + comment are passed
    s4 = api.stage(pid, 4)["current_artifact"]
    client.calls.clear()
    regen = api.decide(pid, 4, "regenerate", s4["id"], comment="README를 더 자세히")
    api.wait(regen["job"]["id"])
    (sent,) = client.user_inputs()
    assert sent["previous_stage_artifact"] == s4["payload"]
    assert sent["user_comments"] == "README를 더 자세히"
    _ = run_id


def test_live_s5_gets_server_metric_bindings(api, monkeypatch):
    client = RecorderClient()
    install(monkeypatch, client)
    pid = api.create()
    for n in (1, 2, 3, 4):
        api.run_wait(pid, n)
        api.approve_current(pid, n)
    run = api.upload(pid)
    client.calls.clear()
    api.run_wait(pid, 5, run_id=run["id"])
    (sent,) = client.user_inputs()
    assert sent["selected_experiment_run"]["experiment_id"] == "E1"
    assert sent["metric_bindings"]["m0"]["value"] == 0.9666666666666667
    assert "metric:m3" in sent["allowed_evidence_refs"]
