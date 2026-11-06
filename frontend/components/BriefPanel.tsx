"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ArtifactView, DecisionRecord } from "@/lib/types";
import { STAGE_NAMES } from "@/lib/types";
import { ErrorBox, Markdown, Modal, fmtTime } from "./common";

interface HistoryItem { artifact: ArtifactView; approvedAt: string }

/** Right panel: approved Brief, input versions of the viewed result, approved Brief history (read-only). */
export default function BriefPanel({ projectId, brief, viewed, decisions }: {
  projectId: string;
  brief: ArtifactView | null;
  viewed: ArtifactView | null;
  decisions: DecisionRecord[];
}) {
  const [inputs, setInputs] = useState<Record<string, ArtifactView>>({});
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [open, setOpen] = useState<ArtifactView | null>(null);
  const [error, setError] = useState<unknown>(null);

  // input versions of the result being viewed
  useEffect(() => {
    if (!viewed) { setInputs({}); return; }
    const ids = Object.values(viewed.input_snapshot.upstream_artifact_ids);
    Promise.all(ids.map((id) => api.artifact(projectId, id)))
      .then((arts) => setInputs(Object.fromEntries(arts.map((a) => [a.id, a]))))
      .catch(setError);
  }, [projectId, viewed]);

  // approved Brief history = S1 approve decisions (newest version first)
  const approveKey = decisions.filter((d) => d.stage_no === 1 && d.action === "approve").map((d) => d.id).join(",");
  useEffect(() => {
    const approvals = decisions.filter((d) => d.stage_no === 1 && d.action === "approve");
    Promise.all(approvals.map(async (d) => ({ artifact: await api.artifact(projectId, d.artifact_id), approvedAt: d.created_at })))
      .then((items) => setHistory(items.sort((a, b) => b.artifact.version - a.artifact.version)))
      .catch(setError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, approveKey]);

  const b = brief?.payload.stage_no === 1 ? brief.payload.content.brief : null;

  return (
    <aside className="right">
      <div className="panel">
        <h2>승인된 Brief</h2>
        {!b && <p className="muted small">아직 승인된 Brief가 없습니다. S1을 승인하면 표시됩니다.</p>}
        {b && brief && (
          <div className="small stack">
            <div className="muted">S1 v{brief.version} · {fmtTime(brief.created_at)}</div>
            <div><strong>연구 문제</strong><div>{b.research_problem}</div></div>
            <div><strong>가설</strong>
              <ul style={{ margin: "2px 0", paddingLeft: 18 }}>
                {b.hypotheses.map((h) => <li key={h.id}><strong>{h.id}</strong> {h.statement}</li>)}
              </ul>
            </div>
            <div><strong>제약</strong><div>{b.constraints}</div></div>
          </div>
        )}
      </div>

      <div className="panel">
        <h2>입력 버전</h2>
        {!viewed && <p className="muted small">보고 있는 결과가 없습니다.</p>}
        {viewed && (
          <div className="small stack">
            <div className="muted">S{viewed.stage_no} v{viewed.version}이(가) 읽은 승인본</div>
            {Object.keys(viewed.input_snapshot.upstream_artifact_ids).length === 0 && <div>상위 입력 없음 (아이디어만 사용)</div>}
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {Object.entries(viewed.input_snapshot.upstream_artifact_ids).map(([n, id]) => (
                <li key={n}>
                  <button className="btn link" onClick={() => inputs[id] && setOpen(inputs[id])}>
                    S{n} {STAGE_NAMES[Number(n)]} v{inputs[id]?.version ?? "…"}
                  </button>
                </li>
              ))}
            </ul>
            {viewed.input_snapshot.run_id && <div>선택 Run: <code>{viewed.input_snapshot.run_id.slice(0, 8)}</code></div>}
            {viewed.input_snapshot.user_comments && <div>사용자 코멘트: “{viewed.input_snapshot.user_comments}”</div>}
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Brief 승인 이력</h2>
        <ErrorBox error={error} />
        {history.length === 0 && <p className="muted small">승인 이력이 없습니다.</p>}
        <ul style={{ margin: 0, paddingLeft: 18 }} className="small">
          {history.map((h) => (
            <li key={h.artifact.id + h.approvedAt}>
              <button className="btn link" onClick={() => setOpen(h.artifact)}>S1 v{h.artifact.version}</button>
              {" "}· 승인 {fmtTime(h.approvedAt)} · {h.artifact.created_by}
              {brief?.id === h.artifact.id && <span className="badge approved" style={{ marginLeft: 4 }}>현재</span>}
            </li>
          ))}
        </ul>
        <p className="small muted" style={{ marginBottom: 0 }}>과거 승인본은 읽기 전용으로 열립니다. 열람해도 상태·승인 기록은 바뀌지 않습니다.</p>
      </div>

      {open && (
        <Modal title={`S${open.stage_no} ${STAGE_NAMES[open.stage_no]} v${open.version}`} onClose={() => setOpen(null)}>
          <div className="small muted">{open.created_by} · {fmtTime(open.created_at)}</div>
          <Markdown text={open.rendered_markdown} />
        </Modal>
      )}
    </aside>
  );
}
