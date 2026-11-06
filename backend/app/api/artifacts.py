from fastapi import APIRouter

from ..services import workflow

router = APIRouter()


@router.get("/projects/{project_id}/artifacts/{artifact_id}")
def get_artifact(project_id: str, artifact_id: str):
    return workflow.get_artifact_view(project_id, artifact_id)
