"""LLMGateway boundaries (AC-15, AC-18) with a fake Anthropic client. No network."""
import json

import anthropic
import httpx

from app.config import settings
from app.services import jobs
from app.services.fixtures import stage_fixture

from live_fakes import RecorderClient, install, text_response


def _fail_with(api, monkeypatch, responder, prices=(None, None)):
    client = RecorderClient(responder)
    install(monkeypatch, client, prices=prices)
    pid = api.create()
    job = api.run(pid, 1)
    return pid, api.wait(job["id"]), client


def test_live_not_configured(api, monkeypatch):
    monkeypatch.setattr(settings, "app_mode", "live")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(jobs, "live_deps_factory", None)
    pid = api.create()
    r = api.run(pid, 1, expect=503)
    assert r["error"]["code"] == "LIVE_NOT_CONFIGURED"
    assert api.project(pid)["project"]["mode"] == "live"


def test_success_records_usage_model_and_ai_author(api, monkeypatch):
    client = RecorderClient()
    install(monkeypatch, client, prices=(3.0, 15.0))
    pid = api.create()
    done = api.run_wait(pid, 1)
    assert done["usage"] == {"input_tokens": 100, "output_tokens": 50, "calls": 1, "estimated_cost_usd": 0.00105}
    art = api.stage(pid, 1)["current_artifact"]
    assert art["created_by"] == "ai" and art["model"] == "test-model"
    sent = client.calls[0]
    assert sent["model"] == "test-model" and sent["max_tokens"] == 1000
    assert "Return exactly one JSON object" in sent["system"]


def test_cost_null_without_prices(api, monkeypatch):
    _, done, _ = _fail_with(api, monkeypatch, lambda req: text_response(json.dumps(stage_fixture(1))))
    assert done["status"] == "succeeded" and done["usage"]["estimated_cost_usd"] is None


def test_timeout_fails_without_fixture_fallback(api, monkeypatch):
    def boom(req):
        raise anthropic.APITimeoutError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    pid, done, client = _fail_with(api, monkeypatch, boom)
    assert done["status"] == "failed" and done["error"]["code"] == "LLM_TIMEOUT"
    assert len(client.calls) == 1  # no hidden retry
    st = api.stage(pid, 1)
    assert st["current_artifact"] is None and st["stage"]["status"] == "needs_review"
    assert api.project(pid)["active_job"] is None  # lock released


def test_refusal_and_truncation(api, monkeypatch):
    _, done, client = _fail_with(api, monkeypatch, lambda r: text_response("I can't help", stop="refusal"))
    assert done["error"]["code"] == "LLM_REFUSAL" and len(client.calls) == 1
    _, done, client = _fail_with(api, monkeypatch, lambda r: text_response('{"stage_no": 1', stop="max_tokens"))
    assert done["error"]["code"] == "LLM_TRUNCATED" and len(client.calls) == 1


def test_one_correction_then_success(api, monkeypatch):
    replies = iter(["not json at all", json.dumps(stage_fixture(1), ensure_ascii=False)])
    pid, done, client = _fail_with(api, monkeypatch, lambda r: text_response(next(replies)))
    assert done["status"] == "succeeded" and done["usage"]["calls"] == 2
    assert "Your previous output failed validation." in client.calls[1]["messages"][0]["content"]


def test_correction_capped_at_one(api, monkeypatch):
    bad = stage_fixture(1)
    bad["content"]["brief"]["hypotheses"].append({"id": "H1", "statement": "dup"})
    pid, done, client = _fail_with(api, monkeypatch, lambda r: text_response(json.dumps(bad, ensure_ascii=False)))
    assert done["status"] == "failed" and done["error"]["code"] == "INVALID_MODEL_JSON"
    assert len(client.calls) == 2 and done["usage"]["calls"] == 2
    assert api.stage(pid, 1)["current_artifact"] is None


def test_api_status_error(api, monkeypatch):
    def unauthorized(req):
        resp = httpx.Response(401, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
        raise anthropic.AuthenticationError("invalid x-api-key", response=resp, body=None)
    _, done, _ = _fail_with(api, monkeypatch, unauthorized)
    assert done["error"]["code"] == "LLM_API_ERROR"


def test_only_gateway_imports_anthropic():
    import pathlib

    src = pathlib.Path(__file__).resolve().parents[1] / "app"
    users = [p.name for p in src.rglob("*.py") if "import anthropic" in p.read_text(encoding="utf-8")]
    assert users == ["llm_gateway.py"]
