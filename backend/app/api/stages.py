from fastapi import APIRouter

from ..schemas.domain import DecisionRequest, EditRequest, RunRequest
from ..services import workflow

router = APIRouter()


@router.get("/projects/{project_id}/stages/{stage_no}")
def get_stage(project_id: str, stage_no: int):
    return workflow.stage_detail(project_id, stage_no)


@router.post("/projects/{project_id}/stages/{stage_no}/run", status_code=202)
def run_stage(project_id: str, stage_no: int, body: RunRequest):
    _check_stage_no(stage_no)
    return workflow.run_stage(project_id, stage_no, body)


@router.post("/projects/{project_id}/stages/{stage_no}/decisions")
def decide(project_id: str, stage_no: int, body: DecisionRequest):
    _check_stage_no(stage_no)
    return workflow.decide(project_id, stage_no, body)


@router.post("/projects/{project_id}/stages/{stage_no}/edits")
def edit(project_id: str, stage_no: int, body: EditRequest):
    _check_stage_no(stage_no)
    return workflow.edit(project_id, stage_no, body)


def _check_stage_no(stage_no: int) -> None:
    from ..errors import AppError

    if not 1 <= stage_no <= 6:
        raise AppError("NOT_FOUND", "단계를 찾을 수 없습니다.")
