"""Export gates and code path safety (AC-12, AC-13)."""
import copy

from app.services.validation import check_file_path


def test_exports_blocked_before_approval_and_when_stale(api, client):
    pid = api.create()
    for f in ("code.zip", "paper.md", "references.bib"):
        assert client.get(f"/api/projects/{pid}/exports/{f}").status_code == 409
    api.through(pid, 2)
    assert client.get(f"/api/projects/{pid}/exports/references.bib").status_code == 200  # from S2
    api.run_wait(pid, 1)  # new S1 draft -> approve -> S2 stale
    api.approve_current(pid, 1)
    r = client.get(f"/api/projects/{pid}/exports/references.bib")
    assert r.status_code == 409


def test_ac12_unsafe_paths_rejected(api):
    pid = api.create()
    api.through(pid, 3)
    api.run_wait(pid, 4)
    s4 = api.stage(pid, 4)["current_artifact"]
    for bad in ["../../escape.py", "/etc/passwd", "a\\b.py", "C:/x.py", ".env", "dir/.env", "a/../b.py", "a\x00.py"]:
        p = copy.deepcopy(s4["payload"])
        p["content"]["files"].append({"path": bad, "content": "x = 1\n", "language": "python"})
        r = api.edit(pid, 4, s4["id"], p, expect=422)
        assert r["error"]["code"] == "INVALID_PAYLOAD", bad
    p = copy.deepcopy(s4["payload"])
    p["content"]["files"].append({"path": "dup.py", "content": "def (:\n", "language": "python"})
    r = api.edit(pid, 4, s4["id"], p, expect=422)
    assert any("문법" in f["message"] for f in r["error"]["fields"])
    assert check_file_path("src/model.py") is None


def test_no_code_execution_path():
    import pathlib

    src = pathlib.Path(__file__).resolve().parents[1] / "app"
    text = "\n".join(p.read_text(encoding="utf-8") for p in src.rglob("*.py"))
    for needle in ("subprocess", "exec(", "eval(", "importlib", "__import__"):
        assert needle not in text, needle
