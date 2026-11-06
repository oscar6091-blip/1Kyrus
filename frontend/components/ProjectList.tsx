"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health, ProjectSummary, StageView } from "@/lib/types";
import { STATUS_LABEL } from "@/lib/types";
import AppSidebar from "./AppSidebar";
import { DEMO_NOTICE, ErrorBox, ModeBadge, fmtTime } from "./common";

/** Dashboard (UI/UX plan UI-01): project cards with the six-stage strip, plus the create form. */
export default function ProjectList() {
  const router = useRouter();
  const [health, setHealth] = useState<Health | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [stages, setStages] = useState<Record<string, StageView[]>>({});
  const [name, setName] = useState("");
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(setError);
    api.listProjects().then((ps) => {
      setProjects(ps);
      // Stage status per project comes from the existing project detail API (read-only).
      ps.forEach((p) => api.project(p.id).then((d) => setStages((s) => ({ ...s, [p.id]: d.stages }))).catch(() => {}));
    }).catch(setError);
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const p = await api.createProject(name.trim(), idea.trim());
      router.push(`/projects/${p.id}`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  const all = Object.values(stages).flat();
  const waiting = all.filter((s) => s.status === "needs_review").length;
  const running = all.filter((s) => s.status === "running").length;
  const stale = all.filter((s) => s.status === "stale").length;

  return (
    <div className="shell">
      <AppSidebar />
      <main className="content stack">
        <div className="page-head">
          <div>
            <div className="eyebrow">R2P Agent</div>
            <h1>연구 프로젝트</h1>
            <div className="meta">결정을 기다리는 단계 {waiting} · 진행 중 {running} · 오래됨 {stale}</div>
          </div>
          <a href="#new" className="btn primary">＋ 새 프로젝트</a>
        </div>

        {health?.default_mode === "demo" && (
          <div className="notice warn small">
            {DEMO_NOTICE}. 새 프로젝트는 demo 모드로 만들어지며, 각 단계 결과는 미리 작성한 고정 시나리오입니다.
            저장·승인·버전·업로드·내보내기는 실제로 동작합니다.
          </div>
        )}
        <ErrorBox error={error} onClose={() => setError(null)} />

        {projects === null && !error && <p className="muted">불러오는 중…</p>}
        <ul className="projects">
          {projects?.map((p) => {
            const st = stages[p.id];
            const focus = st?.find((s) => s.status === "running") ?? st?.find((s) => s.status === "needs_review") ?? st?.find((s) => s.status === "stale");
            const staleN = st?.filter((s) => s.status === "stale").length ?? 0;
            return (
              <li key={p.id} className="pcard">
                <div className="top">
                  <div style={{ minWidth: 0 }}>
                    <div className="row" style={{ gap: 10 }}>
                      <b>{p.name}</b>
                      <ModeBadge mode={p.mode} />
                    </div>
                    <div className="small muted" style={{ marginTop: 4 }}>수정 {fmtTime(p.updated_at)}</div>
                  </div>
                  <div className="row">
                    {focus && focus.status !== "stale" && <span className={`badge ${focus.status}`}>S{focus.stage_no} {STATUS_LABEL[focus.status]}</span>}
                    {staleN > 0 && <span className="badge stale">오래됨 {staleN}</span>}
                    <Link href={`/projects/${p.id}`} className="btn dark">이어서 하기 →</Link>
                  </div>
                </div>
                {st && (
                  <div className="strip">
                    {st.map((s) => (
                      <div key={s.stage_no} className={s.status}>
                        <div className="bar" />
                        <div className="lbl">S{s.stage_no} {STATUS_LABEL[s.status]}</div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="small" style={{ color: "var(--ink-2)" }}>{p.idea.slice(0, 180)}{p.idea.length > 180 ? "…" : ""}</div>
              </li>
            );
          })}
        </ul>
        {projects?.length === 0 && <div className="panel muted">아직 프로젝트가 없습니다. 아래에서 새 프로젝트를 만드세요.</div>}

        <form className="panel" id="new" onSubmit={create}>
          <h2>새 프로젝트</h2>
          <p className="small" style={{ marginTop: 0, color: "var(--ink-2)" }}>
            연구 아이디어를 입력하면 Brief → 관련 연구 → 실험 설계 → 실행 코드 → 결과 분석 → 영어 논문 초안을 순서대로 만들고,
            단계마다 직접 검토·수정·승인합니다. 지원 범위: 공개 데이터셋의 소규모 ML 비교 연구(외부 CPU 실행).
          </p>
          <label className="field" htmlFor="name">프로젝트 이름</label>
          <input id="name" type="text" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} required />
          <label className="field" htmlFor="idea">연구 아이디어</label>
          <textarea id="idea" maxLength={8000} rows={4} value={idea} onChange={(e) => setIdea(e.target.value)} required />
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn primary" disabled={busy || !name.trim() || !idea.trim()}>프로젝트 만들기</button>
            {health && <span className="small muted">이 프로젝트의 모드: {health.default_mode} (생성 후 바뀌지 않음)</span>}
          </div>
        </form>
      </main>
    </div>
  );
}
