"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError } from "@/lib/api";
import type { Mode, StageStatus } from "@/lib/types";
import { STATUS_LABEL } from "@/lib/types";

export function Markdown({ text }: { text: string }) {
  // No rehype-raw: HTML inside Markdown is shown as text, never executed.
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

export function StatusBadge({ status }: { status: StageStatus }) {
  return <span className={`badge ${status}`}>{STATUS_LABEL[status]}</span>;
}

export function ModeBadge({ mode }: { mode: Mode }) {
  return <span className={`badge ${mode}`}>{mode === "demo" ? "demo 모드" : "live 모드"}</span>;
}

export const DEMO_NOTICE = "데모 모드: 사전 작성 산출물 사용";

export function ErrorBox({ error, onClose }: { error: unknown; onClose?: () => void }) {
  if (!error) return null;
  const body = error instanceof ApiError ? error.body : null;
  return (
    <div className="notice bad" role="alert">
      <div className="row">
        <strong style={{ flex: 1 }}>{body ? body.message : String(error)}</strong>
        {onClose && <button className="btn link" onClick={onClose}>닫기</button>}
      </div>
      {body && body.fields.length > 0 && (
        <ul className="small" style={{ margin: "6px 0 0", paddingLeft: 18 }}>
          {body.fields.map((f, i) => (
            <li key={i}><code>{f.path}</code>: {f.message}</li>
          ))}
        </ul>
      )}
      {body && (
        <div className="small" style={{ marginTop: 4 }}>
          오류 코드 {body.code}{body.retryable ? " · 잠시 후 다시 시도할 수 있습니다." : ""}
        </div>
      )}
    </div>
  );
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("ko-KR", { hour12: false });
  } catch {
    return iso;
  }
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
        <header>
          <h2>{title}</h2>
          <span className="badge pending">읽기 전용</span>
          <button className="btn" onClick={onClose}>닫기</button>
        </header>
        {children}
      </div>
    </div>
  );
}

/** Confirmation popup in the plan's exception-popup style (black-bordered card, two pill buttons). */
export function ConfirmDialog({ title, children, confirmLabel, busy, onConfirm, onCancel }: {
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-back" onClick={busy ? undefined : onCancel}>
      <div className="modal confirm" onClick={(e) => e.stopPropagation()} role="alertdialog" aria-label={title}>
        <h2 style={{ fontSize: 20 }}>{title}</h2>
        <div style={{ margin: "10px 0 20px", color: "var(--ink-2)", lineHeight: 1.6 }}>{children}</div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn" onClick={onCancel} disabled={busy}>취소</button>
          <button className="btn dark" onClick={onConfirm} disabled={busy}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
