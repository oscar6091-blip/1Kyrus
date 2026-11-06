"use client";

import { useState } from "react";
import type { CodeFile } from "@/lib/types";

/** File tabs for S4. Read-only view, or per-file editing when onChange is given. */
export default function CodeFiles({ files, onChange }: { files: CodeFile[]; onChange?: (files: CodeFile[]) => void }) {
  const [idx, setIdx] = useState(0);
  const cur = files[Math.min(idx, files.length - 1)];

  function update(patch: Partial<CodeFile>) {
    if (!onChange) return;
    onChange(files.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  }

  return (
    <div>
      <div className="filetabs">
        {files.map((f, i) => (
          <button key={i} className={i === idx ? "active" : ""} onClick={() => setIdx(i)} type="button">{f.path}</button>
        ))}
        {onChange && (
          <button type="button" onClick={() => { onChange([...files, { path: `new_file_${files.length + 1}.py`, content: "", language: "python" }]); setIdx(files.length); }}>
            + 파일
          </button>
        )}
      </div>
      {cur && !onChange && <pre className="code">{cur.content}</pre>}
      {cur && onChange && (
        <div className="stack">
          <div className="grid2">
            <div>
              <label className="field">경로 (상대 경로)</label>
              <input type="text" value={cur.path} onChange={(e) => update({ path: e.target.value })} />
            </div>
            <div>
              <label className="field">언어</label>
              <select value={cur.language} onChange={(e) => update({ language: e.target.value as CodeFile["language"] })}>
                {["python", "text", "markdown", "json", "yaml"].map((l) => <option key={l}>{l}</option>)}
              </select>
            </div>
          </div>
          <textarea className="mono" rows={18} value={cur.content} onChange={(e) => update({ content: e.target.value })} />
          {files.length > 1 && (
            <button type="button" className="btn" onClick={() => { onChange(files.filter((_, i) => i !== idx)); setIdx(0); }}>
              이 파일 삭제
            </button>
          )}
        </div>
      )}
    </div>
  );
}
