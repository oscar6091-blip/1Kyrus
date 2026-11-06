PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  idea TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('demo', 'live')),
  current_brief_artifact_id TEXT REFERENCES artifact_versions(id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stages (
  project_id TEXT NOT NULL REFERENCES projects(id),
  stage_no INTEGER NOT NULL CHECK (stage_no BETWEEN 1 AND 6),
  status TEXT NOT NULL CHECK (status IN ('pending','running','needs_review','approved','stale')),
  current_artifact_id TEXT REFERENCES artifact_versions(id),
  approved_artifact_id TEXT REFERENCES artifact_versions(id),
  PRIMARY KEY (project_id, stage_no)
);

CREATE TABLE IF NOT EXISTS artifact_versions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  stage_no INTEGER NOT NULL,
  version INTEGER NOT NULL CHECK (version >= 1),
  payload_json TEXT NOT NULL,
  input_snapshot_json TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  created_by TEXT NOT NULL CHECK (created_by IN ('ai','user','fixture')),
  model TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (project_id, stage_no) REFERENCES stages(project_id, stage_no),
  UNIQUE (project_id, stage_no, version)
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  request_key TEXT NOT NULL UNIQUE,
  request_fingerprint TEXT NOT NULL,
  project_id TEXT NOT NULL,
  stage_no INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed','interrupted')),
  input_snapshot_json TEXT NOT NULL,
  result_artifact_id TEXT REFERENCES artifact_versions(id),
  usage_json TEXT NOT NULL,
  error_json TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  FOREIGN KEY (project_id, stage_no) REFERENCES stages(project_id, stage_no)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_job_per_project
  ON jobs(project_id) WHERE status IN ('queued','running');

CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  request_key TEXT NOT NULL UNIQUE,
  request_fingerprint TEXT NOT NULL,
  project_id TEXT NOT NULL,
  stage_no INTEGER NOT NULL,
  artifact_id TEXT NOT NULL REFERENCES artifact_versions(id),
  action TEXT NOT NULL CHECK (action IN ('approve','edit','regenerate','back')),
  comment TEXT NOT NULL,
  result_artifact_id TEXT REFERENCES artifact_versions(id),
  job_id TEXT REFERENCES jobs(id),
  navigate_to_stage INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY (project_id, stage_no) REFERENCES stages(project_id, stage_no)
);

CREATE TABLE IF NOT EXISTS experiment_runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  client_upload_id TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (project_id, client_upload_id)
);

-- Same-project/same-stage checks for artifact pointers, state transitions,
-- JSON/schema validation and immutability are enforced in WorkflowService.
-- All writes are short transactions; no network request occurs in a write transaction.
