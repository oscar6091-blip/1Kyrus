# 실제 구현 작업 계획

## 실행 원칙

Claude는 이 문서를 추가 계획의 주제가 아니라 **실행할 작업 목록**으로 사용한다. T01~T08 순서로 코드·실행·검사를 진행한다. 단계별 결과를 IMPLEMENTATION_STATUS.md에 적고 다음 작업으로 넘어간다.

SQLite·S1에서만 Brief 갱신·화면 이동만 수행하는 back·Markdown 출력은 `scope.json.prototype_baseline`에 명시한 프로토타입 전용 임시 설정으로 구현한다. 이 작업 목록은 해당 설정을 SSAD의 확정 사항으로 만들거나 SSRD·SSAD를 수정하는 작업을 포함하지 않는다.

날짜 배치는 권장 작업 순서이며 소요 시간을 보장하지 않는다.

| 날짜 | 우선 완료할 내용 |
| --- | --- |
| 11월 6일 | T01~T03: 설치·DB·승인/버전 규칙·API·오프라인 전체 흐름 |
| 11월 7일 | T04~T06: 화면 연결·live Gateway·arXiv·단계별 생성, 이어서 T07 |
| 11월 8일 | T07~T08: 깨끗한 재실행·시연·버그 수정·제출 정리. 새 기능 추가 중지 |

먼저 demo의 실제 저장·승인·입력 연결을 완성한다. 이 경로의 완성은 모델 품질 검증과는 구분한다. live는 같은 서비스와 계약을 사용하고 생성 공급자만 바꾼다.

source-completion 개정의 N-01~N-09 반영 범위는 `SOURCE_COVERAGE.md`를 따른다. 원본 문서와 배경 정보를 보존하고, 아래 작업에서 기존 API를 사용하는 이력·근거 열람 및 누락됐던 검증·표시를 보완한다. API 경로와 DB 테이블을 추가하지 않는다.

## T01 환경과 앱 골격

**산출 파일**:

- `frontend/package.json`, lockfile, `app/layout.tsx`, `app/page.tsx`, `app/globals.css`.
- `backend/requirements.in`, 실제 설치 버전을 고정한 requirements lockfile.
- `backend/app/main.py`, `config.py`, `db.py`, `models.py`.
- 저장소 루트 `README.md`, `.gitignore`. 기존 계획·fixture는 유지한다.

**구현**:

1. Next.js 16.4.5·TypeScript·App Router를 초기화한다. React는 이 버전과 호환되는 패치를 설치하고 lockfile로 고정한다. CSS로 기본 화면을 만든다.
2. Python 3.11 venv에 FastAPI/Pydantic2/SQLAlchemy2/Uvicorn/Anthropic1.x/HTTP 클라이언트/python-multipart/python-dotenv와 pytest를 설치한다. 서버에 scikit-learn·PyTorch를 넣지 않는다.
3. root `.env.example`을 backend가 읽을 `.env`로 복사하는 절차를 문서화한다. 필수 live 설정이 비어 있어도 demo 시작은 가능하다.
4. API prefix `/api`, CORS 로컬 origin, 표준 오류 응답 handler, `/health`를 만든다.
5. SQLite 경로를 생성하고 FK·WAL·busy timeout을 설정한다. SQLAlchemy 모델은 contracts/database.sql과 같은 관계·제약을 갖게 한다.
6. DB 초기화는 빈 파일에서도 동작하게 한다. Alembic·컨테이너·외부 DB를 도입하지 않는다.

**완료 확인**: API `/health`가 계약대로 응답하고 프런트에서 health를 읽는다. 실행 README에 기본 URL과 두 프로세스의 명령이 있다. 백엔드 기본 명령은 reload·다중 worker 없이 동작한다. AC-01, AC-20의 준비 단계다.

## T02 워크플로·저장·중복 처리

**산출 파일**:

- `backend/app/schemas/domain.py`, `schemas/artifacts.py`, `schemas/upload.py`.
- `backend/app/services/workflow.py`, `context.py`, `repository.py`.
- `backend/app/api/projects.py`, `stages.py`, `artifacts.py`.
- `backend/tests/test_workflow.py`, `test_versions.py`.

**구현 순서**:

