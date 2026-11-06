"""LLMGateway: the ONLY module that talks to the Anthropic SDK.

- SDK auto-retries are disabled (max_retries=0).
- timeout / refusal / max_tokens truncation fail the job; they are never "fixed" by retrying.
- Only parse/schema/evidence validation failures get ONE correction request.
- Every call is added to the Job usage (tokens, calls, cost when prices are configured).
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from ..config import settings
from ..errors import AppError

MAX_PREVIOUS_CHARS = 6000


class ModelOutputInvalid(Exception):
    def __init__(self, message: str, fields: list[dict]):
        super().__init__(message)
        self.fields = fields


def make_client():
    import anthropic

    headers = {"anthropic-workspace-id": settings.anthropic_workspace_id} if settings.anthropic_workspace_id else None
    return anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds,
                               max_retries=0, default_headers=headers)


def parse_json_object(text: str) -> dict:
    t = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, re.S)
    if fence:
        t = fence.group(1)
    try:
        obj = json.loads(t, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ModelOutputInvalid("모델 출력이 JSON이 아닙니다.", [{"path": "$", "message": str(exc)[:500]}]) from exc
    if not isinstance(obj, dict):
        raise ModelOutputInvalid("모델 출력이 JSON 객체가 아닙니다.", [{"path": "$", "message": "object 필요"}])
    return obj


class LLMGateway:
    def __init__(self, client: Any = None, model: str | None = None, max_tokens: int | None = None,
                 input_price: float | None = None, output_price: float | None = None):
        self.client = client if client is not None else make_client()
        self.model = model or settings.llm_model
        self.max_tokens = max_tokens or settings.llm_max_output_tokens
        self.input_price = settings.llm_input_usd_per_million if input_price is None else input_price
        self.output_price = settings.llm_output_usd_per_million if output_price is None else output_price

    # ---- one HTTP call ----
    def call(self, system: str, user_text: str, usage: dict) -> str:
        import anthropic

        try:
            resp = self.client.messages.create(model=self.model, max_tokens=self.max_tokens, system=system,
                                               messages=[{"role": "user", "content": user_text}])
        except anthropic.APITimeoutError as exc:
            raise AppError("LLM_TIMEOUT", "모델 응답 시간이 초과되었습니다.", status=504, retryable=True) from exc
        except anthropic.APIConnectionError as exc:
            raise AppError("LLM_TIMEOUT", "모델 API에 연결하지 못했습니다.", status=504, retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise AppError("LLM_API_ERROR", f"모델 API가 오류를 반환했습니다 (HTTP {exc.status_code}).",
                           status=502, retryable=exc.status_code in (429, 500, 502, 503, 529)) from exc
        self._add_usage(usage, getattr(resp, "usage", None))
        stop = getattr(resp, "stop_reason", None)
        if stop == "refusal":
            raise AppError("LLM_REFUSAL", "모델이 요청을 거절했습니다.", status=502)
        if stop == "max_tokens":
            raise AppError("LLM_TRUNCATED", "모델 출력이 최대 토큰 수에서 잘렸습니다. LLM_MAX_OUTPUT_TOKENS를 늘리거나 입력을 줄이세요.", status=502)
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
        if not text.strip():
            raise AppError("INVALID_MODEL_JSON", "모델 출력에 텍스트가 없습니다.", status=502)
        return text

    def _add_usage(self, usage: dict, u: Any) -> None:
        usage["calls"] = usage.get("calls", 0) + 1
        if u is None:
            return
        it, ot = getattr(u, "input_tokens", None), getattr(u, "output_tokens", None)
        if it is not None:
            usage["input_tokens"] = (usage.get("input_tokens") or 0) + it
        if ot is not None:
            usage["output_tokens"] = (usage.get("output_tokens") or 0) + ot
        if self.input_price is not None and self.output_price is not None \
                and usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
            usage["estimated_cost_usd"] = round(usage["input_tokens"] * self.input_price / 1e6
                                                + usage["output_tokens"] * self.output_price / 1e6, 6)

    # ---- JSON generation with at most one correction ----
    def generate_json(self, system: str, user_obj: dict, validate: Callable[[dict], dict], usage: dict,
                      correction_template: str, allowlist: list[str] | None = None) -> dict:
        user_text = json.dumps(user_obj, ensure_ascii=False)
        text = self.call(system, user_text, usage)
        try:
            return self._check(text, validate)
        except ModelOutputInvalid as first:
            prompt = (correction_template
                      .replace("<structured errors>", json.dumps(first.fields, ensure_ascii=False))
                      .replace("<allowlist>", json.dumps(allowlist or [], ensure_ascii=False))
                      .replace("<bounded previous text>", text[:MAX_PREVIOUS_CHARS]))
            text2 = self.call(system, user_text + "\n\n" + prompt, usage)
            try:
                return self._check(text2, validate)
            except ModelOutputInvalid as second:
                raise AppError("INVALID_MODEL_JSON", f"보정 요청 후에도 모델 출력이 검증을 통과하지 못했습니다: {second}",
                               second.fields, status=502) from second

    @staticmethod
    def _check(text: str, validate: Callable[[dict], dict]) -> dict:
        obj = parse_json_object(text)
        try:
            return validate(obj)
        except AppError as exc:
            if exc.code in ("INVALID_PAYLOAD", "UNKNOWN_EVIDENCE"):
                raise ModelOutputInvalid(exc.message, exc.fields) from exc
            raise
