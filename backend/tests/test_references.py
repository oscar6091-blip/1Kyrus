"""CitationVerifier with a recorded Atom response (AC-08). No network."""
from pathlib import Path

import pytest

from app.errors import AppError
from app.services.references import CitationVerifier, build_query, normalize_arxiv_id

ATOM = (Path(__file__).parent / "data" / "arxiv_recorded.xml").read_text(encoding="utf-8")
EMPTY = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>q</title></feed>'


def test_parse_recorded_atom():
    seen = []

    def http_get(url, params):
        seen.append(params["search_query"])
        return ATOM

    refs, warnings = CitationVerifier(http_get).search("adam optimizer for small MLP")
    assert seen[0] == "all:adam AND all:optimizer AND all:for AND all:small AND all:MLP"
    assert list(refs) == ["arxiv_1412_6980", "arxiv_1711_05101"]
    adam = refs["arxiv_1412_6980"]
    assert adam["arxiv_id"] == "1412.6980"  # version suffix removed
    assert adam["title"] == "Adam: A Method for Stochastic Optimization"  # whitespace normalized
    assert adam["year"] == 2014 and adam["authors"] == ["Diederik P. Kingma", "Jimmy Ba"]
    assert adam["verification_source"] == "arxiv_live" and adam["verified"] is True
    assert "A Candidate Without Authors" in warnings[0] and "저자" in warnings[0]
    # Only 2 papers verified, so the query was shortened down to 2 terms; repeated warnings are not duplicated.
    assert seen[-1] == "all:adam AND all:optimizer" and len(seen) == 4
    assert len(warnings) == 2 and "다시 찾았습니다" in warnings[1]


def _feed(*ids):
    entries = "".join(
        f"<entry><id>http://arxiv.org/abs/{i}v1</id><title>Paper {i}</title>"
        f"<author><name>A. Author</name></author><published>2020-01-01T00:00:00Z</published>"
        f"<summary>abs</summary></entry>" for i in ids)
    return f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{entries}</feed>'


def test_zero_results_retry_with_fewer_terms():
    # The live failure: the fifth term "1D" made the AND query match nothing.
    answers = {5: _feed(), 4: _feed("2001.00001", "2001.00002"), 3: _feed("2001.00002", "2001.00003", "2001.00004")}
    seen = []

    def http_get(url, params):
        seen.append(params["search_query"])
        return answers[params["search_query"].count("all:")]

    refs, warnings = CitationVerifier(http_get).search("implicit neural representation extrapolation 1D")
    assert seen == ["all:implicit AND all:neural AND all:representation AND all:extrapolation AND all:1D",
                    "all:implicit AND all:neural AND all:representation AND all:extrapolation",
                    "all:implicit AND all:neural AND all:representation"]
    assert list(refs) == ["arxiv_2001_00001", "arxiv_2001_00002", "arxiv_2001_00003"]  # merged in query order, no duplicates
    assert "다시 찾았습니다" in warnings[-1]


def test_full_first_result_needs_one_call():
    seen = []

    def http_get(url, params):
        seen.append(params["search_query"])
        return _feed("2001.00001", "2001.00002", "2001.00003", "2001.00004")

    refs, warnings = CitationVerifier(http_get).search("neural extrapolation periodic")
    assert len(seen) == 1 and len(refs) == 3 and warnings == []


def test_failure_after_partial_results_keeps_them():
    def http_get(url, params):
        if params["search_query"].count("all:") == 3:
            return _feed("2001.00001")
        raise ConnectionError("down")

    refs, warnings = CitationVerifier(http_get).search("neural extrapolation periodic")
    assert list(refs) == ["arxiv_2001_00001"] and "추가 검색 실패" in warnings[0]


def test_no_results_after_all_retries_lists_queries():
    with pytest.raises(AppError) as e:
        CitationVerifier(lambda u, p: EMPTY).search("a b c")
    assert e.value.code == "NO_VERIFIED_REFERENCES"
    assert e.value.fields[0]["message"] == "검색 결과 없음: all:a AND all:b AND all:c / all:a AND all:b"


def test_no_verified_references():
    with pytest.raises(AppError) as e:
        CitationVerifier(lambda u, p: EMPTY).search("nothing")
    assert e.value.code == "NO_VERIFIED_REFERENCES" and e.value.fields


def test_all_candidates_rejected_reports_reasons():
    only_bad = ATOM.split("<entry>")[0] + "<entry>" + ATOM.split("<entry>")[2].split("</entry>")[0] + "</entry></feed>"
    with pytest.raises(AppError) as e:
        CitationVerifier(lambda u, p: only_bad).search("x")
    assert e.value.code == "NO_VERIFIED_REFERENCES"
    assert any("A Candidate Without Authors" in f["message"] for f in e.value.fields)


def test_network_failure_is_reported():
    def down(url, params):
        raise ConnectionError("down")
    with pytest.raises(AppError) as e:
        CitationVerifier(down).search("adam")
    assert e.value.code == "ARXIV_UNAVAILABLE"


def test_helpers():
    assert normalize_arxiv_id("http://arxiv.org/abs/cs/0101001v2") == "cs/0101001"
    with pytest.raises(AppError):
        build_query("한국어만")
