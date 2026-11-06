"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health, Mode, ProjectSummary } from "@/lib/types";

/** Left sidebar card from the UI/UX plan (Sidebar.dc.html): brand, new project, my projects, research stages. */
export default function AppSidebar({ activeProjectId, mode, children }: {
  activeProjectId?: string;
  mode?: Mode;
  children?: React.ReactNode;
}) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]));
    api.health().then(setHealth).catch(() => setHealth(null));
  }, [activeProjectId]);

  const shownMode = mode ?? health?.default_mode;

  return (
    <aside className="sidebar">
      <div className="sidebar-card">
        <Link href="/" className="brand" aria-label="R2P+ 프로젝트 목록">R2P+</Link>
        <div className="new">
          <Link href="/#new" className="btn primary" style={{ height: 50 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M6 12h12M12 18V6" /></svg>
            새 프로젝트
          </Link>
        </div>
        <div className="scroll">
          <div className="section"><span>내 프로젝트</span><Link href="/">전체 보기</Link></div>
          <ul className="list projects-mini">
            {projects.slice(0, 6).map((p) => (
              <li key={p.id}>
                <Link href={`/projects/${p.id}`} className={`navrow${p.id === activeProjectId ? " active" : ""}`}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ flex: "none" }}>
                    <path d="M8.5 19H8c-4 0-6-1-6-6V8c0-4 2-6 6-6h8c4 0 6 2 6 6v5c0 4-2 6-6 6h-.5c-.31 0-.61.15-.8.4l-1.5 2c-.66.88-1.74.88-2.4 0l-1.5-2c-.16-.22-.53-.4-.8-.4z" />
                  </svg>
                  <span className="name">{p.name}</span>
                </Link>
              </li>
            ))}
            {projects.length === 0 && <li className="small muted" style={{ padding: "6px 16px" }}>프로젝트가 없습니다.</li>}
          </ul>
          {children}
        </div>
        <div className="foot">
          {shownMode && (
            <div className="foot-pill">
              <span className="ico">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#000" strokeWidth="1.5"><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1" /></svg>
              </span>
              <span style={{ flex: 1 }}>{shownMode === "demo" ? "demo 모드" : "live 모드"}</span>
              {health && <span className="small muted">live 설정 {health.live_configured ? "있음" : "없음"}</span>}
            </div>
          )}
          <div className="foot-pill">
            <span className="ico" style={{ background: "#000", color: "#fff", fontSize: 13, fontWeight: 600 }}>나</span>
            <span style={{ flex: 1 }}>로컬 사용자</span>
            <span className="small muted">연구자</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
