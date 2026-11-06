"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { ArtifactView, ExperimentRun, JobView, Mode, Payload, StageDetail, StageView, Verdict } from "@/lib/types";
import { STAGE_NAMES } from "@/lib/types";
import ArtifactEditor from "./ArtifactEditor";
import CodeFiles from "./CodeFiles";
import EvidenceViewer from "./EvidenceViewer";
import RunUpload from "./RunUpload";
import { ErrorBox, Markdown, StatusBadge, fmtTime } from "./common";

const CREATED_BY: Record<string, string> = { ai: "AI 생성", user: "사용자 수정", fixture: "사전 작성(demo)" };

/**
 * Stage review screen after the UI/UX plan v0.2 (docs/uiux, "02 Common Layout" and UI-03~UI-07 mockups):
 * stage header with status and referenced versions, result card on the left, rationale card on the right,
 * floating checkpoint bar at the bottom. Which actions exist and when they are allowed is unchanged.
 */
export default function StageReview({ projectId, projectName, mode, detail, stages, brief, runs, activeJob, lastJob, onChanged, onNavigate, onJobStarted, onRunsChanged }: {
  projectId: string;
  projectName: string;
  mode: Mode;
  detail: StageDetail;
  stages: StageView[];
  brief: ArtifactView | null;
  runs: ExperimentRun[];
  activeJob: JobView | null;
  lastJob: JobView | null;
  onChanged: () => void;
  onNavigate: (n: number) => void;
  onJobStarted: (job: JobView) => void;
  onRunsChanged: (run?: ExperimentRun) => void;
}) {
  const { stage, current_artifact: current, approved_artifact: approved } = detail;
  const n = stage.stage_no;
  const busy = activeJob !== null;
  const [editing, setEditing] = useState(false);
  const [comment, setComment] = useState("");
  const [showApproved, setShowApproved] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [evidenceRef, setEvidenceRef] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

  useEffect(() => {
    setEditing(false); setShowApproved(false); setError(null); setComment("");
  }, [n, current?.id]);

  useEffect(() => {
    if (n !== 5) return;
    const fromSnapshot = current?.input_snapshot.run_id ?? null;
    setRunId((prev) => prev && runs.some((r) => r.id === prev) ? prev : fromSnapshot ?? runs[runs.length - 1]?.id ?? null);
  }, [n, runs, current?.input_snapshot.run_id]);

  const viewed: ArtifactView | null = showApproved && approved ? approved : current;
  const isStale = stage.status === "stale";
  const isNewDraft = current && approved && current.id !== approved.id;
  const myJob = activeJob && activeJob.stage_no === n ? activeJob : null;
  const failedJob = lastJob && lastJob.stage_no === n && lastJob.status !== "succeeded" ? lastJob : null;

  // Versions of the inputs this result read, and of the upstream approvals now in force.
  const upstream = viewed?.input_snapshot.upstream_artifact_ids ?? {};
  const versions = useArtifactVersions(projectId, [
    ...Object.values(upstream),
    ...stages.filter((s) => s.stage_no < n && s.approved_artifact_id).map((s) => s.approved_artifact_id as string),
  ]);
  const staleCauses = Object.entries(upstream)
    .map(([k, id]) => ({ k: Number(k), oldId: id, newId: stages.find((s) => s.stage_no === Number(k))?.approved_artifact_id ?? null }))
    .filter((c) => c.newId && c.newId !== c.oldId);

  async function act(fn: () => Promise<unknown>) {
    setWorking(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      setWorking(false);
      onChanged();
    }
  }

  const generate = () => act(async () => {
    const rid = n === 5 ? runId : null;
    if (current) {
      const r = await api.decide(projectId, n, "regenerate", current.id, comment.trim(), rid);
      if (r.job) onJobStarted(r.job);
    } else {
      onJobStarted(await api.run(projectId, n, comment.trim(), rid));
    }
    setComment("");
  });

  const approve = () => current && act(() => api.decide(projectId, n, "approve", current.id, ""));
  const back = () => current && act(async () => {
    const r = await api.decide(projectId, n, "back", current.id, "");
    if (r.navigate_to_stage) onNavigate(r.navigate_to_stage);
  });
  const save = (payload: Payload, memo: string) => current && act(async () => {
    await api.edit(projectId, n, current.id, payload, memo);
    setEditing(false);
  });
  const download = (f: "code.zip" | "paper.md" | "references.bib") => act(() => api.download(projectId, f));

  const regenerateNeedsComment = !!current;
  const runDisabled = busy || working || !stage.can_run || (regenerateNeedsComment && !comment.trim()) || (n === 5 && !runId);
  const editDisabled = busy || working || isStale || showApproved || !["needs_review", "approved"].includes(stage.status);

  const hints: string[] = [];
  if (n === 5 && !runId) hints.push("먼저 실험 결과를 업로드하고 Run을 선택하세요.");
  if (!stage.can_run && !busy) hints.push("이전 단계를 모두 승인해야 실행할 수 있습니다.");
  if (current && !stage.can_approve && stage.status === "needs_review" && stage.current_artifact_id === stage.approved_artifact_id) {
    hints.push("기존 승인본과 다른 새 초안이 없어 승인할 수 없습니다.");
  }
  if (isNewDraft && !showApproved) hints.push("승인하면 다음 단계의 입력이 됩니다.");

  const briefId = upstream["1"];

  return (
    <section className="review">
      {/* 1. Stage header */}
      <div className="page-head">
        <div style={{ minWidth: 0 }}>
          <div className="eyebrow">R2P Agent · {projectName}</div>
          <div className="title-row">
            <h2><span className="scode">S{n}</span> {STAGE_NAMES[n]}</h2>
            <StatusBadge status={stage.status} />
            {briefId && <span className={`badge white${staleCauses.some((c) => c.oldId === briefId) ? " stale" : ""}`}>Brief v{versions[briefId] ?? "…"} 참조</span>}
          </div>
          {viewed && (
            <div className="meta">
              <span>결과 v{viewed.version} · {CREATED_BY[viewed.created_by]}{viewed.model ? ` (${viewed.model})` : ""}</span>
              {Object.keys(upstream).length > 0 && <span>· 참조한 승인본</span>}
              {Object.entries(upstream).map(([k, id]) => (
                <span key={k} className={`refchip${staleCauses.some((c) => c.oldId === id) ? " old" : ""}`}>S{k} v{versions[id] ?? "…"}</span>
              ))}
            </div>
          )}
          {!viewed && brief && n > 1 && <div className="meta">현재 승인된 Brief v{brief.version}</div>}
        </div>
        {current && !editing && (
          <div className="row">
            {n === 2 && <button className="btn white" onClick={() => download("references.bib")} disabled={working}>BibTeX</button>}
            {n === 4 && <button className="btn dark" onClick={() => download("code.zip")} disabled={working}>코드 zip 다운로드</button>}
            {n === 6 && <>
              <button className="btn white" onClick={() => download("references.bib")} disabled={working}>BibTeX</button>
              <button className="btn dark" onClick={() => download("paper.md")} disabled={working}>논문 Markdown</button>
            </>}
          </div>
        )}
      </div>

      {/* state notices */}
      {(isStale || (stage.disabled_reason && !isStale) || myJob || (failedJob && !myJob) || !!error) && (
        <div className="stack">
          {isStale && (
            <div className="notice stale">
              {staleCauses.map((c) => (
                <div key={c.k}>
                  <strong>S{c.k} {STAGE_NAMES[c.k]}</strong> 승인본이 v{versions[c.oldId] ?? "…"} → v{versions[c.newId as string] ?? "…"}로 바뀌었습니다.
                </div>
              ))}
              {staleCauses.length > 0
                ? <>이 결과는 이전 입력으로 만들어져 <strong>오래됨</strong> 상태입니다. 읽기 전용이며 수정·승인할 수 없습니다. 아래에 코멘트를 적고 재생성을 요청하세요.</>
                : <>상위 단계가 새로 승인되어 이 결과는 <strong>오래됨</strong> 상태입니다. 읽기 전용이며 수정·승인할 수 없습니다. 아래에서 재생성하세요.</>}
            </div>
          )}
          {stage.disabled_reason && !isStale && <div className="notice info small">{stage.disabled_reason}</div>}
          {myJob && (
            <div className="notice alert">
              <strong>{myJob.status === "queued" ? "대기 중" : "생성 중"}…</strong> 시작 {fmtTime(myJob.started_at)} · 1초마다 상태를 확인합니다. 창을 닫아도 작업은 계속됩니다.
            </div>
          )}
          {failedJob && !myJob && (
            <div>
              <ErrorBox error={new ApiError(0, failedJob.error ?? { code: failedJob.status, message: "작업이 실패했습니다.", fields: [], retryable: true })} />
              <div className="small muted" style={{ marginTop: 6 }}>작업 {failedJob.status === "interrupted" ? "중단" : "실패"} · 기존 결과와 승인본은 그대로입니다. 다시 실행할 수 있습니다.</div>
            </div>
          )}
          <ErrorBox error={error} onClose={() => setError(null)} />
        </div>
      )}

      {/* 2. Result (left) · rationale (right) */}
      <div className={`review-grid${viewed && !editing ? "" : " single"}`}>
        <div className="col">
          {n === 5 && (
            <RunUpload projectId={projectId} runs={runs} selected={runId} onSelect={setRunId} disabled={busy || working}
              onUploaded={(r) => { setRunId(r.id); onRunsChanged(r); }} />
          )}

          {current && (
            <div className="panel">
              <div className="result-head">
                <h3>
                  {showApproved ? "승인본" : "현재 결과"} · v{viewed?.version} · {CREATED_BY[viewed?.created_by ?? "ai"]}
                  {viewed?.model ? ` (${viewed.model})` : ""} · {fmtTime(viewed?.created_at)}
                </h3>
                {isNewDraft && (
                  <button className="btn sm" onClick={() => setShowApproved((v) => !v)}>
                    {showApproved ? "현재 초안 보기" : `승인본 v${approved?.version} 보기`}
                  </button>
                )}
              </div>
              <div className="stack" style={{ marginTop: 12 }}>
                {stage.approved_artifact_id === viewed?.id && !isStale && <div className="notice ok small"><span className="dot approved" style={{ marginRight: 8, verticalAlign: -1 }} />이 버전이 현재 승인본입니다.</div>}
                {stage.approved_artifact_id === viewed?.id && isStale && <div className="notice stale small">마지막 승인본이지만 상위 단계 변경으로 오래됨 상태입니다. 다음 단계의 입력으로 쓸 수 없습니다.</div>}
                {isNewDraft && !showApproved && <div className="notice info small">승인되지 않은 새 초안입니다. 다음 단계에는 승인본만 쓰입니다.</div>}
              </div>

              {!editing && viewed && (
                <div className="stack" style={{ marginTop: 16 }}>
                  <WarningBox artifact={viewed} />
                  {n === 2 && <ReferenceCards artifact={viewed} />}
                  {n === 4 && viewed.payload.stage_no === 4 && (
                    <div className="stack">
                      <div className="notice warn small">서버 미실행: 이 코드는 서비스가 실행하지 않았습니다. 다운로드해 별도 환경에서 실행하세요.</div>
                      <CodeFiles files={viewed.payload.content.files} />
                    </div>
                  )}
                  {n === 5 && viewed.payload.stage_no === 5 && <VerdictCards verdicts={viewed.payload.content.hypothesis_verdicts} />}
                  <Markdown text={viewed.rendered_markdown} />
                  {mode === "demo" && <p className="small muted" style={{ margin: 0 }}>데모 생성 표시: 이 본문은 사전 작성본입니다. 실험 수치는 업로드한 실제 측정 파일에서 옵니다.</p>}
                </div>
              )}
              {editing && current && (
                <div style={{ marginTop: 14 }}>
                  <ArtifactEditor initial={current.payload} saving={working} onSave={save} onCancel={() => setEditing(false)} />
                </div>
              )}
            </div>
          )}

          {!current && !myJob && stage.status !== "running" && (
            <div className="panel muted">아직 결과가 없습니다. {stage.can_run ? "아래 결정 바에서 실행하세요." : ""}</div>
          )}
        </div>

        {viewed && !editing && <RationaleCard artifact={viewed} onOpen={setEvidenceRef} />}
      </div>

      {/* 3. Checkpoint decision bar */}
      {!editing && (
        <div className="stack" style={{ position: "sticky", bottom: 20, zIndex: 4 }}>
          {hints.length > 0 && <div className="decision-hint">{hints.map((h) => <span key={h}>{h}</span>)}</div>}
          <div className="decision-bar">
            <span className="dot needs_review" />
            <textarea rows={1} maxLength={4000} value={comment} onChange={(e) => setComment(e.target.value)} disabled={busy || working}
              aria-label="재생성 코멘트"
              placeholder={current ? "코멘트를 남기면 재생성 요청의 입력으로 사용됩니다" : "추가 요청 사항 (선택)"} />
            {current && n > 1 && <button className="btn" onClick={back} disabled={busy || working}>이전 단계로</button>}
            {current ? (
              <button className="btn" onClick={generate} disabled={runDisabled}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true"><path d="M14.55 21.67A10 10 0 0 0 22 12c0-5.52-4.44-10-10-10C5.33 2 2 7.56 2 7.56m0 0V2.56m0 5H6.44M2 12c0 5.52 4.48 10 10 10" /></svg>
                재생성 요청
              </button>
            ) : (
              <button className="btn primary" onClick={generate} disabled={runDisabled}>S{n} 실행</button>
            )}
            {current && <button className="btn" onClick={() => setEditing(true)} disabled={editDisabled}>직접 수정</button>}
            {current && (
              <button className="btn primary" onClick={approve} disabled={!stage.can_approve || working || showApproved}>
                승인
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 12.5l5 5L20 6.5" /></svg>
              </button>
            )}
          </div>
        </div>
      )}

      {evidenceRef && viewed && (
        <EvidenceViewer projectId={projectId} evidenceRef={evidenceRef} evidence={viewed.evidence} runs={runs} onClose={() => setEvidenceRef(null)} />
      )}
    </section>
  );
}

