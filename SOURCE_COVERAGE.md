# 원문 정보 보완과 이번 프로토타입의 처리 범위

원문 정보 보완: 2026-11-06. 안내 문서 통합: 2026-11-07. 정보 누락 검토 N-01~N-09의 반영 범위를 정리했다. 아래 ‘반영’은 **계획 자료와 구현 지시의 보완**을 뜻하며 앱 구현 완료나 원문 전체 충족을 뜻하지 않는다. 시작 안내와 파일 읽는 순서는 `CLAUDE.md`를 따른다.

## 원문은 어디에 있는가

- `sources/original/SSRD_v0.1.docx`: 첨부 SSRD 원본의 바이트가 동일한 사본. 본문·표·그림·부록 전체를 포함한다.
- `sources/original/SSAD_v0.1.pdf`: 첨부 SSAD 원본의 바이트가 동일한 사본. 다이어그램을 포함한다.
- `sources/requirements.all.json`: SSRD 요구사항 55개·필드 478개. 원문 필드는 그대로이며 `prototype`만 이번 범위를 설명한다.
- `sources/ssrd_context.json`: 요구사항 표 밖의 본문과 일반 표. 시스템 정의, 고객 계층, 근거 ID 정의, UI 정의 10개, A.II 원래 업로드 규격·예시, A.III 가정 7개, 용어를 별도로 찾을 수 있다.
- `sources/ssad_evidence.json`: SSAD 19쪽의 텍스트 추출본. 그림의 최종 근거는 원본 PDF다.
- `sources/external_references.json`: 사용한 SDK·프런트 설치·arXiv API·논문·데이터셋의 공식 근거 링크와 확인일.

원문을 포함한 것은 전체 기능을 구현하라는 지시가 아니다. 프로토타입 범위는 `scope.json`, 구체적인 동작은 `contracts/`, 작업은 `implementation_plan.md`를 따른다. SSRD·SSAD 원본을 수정하지 않는다.

## 원문 보존과 ID 별칭 규칙

요구사항 JSON의 `fields`에 있는 label·value와 여러 문단의 줄바꿈은 원문을 보존한다. M.A.R.S. 전체와 Proposed Activity·WinWin Agreement(s)의 공란도 그대로 두며, CR에 원래 없는 Specific 필드를 만들지 않는다. 원문은 `fields`, 이번 구현 설명은 `prototype`에 구분한다.

원문 일부의 LOS-2·LOS-10은 다른 표에서 LOR-2·LOR-10으로 쓰인다. `original_id`와 `source_identity`는 원문을, `id`는 문서 연결용 ID를 담는다. 이 별칭 처리를 원문 수정으로 설명하지 않는다.

## N-01~N-09 반영표

