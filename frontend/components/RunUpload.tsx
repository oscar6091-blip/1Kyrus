"use client";

import { useRef, useState } from "react";
import { api, newRequestId } from "@/lib/api";
import type { ExperimentRun } from "@/lib/types";
import { ErrorBox, fmtTime } from "./common";

/** S5: upload an externally produced result JSON and pick the Run to analyse. */
export default function RunUpload({ projectId, runs, selected, onSelect, onUploaded, disabled }: {
  projectId: string;
  runs: ExperimentRun[];
  selected: string | null;
  onSelect: (id: string) => void;
  onUploaded: (run: ExperimentRun) => void;
  disabled: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const run = runs.find((r) => r.id === selected) ?? null;

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.upload(projectId, file, newRequestId());
      onUploaded(r);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2>실험 결과 업로드</h2>
      <div className="notice info small">
        서비스 밖에서 S4 코드를 실행해 만든 결과 JSON(<code>prototype_json_v1</code>)을 올립니다. 서버는 실험을 실행하지 않습니다.
        원문 SSRD A.II 형식에 <code>schema_version</code>, <code>data_origin</code>, <code>metrics[].unit</code>이 더 필요하며
        자동 변환하지 않습니다. 정상 예시: <code>handoff/fixtures/experiment_result.valid.json</code>.
        NaN·Infinity, 중복 키, 문자열 수치, 승인된 S3에 없는 실험 ID는 거부됩니다.
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <input ref={fileRef} type="file" accept="application/json,.json" disabled={disabled || busy} />
        <button className="btn" onClick={upload} disabled={disabled || busy}>업로드</button>
      </div>
      <div style={{ marginTop: 8 }}><ErrorBox error={error} onClose={() => setError(null)} /></div>

      {runs.length > 0 && (
        <>
          <h3>분석할 Run 선택</h3>
          <table className="simple">
            <thead><tr><th /><th>업로드</th><th>실험</th><th>seed</th><th>출처</th><th>지표 수</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td><input type="radio" name="run" checked={selected === r.id} onChange={() => onSelect(r.id)} disabled={disabled} /></td>
                  <td>{fmtTime(r.created_at)}</td>
                  <td>{r.payload.experiment_id}</td>
                  <td>{r.payload.seed}</td>
                  <td>{r.payload.data_origin}</td>
                  <td>{r.payload.metrics.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {run && (
        <>
          <h3>선택한 Run의 원본 지표</h3>
          <table className="simple">
            <thead><tr><th>#</th><th>지표</th><th>split</th><th>step</th><th>값</th><th>단위</th></tr></thead>
            <tbody>
              {run.payload.metrics.map((m, i) => (
                <tr key={i}><td>m{i}</td><td>{m.name}</td><td>{m.split}</td><td>{m.step ?? "-"}</td><td><code>{String(m.value)}</code></td><td>{m.unit}</td></tr>
              ))}
            </tbody>
          </table>
          <div className="small muted" style={{ marginTop: 6 }}>
            code_version <code>{run.payload.code_version.slice(0, 16)}…</code> · 환경 {JSON.stringify(run.payload.environment ?? {})}
          </div>
          {Array.isArray(run.payload.config.fit_warnings) && (run.payload.config.fit_warnings as string[]).length > 0 && (
            <div className="notice warn small" style={{ marginTop: 6 }}>
              실행 경고: {(run.payload.config.fit_warnings as string[]).join(" / ")}
            </div>
          )}
        </>
      )}
    </div>
  );
}
