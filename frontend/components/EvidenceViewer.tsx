"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ArtifactView, Evidence, ExperimentRun } from "@/lib/types";
import { STAGE_NAMES } from "@/lib/types";
import { ErrorBox, Markdown, Modal, fmtTime } from "./common";

/** Opens ref:/metric:/artifact: evidence from the artifact's own immutable evidence. Read-only. */
export default function EvidenceViewer({ projectId, evidenceRef, evidence, runs, onClose }: {
  projectId: string;
  evidenceRef: string;
  evidence: Evidence;
  runs: ExperimentRun[];
  onClose: () => void;
}) {
  const kind = evidenceRef.split(":")[0];
  const ident = evidenceRef.slice(evidenceRef.indexOf(":") + 1);
  const [artifact, setArtifact] = useState<ArtifactView | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (kind === "artifact") api.artifact(projectId, ident).then(setArtifact).catch(setError);
  }, [kind, ident, projectId]);

  if (kind === "ref") {
    const r = evidence.references[ident];
    return (
      <Modal title={`논문 근거 ${ident}`} onClose={onClose}>
        {!r ? <p>이 산출물의 근거에 없는 논문 ID입니다.</p> : (
          <div className="stack">
            <div><strong>{r.title}</strong></div>
            <div className="small">{r.authors.join(", ")} · {r.year} (arXiv 첫 제출 연도) · arXiv:{r.arxiv_id}</div>
            <div><a href={r.source_url} target="_blank" rel="noreferrer noopener">{r.source_url}</a></div>
            <div className="small muted">확인 출처: {r.verification_source} · 확인일 {r.verified_at}</div>
            {r.abstract && <div><h3>초록</h3><p>{r.abstract}</p></div>}
            {r.abstract_summary && <div><h3>초록 요약</h3><p>{r.abstract_summary}</p></div>}
          </div>
        )}
      </Modal>
    );
  }

  if (kind === "metric") {
    const b = evidence.metrics[ident];
    const run = b ? runs.find((x) => x.id === b.run_id) : undefined;
    return (
      <Modal title={`지표 근거 ${ident}`} onClose={onClose}>
        {!b ? <p>이 산출물의 근거에 없는 지표 ID입니다.</p> : (
          <div className="stack">
            <table className="simple">
              <tbody>
                <tr><th>지표</th><td>{b.name}</td></tr>
                <tr><th>split / step</th><td>{b.split} / {b.step ?? "-"}</td></tr>
                <tr><th>값 (이 산출물에 복사된 원본)</th><td><code>{String(b.value)}</code> {b.unit}</td></tr>
                <tr><th>Run</th><td><code>{b.run_id}</code> · metrics[{b.metric_index}]</td></tr>
              </tbody>
            </table>
            {run ? (
              <>
                <h3>업로드 원본 행 (metrics[{b.metric_index}])</h3>
                <pre className="code">{JSON.stringify(run.payload.metrics[b.metric_index], null, 2)}</pre>
                <div className="small muted">
                  실험 {run.payload.experiment_id} · seed {run.payload.seed} · data_origin {run.payload.data_origin} · 업로드 {fmtTime(run.created_at)}
                </div>
              </>
            ) : <p className="muted">원본 Run을 목록에서 찾을 수 없습니다.</p>}
          </div>
        )}
      </Modal>
    );
  }

  return (
    <Modal title={`산출물 근거 ${artifact ? `S${artifact.stage_no} v${artifact.version}` : ""}`} onClose={onClose}>
      <ErrorBox error={error} />
      {!artifact && !error && <p className="muted">불러오는 중…</p>}
      {artifact && (
        <div className="stack">
          <div className="small muted">
            {STAGE_NAMES[artifact.stage_no]} · 버전 {artifact.version} · {artifact.created_by} · {fmtTime(artifact.created_at)}
          </div>
          <Markdown text={artifact.rendered_markdown} />
        </div>
      )}
    </Modal>
  );
}