1. Project 생성 시 mode를 환경에서 복사하고 Stage 6행을 pending으로 만든다.
2. 프로젝트 목록·상세, 단계 상세, 산출물 상세, Decision 목록을 계약 경로로 제공한다.
3. request_id별 fingerprint와 기존 응답 객체 참조를 저장한다. 재시도는 중복 검사 후 처리한다.
4. 편집은 payload를 검증하고 새 ArtifactVersion·edit Decision을 저장한다. evidence와 input_snapshot은 서버가 base에서 복사한다.
   S3 검증에는 모든 Brief 가설의 실험 대응과 Ablation 계획/해당 없음 사유를 포함한다. S5는 모든 H ID를 한 번씩 판정하고 선택 Run과 대응하지 않는 H ID는 inconclusive로 제한한다. 생성·편집·승인에서 같은 의미 검증을 사용한다.
5. 승인 트랜잭션에서 current/needs_review·선행 승인·입력 일치·기존 승인과 다른 새 초안 여부를 확인한다.
6. S1 승인만 current_brief 포인터를 바꾼다. S2~S6에서는 Brief를 갱신하지 않는다.
7. 상위 새 승인 시 하위의 결과가 있는 Stage를 stale로 표시한다. 결과 없는 Stage는 pending 유지. 과거 결과를 삭제하지 않는다.
8. back은 Decision 저장·이전 Stage 번호 반환만 구현한다. S1 back은 거부한다.
9. stale 결과 편집·승인을 차단하고 재생성을 안내한다.

**완료 확인**: 실제 SQLite 임시 파일을 사용해 AC-02~05, AC-14, AC-17을 검사한다. 편집·승인 횟수에 맞는 버전과 Decision 수를 DB에서 확인한다. CSS나 단순 getter를 검증하는 테스트를 늘리지 않는다.

## T03 비동기 demo·업로드·렌더링·내보내기

**산출 파일**:

- `backend/app/services/jobs.py`, `stage_runner.py`, `fixtures.py`, `rendering.py`, `exports.py`, `runs.py`.
- `backend/app/api/jobs.py`, `runs.py`, `exports.py`.
- `backend/tests/test_jobs.py`, `test_uploads.py`, `test_exports.py`.

**구현 순서**:

1. 실행 요청에서 입력 snapshot·Job·Stage running을 저장하고 커밋 뒤 executor에 Job ID를 제출한다.
2. 프로젝트별 active Job 1개를 DB 제약과 서비스 검사로 강제한다. 요청 중복 조회는 busy 검사보다 먼저다.
3. demo StageRunner는 `fixtures/stages/sN.json`을 읽고 같은 validation·저장 함수로 새 Artifact를 만든다. 프런트에 fixture를 직접 하드코딩하지 않는다.
4. S2 evidence는 references.snapshot, S5 evidence는 사용자가 선택한 실제 저장 Run, S6 evidence는 승인된 상위 snapshot에서 만든다.
5. S3 fixture가 가리키는 실험 ID·지표 이름과 동봉 업로드 파일이 일치하는지 검사한다.
6. 정상·오류 JSON 업로드와 client_upload_id 중복 처리를 구현한다.
   원문 A.II 예시의 무변환 수락은 구현하지 않는다. 추가 필수 필드의 422 위치를 제공하고 prototype_json_v1의 정상 예시를 안내한다.
7. metric/cite 토큰을 해당 Artifact evidence로 렌더링한다. ArtifactView에 계산된 rendered_markdown을 반환한다.
8. 승인된 S4 zip, 승인된 S6 Markdown, 허용된 BibTeX를 내보낸다. demo 표시는 ExportService가 붙인다.
9. 작업 성공·실패 때 DB 상태를 함께 갱신한다. 성공은 needs_review이며 자동 승인하지 않는다.
10. startup 때 queued/running을 interrupted로 바꾸고 Stage를 needs_review로 정리한다. 기존 Artifact는 유지한다.

**완료 확인**: API만으로 S1~S6를 생성·승인하고 valid JSON을 실제 업로드해 세 종류의 파일을 다운로드할 수 있다. AC-06~13, AC-16을 검사한다. 참조 수치가 동봉 원본과 정확히 일치하고, 과거 Artifact의 근거가 새 Run 때문에 바뀌지 않아야 한다.

## T04 공통 UI와 여섯 단계 화면

**산출 파일**:

- `frontend/app/projects/[id]/page.tsx`.
- `frontend/lib/api.ts`, `types.ts`.
- `frontend/components/ProjectList.tsx`, `StageSidebar.tsx`, `StageReview.tsx`, `BriefPanel.tsx`, `ArtifactEditor.tsx`, `RunUpload.tsx`, `CodeFiles.tsx`.

**구현**:

