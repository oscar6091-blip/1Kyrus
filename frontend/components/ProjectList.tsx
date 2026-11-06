"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health, ProjectSummary } from "@/lib/types";
import { DEMO_NOTICE, ErrorBox, ModeBadge, fmtTime } from "./common";

export default function ProjectList() {
  const router = useRouter();
  const [health, setHealth] = useState<Health | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [name, setName] = useState("");
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(setError);
    api.listProjects().then(setProjects).catch(setError);
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

  return (
    <>
      <div className="topbar">
        <h1>연구 워크플로 프로토타입</h1>
        <span className="spacer" />
        {health && <ModeBadge mode={health.default_mode} />}
        {health && (
          <span className="small muted">live 설정: {health.live_configured ? "있음" : "없음"}</span>
        )}
      </div>
      <div className="container stack">
        {health?.default_mode === "demo" && (
          <div className="notice warn">
            {DEMO_NOTICE}. 새 프로젝트는 demo 모드로 만들어지며, 각 단계 결과는 미리 작성한 고정 시나리오입니다.
            저장·승인·버전·업로드·내보내기는 실제로 동작합니다.
          </div>
        )}
        <ErrorBox error={error} onClose={() => setError(null)} />

        <form className="panel" onSubmit={create}>
          <h2>새 프로젝트</h2>
          <p className="muted small" style={{ marginTop: 0 }}>
            연구 아이디어를 입력하면 Brief → 관련 연구 → 실험 설계 → 실행 코드 → 결과 분석 → 영어 논문 초안을 순서대로 만들고,
            단계마다 직접 검토·수정·승인합니다. 지원 범위: 공개 데이터셋의 소규모 ML 비교 연구(외부 CPU 실행).
          </p>
          <label className="field" htmlFor="name">프로젝트 이름</label>
          <input id="name" type="text" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} required />
          <label className="field" htmlFor="idea">연구 아이디어</label>
          <textarea id="idea" maxLength={8000} rows={4} value={idea} onChange={(e) => setIdea(e.target.value)} required />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn primary" disabled={busy || !name.trim() || !idea.trim()}>프로젝트 만들기</button>
            {health && <span className="small muted">이 프로젝트의 모드: {health.default_mode} (생성 후 바뀌지 않음)</span>}
          </div>
        </form>

        <div className="panel">
          <h2>프로젝트 목록</h2>
          {projects === null && !error && <p className="muted">불러오는 중…</p>}
          {projects?.length === 0 && <p className="muted">아직 프로젝트가 없습니다.</p>}
          <ul className="projects">
            {projects?.map((p) => (
              <li key={p.id}>
                <div className="row">
                  <Link href={`/projects/${p.id}`}><strong>{p.name}</strong></Link>
                  <ModeBadge mode={p.mode} />
                  <span className="spacer" style={{ flex: 1 }} />
                  <span className="small muted">수정 {fmtTime(p.updated_at)}</span>
                </div>
                <div className="small muted" style={{ marginTop: 3 }}>{p.idea.slice(0, 160)}{p.idea.length > 160 ? "…" : ""}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
