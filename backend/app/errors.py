"""Standard error shape: {error:{code,message,fields:[{path,message}],retryable}}."""
from __future__ import annotations

from typing import Any

HTTP_STATUS = {
    "PROJECT_BUSY": 409,
    "PREDECESSOR_NOT_APPROVED": 409,
    "STALE_INPUT": 409,
    "ARTIFACT_NOT_CURRENT": 409,
    "INVALID_STAGE_STATE": 409,
    "REQUEST_ID_CONFLICT": 409,
    "NOT_FOUND": 404,
    "INVALID_PAYLOAD": 422,
    "UNKNOWN_EVIDENCE": 422,
    "INVALID_RUN": 422,
    "LIVE_NOT_CONFIGURED": 503,
    "FILE_TOO_LARGE": 413,
}

RETRYABLE = {"PROJECT_BUSY", "LLM_TIMEOUT", "ARXIV_UNAVAILABLE", "INTERRUPTED_RESTART"}


class AppError(Exception):
    def __init__(self, code: str, message: str, fields: list[dict[str, str]] | None = None,
                 status: int | None = None, retryable: bool | None = None):
        super().__init__(message)
        self.code = code
        self.message = message[:2000]
        self.fields = [
            {"path": (f.get("path") or "$")[:200], "message": (f.get("message") or "invalid")[:1000]}
            for f in (fields or [])
        ][:100]
        self.status = status or HTTP_STATUS.get(code, 500)
        self.retryable = (code in RETRYABLE) if retryable is None else retryable

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "fields": self.fields, "retryable": self.retryable}


def not_found(what: str) -> AppError:
    return AppError("NOT_FOUND", f"{what}을(를) 찾을 수 없습니다.")


def loc_to_path(loc: tuple | list) -> str:
    parts = [str(p) for p in loc if p not in ("body",)]
    return ".".join(parts) or "$"


def pydantic_fields(errors: list[dict], prefix: str = "") -> list[dict[str, str]]:
    out = []
    for e in errors:
        path = loc_to_path(e.get("loc", ()))
        if prefix:
            path = f"{prefix}.{path}" if path != "$" else prefix
        out.append({"path": path, "message": e.get("msg", "invalid")})
    return out
