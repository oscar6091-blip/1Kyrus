"""Experiment result upload (prototype_json_v1), mirroring contracts/upload.schema.json.

The strict JSON parser rejects NaN/Infinity and duplicate object keys before the
Pydantic model sees the data. bool is never accepted as a number.
"""
from __future__ import annotations

import json
import math
from typing import Annotated, Any, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StringConstraints

METRIC_NAME_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$"


class StrictJSONError(ValueError):
    pass


def _reject_constant(name: str) -> Any:
    raise StrictJSONError(f"허용되지 않는 숫자 값: {name}")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise StrictJSONError(f"중복된 키: {k}")
        out[k] = v
    return out


def parse_strict_json(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJSONError("UTF-8 JSON 파일이 아닙니다") from exc
    try:
        return json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise StrictJSONError(f"JSON 문법 오류 (줄 {exc.lineno}, 열 {exc.colno}): {exc.msg}") from exc


def _finite(v: float | int) -> float | int:
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError("유한한 숫자여야 합니다")
    return v


Number = Annotated[Union[StrictInt, StrictFloat], AfterValidator(_finite)]


class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: Annotated[str, StringConstraints(pattern=METRIC_NAME_PATTERN)]
    split: Annotated[str, StringConstraints(min_length=1, max_length=30)]
    value: Number
    step: Annotated[int, Field(ge=0)] | None = None
    unit: Literal["ratio", "percent", "seconds", "count", "loss", "other"]


class ExperimentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0"]
    experiment_id: Annotated[str, StringConstraints(pattern=r"^E[1-9][0-9]*$")]
    code_version: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    config: Annotated[dict[str, Any], Field(min_length=1)]
    seed: StrictInt
    environment: dict[str, Any] | None = None
    metrics: list[Metric] = Field(min_length=1, max_length=100)
    started_at: Annotated[str, StringConstraints(min_length=1, max_length=80)] | None = None
    duration_sec: Annotated[Number, Field(ge=0)] | None = None
    data_origin: Literal["measured", "synthetic_demo"]


MAX_BUNDLE_RUNS = 10


class ExperimentBundle(BaseModel):
    """DEVIATIONS D-07: one upload file holding several runs (one per experiment).
    Each item is checked as an ExperimentResult and stored as its own ExperimentRun."""
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.1"]
    runs: list[dict[str, Any]] = Field(min_length=1, max_length=MAX_BUNDLE_RUNS)
