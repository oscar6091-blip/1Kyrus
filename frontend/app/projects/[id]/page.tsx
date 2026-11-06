"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import BriefPanel from "@/components/BriefPanel";
import StageReview from "@/components/StageReview";
import StageSidebar from "@/components/StageSidebar";
import { DEMO_NOTICE, ErrorBox, ModeBadge } from "@/components/common";
import { api } from "@/lib/api";
import type { DecisionRecord, ExperimentRun, JobView, ProjectDetail, StageDetail } from "@/lib/types";

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [stage, setStage] = useState<StageDetail | null>(null);
  const [runs, setRuns] = useState<ExperimentRun[]>([]);
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [job, setJob] = useState<JobView | null>(null);
  const [lastJob, setLastJob] = useState<JobView | null>(null);
  const [error, setError] = useState<unknown>(null);
  const selectedRef = useRef<number | null>(null);
  selectedRef.current = selected;

  const refresh = useCallback(async () => {
    try {
      const d = await api.project(id);
      setDetail(d);
      setJob(d.active_job);  // reconnect to a running job after reload
      let n = selectedRef.current;
      if (n === null) {
        n = d.active_job?.stage_no ?? d.stages.find((s) => s.status !== "approved")?.stage_no ?? 6;
        setSelected(n);
      }
      const [st, rs, ds] = await Promise.all([api.stage(id, n), api.runs(id), api.decisions(id)]);
      setStage(st);
      setRuns(rs);
      setDecisions(ds);
    } catch (e) {
      setError(e);
    }
  }, [id]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { if (selected !== null) api.stage(id, selected).then(setStage).catch(setError); }, [id, selected]);

  // Poll the active job once per second; reload state when it ends.
  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "running")) return;
    const t = setInterval(async () => {
      try {
        const j = await api.job(job.id);
        if (j.status !== "queued" && j.status !== "running") {
          setJob(null);
          setLastJob(j);
          refresh();
        } else {
          setJob(j);
        }
      } catch (e) {
        setError(e);
      }
    }, 1000);
    return () => clearInterval(t);
  }, [job, refresh]);

  if (!detail) {
    return <div className="container"><ErrorBox error={error} />{!error && <p className="muted">불러오는 중…</p>}</div>;
  }

  return (
    <>
      <div className="topbar">
        <Link href="/">← 프로젝트 목록</Link>
        <h1 style={{ marginLeft: 8 }}>{detail.project.name}</h1>
        <ModeBadge mode={detail.project.mode} />
        <span className="spacer" />
        {job && <span className="badge running">S{job.stage_no} 작업 중</span>}
      </div>
      {detail.project.mode === "demo" && (
        <div className="notice warn" style={{ margin: "10px 16px 0" }}>
          {DEMO_NOTICE}. 단계 결과는 고정 시나리오이며, 저장·승인·버전·오래됨·업로드·내보내기는 실제 앱 코드로 처리됩니다.
        </div>
      )}
      <div style={{ margin: "10px 16px 0" }}><ErrorBox error={error} onClose={() => setError(null)} /></div>
      <div className="workspace">
        <aside>
          <StageSidebar stages={detail.stages} selected={selected ?? 1} onSelect={(n) => { setSelected(n); setLastJob(null); }} />
        </aside>
        <main>
          {stage && stage.stage.stage_no === selected && (
            <StageReview
              projectId={id}
              mode={detail.project.mode}
              detail={stage}
              runs={runs}
              activeJob={job}
              lastJob={lastJob}
              onChanged={refresh}
              onNavigate={(n) => setSelected(n)}
              onJobStarted={(j) => { setJob(j); setLastJob(null); }}
              onRunsChanged={() => refresh()}
            />
          )}
        </main>
        <BriefPanel projectId={id} brief={detail.brief} viewed={stage?.current_artifact ?? null} decisions={decisions} />
      </div>
    </>
  );
}