| 검토 ID | 원문 정보 | 이번 팩에서 정한 처리 | 구현 위치·완료 확인 |
| --- | --- | --- | --- |
| N-01 | 지원 분야·예제 규모·제외 대상 | 원문 정의를 보존하고, 이번 범위는 공개 데이터셋의 소규모 ML·외부 CPU 실행으로 안내한다. 원문의 GPU·시간 기준을 CPU 실행 보장으로 주장하지 않는다. | `scope.json.prototype_supported_work`, `CLAUDE.md`, 이 문서 |
| N-02 | UI-01~UI-10 정의 | 원래 정의를 보존하고 아래 표에서 유지·축소·제외를 연결한다. 실제 디자인은 UI/UX 팀 자료에 맞춰 조정한다. | `sources/ssrd_context.json.ui_definitions`, 아래 화면 대응표, T04 |
| N-03 | A.II 업로드 형식 | 원래 규격과 정상 예시를 보존한다. 이번에는 별도 `prototype_json_v1`만 받고 원문 형식의 자동 변환은 하지 않는다. 차이를 업로드 안내에 표시한다. | `scope.json.upload_format`, `contracts/README.md`, T03·T04, AC-09 |
| N-04 | 고객 검증 가정 A-1~A-7 | 원문과 검증 질문을 보존하고 미검증으로 표시한다. 이번에 새 인터뷰·사용자 평가를 수행했다는 뜻은 아니다. | `sources/ssrd_context.json.customer_assumptions`, `CLAUDE.md` |
| N-05 | ablation과 가설별 실험 대응 | S3 본문에 ablation 계획 또는 해당 없음 사유를 넣는다. 모든 Brief 가설이 최소 한 실험에 연결되도록 서버가 검사한다. S5는 모든 가설을 판정하되 선택 Run에 없는 가설은 inconclusive로 남긴다. | `contracts/README.md`, 단계 프롬프트, T02·T06, AC-10·AC-19 |
| N-06 | Brief 변경 이력 | 기존 Decision 목록의 S1 approve 기록으로 승인 Brief 이력을 만들고, 기존 Artifact 조회로 과거 승인본을 읽기 전용으로 연다. 모든 초안 탐색·diff·복원은 제외한다. | `contracts/README.md`, `architecture.md`, T04, AC-04 |
| N-07 | 근거 확인·근거 없음 표시 | ref는 논문, metric은 해당 Run의 원본 행, artifact는 해당 버전을 연다. 빈 근거는 ‘근거 없음: 사용자 확인 필요’를 표시한다. 모든 문장 단위 근거 매핑·자동 의미 증명은 제외한다. | `contracts/README.md`, `architecture.md`, T04, AC-19 |
| N-08 | LLM 입력 데이터 사용 조건 확인 | `LLM_DATA_POLICY.md`에 확인 기록을 둔다. 현재는 NOT_CHECKED이며 T05에서 실제 확인 근거 또는 확인 불가 상태를 기록한다. 미확인을 PASS나 인증으로 보고하지 않는다. | `LLM_DATA_POLICY.md`, T05, AC-18 |
| N-09 | 미검증 인용의 사용자 표시 | 일부 후보 제외 시 대상과 이유를 `evidence.warnings`로 표시한다. 0편이면 사유를 포함해 실패한다. 검증된 인용 허용 목록은 그대로 유지한다. | `contracts/README.md`, `architecture.md`, T05, AC-08 |

이번 보완은 API 16개·SQLite 테이블 6개·완료 조건 AC-01~20을 유지한다. 이력과 근거 열람도 기존 API로 구현한다. 네 가지 임시 baseline(SQLite·S1 Brief 갱신·back 이동·Markdown 출력)은 그대로다.

demo는 동봉 H1/E1 시나리오의 사전 작성 결과다. 가설·실험 ID 구조까지 바꾸었을 때 fixture가 새 구조를 자동 생성한다고 가정하지 않는다. 공통 검증에 맞지 않으면 오류를 표시하고, 새 구조를 확인할 때는 테스트용 Gateway 또는 live를 사용한다. demo라는 이유로 가설 대응 검사를 우회하지 않는다.

## 전체 시스템의 범위와 이번 범위를 구분

원문은 석사·초기 박사과정 등 연구 실행 경험이 적은 대학원생의 판단을 돕는 시스템이다. 연구자 외에 지도교수·운영자 역할이 있으나, 이번은 로컬 연구자 한 명의 흐름만 구현한다.

원문 ‘예제 규모 연구’는 공개 데이터셋·PyTorch·단일 GPU·12시간 이내 기준을 포함한다. SSAD OD-7에는 실험별 60분 상한과의 충돌이 미결로 남아 있다. 이번은 서버에서 실험을 실행하지 않으므로 이 수치를 해결하거나 실행 상한으로 도입하지 않는다. CPU/scikit-learn 참조 실험은 연결 확인용이며 원문 연구 규모를 충족했다는 증거가 아니다.

원문의 제외 대상인 실제 논문 투고, 비ML 분야, 대규모 학습, 사람 대상 연구, 비공개 대용량 데이터셋 업로드를 프로젝트 안내에 보존한다. 원문을 보존하는 것만으로 별도 분야 분류기나 데이터 업로드 기능을 추가하지 않는다.

## UI/UX 팀과 대조할 화면 ID

정확한 원문 표의 모든 셀은 `sources/ssrd_context.json.ui_definitions`에 있다. 아래는 이번 구현과의 대응이다. 논리 화면 ID와 URL 개수는 다르며 URL은 기존 두 개를 유지한다.

