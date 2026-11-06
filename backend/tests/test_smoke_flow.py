"""AC-01/AC-13 style end-to-end demo flow through the API only."""
import io
import json
import zipfile

from app.config import FIXTURES_DIR


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "default_mode": "demo", "live_configured": False}


def test_full_demo_flow_and_exports(api, client):
    pid = api.create()
    assert api.project(pid)["project"]["mode"] == "demo"
    api.through(pid, 6)
    detail = api.project(pid)
    assert [s["status"] for s in detail["stages"]] == ["approved"] * 6

    z = client.get(f"/api/projects/{pid}/exports/code.zip")
    assert z.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    assert sorted(zf.namelist()) == ["README.md", "requirements.txt", "train.py"]
    assert "데모 모드" in zf.read("README.md").decode()
    ref_train = (FIXTURES_DIR.parent / "reference_experiment" / "train.py").read_bytes()
    assert zf.read("train.py") == ref_train  # original code unchanged (SHA preserved)

    md = client.get(f"/api/projects/{pid}/exports/paper.md")
    assert md.status_code == 200
    text = md.text
    for title in ["## Abstract", "## Introduction", "## Related Work", "## Methods", "## Experiments", "## Conclusion"]:
        assert title in text
    assert "데모 모드" in text
    assert "0.9666666666666667" in text and "0.9665831244778612" in text
    assert "{{" not in text

    bib = client.get(f"/api/projects/{pid}/exports/references.bib")
    assert bib.status_code == 200
    assert bib.text.count("@misc{") == 3
    assert "Kingma" in bib.text and "데모 모드" in bib.text


def test_reference_metrics_are_exact(api):
    pid = api.create()
    api.through(pid, 5)
    expected = json.loads((FIXTURES_DIR / "expected_reference_metrics.json").read_text())
    ev = api.stage(pid, 5)["current_artifact"]["evidence"]
    got = [{k: b[k] for k in ("name", "split", "value", "step", "unit")} for b in ev["metrics"].values()]
    assert got == expected["metrics"]
    verdicts = api.current_payload(pid, 5)["content"]["hypothesis_verdicts"]
    assert verdicts[0]["verdict"] == expected["expected_verdict"]
    assert any("Maximum iterations" in w for w in ev["warnings"])


def test_cors_allows_both_loopback_names_for_changed_web_port(monkeypatch, tmp_path):
    """README "포트를 바꿀 때": FRONTEND_ORIGIN=http://127.0.0.1:3200 also allows http://localhost:3200."""
    from fastapi.testclient import TestClient

    from app import db
    from app.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "frontend_origin", "http://127.0.0.1:3200")
    db.init_engine(f"sqlite:///{tmp_path / 'cors.db'}")
    with TestClient(create_app()) as c:
        for origin in ("http://127.0.0.1:3200", "http://localhost:3200", "http://127.0.0.1:3000"):
            r = c.get("/api/health", headers={"Origin": origin})
            assert r.headers.get("access-control-allow-origin") == origin
        r = c.get("/api/health", headers={"Origin": "http://evil.example"})
        assert "access-control-allow-origin" not in r.headers
