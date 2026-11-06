"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { ArtifactView, ExperimentRun, JobView, Mode, Payload, StageDetail } from "@/lib/types";
import { STAGE_NAMES } from "@/lib/types";
import ArtifactEditor from "./ArtifactEditor";
import CodeFiles from "./CodeFiles";
import EvidenceViewer from "./EvidenceViewer";
import RunUpload from "./RunUpload";
import { DEMO_NOTICE, ErrorBox, Markdown, StatusBadge, fmtTime } from "./common";

const CREATED_BY: Record<string, string> = { ai: "AI 생성", user: "사용자 수정", fixture: "사전 작성(demo)" };

export default function StageReview({ projectId, mode, detail, runs, activeJob, lastJob, onChanged, onNavigate, onJobStarted, onRunsChanged }: {
  projectId: string;
  mode: Mode;
  detail: StageDetail;
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

  return (
    <section className="stack">
      <div className="panel">
        <div className="row">
          <h2 style={{ margin: 0, flex: 1 }}>S{n} {STAGE_NAMES[n]}</h2>
          <StatusBadge status={stage.status} />
        </div>
        {mode === "demo" && <div className="notice warn small" style={{ marginTop: 8 }}>{DEMO_NOTICE} — 결과 본문은 미리 작성한 고정 시나리오입니다.</div>}
        {isStale && (
          <div className="notice stale" style={{ marginTop: 8 }}>
            상위 단계가 새로 승인되어 이 결과는 <strong>오래됨</strong> 상태입니다. 읽기 전용이며 수정·승인할 수 없습니다. 아래에서 재생성하세요.
          </div>
        )}
        {stage.disabled_reason && !isStale && <div className="notice info small" style={{ marginTop: 8 }}>{stage.disabled_reason}</div>}
        {myJob && (
          <div className="notice info" style={{ marginTop: 8 }}>
            {myJob.status === "queued" ? "대기 중" : "생성 중"}… 시작 {fmtTime(myJob.started_at)} (1초마다 상태 확인. 창을 닫아도 작업은 계속됩니다)
          </div>
        )}
        {failedJob && !myJob && (
          <div style={{ marginTop: 8 }}>
            <ErrorBox error={new ApiError(0, failedJob.error ?? { code: failedJob.status, message: "작업이 실패했습니다.", fields: [], retryable: true })} />
            <div className="small muted">작업 {failedJob.status === "interrupted" ? "중단" : "실패"} · 기존 결과와 승인본은 그대로입니다. 다시 실행할 수 있습니다.</div>
          </div>
        )}
        <div style={{ marginTop: 8 }}><ErrorBox error={error} onClose={() => setError(null)} /></div>
      </div>

      {n === 5 && (
        <RunUpload projectId={projectId} runs={runs} selected={runId} onSelect={setRunId} disabled={busy || working}
          onUploaded={(r) => { setRunId(r.id); onRunsChanged(r); }} />
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>{current ? "재생성 (코멘트 반영)" : "실행"}</h3>
        <textarea rows={2} maxLength={4000} value={comment} onChange={(e) => setComment(e.target.value)} disabled={busy || working}
          placeholder={current ? "무엇을 바꿔 다시 생성할지 적어 주세요 (재생성에는 필수)" : "추가 요청 사항 (선택)"} />
        <div className="row" style={{ marginTop: 6 }}>
          <button className="btn primary" onClick={generate} disabled={runDisabled}>{current ? "코멘트로 재생성" : `S${n} 실행`}</button>
          {n === 5 && !runId && <span className="small muted">먼저 실험 결과를 업로드하고 Run을 선택하세요.</span>}
          {!stage.can_run && !busy && <span className="small muted">이전 단계를 모두 승인해야 실행할 수 있습니다.</span>}
        </div>
      </div>

      {current && (
        <div className="panel">
          <div className="row">
            <h3 style={{ margin: 0, flex: 1 }}>
              {showApproved ? "승인본" : "현재 결과"} · v{viewed?.version} · {CREATED_BY[viewed?.created_by ?? "ai"]}
              {viewed?.model ? ` (${viewed.model})` : ""} · {fmtTime(viewed?.created_at)}
            </h3>
            {isNewDraft && (
              <button className="btn" onClick={() => setShowApproved((v) => !v)}>
                {showApproved ? "현재 초안 보기" : `승인본 v${approved?.version} 보기`}
              </button>
            )}
          </div>
          {stage.approved_artifact_id === viewed?.id && !isStale && <div className="notice ok small" style={{ marginTop: 6 }}>이 버전이 현재 승인본입니다.</div>}
          {stage.approved_artifact_id === viewed?.id && isStale && <div className="notice stale small" style={{ marginTop: 6 }}>마지막 승인본이지만 상위 단계 변경으로 오래됨 상태입니다. 다음 단계의 입력으로 쓸 수 없습니다.</div>}
          {isNewDraft && !showApproved && <div className="notice warn small" style={{ marginTop: 6 }}>승인되지 않은 새 초안입니다. 다음 단계에는 승인본만 쓰입니다.</div>}

          {!editing && viewed && (
            <>
              <div className="row" style={{ marginTop: 10 }}>
                <button className="btn ok" onClick={approve} disabled={!stage.can_approve || working || showApproved}>승인</button>
                <button className="btn" onClick={() => setEditing(true)} disabled={busy || working || isStale || showApproved || !["needs_review", "approved"].includes(stage.status)}>직접 수정</button>
                {n > 1 && <button className="btn" onClick={back} disabled={busy || working}>← 이전 단계로</button>}
                <span className="spacer" style={{ flex: 1 }} />
                {n === 2 && <button className="btn" onClick={() => download("references.bib")} disabled={working}>BibTeX</button>}
                {n === 4 && <button className="btn" onClick={() => download("code.zip")} disabled={working}>코드 zip 다운로드</button>}
                {n === 6 && <>
                  <button className="btn" onClick={() => download("paper.md")} disabled={working}>논문 Markdown</button>
                  <button className="btn" onClick={() => download("references.bib")} disabled={working}>BibTeX</button>
                </>}
              </div>
              {!stage.can_approve && stage.status === "needs_review" && stage.current_artifact_id === stage.approved_artifact_id && (
                <div className="small muted" style={{ marginTop: 4 }}>기존 승인본과 다른 새 초안이 없어 승인할 수 없습니다.</div>
              )}

              {n === 2 && <ReferenceCards artifact={viewed} />}
              {n === 4 && viewed.payload.stage_no === 4 && (
                <div style={{ marginTop: 12 }}>
                  <div className="notice warn small">서버 미실행: 이 코드는 서비스가 실행하지 않았습니다. 다운로드해 별도 환경에서 실행하세요.</div>
                  <div style={{ marginTop: 8 }}><CodeFiles files={viewed.payload.content.files} /></div>
                </div>
              )}
              <div style={{ marginTop: 12 }}><Markdown text={viewed.rendered_markdown} /></div>
              <RationaleList artifact={viewed} onOpen={setEvidenceRef} />
              {mode === "demo" && <p className="small muted">데모 생성 표시: 이 본문은 사전 작성본입니다. 실험 수치는 업로드한 실제 측정 파일에서 옵니다.</p>}
            </>
          )}
          {editing && current && (
            <div style={{ marginTop: 10 }}>
              <ArtifactEditor initial={current.payload} saving={working} onSave={save} onCancel={() => setEditing(false)} />
            </div>
          )}
        </div>
      )}

      {!current && !myJob && stage.status !== "running" && (
        <div className="panel muted">아직 결과가 없습니다. {stage.can_run ? "위에서 실행하세요." : ""}</div>
      )}

      {evidenceRef && viewed && (
        <EvidenceViewer projectId={projectId} evidenceRef={evidenceRef} evidence={viewed.evidence} runs={runs} onClose={() => setEvidenceRef(null)} />
      )}
    </section>
  );
}

function ReferenceCards({ artifact }: { artifact: ArtifactView }) {
  const refs = Object.values(artifact.evidence.references);
  return (
    <div style={{ marginTop: 12 }}>
      <div className="small muted">확인된 논문 {refs.length}편 · 초록 기반 정리입니다 (논문 전문을 검토하지 않음).</div>
      {refs.map((r) => (
        <div key={r.id} className="rationale">
          <div><a href={r.source_url} target="_blank" rel="noreferrer noopener"><strong>{r.title}</strong></a></div>
          <div className="small">{r.authors.join(", ")} · {r.year} · arXiv:{r.arxiv_id}</div>
          <div className="small muted">확인: {r.verification_source} · {r.verified_at}</div>
          {r.abstract_summary && <div className="small">{r.abstract_summary}</div>}
        </div>
      ))}
    </div>
  );
}

function RationaleList({ artifact, onOpen }: { artifact: ArtifactView; onOpen: (ref: string) => void }) {
  return (
    <div style={{ marginTop: 14 }}>
      <h3>판단 이유와 근거</h3>
      {artifact.payload.rationale.map((r, i) => (
        <div key={i} className="rationale">
          <div className="small muted">{r.decision_key}</div>
          <div>{r.reason}</div>
          {r.evidence_refs.length === 0
            ? <div className="small" style={{ color: "var(--warn)" }}>근거 없음: 사용자 확인 필요</div>
            : <div className="chips">{r.evidence_refs.map((ref) => (
              <button key={ref} className="chip" onClick={() => onOpen(ref)} title="원본 근거 열기">{ref}</button>
            ))}</div>}
          {r.alternatives.length > 0 && <div className="small muted">대안: {r.alternatives.join(" / ")}</div>}
        </div>
      ))}
      {artifact.evidence.warnings.length > 0 && (
        <div className="small muted">이 결과의 경고 {artifact.evidence.warnings.length}건은 위 본문의 ‘경고’ 절에 표시됩니다 (미검증 후보 제외·실행 경고 포함).</div>
      )}
    </div>
  );
}
