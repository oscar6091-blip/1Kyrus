// API client for http://127.0.0.1:8000/api. Never touches server secrets.
import type {
  ApiErrorBody, ArtifactView, DecisionRecord, DecisionResponse, ExperimentRun, Health, JobView, Payload,
  ProjectDetail, ProjectSummary, StageDetail,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody;
  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.body = body;
  }
}

/** One UUID per intended user action; reused when the same action is retried. */
export function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

async function parseError(res: Response): Promise<ApiError> {
  let body: ApiErrorBody;
  try {
    const data = await res.json();
    body = data.error ?? { code: "HTTP_" + res.status, message: res.statusText, fields: [], retryable: false };
  } catch {
    body = { code: "HTTP_" + res.status, message: `서버 응답을 읽을 수 없습니다 (${res.status})`, fields: [], retryable: false };
  }
  return new ApiError(res.status, body);
}

async function request<T>(path: string, init?: RequestInit, retryOnNetwork = false): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_BASE + path, { cache: "no-store", ...init });
  } catch (e) {
    if (retryOnNetwork) return request<T>(path, init, false); // same body => same request_id
    throw new ApiError(0, {
      code: "NETWORK", message: `API 서버(${API_BASE})에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.`,
      fields: [], retryable: true,
    });
  }
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/health"),
  listProjects: () => request<ProjectSummary[]>("/projects"),
  createProject: (name: string, idea: string) => request<ProjectSummary>("/projects", json({ name, idea })),
  project: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  stage: (id: string, n: number) => request<StageDetail>(`/projects/${id}/stages/${n}`),
  artifact: (id: string, artifactId: string) => request<ArtifactView>(`/projects/${id}/artifacts/${artifactId}`),
  decisions: (id: string) => request<DecisionRecord[]>(`/projects/${id}/decisions`),
  job: (jobId: string) => request<JobView>(`/jobs/${jobId}`),
  runs: (id: string) => request<ExperimentRun[]>(`/projects/${id}/runs`),

  run: (id: string, n: number, userComments: string, runId: string | null, requestId = newRequestId()) =>
    request<JobView>(`/projects/${id}/stages/${n}/run`,
      json({ request_id: requestId, user_comments: userComments, run_id: runId }), true),

  decide: (id: string, n: number, action: "approve" | "regenerate" | "back", artifactId: string, comment: string,
    runId: string | null = null, requestId = newRequestId()) =>
    request<DecisionResponse>(`/projects/${id}/stages/${n}/decisions`,
      json({ request_id: requestId, action, artifact_id: artifactId, comment, run_id: runId }), true),

  edit: (id: string, n: number, baseId: string, payload: Payload, comment: string, requestId = newRequestId()) =>
    request<DecisionResponse>(`/projects/${id}/stages/${n}/edits`,
      json({ request_id: requestId, base_artifact_id: baseId, payload, comment }), true),

  upload: async (id: string, file: File, clientUploadId = newRequestId()) => {
    const form = new FormData();
    form.append("file", file);
    form.append("client_upload_id", clientUploadId);
    return request<ExperimentRun>(`/projects/${id}/runs`, { method: "POST", body: form }, true);
  },

  /** Download an export; errors come back as ApiError instead of a JSON page. */
  download: async (id: string, file: "code.zip" | "paper.md" | "references.bib") => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/projects/${id}/exports/${file}`, { cache: "no-store" });
    } catch {
      throw new ApiError(0, { code: "NETWORK", message: "API 서버에 연결할 수 없습니다.", fields: [], retryable: true });
    }
    if (!res.ok) throw await parseError(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = file;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
