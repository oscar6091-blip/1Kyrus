"""ExportService: approved S4 zip, approved S6 Markdown, BibTeX. Adds the demo marker."""
from __future__ import annotations

import io
import json
import zipfile

from ..db import tx
from ..errors import AppError
from .rendering import render_paper_body
from .repository import get_artifact, get_project, get_stages
from .validation import check_file_path

DEMO_MARK = "데모 모드: 사전 작성 산출물 사용"


def _approved(s, project_id: str, stage_no: int, what: str):
    st = get_stages(s, project_id)[stage_no - 1]
    if st.status == "stale":
        raise AppError("STALE_INPUT", f"S{stage_no}이(가) 오래됨(stale) 상태라 {what}을(를) 내보낼 수 없습니다. 재생성·재승인하세요.")
    if st.status != "approved" or not st.approved_artifact_id:
        raise AppError("INVALID_STAGE_STATE", f"S{stage_no}을(를) 승인해야 {what}을(를) 내보낼 수 있습니다.")
    return get_artifact(s, project_id, st.approved_artifact_id)


def code_zip(project_id: str) -> bytes:
    with tx() as s:
        p = get_project(s, project_id)
        art = _approved(s, project_id, 4, "코드 zip")
        files = json.loads(art.payload_json)["content"]["files"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        has_readme = False
        for f in files:
            err = check_file_path(f["path"])
            if err:
                raise AppError("INVALID_PAYLOAD", "zip에 넣을 수 없는 파일 경로가 있습니다.", [{"path": f["path"], "message": err}])
            content = f["content"]
            if f["path"] == "README.md":
                has_readme = True
                if p.mode == "demo":
                    content = f"> {DEMO_MARK}. 이 코드는 서버에서 실행되지 않았습니다.\n\n{content}"
            zf.writestr(f["path"], content)
        if p.mode == "demo" and not has_readme:
            zf.writestr("README.md", f"> {DEMO_MARK}. 이 코드는 서버에서 실행되지 않았습니다.\n")
    return buf.getvalue()


def paper_md(project_id: str) -> str:
    with tx() as s:
        p = get_project(s, project_id)
        art = _approved(s, project_id, 6, "논문 초안")
        payload, evidence = json.loads(art.payload_json), json.loads(art.evidence_json)
    head = f"# {p.name}\n\n"
    if p.mode == "demo":
        head += f"> **{DEMO_MARK}** (Demo mode: pre-written stage outputs). Measured values come from the uploaded run file.\n\n"
    head += f"> Draft exported from approved S6 version {art.version} ({art.id}).\n\n"
    return head + render_paper_body(payload, evidence) + "\n"


def _bib_escape(text: str) -> str:
    out = []
    for ch in str(text):
        if ch in "{}\\":
            out.append({"{": "\\{", "}": "\\}", "\\": "\\textbackslash{}"}[ch])
        elif ch in "&%$#_":
            out.append("\\" + ch)
        elif ch == "~":
            out.append("\\textasciitilde{}")
        elif ch == "^":
            out.append("\\textasciicircum{}")
        else:
            out.append(ch)
    return "".join(out)


def references_bib(project_id: str) -> str:
    with tx() as s:
        p = get_project(s, project_id)
        stages = get_stages(s, project_id)
        s6, s2 = stages[5], stages[1]
        if s6.status == "approved" and s6.approved_artifact_id:
            art = get_artifact(s, project_id, s6.approved_artifact_id)
        elif s6.status == "stale":
            raise AppError("STALE_INPUT", "S6가 오래됨(stale) 상태라 참고문헌을 내보낼 수 없습니다.")
        else:
            art = _approved(s, project_id, 2, "참고문헌")
        refs = json.loads(art.evidence_json)["references"]
    lines = []
    if p.mode == "demo":
        lines.append(f"% {DEMO_MARK}")
    lines.append(f"% Exported from S{art.stage_no} version {art.version}. Only verified references are included.")
    for r in refs.values():
        key = "".join(ch if ch.isalnum() or ch in "_-:" else "_" for ch in r["id"])
        authors = " and ".join(_bib_escape(a) for a in r["authors"])
        lines.append(
            f"@misc{{{key},\n  title = {{{_bib_escape(r['title'])}}},\n  author = {{{authors}}},\n"
            f"  year = {{{r['year']}}},\n  eprint = {{{_bib_escape(r['arxiv_id'])}}},\n  archivePrefix = {{arXiv}},\n"
            f"  url = {{{_bib_escape(r['source_url'])}}},\n  note = {{Verified: {r['verification_source']}, {_bib_escape(r['verified_at'])}}}\n}}"
        )
    return "\n\n".join(lines) + "\n"
