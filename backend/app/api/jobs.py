from fastapi import APIRouter

from ..services import workflow

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    return workflow.get_job(job_id)