/** id → version for the given artifact ids, fetched once each (read-only). */
function useArtifactVersions(projectId: string, ids: string[]): Record<string, number> {
  const [versions, setVersions] = useState<Record<string, number>>({});
  const key = Array.from(new Set(ids)).sort().join(",");
  useEffect(() => {
    const missing = key ? key.split(",").filter((id) => !(id in versions)) : [];
    if (missing.length === 0) return;
    Promise.all(missing.map((id) => api.artifact(projectId, id)))
      .then((arts) => setVersions((v) => ({ ...v, ...Object.fromEntries(arts.map((a) => [a.id, a.version])) })))
      .catch(() => { /* version labels fall back to "…" */ });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, key]);
  return versions;
}

function WarningBox({ artifact }: { artifact: ArtifactView }) {
  const w = artifact.evidence.warnings;
  if (w.length === 0) return null;
  return (
    <div className="notice warn small">
      <strong>경고 {w.length}건</strong>{artifact.stage_no === 2 ? " · 확인되지 않은 후보는 목록과 BibTeX에서 제외했고 다른 논문으로 대체하지 않았습니다." : ""}
      <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>{w.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}

const VERDICT: Record<Verdict["verdict"], string> = {
  supported: "지지",
  partly_supported: "부분 지지",
  not_supported: "기각",
  inconclusive: "판단 보류",
};

function VerdictCards({ verdicts }: { verdicts: Verdict[] }) {
  if (verdicts.length === 0) return null;
  return (
    <div>
      <h3 style={{ marginTop: 0 }}>가설 판정</h3>
      <div className="verdicts">
        {verdicts.map((v) => (
          <div key={v.hypothesis_id} className="verdict">
            <div className="head">
              <b>{v.hypothesis_id}</b>
              <span className={`vchip ${v.verdict}`}>{VERDICT[v.verdict]}</span>
            </div>
            <div className="small" style={{ color: "rgba(0,0,0,.7)" }}>{v.reason}</div>
          </div>
        ))}
      </div>
      <div className="small muted" style={{ marginTop: 8 }}>결과를 감추거나 바꾸지 않고 그대로 기록합니다. 판정과 해석은 직접 수정할 수 있습니다.</div>
    </div>
  );
}

function ReferenceCards({ artifact }: { artifact: ArtifactView }) {
  const refs = Object.values(artifact.evidence.references);
  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <b style={{ fontSize: 17 }}>관련 연구 {refs.length}편</b>
        <span className="small muted">arXiv에서 확인한 논문만 표시 · 초록 기반 정리 (논문 전문을 검토하지 않음)</span>
      </div>
      {refs.map((r) => (
        <div key={r.id} className="refcard">
          <a href={r.source_url} target="_blank" rel="noreferrer noopener"><strong>{r.title}</strong></a>
          <div className="small">{r.authors.join(", ")} · {r.year} · <span className="mono">arXiv:{r.arxiv_id}</span></div>
          <div className="small muted">확인: {r.verification_source} · {r.verified_at}</div>
          {r.abstract_summary && <div className="small" style={{ color: "rgba(0,0,0,.7)" }}>{r.abstract_summary}</div>}
        </div>
      ))}
    </div>
  );
}

function RationaleCard({ artifact, onOpen }: { artifact: ArtifactView; onOpen: (ref: string) => void }) {
  const rs = artifact.payload.rationale;
  return (
    <div className="panel review-side">
      <b style={{ fontSize: 19 }}>결정 근거</b>
      {rs.length === 0 && <div className="small muted">기록된 판단 이유가 없습니다.</div>}
      {rs.map((r, i) => (
        <div key={i} className="stack" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {r.evidence_refs.length === 0 ? (
            <div className="rat-none">
              <b>{r.decision_key}</b> · {r.reason}
              <div style={{ marginTop: 6 }}>근거 없음 · 사용자 확인 필요</div>
            </div>
          ) : (
            <div className="rat">
              <span className="key">{r.decision_key}</span>
              <span className="why">{r.reason}</span>
              <span className="ev">근거 {r.evidence_refs.map((ref) => (
                <button key={ref} className="chip" onClick={() => onOpen(ref)} title="원본 근거 열기">{ref}</button>
              ))}</span>
            </div>
          )}
          {r.alternatives.length > 0 && (
            <div className="rat alt">
              <span className="key">대안</span>
              <span className="why">{r.alternatives.join(" / ")}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
