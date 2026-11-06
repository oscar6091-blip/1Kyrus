from fastapi import APIRouter, Response

from ..schemas.domain import ProjectCreate
from ..services import workflow

router = APIRouter()


@router.get("/projects")
def list_projects():
    return workflow.list_projects()


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate):
    return workflow.create_project(body)


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return workflow.project_detail(project_id)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    """DEVIATIONS D-04: not in contracts/api.openapi.json."""
    workflow.delete_project(project_id)
    return Response(status_code=204)


@router.get("/projects/{project_id}/decisions")
def list_decisions(project_id: str):
    return workflow.list_decisions(project_id)
