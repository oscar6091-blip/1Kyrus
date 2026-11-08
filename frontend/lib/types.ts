// Mirrors handoff/contracts/domain.schema.json and artifacts.schema.json.

export type Mode = "demo" | "live";
export type StageStatus = "pending" | "running" | "needs_review" | "approved" | "stale";
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "interrupted";

export interface ApiErrorBody {
  code: string;
  message: string;
  fields: { path: string; message: string }[];
  retryable: boolean;
}

export interface Health {
  status: "ok";
  default_mode: Mode;
  live_configured: boolean;
}

export interface ProjectSummary {
  id: string;
  name: string;
  idea: string;
  mode: Mode;
  current_brief_artifact_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface StageView {
  stage_no: number;
  status: StageStatus;
  current_artifact_id: string | null;
  approved_artifact_id: string | null;
  can_run: boolean;
  can_approve: boolean;
  disabled_reason: string | null;
  active_job_id: string | null;
}

export interface Usage {
  input_tokens: number | null;
  output_tokens: number | null;
  calls: number;
  estimated_cost_usd: number | null;
}

export interface JobView {
  id: string;
  project_id: string;
  stage_no: number;
  status: JobStatus;
  result_artifact_id: string | null;
  error: ApiErrorBody | null;
  usage: Usage;
  started_at: string | null;
  finished_at: string | null;
}

export interface Rationale {
  decision_key: string;
  reason: string;
  evidence_refs: string[];
  alternatives: string[];
}

export interface Hypothesis {
  id: string;
  statement: string;
}

export interface Brief {
  research_problem: string;
  hypotheses: Hypothesis[];
  expected_contribution: string;
  evaluation_plan: string;
  constraints: string;
  results_conclusion: null;
}

export interface Experiment {
  id: string;
  label: string;
  hypothesis_ids: string[];
  metric_names: string[];
}

export interface CodeFile {
  path: string;
  content: string;
  language: "python" | "text" | "markdown" | "json" | "yaml";
}

export interface Verdict {
  hypothesis_id: string;
  verdict: "supported" | "partly_supported" | "not_supported" | "inconclusive";
  reason: string;
}

export interface Section {
  key: "abstract" | "introduction" | "related_work" | "methods" | "experiments" | "conclusion";
  body_md: string;
}

export type Payload =
  | { stage_no: 1; content: { brief: Brief; clarification_questions: string[] }; rationale: Rationale[] }
  | { stage_no: 2; content: { body_md: string }; rationale: Rationale[] }
  | { stage_no: 3; content: { body_md: string; experiments: Experiment[] }; rationale: Rationale[] }
  | { stage_no: 4; content: { body_md: string; files: CodeFile[] }; rationale: Rationale[] }
  | { stage_no: 5; content: { body_md: string; hypothesis_verdicts: Verdict[] }; rationale: Rationale[] }
  | { stage_no: 6; content: { sections: Section[] }; rationale: Rationale[] };

export interface ReferenceSnapshot {
  id: string;
  arxiv_id: string;
  title: string;
  authors: string[];
  year: number;
  source_url: string;
  abstract: string | null;
  abstract_summary: string | null;
  verified: true;
  verification_source: "arxiv_live" | "bundled_snapshot";
  verified_at: string;
}

export interface MetricBinding {
  run_id: string;
  metric_index: number;
  name: string;
  split: string;
  value: number;
  step: number | null;
  unit: string;
}

export interface Evidence {
  references: Record<string, ReferenceSnapshot>;
  metrics: Record<string, MetricBinding>;
  warnings: string[];
}

export interface ContextSnapshot {
  brief_artifact_id: string | null;
  upstream_artifact_ids: Record<string, string>;
  previous_artifact_id: string | null;
  run_id: string | null;
  user_comments: string;
  idea_snapshot: string;
}

export interface ArtifactView {
  id: string;
  project_id: string;
  stage_no: number;
  version: number;
  payload: Payload;
  input_snapshot: ContextSnapshot;
  evidence: Evidence;
  rendered_markdown: string;
  created_by: "ai" | "user" | "fixture";
  created_at: string;
  model: string | null;
}

export interface ProjectDetail {
  project: ProjectSummary;
  stages: StageView[];
  brief: ArtifactView | null;
  active_job: JobView | null;
}

export interface StageDetail {
  stage: StageView;
  current_artifact: ArtifactView | null;
  approved_artifact: ArtifactView | null;
}

export interface DecisionRecord {
  id: string;
  request_id: string;
  project_id: string;
  stage_no: number;
  artifact_id: string;
  action: "approve" | "edit" | "regenerate" | "back";
  comment: string;
  created_at: string;
}

export interface DecisionResponse {
  decision: DecisionRecord;
  stage: StageView;
  job: JobView | null;
  artifact: ArtifactView | null;
  navigate_to_stage: number | null;
}

export interface UploadMetric {
  name: string;
  split: string;
  value: number;
  step?: number | null;
  unit: string;
}

export interface ExperimentRun {
  id: string;
  project_id: string;
  client_upload_id: string;
  payload: {
    schema_version: string;
    experiment_id: string;
    code_version: string;
    config: Record<string, unknown>;
    seed: number;
    environment?: Record<string, unknown> | null;
    metrics: UploadMetric[];
    started_at?: string | null;
    duration_sec?: number | null;
    data_origin: "measured" | "synthetic_demo";
  };
  created_at: string;
}

export const STAGE_NAMES: Record<number, string> = {
  1: "연구 Brief",
  2: "관련 연구",
  3: "방법론·실험 설계",
  4: "실행 코드",
  5: "결과 분석",
  6: "논문 초안",
};

export const STATUS_LABEL: Record<StageStatus, string> = {
  pending: "대기",
  running: "진행 중",
  needs_review: "검토 필요",
  approved: "승인",
  stale: "오래됨",
};
