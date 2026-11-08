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

# DEVIATIONS D-08: raised from the plan's 80,000 so S4 regeneration (previous code included) fits.
MAX_MODEL_INPUT_CHARS = 150_000
MAX_CONFIG_VALUE_CHARS = 2_000
MAX_WARNINGS = 30


def build_snapshot(project: Project, stage: Stage, stages: list[Stage], user_comments: str,
                   run_ids: list[str] | None) -> dict:
    upstream = {str(st.stage_no): st.approved_artifact_id for st in stages
                if st.stage_no < stage.stage_no and st.approved_artifact_id}
    return {
        "brief_artifact_id": project.current_brief_artifact_id if stage.stage_no > 1 else None,
        "upstream_artifact_ids": upstream,
        "previous_artifact_id": stage.current_artifact_id,
        # DEVIATIONS D-07: run_ids lists every S5 input run; run_id keeps the first for older readers.
        "run_id": run_ids[0] if stage.stage_no == 5 and run_ids else None,
        "run_ids": list(run_ids) if stage.stage_no == 5 and run_ids else None,
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


def snapshot_run_ids(snapshot: dict) -> list[str]:
    """S5 input runs. Older snapshots only have run_id."""
    if snapshot.get("run_ids"):
        return list(snapshot["run_ids"])
    return [snapshot["run_id"]] if snapshot.get("run_id") else []


def metric_bindings(run: ExperimentRun, multi: bool = False) -> dict[str, dict]:
    """One ID per uploaded metric row. A single run keeps m0, m1, ...; with several runs
    the ID starts with the experiment ID (E1.m0, E2.m0, ...) so IDs stay unique."""
    payload = json.loads(run.payload_json)
    exp_id = payload["experiment_id"]
    out = {}
    for i, m in enumerate(payload["metrics"]):
        b = {"run_id": run.id, "metric_index": i, "name": m["name"], "split": m["split"],
             "value": m["value"], "step": m.get("step"), "unit": m["unit"]}
        if multi:
            b["experiment_id"] = exp_id
        out[f"{exp_id}.m{i}" if multi else f"m{i}"] = b
    return out


def run_warnings(run: ExperimentRun, multi: bool = False) -> list[str]:
    payload = json.loads(run.payload_json)
    tag = f"[{payload['experiment_id']}] " if multi else ""
    cfg = payload.get("config") or {}
    out = []
    for w in cfg.get("fit_warnings") or []:
        if isinstance(w, str) and w.strip():
            out.append(f"{tag}실행 경고(업로드 config.fit_warnings): {w}"[:2000])
    limit = cfg.get("interpretation_limit")
    if isinstance(limit, str) and limit.strip():
        out.append(f"{tag}해석 한계(업로드 config.interpretation_limit): {limit}"[:2000])
    if payload.get("data_origin") == "synthetic_demo":
        out.append(f"{tag}이 Run의 data_origin은 synthetic_demo입니다. 실제 측정값이 아닙니다.")
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
        runs = [get_run(s, project_id, rid) for rid in snapshot_run_ids(snapshot)]
        multi = len(runs) > 1
        warnings: list[str] = []
        for run in runs:
            ev["metrics"].update(metric_bindings(run, multi))
            warnings += run_warnings(run, multi)
        ev["warnings"] = _dedupe(warnings)
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
    run_ids = snapshot_run_ids(snapshot) if stage_no == 5 else []
    if run_ids:
        exp_ids = [json.loads(get_run(s, project_id, rid).payload_json)["experiment_id"] for rid in run_ids]
        s3 = _payload(get_artifact(s, project_id, snapshot["upstream_artifact_ids"]["3"]))
        ctx.run_hypothesis_ids = set()
        for e in s3["content"]["experiments"]:
            if e["id"] in exp_ids:
                ctx.run_hypothesis_ids.update(e["hypothesis_ids"])
        # With several runs S5 must write one "## E<n>" section per experiment (DEVIATIONS D-07).
        ctx.run_experiment_ids = exp_ids if len(exp_ids) > 1 else []
    return ctx


def allowed_evidence_refs(ctx: ValidationContext) -> list[str]:
    return sorted([f"ref:{i}" for i in ctx.reference_ids] + [f"metric:{i}" for i in ctx.metric_ids]
                  + [f"artifact:{i}" for i in ctx.artifact_ids])


def _upstream_for_model(stage_no: int, n: int, payload: dict) -> dict:
    """S5/S6 interpret results and never need S4 source code, so file contents become a size note
    (DEVIATIONS D-08). Stored artifacts are unchanged."""
    if n != 4 or stage_no < 5:
        return payload
    p = json.loads(json.dumps(payload))
    files = p.get("content", {}).get("files")
    if isinstance(files, list):
        p["content"]["files"] = [{"path": f.get("path"), "omitted_chars": len(f.get("content") or "")}
                                 if isinstance(f, dict) else f for f in files]
    return p


def _run_for_model(run: dict, multi: bool) -> dict:
    """Large config values (seed-wise raw values, step maps) become a size note. With several runs
    metrics are dropped too: metric_bindings already carries every value (DEVIATIONS D-08)."""
    r = dict(run)
    cfg = r.get("config")
    if isinstance(cfg, dict):
        out = {}
        for k, v in cfg.items():
            n = len(json.dumps(v, ensure_ascii=False))
            out[k] = v if n <= MAX_CONFIG_VALUE_CHARS else f"(생략: {n:,}자, 원본은 업로드 Run에 있음)"
        r["config"] = out
    if multi:
        r["metrics"] = f"(metric_bindings의 {r['experiment_id']}.m* 항목 참고)"
    return r


def build_model_input(s: Session, project_id: str, stage_no: int, snapshot: dict, evidence: dict,
                      task_instruction: str, output_schema: dict) -> dict:
    """User-message content for live generation (prompts/stage_prompts.md common structure)."""
    up = load_upstream(s, project_id, snapshot)
    brief = _payload(get_artifact(s, project_id, snapshot["brief_artifact_id"]))["content"]["brief"] \
        if snapshot.get("brief_artifact_id") else None
    prev = _payload(get_artifact(s, project_id, snapshot["previous_artifact_id"])) \
        if snapshot.get("previous_artifact_id") else None
    run_list = [json.loads(get_run(s, project_id, rid).payload_json) for rid in snapshot_run_ids(snapshot)]
    run_list = [_run_for_model(r, len(run_list) > 1) for r in run_list]
    run = run_list[0] if len(run_list) == 1 else None
    ctx = validation_context(s, project_id, stage_no, snapshot, evidence)
    data = {
        "stage_no": stage_no,
        "task_instruction": task_instruction,
        "expected_output_schema": output_schema,
        "project_idea": snapshot["idea_snapshot"],
        "approved_brief": brief,
        "approved_upstream_artifacts": [
            {"stage_no": n, "artifact_id": a.id, "payload": _upstream_for_model(stage_no, n, _payload(a))}
            for n, a in sorted(up.items())
        ],
        "previous_stage_artifact": prev,
        "user_comments": snapshot["user_comments"],
        "verified_references": list(evidence.get("references", {}).values()),
        "selected_experiment_run": run,
        "selected_experiment_runs": run_list if len(run_list) > 1 else [],
        "metric_bindings": evidence.get("metrics", {}),
        "allowed_evidence_refs": allowed_evidence_refs(ctx),
    }
    size = len(json.dumps(data, ensure_ascii=False))
    if size > MAX_MODEL_INPUT_CHARS:
        raise AppError("CONTEXT_TOO_LARGE",
                       f"모델 입력이 {size:,}자로 상한 {MAX_MODEL_INPUT_CHARS:,}자를 넘습니다. 상위 결과나 코멘트를 줄여 주세요.",
                       status=422)
    return data
