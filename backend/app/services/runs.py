"""ExperimentRun upload (prototype_json_v1). The server never runs experiments."""
from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError
from sqlalchemy import select

from ..db import tx
from ..errors import AppError, pydantic_fields
from ..models import ExperimentRun
from ..schemas.upload import ExperimentResult, StrictJSONError, parse_strict_json
from .repository import active_job, dumps, get_artifact, get_project, get_stages, new_id, now, run_view, touch

MAX_UPLOAD_BYTES = 1024 * 1024
FORMAT_HINT = ("현재 업로드 형식은 prototype_json_v1입니다. 원문 SSRD A.II 형식에 schema_version, data_origin, "
               "metrics[].unit 필드가 추가로 필요하며 자동 변환은 하지 않습니다. 정상 예시: handoff/fixtures/experiment_result.valid.json")

UNIT_RULES = {
    "ratio": (lambda v: 0 <= v <= 1, "ratio는 0~1이어야 합니다"),
    "percent": (lambda v: 0 <= v <= 100, "percent는 0~100이어야 합니다"),
    "seconds": (lambda v: v >= 0, "seconds는 음수일 수 없습니다"),
    "count": (lambda v: v >= 0, "count는 음수일 수 없습니다"),
}


def _invalid(message: str, fields: list[dict]) -> AppError:
    return AppError("INVALID_RUN", f"{message} {FORMAT_HINT}", fields)


def validate_upload(raw: bytes) -> dict:
    """Parse + structure checks that do not need the project. Returns the parsed object."""
    try:
        data = parse_strict_json(raw)
    except StrictJSONError as exc:
        raise _invalid("JSON 파일을 읽을 수 없습니다.", [{"path": "$", "message": str(exc)}]) from exc
    try:
        ExperimentResult.model_validate(data)
    except ValidationError as exc:
        raise _invalid("업로드 형식이 prototype_json_v1과 다릅니다.", pydantic_fields(exc.errors())) from exc
    fields = []
    seen = {}
    for i, m in enumerate(data["metrics"]):
        rule = UNIT_RULES.get(m["unit"])
        if rule and not rule[0](m["value"]):
            fields.append({"path": f"metrics.{i}.value", "message": rule[1]})
        k = (m["name"], m["split"], m.get("step"))
        if k in seen:
            fields.append({"path": f"metrics.{i}", "message": f"metrics.{seen[k]}과 (name, split, step)이 중복됩니다"})
        seen.setdefault(k, i)
    if fields:
        raise _invalid("지표 값이 규칙에 맞지 않습니다.", fields)
    return data


def upload(project_id: str, raw: bytes, client_upload_id: str) -> dict:
    if not client_upload_id or len(client_upload_id) > 100:
        raise AppError("INVALID_PAYLOAD", "client_upload_id는 1~100자여야 합니다.", [{"path": "client_upload_id", "message": "1~100자"}])
    if len(raw) > MAX_UPLOAD_BYTES:
        raise AppError("FILE_TOO_LARGE", "업로드 파일은 1 MiB 이하여야 합니다.", [{"path": "file", "message": f"{len(raw)} bytes"}])
    data = validate_upload(raw)
    sha = hashlib.sha256(dumps(data).encode("utf-8")).hexdigest()
    with tx() as s:
        p = get_project(s, project_id)
        prior = s.scalars(select(ExperimentRun).where(ExperimentRun.project_id == project_id,
                                                      ExperimentRun.client_upload_id == client_upload_id)).first()
        if prior is not None:
            if prior.payload_sha256 != sha:
                raise AppError("REQUEST_ID_CONFLICT", "같은 client_upload_id로 다른 내용이 이미 업로드되었습니다.")
            return run_view(prior)
        if active_job(s, project_id) is not None:
            raise AppError("PROJECT_BUSY", "이 프로젝트에서 작업이 진행 중입니다. 완료된 뒤 업로드하세요.")
        stages = get_stages(s, project_id)
        for st in stages[:4]:
            if not (st.status == "approved" and st.approved_artifact_id):
                raise AppError("PREDECESSOR_NOT_APPROVED", "S1~S4를 모두 승인한 뒤 실험 결과를 업로드할 수 있습니다.")
        if data["data_origin"] == "synthetic_demo" and p.mode != "demo":
            raise _invalid("synthetic_demo 결과는 demo 프로젝트에만 올릴 수 있습니다.",
                           [{"path": "data_origin", "message": "live 프로젝트에는 measured만 허용"}])
        s3 = json.loads(get_artifact(s, project_id, stages[2].approved_artifact_id).payload_json)
        exps = {e["id"]: e for e in s3["content"]["experiments"]}
        exp = exps.get(data["experiment_id"])
        if exp is None:
            raise _invalid("승인된 S3 계획에 없는 실험 ID입니다.",
                           [{"path": "experiment_id", "message": f"{data['experiment_id']} 없음. 허용: {', '.join(exps)}"}])
        names = {m["name"] for m in data["metrics"]}
        missing = [n for n in exp["metric_names"] if n not in names]
        if missing:
            raise _invalid("승인된 S3의 필수 지표가 빠졌습니다.", [{"path": "metrics", "message": f"누락: {', '.join(missing)}"}])
        run = ExperimentRun(id=new_id(), project_id=project_id, client_upload_id=client_upload_id,
                            payload_sha256=sha, payload_json=json.dumps(data, ensure_ascii=False), created_at=now())
        s.add(run)
        s.flush()
        touch(s, project_id)
        return run_view(run)


def list_runs(project_id: str) -> list[dict]:
    with tx() as s:
        get_project(s, project_id)
        rows = s.scalars(select(ExperimentRun).where(ExperimentRun.project_id == project_id)
                         .order_by(ExperimentRun.created_at).limit(100))
        return [run_view(r) for r in rows]
