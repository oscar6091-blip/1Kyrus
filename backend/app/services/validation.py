"""Structure + meaning checks shared by generation, edit and approval (WF-15).

`validate_payload` returns the normalized payload dict or raises AppError
(INVALID_PAYLOAD for structure/meaning, UNKNOWN_EVIDENCE for unknown IDs/tokens).
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from pydantic import ValidationError

from ..errors import AppError, pydantic_fields
from ..schemas.artifacts import SECTION_ORDER, STAGE_MODELS
from ..schemas.upload import METRIC_NAME_PATTERN

TOKEN_RE = re.compile(r"\{\{(.*?)\}\}", re.S)
TOKEN_BODY_RE = re.compile(r"^(cite|metric):([A-Za-z0-9_.\-]+)$")
ABLATION_HEADING = "## Ablation 계획"

MAX_FILES_TOTAL_BYTES = 500 * 1024


@dataclass
class ValidationContext:
    """What the payload may refer to. Built from the artifact's own snapshot/evidence."""

    hypothesis_ids: list[str] = field(default_factory=list)      # approved Brief H IDs (S3, S5)
    reference_ids: set[str] = field(default_factory=set)         # evidence.references keys
    metric_ids: set[str] = field(default_factory=set)            # evidence.metrics keys
    artifact_ids: set[str] = field(default_factory=set)          # IDs in input_snapshot
    run_hypothesis_ids: set[str] | None = None                   # S5: H IDs of the selected run's experiment


class _Collector:
    def __init__(self) -> None:
        self.invalid: list[dict[str, str]] = []
        self.unknown: list[dict[str, str]] = []

    def bad(self, path: str, msg: str) -> None:
        self.invalid.append({"path": path, "message": msg})

    def unk(self, path: str, msg: str) -> None:
        self.unknown.append({"path": path, "message": msg})

    def raise_if_any(self) -> None:
        if self.invalid:
            raise AppError("INVALID_PAYLOAD", "결과 내용이 형식 또는 규칙에 맞지 않습니다.", self.invalid + self.unknown)
        if self.unknown:
            raise AppError("UNKNOWN_EVIDENCE", "허용되지 않은 근거·인용·지표 ID가 있습니다.", self.unknown)


def check_tokens(text: str, path: str, ctx: ValidationContext, col: _Collector,
                 allow_cite: bool = True, allow_metric: bool = True) -> None:
    for m in TOKEN_RE.finditer(text):
        body = m.group(1).strip()
        tm = TOKEN_BODY_RE.match(body)
        if not tm:
            col.unk(path, f"지원하지 않는 토큰: {{{{{body}}}}}")
            continue
        kind, ident = tm.groups()
        if kind == "cite" and (not allow_cite or ident not in ctx.reference_ids):
            col.unk(path, f"확인되지 않은 인용 ID: {ident}")
        if kind == "metric" and (not allow_metric or ident not in ctx.metric_ids):
            col.unk(path, f"등록되지 않은 지표 ID: {ident}")
    stripped = TOKEN_RE.sub("", text)
    if "{{" in stripped or "}}" in stripped:
        col.unk(path, "닫히지 않았거나 깨진 {{...}} 토큰이 있습니다")


def _check_rationale(payload: dict, ctx: ValidationContext, col: _Collector) -> None:
    for i, r in enumerate(payload.get("rationale", [])):
        for j, ref in enumerate(r.get("evidence_refs", [])):
            kind, _, ident = ref.partition(":")
            ok = (kind == "ref" and ident in ctx.reference_ids) or \
                 (kind == "metric" and ident in ctx.metric_ids) or \
                 (kind == "artifact" and ident in ctx.artifact_ids)
            if not ok:
                col.unk(f"rationale.{i}.evidence_refs.{j}", f"현재 근거에 없는 ID: {ref}")


def _ablation_ok(body: str) -> bool:
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == ABLATION_HEADING:
            rest = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                rest.append(nxt)
            return bool("".join(rest).strip())
    return False


def check_file_path(path: str) -> str | None:
    """Return an error message, or None if the path is a safe relative POSIX path."""
    if "\x00" in path:
        return "NUL 문자는 허용되지 않습니다"
    if "\\" in path:
        return "역슬래시는 허용되지 않습니다"
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        return "절대 경로는 허용되지 않습니다"
    parts = PurePosixPath(path).parts
    if not parts or any(p in ("..", ".", "") for p in path.split("/")):
        return "상대 경로의 '..', '.', 빈 경로 조각은 허용되지 않습니다"
    name = parts[-1]
    if name == ".env" or name.startswith(".env."):
        return ".env 파일은 허용되지 않습니다"
    return None


