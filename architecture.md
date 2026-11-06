# 이번 프로토타입의 구현 구조

이 문서는 원본 SSAD의 전부를 구현하기 위한 설계가 아니라 **2026-11-08 수업 제출 범위의 설계**다. 범위의 기계 판독 버전은 `scope.json`, 동작 규칙은 `contracts/workflow.json`이다.

SQLite·S1에서만 Brief 갱신·화면 이동만 수행하는 back·Markdown 출력은 **SSAD와 별도로 둔 프로토타입 전용 임시 baseline**이다. 아래 구현 설명은 이 baseline을 구체화하며, SSAD의 확정 사항이나 설계 변경을 뜻하지 않는다. SSRD·SSAD 원본은 수정하지 않는다. 네 설정의 정확한 범위는 `CLAUDE.md`와 `scope.json.prototype_baseline`을 따른다.

## 내부 프로그램과 외부 서비스를 구분

| 프로그램 | 어디서 실행하는가? | 누가 무엇을 요청하는가? | 읽고 만드는 데이터 |
| --- | --- | --- | --- |
| Web UI | 사용자 브라우저 | 사용자가 생성·편집·승인·업로드·다운로드 조작 | 서버의 프로젝트·Stage·Artifact 표시 |
| API | FastAPI 프로세스 | Web UI가 JSON/파일 요청 | 요청 검증 후 서비스 함수 호출 |
| WorkflowService | 같은 백엔드 | API가 단계 실행·승인·수정 요청 | Stage 상태, 승인 포인터, Decision, stale 갱신 |
| JobRunner | 같은 백엔드의 실행 스레드 1개 | API가 만든 Job ID를 받아 실행 | 실행 시작 시 고정한 입력과 생성 결과 |
| ContextBuilder | 백엔드 함수 | JobRunner가 snapshot의 ID 목록 전달 | 고정된 Brief·상위 승인 Artifact·코멘트·선택 Run으로 모델 입력 작성 |
| Stage functions | 백엔드의 S1~S6 함수 | JobRunner가 특정 단계 실행 | 공통 payload 계약에 맞는 결과 반환 |
| LLMGateway | 백엔드 공통 모듈 | 모든 live 단계의 모델 호출 | 외부 Anthropic API 응답·모델·사용량 |
| CitationVerifier | 백엔드 공통 모듈 | S2의 검색/확인, S6의 인용 허용 목록 확인 | 외부 arXiv 메타데이터를 확인하고 Reference snapshot 반환 |
| TokenRenderer | 백엔드 순수 함수 | API가 미리보기·내보내기 요청 | Artifact evidence의 metric/cite를 Markdown에 삽입 |
| ExportService | 백엔드 함수 | 사용자가 다운로드 요청 | 승인된 코드 zip·초안 Markdown·BibTeX |
| SQLite | 로컬 DB 파일 | 위 내부 서비스가 짧은 트랜잭션으로 접근 | 프로젝트·단계·결과 버전·결정·Job·실험 기록 |

외부 시스템은 live Anthropic API와 arXiv API뿐이다. PostgreSQL·Redis·외부 객체 저장소·GitHub·Overleaf를 설치하거나 연결하지 않는다. **CitationVerifier는 내부 프로그램이며 arXiv가 외부 서비스**다.

## 실행 경계

1. 프런트엔드는 `http://127.0.0.1:3000`, API는 `http://127.0.0.1:8000/api`에서 실행한다.
2. CORS는 로컬 프런트엔드의 localhost·127.0.0.1 두 origin만 허용한다.
3. 백엔드 서버는 한 프로세스다. 다중 uvicorn worker나 자동 reload를 기본 명령에 넣지 않는다.
4. 긴 작업은 `ThreadPoolExecutor(max_workers=1)`에 Job ID를 넘겨 실행한다. Queue/Worker의 최소 기능을 프로세스 내부에서 구현한다.
5. Job과 상태는 먼저 DB에 기록한다. 모델/API 요청 중에는 DB write transaction을 열어 두지 않는다.
6. Worker는 각 처리 시점에 별도의 DB 세션을 연다. 요청 세션을 스레드로 넘기지 않는다.
7. 서버가 종료되면 실행 중 모델 호출을 중간 토큰부터 재개하지 않는다. 재시작 시 active Job을 interrupted로 표시하고 사용자가 다시 실행한다.

