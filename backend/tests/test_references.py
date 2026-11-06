"""CitationVerifier with a recorded Atom response (AC-08). No network."""
from pathlib import Path

import pytest

from app.errors import AppError
from app.services.references import CitationVerifier, build_query, normalize_arxiv_id

ATOM = (Path(__file__).parent / "data" / "arxiv_recorded.xml").read_text(encoding="utf-8")
EMPTY = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>q</title></feed>'


def test_parse_recorded_atom():
    seen = {}

    def http_get(url, params):
        seen.update(params)
        return ATOM

    refs, warnings = CitationVerifier(http_get).search("adam optimizer for small MLP")
    assert seen["search_query"] == "all:adam AND all:optimizer AND all:for AND all:small AND all:MLP"
    assert list(refs) == ["arxiv_1412_6980", "arxiv_1711_05101"]
    adam = refs["arxiv_1412_6980"]
    assert adam["arxiv_id"] == "1412.6980"  # version suffix removed
    assert adam["title"] == "Adam: A Method for Stochastic Optimization"  # whitespace normalized
    assert adam["year"] == 2014 and adam["authors"] == ["Diederik P. Kingma", "Jimmy Ba"]
    assert adam["verification_source"] == "arxiv_live" and adam["verified"] is True
    assert len(warnings) == 1 and "A Candidate Without Authors" in warnings[0] and "저자" in warnings[0]


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
