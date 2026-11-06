"use client";

import type { StageView } from "@/lib/types";
import { STAGE_NAMES, STATUS_LABEL } from "@/lib/types";

/** "연구 단계" rows inside the sidebar card: status dot · S code · name · status tag. */
export default function StageSidebar({ stages, selected, onSelect }: {
  stages: StageView[];
  selected: number;
  onSelect: (n: number) => void;
}) {
  return (
    <nav aria-label="연구 단계">
      <div className="section"><span>연구 단계</span></div>
      <ul className="list stagelist">
        {stages.map((s) => {
          const draft = s.current_artifact_id && s.approved_artifact_id && s.current_artifact_id !== s.approved_artifact_id;
          const cls = s.stage_no === selected ? " active" : s.status === "pending" ? " wait" : "";
          return (
            <li key={s.stage_no}>
              <button className={`navrow${cls}`} onClick={() => onSelect(s.stage_no)}>
                <span className={`dot ${s.status}`} />
                <span className="stage-code">S{s.stage_no}</span>
                <span className="name">{STAGE_NAMES[s.stage_no]}</span>
                <span className="tag">{STATUS_LABEL[s.status]}{draft ? " · 새 초안" : ""}</span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="sidebar-note">
        앞 단계를 모두 승인해야 다음 단계를 실행할 수 있습니다. 상위 단계를 새로 승인하면 결과가 있는 하위 단계는 오래됨으로 바뀝니다.
      </p>
    </nav>
  );
}