SQLite engine은 스레드별 세션 사용을 전제로 `check_same_thread=False`로 구성한다. foreign_keys와 busy_timeout은 새 연결마다 설정한다. WorkflowService의 쓰기는 짧은 `BEGIN IMMEDIATE` 트랜잭션 안에서 상태를 다시 읽고 적용해 두 요청이 같은 과거 상태를 동시에 승인하지 않도록 한다. 네트워크 호출은 그 밖에서 수행한다.

## 저장할 데이터 6종과 개념 대응

정확한 컬럼은 `contracts/database.sql`, API 데이터 형태는 `domain.schema.json`을 따른다.

| 테이블 | 무엇을 저장하는가? | 원문 SSAD 개념과의 관계 |
| --- | --- | --- |
| projects | 프로젝트 ID·이름·아이디어·mode·현재 승인 Brief 포인터 | Project. 사용자 테이블 없이 로컬 한 명이 사용 |
| stages | 프로젝트별 S1~S6 상태·현재 결과·현재 승인 결과 포인터 | Stage |
| artifact_versions | 모든 단계 결과 payload·입력 참조·근거 snapshot·생성 주체·버전 | Stage Artifact, Rationale, 최소 Provenance. S1의 승인 Artifact를 BriefVersion으로 사용 |
| decisions | 승인·편집·재생성·이전 이동 기록 | Decision Record |
| jobs | 비동기 작업 상태·요청 중복 방지·입력 snapshot·사용량·오류 | 실행 관리. 원문 도메인 표에 없지만 필요한 구현 데이터 |
| experiment_runs | 업로드한 실행 조건·측정값 JSON | ExperimentRun |

Reference는 별도 테이블을 만들지 않고 해당 Artifact의 `evidence.references`에 메타데이터 snapshot으로 보관한다. Rationale도 payload에 포함한다. 모든 쓰기의 별도 감사 로그, User, ShareGrant, Comment는 만들지 않는다.

이 통합은 프로토타입의 의도적인 축소다. 원본 SSAD의 엔티티 표와 동일한 테이블 개수를 맞추려고 기능을 추가하지 않는다.

## 입력 버전과 현재 결과를 구별

- `stages.current_artifact_id`: 현재 화면에서 검토할 최신 결과.
- `stages.approved_artifact_id`: 가장 최근에 승인한 결과. 새 초안을 만드는 동안 과거 승인 결과 자체는 보존한다.
- `projects.current_brief_artifact_id`: 가장 최근에 승인한 S1 Artifact. 별도 Brief 테이블을 만들지 않는다.
- `artifact_versions.input_snapshot_json`: 그 결과가 읽은 Brief·상위 결과·Run의 ID와 사용자 의견.
- `artifact_versions.evidence_json`: 그 결과가 사용한 논문 메타데이터·지표 값을 복사한 불변 근거.

다음 단계 실행 여부는 포인터 존재만으로 판단하지 않는다. **모든 이전 Stage가 approved인지도 확인**한다. 과거 승인 포인터가 남아 있어도 상태가 stale이면 새 작업의 입력으로 쓸 수 없다.

승인 Brief 이력은 새 API 없이 Project의 Decision 목록에서 S1 approve를 모아 만든다. 해당 artifact_id를 기존 Artifact 조회로 열고 버전·승인 시각을 표시한다. 과거본 열람은 읽기 전용이며 상태·포인터·결정 기록을 바꾸지 않는다. 전체 초안 이력 탐색·diff·복원은 이번 범위에서 제외한다.

## Brief 갱신 범위를 S1로 제한