def validate_payload(stage_no: int, payload: Any, ctx: ValidationContext) -> dict:
    if not isinstance(payload, dict):
        raise AppError("INVALID_PAYLOAD", "payload는 객체여야 합니다.", [{"path": "payload", "message": "object 필요"}])
    if payload.get("stage_no") != stage_no:
        raise AppError("INVALID_PAYLOAD", "payload.stage_no가 경로의 단계 번호와 다릅니다.",
                       [{"path": "stage_no", "message": f"{stage_no} 이어야 합니다"}])
    model = STAGE_MODELS[stage_no]
    try:
        obj = model.model_validate(payload)
    except ValidationError as exc:
        raise AppError("INVALID_PAYLOAD", "결과 형식이 계약과 다릅니다.", pydantic_fields(exc.errors())) from exc
    data = obj.model_dump(mode="json")
    col = _Collector()
    c = data["content"]

    if stage_no == 1:
        ids = [h["id"] for h in c["brief"]["hypotheses"]]
        for i, h in enumerate(ids):
            if ids.count(h) > 1:
                col.bad(f"content.brief.hypotheses.{i}.id", f"가설 ID 중복: {h}")
        for key in ("research_problem", "expected_contribution", "evaluation_plan", "constraints"):
            check_tokens(c["brief"][key], f"content.brief.{key}", ctx, col, allow_cite=False, allow_metric=False)

    elif stage_no == 2:
        if not (1 <= len(ctx.reference_ids) <= 3):
            col.bad("evidence.references", "확인된 참고문헌은 1~3개여야 합니다")
        check_tokens(c["body_md"], "content.body_md", ctx, col, allow_metric=False)

    elif stage_no == 3:
        check_tokens(c["body_md"], "content.body_md", ctx, col, allow_metric=False)
        if not _ablation_ok(c["body_md"]):
            col.bad("content.body_md", f"'{ABLATION_HEADING}' 제목과 비어 있지 않은 계획 또는 해당 없음 사유가 필요합니다")
        brief_h = set(ctx.hypothesis_ids)
        seen_e: set[str] = set()
        covered: set[str] = set()
        for i, e in enumerate(c["experiments"]):
            if e["id"] in seen_e:
                col.bad(f"content.experiments.{i}.id", f"실험 ID 중복: {e['id']}")
            seen_e.add(e["id"])
            for j, h in enumerate(e["hypothesis_ids"]):
                if h not in brief_h:
                    col.bad(f"content.experiments.{i}.hypothesis_ids.{j}", f"승인 Brief에 없는 가설 ID: {h}")
                if e["hypothesis_ids"].count(h) > 1:
                    col.bad(f"content.experiments.{i}.hypothesis_ids.{j}", f"한 실험 안의 가설 ID 중복: {h}")
                covered.add(h)
            for j, mname in enumerate(e["metric_names"]):
                if not re.match(METRIC_NAME_PATTERN, mname):
                    col.bad(f"content.experiments.{i}.metric_names.{j}", "업로드 지표 이름 형식(영문 시작, 영숫자·_.-)이 아닙니다")
                if e["metric_names"].count(mname) > 1:
                    col.bad(f"content.experiments.{i}.metric_names.{j}", f"지표 이름 중복: {mname}")
        for h in sorted(brief_h - covered):
            col.bad("content.experiments", f"가설 {h}에 대응하는 실험이 없습니다")

    elif stage_no == 4:
        check_tokens(c["body_md"], "content.body_md", ctx, col, allow_metric=False)
        seen_p: set[str] = set()
        total = 0
        for i, f in enumerate(c["files"]):
            err = check_file_path(f["path"])
            if err:
                col.bad(f"content.files.{i}.path", err)
            if f["path"] in seen_p:
                col.bad(f"content.files.{i}.path", f"중복 경로: {f['path']}")
            seen_p.add(f["path"])
            total += len(f["content"].encode("utf-8"))
            if f["language"] == "python" or f["path"].endswith(".py"):
                try:
                    ast.parse(f["content"], filename="<generated>")
                except SyntaxError as exc:
                    col.bad(f"content.files.{i}.content", f"Python 문법 오류 (줄 {exc.lineno}): {exc.msg}")
                except ValueError as exc:  # e.g. NUL bytes in source
                    col.bad(f"content.files.{i}.content", f"Python 코드를 읽을 수 없습니다: {exc}")
        if total > MAX_FILES_TOTAL_BYTES:
            col.bad("content.files", "파일 전체 크기는 500 KiB 이하여야 합니다")

    elif stage_no == 5:
        check_tokens(c["body_md"], "content.body_md", ctx, col)
        brief_h = list(ctx.hypothesis_ids)
        got = [v["hypothesis_id"] for v in c["hypothesis_verdicts"]]
        for i, v in enumerate(c["hypothesis_verdicts"]):
            h = v["hypothesis_id"]
            path = f"content.hypothesis_verdicts.{i}"
            if h not in brief_h:
                col.bad(f"{path}.hypothesis_id", f"승인 Brief에 없는 가설 ID: {h}")
            elif got.count(h) > 1:
                col.bad(f"{path}.hypothesis_id", f"가설 판정 중복: {h}")
            elif ctx.run_hypothesis_ids is not None and h not in ctx.run_hypothesis_ids and v["verdict"] != "inconclusive":
                col.bad(f"{path}.verdict", f"{h}는 선택한 실행의 실험에 대응하지 않으므로 inconclusive만 허용됩니다")
        for h in brief_h:
            if h not in got:
                col.bad("content.hypothesis_verdicts", f"가설 {h}의 판정이 없습니다")

    elif stage_no == 6:
        keys = [s["key"] for s in c["sections"]]
        if keys != SECTION_ORDER:
            col.bad("content.sections", "섹션은 " + ", ".join(SECTION_ORDER) + " 순서로 한 번씩 있어야 합니다")
        for i, s in enumerate(c["sections"]):
            check_tokens(s["body_md"], f"content.sections.{i}.body_md", ctx, col)

    _check_rationale(data, ctx, col)
    col.raise_if_any()
    return data
