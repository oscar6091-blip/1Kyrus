"""ORM mapping onto the tables created from handoff/contracts/database.sql.

Columns, keys and constraints mirror the DDL. The DDL itself (not create_all)
creates the tables, including the partial unique index for one active job.
"""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    idea: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    current_brief_artifact_id: Mapped[str | None] = mapped_column(Text, ForeignKey("artifact_versions.id"))
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (CheckConstraint("mode IN ('demo','live')"),)


class Stage(Base):
    __tablename__ = "stages"
    project_id: Mapped[str] = mapped_column(Text, ForeignKey("projects.id"), primary_key=True)
    stage_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    current_artifact_id: Mapped[str | None] = mapped_column(Text, ForeignKey("artifact_versions.id"))
    approved_artifact_id: Mapped[str | None] = mapped_column(Text, ForeignKey("artifact_versions.id"))
    __table_args__ = (
        CheckConstraint("stage_no BETWEEN 1 AND 6"),
        CheckConstraint("status IN ('pending','running','needs_review','approved','stale')"),
    )


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(Text, nullable=False)
    stage_no: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "stage_no"], ["stages.project_id", "stages.stage_no"]),
        UniqueConstraint("project_id", "stage_no", "version"),
        CheckConstraint("version >= 1"),
        CheckConstraint("created_by IN ('ai','user','fixture')"),
    )


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    request_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str] = mapped_column(Text, nullable=False)
    stage_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_artifact_id: Mapped[str | None] = mapped_column(Text, ForeignKey("artifact_versions.id"))
    usage_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "stage_no"], ["stages.project_id", "stages.stage_no"]),
        CheckConstraint("status IN ('queued','running','succeeded','failed','interrupted')"),
        Index("uq_active_job_per_project", "project_id", unique=True,
              sqlite_where=text("status IN ('queued','running')")),
    )


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    request_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str] = mapped_column(Text, nullable=False)
    stage_no: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_id: Mapped[str] = mapped_column(Text, ForeignKey("artifact_versions.id"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    result_artifact_id: Mapped[str | None] = mapped_column(Text, ForeignKey("artifact_versions.id"))
    job_id: Mapped[str | None] = mapped_column(Text, ForeignKey("jobs.id"))
    navigate_to_stage: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "stage_no"], ["stages.project_id", "stages.stage_no"]),
        CheckConstraint("action IN ('approve','edit','regenerate','back')"),
    )


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(Text, ForeignKey("projects.id"), nullable=False)
    client_upload_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "client_upload_id"),)

