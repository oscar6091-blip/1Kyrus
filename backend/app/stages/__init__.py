"""Live stage generation (T06). Every model call goes through services/llm_gateway.

The system prompt, per-stage task text and correction text are read from
handoff/prompts/stage_prompts.md, so the app and the plan share one source.
Output schemas come from handoff/contracts/artifacts.schema.json with $refs inlined.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ..config import CONTRACTS_DIR, PROMPTS_FILE
from ..db import tx
from ..schemas.artifacts import SearchQuery
from ..services import jobs
from ..services.context import allowed_evidence_refs, build_evidence, build_model_input, validation_context
from ..services.llm_gateway import LLMGateway
from ..services.references import CitationVerifier
from ..services.stage_runner import GenerationResult
from ..services.validation import validate_payload
from . import s1, s2, s3, s4, s5, s6

STAGES = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6}


@dataclass
class LiveDeps:
    gateway: LLMGateway
    verifier: CitationVerifier


def get_live_deps() -> LiveDeps:
    if jobs.live_deps_factory is not None:
        return jobs.live_deps_factory()
    return LiveDeps(gateway=LLMGateway(), verifier=CitationVerifier())


# ---------- prompt text from handoff/prompts/stage_prompts.md ----------

@lru_cache(maxsize=1)
def _prompt_doc() -> str:
    return PROMPTS_FILE.read_text(encoding="utf-8")


def section(heading: str) -> str:
    doc = _prompt_doc()
    start = doc.index(heading + "\n")
    rest = doc[start + len(heading) + 1:]
    m = re.search(r"^## ", rest, re.M)
    return (rest[: m.start()] if m else rest).strip()


def code_block(text: str) -> str:
    m = re.search(r"```text\n(.*?)\n```", text, re.S)
    return m.group(1).strip() if m else text.strip()


def system_prompt() -> str:
    return code_block(section("## 모든 단계의 system 지시"))


def correction_template() -> str:
    return code_block(section("## JSON 보정 지시"))


# ---------- output schemas from contracts/artifacts.schema.json ----------

@lru_cache(maxsize=1)
def _schema_doc() -> dict:
    return json.loads((CONTRACTS_DIR / "artifacts.schema.json").read_text(encoding="utf-8"))


def output_schema(name: str) -> dict:
    defs = _schema_doc()["$defs"]

    def inline(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node and node["$ref"].startswith("#/$defs/"):
                return inline(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: inline(v) for k, v in node.items()}
        if isinstance(node, list):
            return [inline(x) for x in node]
        return node

    return inline(copy.deepcopy(defs[name]))


def _validate_search(obj: dict) -> dict:
    from pydantic import ValidationError

    from ..errors import AppError, pydantic_fields

    try:
        return SearchQuery.model_validate(obj).model_dump()
    except ValidationError as exc:
        raise AppError("INVALID_PAYLOAD", "검색어 형식이 다릅니다.", pydantic_fields(exc.errors())) from exc


def generate_live(project_id: str, stage_no: int, snapshot: dict, usage: dict) -> GenerationResult:
    deps = get_live_deps()
    gw = deps.gateway
    system = system_prompt()
    s2_refs, s2_warnings = None, None

    if stage_no == 2:
        with tx() as s:
            query_input = build_model_input(s, project_id, 2, snapshot, {"references": {}, "metrics": {}, "warnings": []},
                                            code_block(section(s2.SEARCH_SECTION)), output_schema("SearchQuery"))
        query = gw.generate_json(system, query_input, _validate_search, usage, correction_template())
        s2_refs, s2_warnings = deps.verifier.search(query["search_query"])  # network, outside any transaction

    with tx() as s:
        evidence = build_evidence(s, project_id, stage_no, snapshot, s2_references=s2_refs, s2_warnings=s2_warnings)
        ctx = validation_context(s, project_id, stage_no, snapshot, evidence)
        model_input = build_model_input(s, project_id, stage_no, snapshot, evidence,
                                        section(STAGES[stage_no].SECTION), output_schema(f"Stage{stage_no}"))

    payload = gw.generate_json(system, model_input, lambda obj: validate_payload(stage_no, obj, ctx), usage,
                               correction_template(), allowed_evidence_refs(ctx))
    return GenerationResult(payload=payload, evidence=evidence, created_by="ai", model=gw.model)
