from fastapi import APIRouter
from fastapi.responses import Response

from ..services import exports

router = APIRouter()


def _attachment(content: bytes | str, media_type: str, filename: str) -> Response:
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/projects/{project_id}/exports/code.zip")
def export_code(project_id: str):
    return _attachment(exports.code_zip(project_id), "application/zip", "code.zip")


@router.get("/projects/{project_id}/exports/paper.md")
def export_paper(project_id: str):
    return _attachment(exports.paper_md(project_id).encode("utf-8"), "text/markdown; charset=utf-8", "paper.md")


@router.get("/projects/{project_id}/exports/references.bib")
def export_bib(project_id: str):
    return _attachment(exports.references_bib(project_id).encode("utf-8"), "application/x-bibtex; charset=utf-8",
                       "references.bib")
