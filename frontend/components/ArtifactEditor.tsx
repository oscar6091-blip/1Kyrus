"use client";

import { useState } from "react";
import type { Payload } from "@/lib/types";
import CodeFiles from "./CodeFiles";

const SECTION_LABEL: Record<string, string> = {
  abstract: "Abstract", introduction: "Introduction", related_work: "Related Work",
  methods: "Methods", experiments: "Experiments", conclusion: "Conclusion",
};
const VERDICTS = [
  ["supported", "지지"], ["partly_supported", "부분 지지"], ["not_supported", "지지되지 않음"], ["inconclusive", "판단 불가"],
] as const;

const splitList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

/** Stage-specific forms. Rationale and evidence are not editable here (server copies evidence). */
export default function ArtifactEditor({ initial, saving, onSave, onCancel }: {
  initial: Payload;
  saving: boolean;
  onSave: (payload: Payload, comment: string) => void;
  onCancel: () => void;
}) {
  const [p, setP] = useState<Payload>(() => structuredClone(initial));
  const [comment, setComment] = useState("");

  // helper: shallow update of content
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const setContent = (patch: any) => setP((prev) => ({ ...prev, content: { ...prev.content, ...patch } }) as Payload);

  let form: React.ReactNode = null;
  if (p.stage_no === 1) {
    const b = p.content.brief;
    const setBrief = (patch: Partial<typeof b>) => setContent({ brief: { ...b, ...patch } });
    form = (
      <>
        <label className="field">연구 문제</label>
        <textarea rows={3} value={b.research_problem} onChange={(e) => setBrief({ research_problem: e.target.value })} />
        <label className="field">가설 (ID는 H1, H2 …)</label>
        {b.hypotheses.map((h, i) => (
          <div className="row" key={i} style={{ marginBottom: 6, alignItems: "flex-start" }}>
            <input type="text" style={{ width: 70 }} value={h.id}
              onChange={(e) => setBrief({ hypotheses: b.hypotheses.map((x, j) => (j === i ? { ...x, id: e.target.value } : x)) })} />
            <textarea rows={2} style={{ flex: 1 }} value={h.statement}
              onChange={(e) => setBrief({ hypotheses: b.hypotheses.map((x, j) => (j === i ? { ...x, statement: e.target.value } : x)) })} />
            <button type="button" className="btn" disabled={b.hypotheses.length <= 1}
              onClick={() => setBrief({ hypotheses: b.hypotheses.filter((_, j) => j !== i) })}>삭제</button>
          </div>
        ))}
        <button type="button" className="btn" disabled={b.hypotheses.length >= 5}
          onClick={() => setBrief({ hypotheses: [...b.hypotheses, { id: `H${b.hypotheses.length + 1}`, statement: "" }] })}>+ 가설</button>
        <label className="field">예상 기여</label>
        <textarea rows={2} value={b.expected_contribution} onChange={(e) => setBrief({ expected_contribution: e.target.value })} />
        <label className="field">평가 계획</label>
        <textarea rows={3} value={b.evaluation_plan} onChange={(e) => setBrief({ evaluation_plan: e.target.value })} />
        <label className="field">제약</label>
        <textarea rows={2} value={b.constraints} onChange={(e) => setBrief({ constraints: e.target.value })} />
        <label className="field">확인 질문 (최대 3개, 한 줄에 하나)</label>
        <textarea rows={3} value={p.content.clarification_questions.join("\n")}
          onChange={(e) => setContent({ clarification_questions: e.target.value.split("\n").filter((x) => x.trim()) })} />
      </>
    );
  } else if (p.stage_no === 2) {
    form = (
      <>
        <label className="field">관련 연구 정리 (Markdown, 인용은 {"{{cite:ID}}"} 유지)</label>
        <textarea className="mono" rows={14} value={p.content.body_md} onChange={(e) => setContent({ body_md: e.target.value })} />
      </>
    );
  } else if (p.stage_no === 3) {
    const exps = p.content.experiments;
    const setExp = (i: number, patch: object) => setContent({ experiments: exps.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
    form = (
      <>
        <label className="field">방법론·실험 계획 (Markdown, “## 방법론”·“## Ablation 계획” 절 포함)</label>
        <textarea className="mono" rows={14} value={p.content.body_md} onChange={(e) => setContent({ body_md: e.target.value })} />
        <label className="field">실험 목록</label>
        <table className="simple">
          <thead><tr><th>ID</th><th>설명</th><th>가설 ID (쉼표)</th><th>필수 지표 이름 (쉼표)</th><th /></tr></thead>
          <tbody>
            {exps.map((e, i) => (
              <tr key={i}>
                <td><input type="text" style={{ width: 60 }} value={e.id} onChange={(ev) => setExp(i, { id: ev.target.value })} /></td>
                <td><input type="text" value={e.label} onChange={(ev) => setExp(i, { label: ev.target.value })} /></td>
                <td><input type="text" defaultValue={e.hypothesis_ids.join(", ")} onBlur={(ev) => setExp(i, { hypothesis_ids: splitList(ev.target.value) })} /></td>
                <td><input type="text" defaultValue={e.metric_names.join(", ")} onBlur={(ev) => setExp(i, { metric_names: splitList(ev.target.value) })} /></td>
                <td><button type="button" className="btn" disabled={exps.length <= 1}
                  onClick={() => setContent({ experiments: exps.filter((_, j) => j !== i) })}>삭제</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" className="btn" style={{ marginTop: 6 }} disabled={exps.length >= 5}
          onClick={() => setContent({ experiments: [...exps, { id: `E${exps.length + 1}`, label: "", hypothesis_ids: [], metric_names: [] }] })}>+ 실험</button>
      </>
    );
  } else if (p.stage_no === 4) {
    form = (
      <>
        <label className="field">설명 (Markdown)</label>
        <textarea rows={4} value={p.content.body_md} onChange={(e) => setContent({ body_md: e.target.value })} />
        <label className="field">파일 (서버는 실행하지 않음, Python은 문법 검사만)</label>
        <CodeFiles files={p.content.files} onChange={(files) => setContent({ files })} />
      </>
    );
  } else if (p.stage_no === 5) {
    const vs = p.content.hypothesis_verdicts;
    form = (
      <>
        <label className="field">분석 (Markdown, 수치는 {"{{metric:ID}}"} 토큰 사용)</label>
        <textarea className="mono" rows={12} value={p.content.body_md} onChange={(e) => setContent({ body_md: e.target.value })} />
        <label className="field">가설 판정 (모든 가설을 한 번씩)</label>
        {vs.map((v, i) => (
          <div className="row" key={i} style={{ alignItems: "flex-start", marginBottom: 6 }}>
            <strong style={{ width: 40 }}>{v.hypothesis_id}</strong>
            <select style={{ width: 150 }} value={v.verdict}
              onChange={(e) => setContent({ hypothesis_verdicts: vs.map((x, j) => (j === i ? { ...x, verdict: e.target.value } : x)) })}>
              {VERDICTS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
            <textarea rows={2} style={{ flex: 1 }} value={v.reason}
              onChange={(e) => setContent({ hypothesis_verdicts: vs.map((x, j) => (j === i ? { ...x, reason: e.target.value } : x)) })} />
          </div>
        ))}
      </>
    );
  } else if (p.stage_no === 6) {
    const secs = p.content.sections;
    form = (
      <>
        <p className="small muted">영어 본문입니다. 인용은 {"{{cite:ID}}"}, 수치는 {"{{metric:ID}}"} 토큰을 유지해야 원본 근거와 연결됩니다.</p>
        {secs.map((s, i) => (
          <div key={s.key}>
            <label className="field">{SECTION_LABEL[s.key]}</label>
            <textarea className="mono" rows={5} value={s.body_md}
              onChange={(e) => setContent({ sections: secs.map((x, j) => (j === i ? { ...x, body_md: e.target.value } : x)) })} />
          </div>
        ))}
      </>
    );
  }

  return (
    <form className="stack" onSubmit={(e) => { e.preventDefault(); onSave(p, comment); }}>
      {form}
      <label className="field">수정 메모 (선택)</label>
      <input type="text" maxLength={4000} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="무엇을 왜 바꿨는지" />
      <div className="row">
        <button className="btn primary" disabled={saving}>새 버전으로 저장</button>
        <button type="button" className="btn" onClick={onCancel} disabled={saving}>취소</button>
        <span className="small muted">저장은 승인이 아닙니다. 저장 후 다시 승인해야 다음 단계에 반영됩니다.</span>
      </div>
    </form>
  );
}
