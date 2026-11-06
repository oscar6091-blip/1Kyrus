"""TokenRenderer: payload + the artifact's own evidence -> Markdown preview.

Values are formatted by one function (`fmt_value`) with no rounding, so
0.9666666666666667 is never shown as 97%. Units get their own table column.
"""
from __future__ import annotations

import re

TOKEN_RE = re.compile(r"\{\{\s*(cite|metric):([A-Za-z0-9_.\-]+)\s*\}\}")

SECTION_TITLES = {"abstract": "Abstract", "introduction": "Introduction", "related_work": "Related Work",
                  "methods": "Methods", "experiments": "Experiments", "conclusion": "Conclusion"}
VERDICT_KO = {"supported": "지지", "partly_supported": "부분 지지", "not_supported": "지지되지 않음",
              "inconclusive": "판단 불가(inconclusive)"}


def fmt_value(v) -> str:
    if isinstance(v, bool):
        return str(v)
    return repr(v) if isinstance(v, float) else str(v)


def _esc(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def cite_label(ref: dict) -> str:
    authors = ref.get("authors") or []
    last = lambda name: name.split()[-1] if name.split() else name  # noqa: E731
    if len(authors) == 1:
        who = last(authors[0])
    elif len(authors) == 2:
        who = f"{last(authors[0])} and {last(authors[1])}"
    else:
        who = f"{last(authors[0])} et al."
    return f"[{who}, {ref.get('year')}]({ref.get('source_url')})"


def replace_tokens(text: str, evidence: dict) -> str:
    refs, metrics = evidence.get("references", {}), evidence.get("metrics", {})

    def sub(m: re.Match) -> str:
        kind, ident = m.group(1), m.group(2)
        if kind == "cite" and ident in refs:
            return cite_label(refs[ident])
        if kind == "metric" and ident in metrics:
            b = metrics[ident]
            return f"{fmt_value(b['value'])} ({b['unit']})"
        return f"⟦알 수 없는 근거: {kind}:{ident}⟧"

    return TOKEN_RE.sub(sub, text)


def metrics_table(evidence: dict, english: bool = False) -> str:
    metrics = evidence.get("metrics", {})
    if not metrics:
        return ""
    head = "| ID | metric | split | step | value | unit |" if english else "| ID | 지표 | split | step | 값 | 단위 |"
    rows = [head, "|---|---|---|---|---|---|"]
    for key, b in metrics.items():
        rows.append(f"| {key} | {_esc(b['name'])} | {_esc(b['split'])} | {'' if b['step'] is None else b['step']} "
                    f"| {fmt_value(b['value'])} | {b['unit']} |")
    return "\n".join(rows)


def references_list(evidence: dict, english: bool = False) -> str:
    out = []
    label = "verified" if english else "확인"
    for ref in evidence.get("references", {}).values():
        authors = ", ".join(ref["authors"])
        out.append(f"- **{ref['id']}** — {authors} ({ref['year']}). *{ref['title']}*. arXiv:{ref['arxiv_id']}. "
                   f"<{ref['source_url']}> ({label}: {ref['verification_source']}, {ref['verified_at']})")
    return "\n".join(out)


def warnings_block(evidence: dict, english: bool = False) -> str:
    ws = evidence.get("warnings", [])
    if not ws:
        return ""
    title = "## Warnings" if english else "## 경고"
    return title + "\n" + "\n".join(f"- {_esc(w)}" for w in ws)


def render_paper_body(payload: dict, evidence: dict) -> str:
    parts = []
    for s in payload["content"]["sections"]:
        parts.append(f"## {SECTION_TITLES.get(s['key'], s['key'])}\n\n{replace_tokens(s['body_md'], evidence)}")
    table = metrics_table(evidence, english=True)
    if table:
        parts.append("## Measurement Table (from uploaded run)\n\n" + table)
    refs = references_list(evidence, english=True)
    if refs:
        parts.append("## References\n\n" + refs)
    w = warnings_block(evidence, english=True)
    if w:
        parts.append(w)
    return "\n\n".join(parts)


def render_markdown(stage_no: int, payload: dict, evidence: dict) -> str:
    c = payload.get("content", {})
    parts: list[str] = []
    if stage_no == 1:
        b = c["brief"]
        parts.append(f"## 연구 문제\n{replace_tokens(b['research_problem'], evidence)}")
        parts.append("## 가설\n" + "\n".join(f"- **{h['id']}**: {h['statement']}" for h in b["hypotheses"]))
        parts.append(f"## 예상 기여\n{b['expected_contribution']}")
        parts.append(f"## 평가 계획\n{b['evaluation_plan']}")
        parts.append(f"## 제약\n{b['constraints']}")
        if c.get("clarification_questions"):
            parts.append("## 확인 질문\n" + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(c["clarification_questions"])))
    elif stage_no == 2:
        parts.append(replace_tokens(c["body_md"], evidence))
        parts.append("## 확인된 참고문헌 (초록 기반)\n" + references_list(evidence))
    elif stage_no == 3:
        parts.append(replace_tokens(c["body_md"], evidence))
        rows = ["## 실험 목록", "| 실험 ID | 설명 | 가설 | 필수 지표 |", "|---|---|---|---|"]
        for e in c["experiments"]:
            rows.append(f"| {e['id']} | {_esc(e['label'])} | {', '.join(e['hypothesis_ids'])} | {', '.join(e['metric_names'])} |")
        parts.append("\n".join(rows))
    elif stage_no == 4:
        parts.append(replace_tokens(c["body_md"], evidence))
        parts.append("## 파일\n" + "\n".join(f"- `{f['path']}` ({f['language']}, {len(f['content'])}자)" for f in c["files"]))
        parts.append("> 서버 미실행: 이 코드는 서비스가 실행하지 않습니다. 문법 검사만 통과했을 수 있으며 학습 성공을 뜻하지 않습니다.")
    elif stage_no == 5:
        table = metrics_table(evidence)
        if table:
            parts.append("## 원본 지표 표 (업로드 Run, 서버 생성)\n" + table)
        parts.append(replace_tokens(c["body_md"], evidence))
        rows = ["## 가설 판정", "| 가설 | 판정 | 사유 |", "|---|---|---|"]
        for v in c["hypothesis_verdicts"]:
            rows.append(f"| {v['hypothesis_id']} | {VERDICT_KO[v['verdict']]} | {_esc(v['reason'])} |")
        parts.append("\n".join(rows))
    elif stage_no == 6:
        parts.append(render_paper_body(payload, evidence))
        return "\n\n".join(parts)
    w = warnings_block(evidence)
    if w:
        parts.append(w)
    return "\n\n".join(parts)