S1을 승인할 때만 `current_brief_artifact_id`를 바꾼다. S2~S6의 결과는 각 단계 Artifact에 남기며 Brief에 자동 병합하지 않는다. `brief_delta`를 이번 API나 모델 결과에 넣지 않는다.

이 결정은 원문 RQ-8의 일부를 축소한다. 결과·결론을 추가할 때마다 Brief 전체 버전이 바뀌어 이전 단계 전체가 반복해서 stale이 되는 문제를 피하고, 고정된 순서의 버전 전파를 먼저 완성하려는 선택이다.

## 상태 변경의 정확한 동작

1. 실행 요청이 오면 선행 승인·프로젝트 잠금·S5 Run 조건을 검사한다.
2. 요청 중복을 먼저 확인한다. 이미 처리한 같은 요청이면 새 Job을 만들지 않는다.
3. 짧은 DB 트랜잭션에서 입력 ID를 snapshot으로 저장하고 Job queued·Stage running을 기록한다.
4. 커밋 뒤 executor에 전달한다. 모델·arXiv 호출은 트랜잭션 밖에서 수행한다.
5. 결과를 검증한 뒤 새 ArtifactVersion과 evidence를 저장하고 Job succeeded·Stage needs_review를 함께 기록한다.
6. 사용자가 approve하면 같은 트랜잭션에서 Decision, 승인 포인터, S1 Brief 포인터, 하위 stale을 갱신한다.
7. 하위 Stage 중 결과가 없는 것은 pending으로 둔다. 기존 결과가 있는 것은 needs_review·approved 여부와 관계없이 stale로 바꾼다.

편집은 새 결과 버전을 저장하는 동작이며 승인하지 않는다. back은 이동 기록을 남기고 이전 화면으로 이동할 뿐, 기존 결과를 자동 무효화하지 않는다. 사용자가 실제 수정본을 승인했을 때만 변경을 전파한다.

## 중복 요청 처리

UI는 사용자의 한 번의 의도에 UUID `request_id`를 하나 만들고 통신 재시도에서는 재사용한다. 다른 조작에는 새 UUID를 만든다.

- 요청 키는 `operation + project + stage + request_id`를 합쳐 만든다. operation은 run, decision, edit다. decision의 action은 fingerprint에 들어간다.
- 정렬된 요청 JSON과 경로로 fingerprint를 만든다.
- 같은 키·같은 fingerprint는 기존 Job/Decision과 결과 ID를 반환한다. 조회 시점의 Stage·Job 상태는 최신일 수 있다.
- 같은 키·다른 fingerprint는 409 REQUEST_ID_CONFLICT다.
- edit와 regenerate의 재전송도 새 Artifact나 모델 호출을 만들지 않는다.
- 프로젝트 busy 검사보다 중복 요청 조회가 먼저다. 진행 중 같은 요청 재조회가 409로 바뀌지 않아야 한다.

## 단계별 처리와 프롬프트 입력

| 단계 | 입력 | 처리 | 출력 |
| --- | --- | --- | --- |
| S1 | Project.idea, 사용자 코멘트, 재생성 시 현재 S1 내용 | Brief 초안과 최대 3개 확인 질문 생성 | Stage1 payload |
| S2 | 승인 S1 Brief, 이전 결과, 사용자 코멘트 | live는 Brief로 검색어를 구성해 arXiv 조회·확인 후 그 metadata/abstract로 정리. demo는 동봉 snapshot | Stage2 payload + 서버 evidence.references |
| S3 | Brief + 승인 S2 + 코멘트 | 계획과 실험 ID·가설 ID·필수 지표 이름 작성 | Stage3 payload |
| S4 | Brief + 승인 S2·S3 + 코멘트 | 외부 CPU Python 실행용 파일 생성. JSON 출력 스키마도 전달 | Stage4 payload |
| S5 | Brief + 승인 S3·S4 + 선택 Run + 코멘트 | 서버가 metric binding을 먼저 만든 뒤 모델에 전달하여 해석 | Stage5 payload + metrics evidence |
| S6 | Brief + 승인 S2~S5 + 코멘트 | 검증 참조·로그 binding을 허용 목록으로 전달하여 영어 여섯 섹션 작성 | Stage6 payload + 참조·지표 evidence |

