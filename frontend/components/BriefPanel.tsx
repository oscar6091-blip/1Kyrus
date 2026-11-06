"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ArtifactView, DecisionRecord } from "@/lib/types";
import { STAGE_NAMES } from "@/lib/types";
import { ErrorBox, Markdown, Modal, fmtTime } from "./common";

interface HistoryItem { artifact: ArtifactView; approvedAt: string }

const CREATED_BY: Record<string, string> = { ai: "AI", user: "사용자 수정", fixture: "사전 작성" };

/**
 * Research Brief panel (UI/UX plan UI-08): opens from the right-edge tab.
 * "현재 Brief" shows the approved Brief and the input versions of the viewed result;
 * "변경 이력" lists approved Brief versions (read-only).
 */
export default function BriefPanel({ projectId, brief, viewed, decisions, onClose }: {
  projectId: string;
  brief: ArtifactView | null;
  viewed: ArtifactView | null;
  decisions: DecisionRecord[];
  onClose: () => void;
}) {
  const [inputs, setInputs] = useState<Record<string, ArtifactView>>({});
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [open, setOpen] = useState<ArtifactView | null>(null);
  const [tab, setTab] = useState<"current" | "history">("current");
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
    <aside className="right" aria-label="Research Brief">
      <div className="drawer-head">
        <b>Research Brief</b>
        {brief && <span className="badge approved" style={{ padding: "4px 12px", fontSize: 12, fontWeight: 500 }}>v{brief.version} 승인</span>}
        <button className="btn link small" style={{ marginLeft: "auto", color: "var(--muted)" }} onClick={onClose}>접기 »</button>
      </div>
      <div className="seg" role="tablist">
        <button role="tab" aria-selected={tab === "current"} className={tab === "current" ? "on" : ""} onClick={() => setTab("current")}>현재 Brief</button>
        <button role="tab" aria-selected={tab === "history"} className={tab === "history" ? "on" : ""} onClick={() => setTab("history")}>변경 이력</button>
      </div>

      <div className="drawer-body">
        <ErrorBox error={error} />
        {tab === "current" && (
          <>
            {!b && <p className="muted small" style={{ margin: 0 }}>아직 승인된 Brief가 없습니다. S1을 승인하면 표시됩니다.</p>}
            {b && brief && (
              <>
                <Field label="연구 문제" source="S1">{b.research_problem}</Field>
                <Field label="가설" source="S1">
                  {b.hypotheses.map((h) => <div key={h.id}><strong>{h.id}</strong> {h.statement}</div>)}
                </Field>
                <Field label="예상 기여" source="S1">{b.expected_contribution}</Field>
                <Field label="평가 계획 · 제약 조건" source="S1">{b.evaluation_plan}<br />{b.constraints}</Field>
                <div className="small muted">S1 v{brief.version} 승인본 · {fmtTime(brief.created_at)} · Brief는 S1을 승인할 때만 바뀝니다.</div>
              </>
            )}

            <div className="subhead">입력 버전</div>
            {!viewed && <p className="muted small" style={{ margin: 0 }}>보고 있는 결과가 없습니다.</p>}
            {viewed && (
              <>
                <div className="small muted">S{viewed.stage_no} v{viewed.version}이(가) 읽은 승인본</div>
                {Object.keys(viewed.input_snapshot.upstream_artifact_ids).length === 0 && <div className="inrow">상위 입력 없음 (아이디어만 사용)</div>}
                {Object.entries(viewed.input_snapshot.upstream_artifact_ids).map(([n, id]) => (
                  <div className="inrow" key={n}>
                    <span className="sq" />
                    <button className="btn link" style={{ flex: 1, justifyContent: "flex-start" }} onClick={() => inputs[id] && setOpen(inputs[id])}>
                      S{n} {STAGE_NAMES[Number(n)]} v{inputs[id]?.version ?? "…"}
                    </button>
                    <span className="right">승인본</span>
                  </div>
                ))}
                {viewed.input_snapshot.run_id && <div className="small">선택 Run <code>{viewed.input_snapshot.run_id.slice(0, 8)}</code></div>}
                {viewed.input_snapshot.user_comments && <div className="small">사용자 코멘트: “{viewed.input_snapshot.user_comments}”</div>}
              </>
            )}
          </>
        )}

        {tab === "history" && (
          <>
            <div className="subhead" style={{ borderTop: "none", paddingTop: 0 }}>Brief 승인 이력</div>
            {history.length === 0 && <p className="muted small" style={{ margin: 0 }}>승인 이력이 없습니다.</p>}
            {history.map((h) => (
              <div className="hist" key={h.artifact.id + h.approvedAt}>
                <button className="btn link mono" onClick={() => setOpen(h.artifact)}>S1 v{h.artifact.version}</button>
                <span>승인 {fmtTime(h.approvedAt)} · {CREATED_BY[h.artifact.created_by] ?? h.artifact.created_by}</span>
                {brief?.id === h.artifact.id && <span className="badge approved" style={{ padding: "2px 10px", fontSize: 11 }}>현재</span>}
              </div>
            ))}
            <div className="notice warn small">과거 승인본은 읽기 전용으로 열립니다. 열람해도 상태·승인 기록은 바뀌지 않습니다.</div>
          </>
        )}
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

function Field({ label, source, children }: { label: string; source: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="field-label"><span>{label}</span><span>{source}</span></div>
      <div className="field-val">{children}</div>
    </div>
  );
}
