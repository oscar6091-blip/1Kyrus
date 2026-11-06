"""ContextBuilder: input snapshots, evidence copying, validation context, model input.

Snapshots hold artifact IDs only. Workers load those exact IDs and never reread
the current stage pointers (WF-10).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import ArtifactVersion, ExperimentRun, Project, Stage
from .repository import get_artifact, get_run
from .validation import ValidationContext

MAX_MODEL_INPUT_CHARS = 80_000
MAX_WARNINGS = 30


def build_snapshot(project: Project, stage: Stage, stages: list[Stage], user_comments: str,
                   run_id: str | None) -> dict:
    upstream = {str(st.stage_no): st.approved_artifact_id for st in stages
                if st.stage_no < stage.stage_no and st.approved_artifact_id}
    return {
        "brief_artifact_id": project.current_brief_artifact_id if stage.stage_no > 1 else None,
        "upstream_artifact_ids": upstream,
        "previous_artifact_id": stage.current_artifact_id,
        "run_id": run_id if stage.stage_no == 5 else None,
        "user_comments": user_comments,
        "idea_snapshot": project.idea,
    }


def snapshot_is_current(snapshot: dict, stage_no: int, stages: list[Stage]) -> bool:
    by_no = {st.stage_no: st for st in stages}
    for n in range(1, stage_no):
        st = by_no[n]
        if st.status != "approved" or snapshot["upstream_artifact_ids"].get(str(n)) != st.approved_artifact_id:
            return False
    return True


def _payload(a: ArtifactVersion) -> dict:
    return json.loads(a.payload_json)


def _evidence(a: ArtifactVersion) -> dict:
    return json.loads(a.evidence_json)


def load_upstream(s: Session, project_id: str, snapshot: dict) -> dict[int, ArtifactVersion]:
    return {int(k): get_artifact(s, project_id, v) for k, v in snapshot["upstream_artifact_ids"].items()}


def brief_hypothesis_ids(s: Session, project_id: str, snapshot: dict) -> list[str]:
    bid = snapshot.get("brief_artifact_id")
    if not bid:
        return []
    brief = _payload(get_artifact(s, project_id, bid))
    return [h["id"] for h in brief["content"]["brief"]["hypotheses"]]


def metric_bindings(run: ExperimentRun) -> dict[str, dict]:
    payload = json.loads(run.payload_json)
    out = {}
    for i, m in enumerate(payload["metrics"]):
        out[f"m{i}"] = {"run_id": run.id, "metric_index": i, "name": m["name"], "split": m["split"],
                        "value": m["value"], "step": m.get("step"), "unit": m["unit"]}
    return out


def run_warnings(run: ExperimentRun) -> list[str]:
    payload = json.loads(run.payload_json)
    cfg = payload.get("config") or {}
    out = []
    for w in cfg.get("fit_warnings") or []:
        if isinstance(w, str) and w.strip():
            out.append(f"실행 경고(업로드 config.fit_warnings): {w}"[:2000])
    limit = cfg.get("interpretation_limit")
    if isinstance(limit, str) and limit.strip():
        out.append(f"해석 한계(업로드 config.interpretation_limit): {limit}"[:2000])
    if payload.get("data_origin") == "synthetic_demo":
        out.append("이 Run의 data_origin은 synthetic_demo입니다. 실제 측정값이 아닙니다.")
    return out


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for w in items:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:MAX_WARNINGS]


def build_evidence(s: Session, project_id: str, stage_no: int, snapshot: dict,
                   s2_references: dict | None = None, s2_warnings: list[str] | None = None) -> dict:
    """Evidence for a new generation. S2 references come from the caller (fixture or arXiv)."""
    up = load_upstream(s, project_id, snapshot)
    ev: dict[str, Any] = {"references": {}, "metrics": {}, "warnings": []}
    if stage_no == 2:
        ev["references"] = s2_references or {}
        ev["warnings"] = _dedupe(s2_warnings or [])
    elif stage_no in (3, 4):
        ev["references"] = _evidence(up[2])["references"]
    elif stage_no == 5:
        ev["references"] = _evidence(up[2])["references"]
        run = get_run(s, project_id, snapshot["run_id"])
        ev["metrics"] = metric_bindings(run)
        ev["warnings"] = _dedupe(run_warnings(run))
    elif stage_no == 6:
        s2, s5 = _evidence(up[2]), _evidence(up[5])
        ev["references"] = s2["references"]
        ev["metrics"] = s5["metrics"]
        ev["warnings"] = _dedupe(s2["warnings"] + s5["warnings"])
    return ev


def validation_context(s: Session, project_id: str, stage_no: int, snapshot: dict, evidence: dict) -> ValidationContext:
    ctx = ValidationContext(
        hypothesis_ids=brief_hypothesis_ids(s, project_id, snapshot),
        reference_ids=set(evidence.get("references", {})),
        metric_ids=set(evidence.get("metrics", {})),
        artifact_ids={v for v in [snapshot.get("brief_artifact_id"), snapshot.get("previous_artifact_id"),
                                  *snapshot.get("upstream_artifact_ids", {}).values()] if v},
    )
    if stage_no == 5 and snapshot.get("run_id"):
        run = get_run(s, project_id, snapshot["run_id"])
        exp_id = json.loads(run.payload_json)["experiment_id"]
        s3 = _payload(get_artifact(s, project_id, snapshot["upstream_artifact_ids"]["3"]))
        ctx.run_hypothesis_ids = set()
        for e in s3["content"]["experiments"]:
            if e["id"] == exp_id:
                ctx.run_hypothesis_ids.update(e["hypothesis_ids"])
    return ctx


def allowed_evidence_refs(ctx: ValidationContext) -> list[str]:
    return sorted([f"ref:{i}" for i in ctx.reference_ids] + [f"metric:{i}" for i in ctx.metric_ids]
                  + [f"artifact:{i}" for i in ctx.artifact_ids])


def build_model_input(s: Session, project_id: str, stage_no: int, snapshot: dict, evidence: dict,
                      task_instruction: str, output_schema: dict) -> dict:
    """User-message content for live generation (prompts/stage_prompts.md common structure)."""
    up = load_upstream(s, project_id, snapshot)
    brief = _payload(get_artifact(s, project_id, snapshot["brief_artifact_id"]))["content"]["brief"] \
        if snapshot.get("brief_artifact_id") else None
    prev = _payload(get_artifact(s, project_id, snapshot["previous_artifact_id"])) \
        if snapshot.get("previous_artifact_id") else None
    run = json.loads(get_run(s, project_id, snapshot["run_id"]).payload_json) if snapshot.get("run_id") else None
    ctx = validation_context(s, project_id, stage_no, snapshot, evidence)
    data = {
        "stage_no": stage_no,
        "task_instruction": task_instruction,
        "expected_output_schema": output_schema,
        "project_idea": snapshot["idea_snapshot"],
        "approved_brief": brief,
        "approved_upstream_artifacts": [
            {"stage_no": n, "artifact_id": a.id, "payload": _payload(a)} for n, a in sorted(up.items())
        ],
        "previous_stage_artifact": prev,
        "user_comments": snapshot["user_comments"],
        "verified_references": list(evidence.get("references", {}).values()),
        "selected_experiment_run": run,
        "metric_bindings": evidence.get("metrics", {}),
        "allowed_evidence_refs": allowed_evidence_refs(ctx),
    }
    size = len(json.dumps(data, ensure_ascii=False))
    if size > MAX_MODEL_INPUT_CHARS:
        raise AppError("CONTEXT_TOO_LARGE",
                       f"모델 입력이 {size:,}자로 상한 {MAX_MODEL_INPUT_CHARS:,}자를 넘습니다. 상위 결과나 코멘트를 줄여 주세요.",
                       status=422)
    return data