각 단계에는 실제 snapshot으로 고정한 이전 승인 결과 전체를 전달한다. 현재 포인터를 worker 실행 시 다시 읽어 다른 입력으로 바꾸지 않는다. MVP에서는 자동 요약·RAG를 만들지 않는다. 구성한 모델 입력이 80,000자를 넘으면 `CONTEXT_TOO_LARGE`로 명확히 실패하고 사용자가 내용을 줄이도록 안내한다.

재생성에서는 해당 단계의 직전 결과와 코멘트도 전달한다. 최초 실행과 재생성을 동일한 고정 프롬프트로 처리해 의견을 무시하지 않는다.

## CitationVerifier의 실제 동작

`backend/app/services/references.py`의 내부 함수로 구현한다.

- live S2: 모델이 `search_query` 문자열을 만들고 서버가 arXiv 검색 API를 호출한다. 최대 3개를 채택한다. 검색 결과의 ID로 필요시 `id_list` 조회하고 제목·저자·첫 제출 연도를 서버 metadata로 채운다. LLM이 만든 서지를 그대로 채택하지 않는다.
- live S6: 승인 S2의 확인된 snapshot을 허용 목록으로 사용한다. 새 논문을 생성하지 않는다. snapshot의 상태와 cite 토큰 ID를 확인한다. 매번 외부 API를 다시 조회하지 않는다.
- 원문 제목의 공백·개행 정규화는 허용하되 저자·연도·식별자를 임의 보정하지 않는다.
- Atom의 `published` 첫 제출 연도를 사용한다. 학회 연도와 혼동하지 않는다. `arxiv_id`의 버전 접미사는 별도로 정규화한다.
- arXiv 요청은 한 연결씩, 최소 3초 간격. timeout 20초. 실패하면 ARXIV_UNAVAILABLE이며 fixture로 대체하지 않는다.
- PDF 전문 다운로드·저장·분석은 하지 않는다. 초록 기반 정리임을 UI에 표시한다.
- 확인된 논문이 한 편도 없으면 NO_VERIFIED_REFERENCES로 실패한다.
- 일부 후보가 미검증으로 제외되면 evidence.warnings에 대상과 이유를 남겨 화면에 보여 준다. 0편 실패에도 오류 message/fields로 사유를 전달한다. 새 미검증 후보를 가정해 만들거나 검증 허용 목록에 포함하지 않는다.

## 지표·인용 렌더링

허용 문법은 `{{metric:m0}}`, `{{cite:arxiv_1412_6980}}`다. m0 등은 선택 Run.metrics 배열의 순서로 서버가 부여한다. binding은 Run ID·배열 index·원본 값·단위를 포함한다.

- 모델은 원본 지표를 새 숫자로 써내는 대신 허용 토큰을 사용한다.
- 서버는 Artifact에 저장된 evidence를 사용해 토큰을 치환한다. 전체 지표 표도 서버가 원본 값으로 만든다.
- 원본 수치의 문자열 변환은 한 함수를 사용한다. 0.9666을 임의로 97%로 바꾸지 않는다. 단위를 별도 열로 표시한다.
- 모르는 토큰, 깨진 토큰 문법, 허용 목록에 없는 근거 ID는 저장·승인 전에 422 UNKNOWN_EVIDENCE다.
- 사용자가 올린 새 Run으로 옛 Artifact의 evidence를 덮어쓰지 않는다.
- S6의 methods·experiments에는 실행 설정·수렴 경고·한계를 함께 반영한다.

