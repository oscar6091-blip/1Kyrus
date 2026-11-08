"use client";

import { useRef, useState } from "react";
import { api, newRequestId } from "@/lib/api";
import type { ExperimentRun } from "@/lib/types";
import { ErrorBox, fmtTime } from "./common";

/** Default S5 input: the latest uploaded run of each experiment. */
export function latestRunPerExperiment(runs: ExperimentRun[]): string[] {
  const latest = new Map<string, ExperimentRun>();
  for (const r of runs) latest.set(r.payload.experiment_id, r); // runs come oldest first
  return [...latest.values()].map((r) => r.id);
}

/**
 * S5: upload externally produced result JSON (one run, or a bundle with one run per experiment,
 * DEVIATIONS D-07) and pick the runs to analyse, at most one per experiment.
 */
export default function RunUpload({ projectId, runs, selected, onSelect, onUploaded, disabled }: {
  projectId: string;
  runs: ExperimentRun[];
  selected: string[];
  onSelect: (ids: string[]) => void;
  onUploaded: (runs: ExperimentRun[]) => void;
  disabled: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const chosen = runs.filter((r) => selected.includes(r.id));

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.upload(projectId, file, newRequestId());
      onUploaded("bundle" in r ? r.runs : [r]);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function toggle(run: ExperimentRun) {
    if (selected.includes(run.id)) {
      onSelect(selected.filter((id) => id !== run.id));
      return;
    }
    // one run per experiment: picking a run replaces another run of the same experiment
    const sameExp = new Set(runs.filter((r) => r.payload.experiment_id === run.payload.experiment_id).map((r) => r.id));
    onSelect([...selected.filter((id) => !sameExp.has(id)), run.id]);
  }

  return (
    <div className="panel">
      <h2>실험 결과 업로드</h2>
      <div className="notice info small">
        서비스 밖에서 S4 코드를 실행해 만든 결과 JSON(<code>prototype_json_v1</code>)을 올립니다. 서버는 실험을 실행하지 않습니다.
        실험 하나의 결과 파일(예: <code>results/E1.json</code>) 또는 모든 실험을 담은 묶음 파일
        (<code>results/results_bundle.json</code>, <code>schema_version</code> 1.1)을 올릴 수 있습니다.
        정상 예시: <code>handoff/fixtures/experiment_result.valid.json</code>.
        NaN·Infinity, 중복 키, 문자열 수치, 승인된 S3에 없는 실험 ID는 거부됩니다.
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <input ref={fileRef} type="file" accept="application/json,.json" disabled={disabled || busy} />
        <button className="btn" onClick={upload} disabled={disabled || busy}>업로드</button>
      </div>
      <div style={{ marginTop: 8 }}><ErrorBox error={error} onClose={() => setError(null)} /></div>

      {runs.length > 0 && (
        <>
          <h3>분석할 Run 선택 <span className="small muted">(실험마다 하나씩, 여러 실험 선택 가능)</span></h3>
          <table className="simple">
            <thead><tr><th /><th>업로드</th><th>실험</th><th>seed</th><th>출처</th><th>지표 수</th></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td><input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggle(r)} disabled={disabled} /></td>
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

      {chosen.map((run) => (
        <details key={run.id} open={chosen.length === 1} style={{ marginTop: 12 }}>
          <summary><b>{run.payload.experiment_id}</b> 원본 지표 ({run.payload.metrics.length}개)</summary>
          <table className="simple" style={{ marginTop: 8 }}>
            <thead><tr><th>#</th><th>지표</th><th>split</th><th>step</th><th>값</th><th>단위</th></tr></thead>
            <tbody>
              {run.payload.metrics.map((m, i) => (
                <tr key={i}><td>{chosen.length > 1 ? `${run.payload.experiment_id}.m${i}` : `m${i}`}</td><td>{m.name}</td><td>{m.split}</td><td>{m.step ?? "-"}</td><td><code>{String(m.value)}</code></td><td>{m.unit}</td></tr>
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
        </details>
      ))}
    </div>
  );
}
