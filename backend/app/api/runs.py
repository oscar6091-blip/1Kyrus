from fastapi import APIRouter, File, Form, UploadFile

from ..errors import AppError
from ..services import runs

router = APIRouter()


@router.get("/projects/{project_id}/runs")
def list_runs(project_id: str):
    return runs.list_runs(project_id)


@router.post("/projects/{project_id}/runs", status_code=201)
async def upload_run(project_id: str, file: UploadFile = File(...), client_upload_id: str = Form(...)):
    raw = await file.read(runs.MAX_UPLOAD_BYTES + 1)
    if len(raw) > runs.MAX_UPLOAD_BYTES:
        raise AppError("FILE_TOO_LARGE", "업로드 파일은 1 MiB 이하여야 합니다.", [{"path": "file", "message": "1 MiB 초과"}])
    return runs.upload(project_id, raw, client_upload_id)
