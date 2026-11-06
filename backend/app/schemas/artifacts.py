"""Pydantic models mirroring handoff/contracts/artifacts.schema.json (S1~S6 payloads).

Structure only. Cross-artifact rules (hypothesis coverage, evidence IDs, tokens)
live in services/validation.py.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _nonblank(v: str) -> str:
    if not v.strip():
        raise ValueError("빈 문자열은 저장할 수 없습니다")
    return v


def Text(max_len: int, min_len: int = 1):  # noqa: N802
    return Annotated[str, StringConstraints(min_length=min_len, max_length=max_len), AfterValidator(_nonblank)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Rationale(Strict):
    decision_key: Text(100)
    reason: Text(3000)
    evidence_refs: list[Annotated[str, StringConstraints(min_length=1, max_length=160)]] = Field(max_length=20)
    alternatives: list[Text(500)] = Field(max_length=5)


RationaleList = Annotated[list[Rationale], Field(min_length=1, max_length=20)]


class Hypothesis(Strict):
    id: Annotated[str, StringConstraints(pattern=r"^H[1-9][0-9]*$")]
    statement: Text(2000)


class Brief(Strict):
    research_problem: Text(3000)
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=5)
    expected_contribution: Text(2000)
    evaluation_plan: Text(4000)
    constraints: Text(2000)
    results_conclusion: None


class Stage1Content(Strict):
    brief: Brief
    clarification_questions: list[Text(500)] = Field(max_length=3)


class Stage1(Strict):
    stage_no: Literal[1]
    content: Stage1Content
    rationale: RationaleList


class BodyContent(Strict):
    body_md: Text(20000)


class Stage2(Strict):
    stage_no: Literal[2]
    content: BodyContent
    rationale: RationaleList


class Experiment(Strict):
    id: Annotated[str, StringConstraints(pattern=r"^E[1-9][0-9]*$")]
    label: Text(200)
    hypothesis_ids: list[Text(20)] = Field(min_length=1, max_length=5)
    metric_names: list[Text(64)] = Field(min_length=1, max_length=20)


class Stage3Content(Strict):
    body_md: Text(20000)
    experiments: list[Experiment] = Field(min_length=1, max_length=5)


class Stage3(Strict):
    stage_no: Literal[3]
    content: Stage3Content
    rationale: RationaleList


class CodeFile(Strict):
    path: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    content: Annotated[str, StringConstraints(max_length=65536)]
    language: Literal["python", "text", "markdown", "json", "yaml"]


class Stage4Content(Strict):
    body_md: Text(20000)
    files: list[CodeFile] = Field(min_length=1, max_length=10)


class Stage4(Strict):
    stage_no: Literal[4]
    content: Stage4Content
    rationale: RationaleList


class Verdict(Strict):
    hypothesis_id: Text(20)
    verdict: Literal["supported", "partly_supported", "not_supported", "inconclusive"]
    reason: Text(3000)


class Stage5Content(Strict):
    body_md: Text(20000)
    hypothesis_verdicts: list[Verdict] = Field(min_length=1, max_length=5)


class Stage5(Strict):
    stage_no: Literal[5]
    content: Stage5Content
    rationale: RationaleList


class Section(Strict):
    key: Literal["abstract", "introduction", "related_work", "methods", "experiments", "conclusion"]
    body_md: Text(15000)


class Stage6Content(Strict):
    sections: list[Section] = Field(min_length=6, max_length=6)


class Stage6(Strict):
    stage_no: Literal[6]
    content: Stage6Content
    rationale: RationaleList


class SearchQuery(Strict):
    search_query: Text(300)


STAGE_MODELS: dict[int, type[Strict]] = {1: Stage1, 2: Stage2, 3: Stage3, 4: Stage4, 5: Stage5, 6: Stage6}

Payload = Union[Stage1, Stage2, Stage3, Stage4, Stage5, Stage6]

SECTION_ORDER = ["abstract", "introduction", "related_work", "methods", "experiments", "conclusion"]
