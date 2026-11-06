"""CitationVerifier (internal module). arXiv is the external service.

Bibliographic fields come from the arXiv Atom response, never from the model.
One connection at a time, at least 3 seconds apart, 20 s timeout. Failures are
reported (ARXIV_UNAVAILABLE / NO_VERIFIED_REFERENCES), never replaced by fixtures.
"""
from __future__ import annotations

import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Callable

from ..errors import AppError

ARXIV_URL = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}
MAX_REFERENCES = 3

_lock = threading.Lock()
_last_call = [0.0]


def default_http_get(url: str, params: dict, timeout: float = 20.0) -> str:
    import httpx

    with _lock:
        wait = 3.0 - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.get(url, params=params, headers={"User-Agent": "research-workflow-prototype/0.1"})
            r.raise_for_status()
            return r.text
        finally:
            _last_call[0] = time.monotonic()


def normalize_arxiv_id(raw: str) -> str:
    m = re.search(r"arxiv\.org/abs/(.+)$", raw.strip())
    ident = m.group(1) if m else raw.strip()
    return re.sub(r"v\d+$", "", ident)


def ref_key(arxiv_id: str) -> str:
    return "arxiv_" + re.sub(r"[^A-Za-z0-9]", "_", arxiv_id)


def build_query(text: str) -> str:
    terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", text)[:5]
    if not terms:
        raise AppError("NO_VERIFIED_REFERENCES", "검색어에서 영문 검색 키워드를 찾지 못했습니다.",
                       [{"path": "search_query", "message": text[:200] or "(빈 검색어)"}], status=422)
    return " AND ".join(f"all:{t}" for t in terms)


def _text(el, path: str) -> str:
    found = el.find(path, NS)
    return re.sub(r"\s+", " ", found.text).strip() if found is not None and found.text else ""


def parse_atom(xml_text: str, verified_at: str) -> tuple[list[dict], list[str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise AppError("ARXIV_UNAVAILABLE", "arXiv 응답을 해석할 수 없습니다.", status=502, retryable=True) from exc
    refs, warnings = [], []
    for entry in root.findall("a:entry", NS):
        raw_id = _text(entry, "a:id")
        title = _text(entry, "a:title")
        label = title or raw_id or "(제목 없음)"
        if "api/errors" in raw_id or title.lower() == "error":
            warnings.append(f"arXiv 오류 항목 제외: {_text(entry, 'a:summary')[:300]}")
            continue
        arxiv_id = normalize_arxiv_id(raw_id) if raw_id else ""
        authors = [_text(a, "a:name") for a in entry.findall("a:author", NS)]
        authors = [a for a in authors if a]
        published = _text(entry, "a:published")
        year = int(published[:4]) if re.match(r"^\d{4}", published) else None
        missing = [n for n, v in (("arXiv ID", arxiv_id), ("제목", title), ("저자", authors), ("첫 제출 연도", year)) if not v]
        if missing:
            warnings.append(f"미검증 후보 제외: {label[:200]} — 메타데이터 누락({', '.join(missing)})")
            continue
        abstract = _text(entry, "a:summary") or None
        refs.append({
            "id": ref_key(arxiv_id), "arxiv_id": arxiv_id, "title": title[:1000], "authors": [a[:160] for a in authors[:40]],
            "year": year, "source_url": f"https://arxiv.org/abs/{arxiv_id}",
            "abstract": abstract[:20000] if abstract else None, "abstract_summary": None,
            "verified": True, "verification_source": "arxiv_live", "verified_at": verified_at,
        })
    return refs, warnings


class CitationVerifier:
    def __init__(self, http_get: Callable[[str, dict], str] | None = None):
        self.http_get = http_get or default_http_get

    def search(self, query_text: str) -> tuple[dict, list[str]]:
        params = {"search_query": build_query(query_text), "start": 0, "max_results": MAX_REFERENCES + 2,
                  "sortBy": "relevance"}
        try:
            xml_text = self.http_get(ARXIV_URL, params)
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001 - any network/HTTP failure
            raise AppError("ARXIV_UNAVAILABLE", f"arXiv 조회에 실패했습니다: {type(exc).__name__}", status=502,
                           retryable=True) from exc
        verified_at = datetime.now(timezone.utc).date().isoformat()
        refs, warnings = parse_atom(xml_text, verified_at)
        seen, chosen = set(), []
        for r in refs:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            chosen.append(r)
        if not chosen:
            fields = [{"path": "references", "message": w} for w in warnings] or \
                     [{"path": "search_query", "message": f"검색 결과 없음: {params['search_query']}"}]
            raise AppError("NO_VERIFIED_REFERENCES", "확인된 논문이 한 편도 없어 S2를 만들 수 없습니다.", fields, status=422)
        return {r["id"]: r for r in chosen[:MAX_REFERENCES]}, warnings
