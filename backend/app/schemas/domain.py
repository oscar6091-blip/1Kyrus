"""Request bodies from contracts/domain.schema.json. Response views are plain dicts
built in services/repository.py with exactly the contract's fields."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from .artifacts import Text

Id = Annotated[str, StringConstraints(min_length=1, max_length=100)]
Comment = Annotated[str, StringConstraints(max_length=4000)]


class Req(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCreate(Req):
    name: Text(120)
    idea: Text(8000)


class RunRequest(Req):
    request_id: Id
    user_comments: Comment
    run_id: Id | None


class DecisionRequest(Req):
    request_id: Id
    action: Literal["approve", "regenerate", "back"]
    artifact_id: Id
    comment: Comment
    run_id: Id | None


class EditRequest(Req):
    request_id: Id
    base_artifact_id: Id
    payload: dict[str, Any]
    comment: Comment