1. 프로젝트 목록·생성·재접속을 API에 연결한다.
2. 왼쪽 단계 상태, 가운데 검토 결과, 오른쪽 승인 Brief·입력 버전 목록을 배치한다.
3. 현재 단계·승인 버전·검토 필요·오래됨을 구분한다. 승인본이 남아 있더라도 상태가 stale이면 다음 실행을 막는 서버 오류를 그대로 반영한다.
4. S1 폼, S2·S3 Markdown 편집, S3 실험 목록 폼, S4 코드 편집, S5 업로드·지표 표, S6 섹션 편집을 구현한다.
5. 수정 저장과 승인 버튼을 분리한다. 재생성은 코멘트 입력 후 요청한다.
6. Job ID를 1초 간격 조회한다. 페이지 재접속 때 Project.active_job에서 다시 연결한다. busy 때 쓰기 버튼을 잠그되 화면 이동·조회는 유지한다.
7. 서버가 계산한 rendered_markdown으로 저장 후 미리보기를 제공한다. 지표·인용 참조를 유지해야 하는 이유를 짧게 안내한다.
8. mode 배지를 항상 보이고, demo에서 고정 시나리오를 사용한다는 안내를 유지한다.
9. BriefPanel에서 기존 Decision 목록의 S1 approve를 모아 버전·승인 시각을 표시한다. 기존 Artifact 조회로 과거 승인본을 읽기 전용으로 연다. 열람은 편집 중 내용·포인터·상태·Decision 수를 바꾸지 않는다. 전체 초안 탐색·diff·복원은 만들지 않는다.
10. StageReview에서 Rationale의 논문·Run 원본 행·Artifact 버전을 연다. 기존 API와 해당 버전 evidence를 사용한다. 빈 근거에는 ‘근거 없음: 사용자 확인 필요’를 표시하고 인용 제외 경고를 보여 준다. 사용자에게 내부 ID만 보여 주고 완료 처리하지 않는다.
11. 업로드 안내에 prototype_json_v1과 A.II의 차이 및 정상 예시를 제공한다. 원문 UI-01~UI-10의 유지·축소·제외는 SOURCE_COVERAGE.md를 참고하고 아직 없는 디자인을 확정하지 않는다.

**완료 확인**: 브라우저에서 README의 시연 절차를 처음부터 수행한다. AC-01~06, AC-09~13, AC-19의 실제 화면 조작을 확인한다. 승인 Brief 과거본·원본 근거를 열람해도 연구 상태가 바뀌지 않아야 한다. 원시 JSON 편집기가 기본 사용 화면이 되어서는 안 된다.

## T05 live Gateway와 내부 CitationVerifier

**산출 파일**:

- `backend/app/services/llm_gateway.py`, `references.py`.
- `backend/tests/test_gateway.py`, `test_references.py`.

**구현**:

1. Anthropic SDK 1.x를 한 모듈에서만 사용한다. `Anthropic(api_key=..., timeout=..., max_retries=0)`으로 SDK의 숨은 자동 재시도를 끈다.
   선택 설정 ANTHROPIC_WORKSPACE_ID가 있으면 SDK의 default_headers에 anthropic-workspace-id로 전달한다. anthropic-version 헤더는 임의로 덮어쓰지 않는다.
2. `client.messages.create(model=LLM_MODEL, max_tokens=..., system=..., messages=...)`로 요청한다. text block을 조합한 뒤 JSON 객체 하나를 읽는다.
3. 스키마·의미 검증 실패에 한해 오류와 허용 스키마로 보정을 한 번 요청한다. 네트워크 timeout·거절·토큰 잘림은 실패로 보고한다. 무한 루프를 만들지 않는다.
4. 각 실제 호출의 모델·토큰·시간·오류를 Job.usage에 합산한다. 단가 미설정 비용은 null이다. demo는 calls=0, 토큰·비용 null이다.
5. arXiv 검색어 JSON용 SearchQuery 스키마를 사용한다. 모델이 반환한 query를 URL params로 인코딩해 조회한다.
6. Atom을 파싱해 최대 3편의 ID·제목·저자·첫 제출 연도·초록을 가져온다. ID 조회 시 버전 접미사를 정규화한다.
7. 실제 메타데이터를 ReferenceSnapshot으로 만들고 모델에는 이 허용 목록만 제공한다. 결과가 없으면 명확히 실패한다.
8. 한 연결과 3초 간격을 적용한다. 외부 응답·API 오류를 fixture 성공으로 바꾸지 않는다.
9. 일부 인용 후보 제외 시 대상과 이유를 evidence.warnings에 저장한다. 전부 제외되면 오류 message/fields로 이유를 제공한다. warning을 검증된 참고문헌 목록으로 취급하지 않는다.
10. `LLM_DATA_POLICY.md`에 실제 사용할 제품·적용 조건·근거 문서·확인일 또는 확인 불가 상태를 기록한다. 초기 NOT_CHECKED를 근거 없이 PASS로 바꾸지 않는다. demo 시험과 live 기능 시험, 데이터 사용 조건 확인은 각각 구분한다.