Rationale의 ref/metric/artifact 링크는 해당 버전의 evidence와 input_snapshot으로 해석한다. 논문은 source_url, 지표는 기존 Run 목록의 원본 행, 산출물은 기존 Artifact 조회로 연다. 빈 근거에는 ‘근거 없음: 사용자 확인 필요’를 표시한다. 읽기 전용 패널을 열 때 현재 연구 상태나 사용자의 편집 중 내용을 변경하지 않는다.

이 검사는 모든 자연어 수치의 의미를 자동 증명하는 Numeric Checker 전체 구현이 아니다. 해당 한계를 제출 설명에 적는다.

## 프런트엔드 화면

라우트는 `/`와 `/projects/[id]` 두 개로 제한한다.

- `/`: 이름·아이디어로 생성, 프로젝트 목록과 mode 표시.
- 프로젝트 화면: 왼쪽 S1~S6 상태, 가운데 현재 단계 결과·편집·승인·재생성·이전 이동, 오른쪽 승인 Brief와 입력 버전 목록.
- S1: Brief 필드와 가설 항목을 폼으로 수정한다. 질문도 표시한다.
- S2: 확인된 논문 카드를 evidence로 표시하고 본문 Markdown을 수정한다.
- S3: 계획 Markdown과 실험 ID·가설 ID·지표 목록을 수정한다. 원시 JSON 편집을 기본 UX로 쓰지 않는다.
- S3 서버 검증은 모든 Brief 가설의 실험 대응과 본문의 Ablation 계획/해당 없음 사유를 포함한다. S5는 모든 가설을 표시하되 선택 Run에 대응하지 않는 가설은 미검증/inconclusive로 남긴다.
- S4: 파일 선택과 텍스트 편집, zip 다운로드. ‘서버 미실행’ 상태 표시.
- S5: JSON 업로드, Run 선택, 원본 지표 표·경고·해석. run_id/evidence를 사용자가 편집할 수 없게 한다.
- S6: 섹션별 Markdown 편집·미리보기, 승인 후 Markdown·BibTeX 다운로드.
- Brief 패널에서 S1 승인 이력을, 검토 화면에서 이유·원본 근거·빈 근거 표시·검증 제외 경고를 제공한다. 원문 UI-01~UI-10과의 대응·제외 범위는 `SOURCE_COVERAGE.md`를 따른다.
- 업로드 화면은 prototype_json_v1의 추가 필수 필드와 정상 예시를 안내한다. 원문 A.II 형식을 그대로 지원한다고 표시하지 않는다.
- 작업 중에는 저장된 상태를 조회한다. 가짜 진행률을 계산하지 않고 ‘대기/생성 중/실패’와 소요 시간을 표시한다.
- 오류는 한국어 요약과 필드 위치·다시 할 수 있는 행동을 보여 준다. 내부 stack trace나 비밀키는 화면에 보내지 않는다.

## 의존성과 파일 구성

프런트는 Next/React/TypeScript, react-markdown, remark-gfm, 간단한 CSS만 우선 사용한다. 추가 UI 프레임워크·상태 관리 라이브러리는 넣지 않는다. 백엔드는 FastAPI/Pydantic/SQLAlchemy/Uvicorn/Anthropic SDK/HTTP 클라이언트/python-multipart/python-dotenv와 테스트 의존성으로 제한한다. scikit-learn은 웹 서버 의존성이 아니라 외부 참조 실험의 의존성이다.

권장 실제 파일 위치는 implementation_plan의 T 작업을 따른다. 환경 변수는 저장소 루트 `.env`를 백엔드가 읽는다. 프런트 API client는 `NEXT_PUBLIC_API_BASE_URL` 또는 고정된 로컬 기본값을 사용하며 서버 API 키를 참조하지 않는다.

## 이번 설계에서 의도적으로 제외한 것

로그인·다중 사용자·교수 공유, 생성 코드의 서버 실행, 자동 오류 수정, GPU, 영속 외부 작업 큐, 세션 중간 토큰 재개, 자동 최신 Brief 병합, 섹션별 stale, 전문 novelty 판정, 통계적 가설 검증, 정식 가용률·보안 인증·사용자 평가를 추가하지 않는다.