| 원문 ID | 원래 화면 | 이번 프로토타입 |
| --- | --- | --- |
| UI-01 | 대시보드 | 프로젝트 목록·생성·단계 상태·mode. 예산 관리·정식 알림 시스템은 제외. |
| UI-02 | 아이디어 구체화 | S1 Brief 폼·질문·코멘트 재생성. 완전한 대화 관리·논문 PDF 첨부는 제외. |
| UI-03 | 관련 연구 검토 | 확인 논문 카드·초록 기반 본문·근거. 논문 수동 추가·포함/제외·연도/분야 필터는 제외. |
| UI-04 | 실험 설계 검토 | 계획 본문·가설/실험/지표 폼·ablation 계획 또는 해당 없음 사유. |
| UI-05 | 코드 검토 | 파일 선택·편집·다운로드. diff 뷰어·smoke test 실행은 제외. |
| UI-06 | 실험·분석 | 외부 결과 JSON 업로드·Run 선택·지표 표·가설 판정·한계. 서버 실행·자동 추가 실험·필수 그래프는 제외. |
| UI-07 | 논문 에디터 | 여섯 섹션 직접 편집·전체 S6 재생성·근거 확인·Markdown/BibTeX. 문장별 전체 근거 매핑·섹션별 재생성·PDF는 제외. |
| UI-08 | 연구 맥락 패널 | 승인 Brief·입력 버전·S1 승인 이력 열람. 전체 초안 이력 탐색·diff·과거본 복원은 제외. |
| UI-09 | 공유·코멘트 | 교수 공유·권한·검토자 코멘트는 제외. 연구자 본인의 재생성 코멘트는 지원. |
| UI-10 | 로그인·계정 | 로컬 단일 사용자이므로 제외. |

## 업로드 형식의 차이

| 항목 | 원문 A.II | 이번 prototype_json_v1 |
| --- | --- | --- |
| 최상위 버전 | 없음 | `schema_version="1.0"` 필수 |
| 데이터 출처 | 별도 필드 없음 | `data_origin` 필수 |
| 지표 단위 | 지표별 unit 없음 | `metrics[].unit` 필수 |
| code_version 의미 | Git 커밋 해시 | Git 커밋 또는 소스 해시 등 식별자. 자동 코드 일치 검증 없음 |
| CSV | 지표 CSV와 나머지 메타데이터 입력 | 지원하지 않음 |

현재 스키마를 바꾸거나 원문 예시에 임의 단위를 채우지 않는다. 원문 예시를 그대로 올리면 422로 부족한 필드 위치를 설명하고, `fixtures/experiment_result.valid.json` 및 현재 형식 안내로 연결한다. ‘SSRD A.II 무변환 호환’을 주장하지 않는다.

## SSAD의 구성요소와 미결 상태

SSAD의 Web UI·API Gateway·Orchestrator·Stage Agents·LLM Gateway·Citation Verifier·Numeric Checker·Job Queue/Workers·Sandbox·Context Store·Share/Export는 `architecture.md`의 역할 또는 명시적 제외 범위로 대응한다. 논리 구성요소를 모두 별도 서버·테이블로 만들지 않는다.

| 원문 미결 항목 | 이번 프로토타입의 선택 또는 보류 |
| --- | --- |
| OD-1 오케스트레이터 | WorkflowService에 직접 상태 규칙 구현 |
| OD-2 작업 큐 | 프로세스 내부 executor. 영속 외부 큐·중간 토큰 재개 제외 |
| OD-3 객체 저장소 | 도입하지 않고 SQLite의 payload/snapshot과 다운로드 생성 사용 |
| OD-4 2차 LLM | 제외. 단일 Gateway·어댑터 |
| OD-5 GPU 노드 | 서버 실험 실행과 함께 제외 |
| OD-6 배포 위치 | localhost 단일 사용자 |
| OD-7 시간 상한 충돌 | 서버 실험이 없어 이번에 해결하지 않음. 원문 미결 상태 보존 |

위 선택은 이번 프로토타입 실행을 위한 것이다. 원래 SSAD의 미결 사항을 정식으로 확정하거나 원문을 변경한 것으로 보고하지 않는다.
