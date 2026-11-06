"use client";

import type { StageView } from "@/lib/types";
import { STAGE_NAMES } from "@/lib/types";
import { StatusBadge } from "./common";

export default function StageSidebar({ stages, selected, onSelect }: {
  stages: StageView[];
  selected: number;
  onSelect: (n: number) => void;
}) {
  return (
    <nav className="panel" aria-label="단계">
      <h2>단계</h2>
      <ul className="stagelist">
        {stages.map((s) => (
          <li key={s.stage_no}>
            <button className={s.stage_no === selected ? "active" : ""} onClick={() => onSelect(s.stage_no)}>
              <span><strong>S{s.stage_no}</strong> {STAGE_NAMES[s.stage_no]}</span>
              <span className="row" style={{ gap: 4 }}>
                <StatusBadge status={s.status} />
                {s.current_artifact_id && s.approved_artifact_id && s.current_artifact_id !== s.approved_artifact_id && (
                  <span className="small muted">새 초안</span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p className="small muted" style={{ marginBottom: 0 }}>
        앞 단계를 모두 승인해야 다음 단계를 실행할 수 있습니다. 상위 단계를 새로 승인하면 결과가 있는 하위 단계는 오래됨으로 바뀝니다.
      </p>
    </nav>
  );
}