**완료 확인**: AC-08, AC-15, AC-18을 FakeGateway·기록된 Atom 응답으로 오프라인 검사한다. 사용할 수 있는 키가 있으면 live 프로젝트에서 한 단계 이상의 실제 호출을 수행한다. 키가 없으면 live 미실행을 적고 나머지 작업을 계속한다.

## T06 단계별 live 생성과 근거 연결

**산출 파일**:

- `backend/app/stages/s1.py` ~ `s6.py`와 공통 context/schema helpers.
- `backend/tests/test_context_handoff.py`, `test_evidence.py`.

**구현**:

1. prompts/stage_prompts.md의 공통 지시와 해당 단계 계약만 전달한다. 원문 전체 SSRD/SSAD를 실행 프롬프트에 넣지 않는다.
   프롬프트용 schema는 해당 Stage 정의와 필요한 Rationale 정의를 함께 넣어 $ref가 미해결로 남지 않게 한다. SearchQuery는 별도 작은 schema다.
2. S1은 Brief와 질문, S2는 확인된 논문에 대한 본문, S3는 계획·experiments, S4는 외부 실행 파일, S5는 로그 해석, S6는 영어 여섯 섹션을 만든다.
3. 각 단계가 임의로 DB 상태를 바꾸거나 직접 승인하지 않도록 한다. 결과 반환 후 공통 JobRunner가 저장한다.
4. 입력 snapshot의 정확한 승인 ID를 사용하고, 재생성에는 직전 Artifact와 실제 코멘트를 넣는다.
5. S5는 선택 Run의 원본 값·경고를 사용한다. S6는 승인 S2·S5의 근거를 복사한다.
   S5의 다른 가설은 선택한 실험으로 미검증임을 표시한다. S6에 S2의 인용 제외 경고도 보존한다. 실험 설계의 ablation 계획과 실제 실행 여부를 혼동하지 않는다.
6. Unknown cite/metric/rationale ID는 모델이 만들어도 채택하지 않는다. 보정 한 번 후 계속 틀리면 실패한다.

**완료 확인**: AC-03, AC-10~11, AC-19를 recorder Gateway로 검사한다. 수정한 S3 내용이 S4의 실제 요청에 포함됐는지 로그 아닌 테스트 인자로 확인한다. 키가 있으면 live 여섯 단계를 수행해 출력 구조·실패 UX를 확인한다. scientific quality까지 검증했다고 보고하지 않는다.

## T07 제출 필수 검증

- acceptance.cases.json의 AC-01~20을 실제 구현과 대조한다.
- 우선 자동화할 것은 승인 차단·버전 보존·stale·중복 요청·업로드 오류·근거 렌더링·live 실패 경계다.
- 브라우저에서 프로젝트 생성부터 초안 다운로드까지 한 번은 실제 조작한다.
- `npm run build`와 백엔드 테스트를 통과시킨다. Next의 라우트 params 타입 오류도 이때 잡는다.
- 테스트가 안 된 항목은 PASS로 쓰지 않는다. live에 키가 없으면 NOT RUN으로 남긴다.
- 필요 이상의 UI snapshot 테스트나 모든 함수의 구현 복제 테스트를 추가하지 않는다.

**결과 문서**: IMPLEMENTATION_STATUS.md에 환경·명령·PASS/FAIL/NOT RUN·문제를 기록한다. 데이터가 같은지와 앱의 승인 규칙이 맞는지를 분리해 확인한다.

## T08 제출 정리

실제 코드 기준 README에 다음을 적는다.

1. 프로젝트 목적과 이번 범위.
2. 두 터미널의 정확한 설치·실행 명령, 기본 접속 주소.
3. demo와 live의 차이, 키·모델 설정 방법.
4. 동봉 결과 JSON의 위치와 5분 시연 순서.
5. 상위 계획 수정 → 하위 오래됨 → 재생성 시연 방법.
6. 서버 자동 실험·사용자 공유·LaTeX가 없다는 제한.
7. 실제 수행한 검사와 수행하지 않은 live/사용자 평가.

11월 8일에는 새 프레임워크나 기능을 추가하지 않는다. 핵심 흐름이 깨졌다면 화면 장식보다 승인·입력 버전·업로드·다운로드 복구를 우선한다.
