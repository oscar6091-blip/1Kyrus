"""Upload validation and metric evidence immutability (AC-09, AC-11)."""
import copy
import json

from app.config import HANDOFF_DIR

from conftest import INVALID_RUN, VALID_RUN, rid


def _variant(mutate) -> bytes:
    d = json.loads(VALID_RUN)
    mutate(d)
    return json.dumps(d).encode()


def test_upload_requires_s1_to_s4(api):
    pid = api.create()
    api.through(pid, 3)
    assert api.upload(pid, expect=409)["error"]["code"] == "PREDECESSOR_NOT_APPROVED"


def test_ac09_upload_validation(api):
    pid = api.create()
    api.through(pid, 4)
    run = api.upload(pid)
    assert run["payload"]["metrics"][0]["value"] == 0.9666666666666667

    r = api.upload(pid, INVALID_RUN, expect=422)["error"]
    assert r["code"] == "INVALID_RUN"
    paths = {f["path"] for f in r["fields"]}
    assert "seed" in paths and any(p.startswith("metrics.0.value") for p in paths)

    cases = {
        "nan": VALID_RUN.replace(b"0.9666666666666667", b"NaN", 1),
        "inf": VALID_RUN.replace(b"0.9666666666666667", b"Infinity", 1),
        "dup_key": VALID_RUN.replace(b'"seed": 42,', b'"seed": 42, "seed": 43,'),
        "string_value": _variant(lambda d: d["metrics"][0].__setitem__("value", "0.9")),
        "bool_seed": _variant(lambda d: d.__setitem__("seed", True)),
        "dup_metric": _variant(lambda d: d["metrics"].append(copy.deepcopy(d["metrics"][0]))),
        "unknown_exp": _variant(lambda d: d.__setitem__("experiment_id", "E7")),
        "missing_metric": _variant(lambda d: d.__setitem__("metrics", d["metrics"][:2])),
        "ratio_range": _variant(lambda d: d["metrics"][0].__setitem__("value", 1.5)),
        "no_seed": _variant(lambda d: d.pop("seed")),
    }
    for name, raw in cases.items():
        r = api.upload(pid, raw, expect=422)
        assert r["error"]["code"] == "INVALID_RUN", name
        assert r["error"]["fields"], name

    # original SSRD A.II example: prototype-only fields missing -> 422 at three places
    ctx = json.loads((HANDOFF_DIR / "sources" / "ssrd_context.json").read_text(encoding="utf-8"))
    original = json.dumps(ctx["external_upload_original"]["json_example"]).encode()
    r = api.upload(pid, original, expect=422)["error"]
    paths = {f["path"] for f in r["fields"]}
    assert {"schema_version", "data_origin", "metrics.0.unit"} <= paths
    assert "experiment_result.valid.json" in r["message"]


def test_upload_dedupe_and_other_project_run(api):
    a = api.create()
    api.through(a, 4)
    uid = rid()
    r1 = api.upload(a, upload_id=uid)
    r2 = api.upload(a, upload_id=uid)
    assert r1["id"] == r2["id"]
    other = _variant(lambda d: d.__setitem__("seed", 7))
    assert api.upload(a, other, upload_id=uid, expect=409)["error"]["code"] == "REQUEST_ID_CONFLICT"
    assert len(api.c.get(f"/api/projects/{a}/runs").json()) == 1

    b = api.create(name="b")
    api.through(b, 4)
    r = api.run(b, 5, run_id=r1["id"], expect=422)
    assert r["error"]["code"] == "INVALID_RUN"


def test_file_too_large(api):
    pid = api.create()
    api.through(pid, 4)
    big = b" " * (1024 * 1024 + 10)
    assert api.upload(pid, big, expect=413)["error"]["code"] == "FILE_TOO_LARGE"


def test_ac11_new_run_does_not_change_old_draft(api, client):
    pid = api.create()
    api.through(pid, 6)
    old_s6 = api.stage(pid, 6)["current_artifact"]
    paper_before = client.get(f"/api/projects/{pid}/exports/paper.md").text
    api.upload(pid, _variant(lambda d: d["metrics"][0].__setitem__("value", 0.5)))
    same = client.get(f"/api/projects/{pid}/artifacts/{old_s6['id']}").json()
    assert same["rendered_markdown"] == old_s6["rendered_markdown"]
    assert "0.9666666666666667" in same["rendered_markdown"] and "0.5 (ratio)" not in same["rendered_markdown"]
    assert client.get(f"/api/projects/{pid}/exports/paper.md").text == paper_before
