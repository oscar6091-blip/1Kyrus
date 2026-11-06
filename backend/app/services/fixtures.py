"""Read demo fixtures from handoff/fixtures. The frontend never hardcodes them."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from ..config import FIXTURES_DIR


@lru_cache(maxsize=None)
def _load(rel: str) -> str:
    return (FIXTURES_DIR / rel).read_text(encoding="utf-8")


def load_fixture(rel: str) -> Any:
    # parse fresh each time so callers can't mutate a shared object
    return json.loads(_load(rel))


def stage_fixture(stage_no: int) -> dict:
    return load_fixture(f"stages/s{stage_no}.json")


def reference_snapshot() -> list[dict]:
    return load_fixture("references.snapshot.json")["references"]
