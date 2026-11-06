"""Fake/Recorder Anthropic client and fake CitationVerifier for offline live-path tests."""
from __future__ import annotations

import json
import threading
from types import SimpleNamespace
from typing import Callable

from app.services.fixtures import reference_snapshot, stage_fixture
from app.services.llm_gateway import LLMGateway
from app.stages import LiveDeps


def text_response(text: str, stop: str = "end_turn", tokens=(100, 50)):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]))


def default_responder(req: dict):
    user = json.loads(req["messages"][0]["content"].split("\n\nYour previous output failed validation.")[0])
    if "search_query" in json.dumps(user["expected_output_schema"]) and "content" not in user["expected_output_schema"].get("properties", {}):
        return text_response(json.dumps({"search_query": "adam optimizer"}))
    return text_response(json.dumps(stage_fixture(user["stage_no"]), ensure_ascii=False))


class RecorderClient:
    """Records every messages.create call; `responder` decides the reply (or raises)."""

    def __init__(self, responder: Callable | None = None, gate: threading.Event | None = None):
        self.calls: list[dict] = []
        self.responder = responder or default_responder
        self.gate = gate
        self.messages = self

    def create(self, **kwargs):
        if self.gate is not None:
            self.gate.wait(10)
        self.calls.append(kwargs)
        return self.responder(kwargs)

    def user_inputs(self) -> list[dict]:
        out = []
        for c in self.calls:
            text = c["messages"][0]["content"].split("\n\nYour previous output failed validation.")[0]
            out.append(json.loads(text))
        return out


class FakeVerifier:
    def __init__(self, refs: list[dict] | None = None, warnings: list[str] | None = None, error=None):
        self.refs = refs if refs is not None else reference_snapshot()
        self.warnings = warnings or []
        self.error = error
        self.queries: list[str] = []

    def search(self, query: str):
        self.queries.append(query)
        if self.error:
            raise self.error
        return {r["id"]: r for r in self.refs}, list(self.warnings)


def install(monkeypatch, client: RecorderClient, verifier: FakeVerifier | None = None, prices=(None, None)):
    from app.config import settings
    from app.services import jobs

    verifier = verifier or FakeVerifier()
    monkeypatch.setattr(settings, "app_mode", "live")
    monkeypatch.setattr(settings, "llm_input_usd_per_million", prices[0])
    monkeypatch.setattr(settings, "llm_output_usd_per_million", prices[1])
    monkeypatch.setattr(jobs, "live_deps_factory",
                        lambda: LiveDeps(gateway=LLMGateway(client=client, model="test-model", max_tokens=1000,
                                                            input_price=prices[0], output_price=prices[1]),
                                         verifier=verifier))
    return verifier
