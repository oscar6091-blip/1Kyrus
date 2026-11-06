# 구현 상태

현재 상태 (2026-11-07 갱신): **T01~T08 구현 완료. demo 경로는 API 테스트와 헤드리스 브라우저 조작으로 확인. live는 Fake/Recorder Gateway로만 오프라인 검사했고 실제 API 키 호출은 NOT RUN.**

아래 문단은 배포한 계획팩의 초기 설명이다. 기존 작업 폴더에 구현이 있다면 현재 코드·검사 결과를 확인해 갱신하고 이어서 작업한다. source-completion 개정으로 원문 자료와 N-01~N-09 구현 지시를 보완했으며, 이것이 앱 구현 완료라는 뜻은 아니다. LLM 입력 데이터 조건의 확인 상태는 LLM_DATA_POLICY.md의 NOT_CHECKED에서 시작한다.

범위 설명: SQLite·S1에서만 Brief 갱신·화면 이동만 수행하는 back·Markdown 출력은 SSAD와 별도로 둔 프로토타입 전용 임시 baseline이다. 구현 상태 보고에서도 이를 SSAD의 확정 사항이나 설계 변경으로 표현하지 않는다. SSRD·SSAD 원본 수정은 이번 작업에 포함되지 않는다.

검사 환경: 개발 컨테이너 `jwpark_kyrus_dev` (Ubuntu 20.04), Python 3.11.13, Node 22.23.2, npm 10.9.8. 컨테이너는 개발용이며 앱 실행에는 필요 없다 (`DEVIATIONS.md` D-01). 명령은 저장소 루트 기준이다.

| 작업 | 상태 | 실제 실행 명령과 결과 |
| --- | --- | --- |
| T01 환경·골격 | DONE | `cd backend && .venv/bin/pip install -r requirements.lock`(uv로 고정), `npm ci`. `.venv/bin/python -m app` 기동 후 `GET /api/health` → `{"status":"ok","default_mode":"demo","live_configured":false}`. 프런트가 health를 읽어 모드 표시. DB는 `handoff/contracts/database.sql`을 그대로 실행해 생성 |
| T02 DB·워크플로 | DONE | `pytest tests/test_workflow.py tests/test_versions.py` PASS. 승인 게이트, 버전·Decision 수, stale 전파, back, request_id 중복, 작업 잠금, S3/S5 의미 검증 |
| T03 demo 실행·업로드·내보내기 | DONE | `pytest tests/test_smoke_flow.py tests/test_jobs.py tests/test_uploads.py tests/test_exports.py` PASS. API만으로 S1~S6 생성·승인, valid JSON 업로드, code.zip·paper.md·references.bib 다운로드. 참조 수치 4개가 `expected_reference_metrics.json`과 정확히 일치. zip의 train.py는 원본과 바이트 동일 |
| T04 공통 UI | DONE | `npm run build` PASS (Next.js 16.4.5, TypeScript). `scripts/browser_demo_check.py`로 헤드리스 Chromium에서 5분 시연과 변경 전파 시연 전 과정 PASS. 2026-11-07 UI/UX 기획안 v0.2 디자인 반영 후 `npm run typecheck`·`npm run build`·`browser_demo_check.py`(별도 demo 서버, 새 버튼 문구·Brief 탭 열기 반영) 다시 PASS |
| T05 live Gateway·arXiv | DONE (오프라인) | `pytest tests/test_gateway.py tests/test_references.py` PASS. timeout·거절·잘림·HTTP 오류는 failed로 끝나고 SDK 재시도 0회, 보정은 최대 1회, fixture 대체 없음. 기록된 Atom 응답으로 버전 접미사 정규화, 첫 제출 연도, 미검증 후보 경고, 0편 실패 확인. arXiv 실제 응답 형식은 컨테이너에서 한 번 조회해 확인. `LLM_DATA_POLICY.md`는 DOCUMENTS_REVIEWED |
| T06 단계별 live 생성 | DONE (오프라인) | `pytest tests/test_context_handoff.py tests/test_evidence.py` PASS. 수정·재승인한 S3 본문, 정확한 상위 ID, 코멘트가 S4 요청 인자에 들어감 (AC-03). S5는 서버 metric binding을 받음. 모델이 만든 미등록 cite는 채택하지 않음. 실제 키 live 실행은 NOT RUN |
| T07 필수 동작 검증 | DONE | `cd backend && .venv/bin/python -m pytest -q` → **49 passed**. `cd frontend && npm run build` → PASS. 브라우저 시연 PASS. AC별 결과는 아래 "앱 검사 결과". 2026-11-07 D-04(삭제)·D-05(생성 시 모드 선택) 추가 후 `ANTHROPIC_API_KEY= LLM_MODEL= .venv/bin/python -m pytest -q` → **56 passed**. 실제 키가 든 `.env` 그대로 돌리면 `test_health`가 live_configured=false를 기대해 실패한다(환경 차이, 코드 문제 아님). 브라우저 검사에 삭제 단계 추가, PASS |
| T08 제출 정리 | DONE | 루트 `README.md`(설치·실행·demo/live·5분 시연·변경 전파·제한·검사 결과), 이 문서, `LLM_DATA_POLICY.md`, `DEVIATIONS.md` 작성. 깨끗한 설치 재현 결과는 아래 "깨끗한 설치 재현" |

## 구현 선택

계획팩이 정하지 않아 구현하면서 정한 것을 기록한다(`handoff/CLAUDE.md` "범위 안의 일반적인 구현 선택은 스스로 해결하고 기록한다"). 계획과 다르게 한 것은 여기가 아니라 루트 `DEVIATIONS.md`에 적는다.

| 날짜 | 관련 T | 항목 | 선택 | 이유 |
| --- | --- | --- | --- | --- |
| 2026-11-07 | T01 | 백엔드 lockfile | `uv pip compile`로 만든 `backend/requirements.lock` (pip 형식) | pip만으로도 설치 가능하고 버전이 모두 고정됨 |
| 2026-11-07 | T01 | 경로 해석 | `.env`와 `DATABASE_URL`의 상대 경로를 저장소 루트 기준으로 해석 | 백엔드를 `backend/`에서 실행해도 "저장소 루트 `.env`"를 읽도록 |
| 2026-11-07 | T01 | DB 생성 | ORM `create_all` 대신 `handoff/contracts/database.sql`을 그대로 실행하고, ORM은 그 테이블에 매핑 | 계약 DDL과 관계·제약을 정확히 일치시키기 위해 |
| 2026-11-07 | T01 | 트랜잭션 | 모든 세션 트랜잭션을 `BEGIN IMMEDIATE`로 시작 (연결마다 FK·busy_timeout·WAL) | 두 요청이 같은 과거 상태로 승인하지 않도록 (architecture.md) |
| 2026-11-07 | T01 | 백엔드 실행 명령 | `python -m app` (uvicorn, reload 없음, worker 1)이 `.env`의 BACKEND_HOST/PORT 사용 | 한 줄 명령으로 계획의 실행 조건을 지키기 위해 |
| 2026-11-07 | T01 | 프런트 버전 | React 19.3.1, react-markdown 10.1.0, remark-gfm 4.0.1, TypeScript 5.9.3 고정 | TypeScript 7은 Next 빌드 타입 검사와의 호환을 확인하지 못해 5.x 사용 |
| 2026-11-07 | T04 | Next dev 허용 origin | `allowedDevOrigins: ["127.0.0.1","localhost"]`, dev/start는 `-H 127.0.0.1` | 계획의 주소 `http://127.0.0.1:3000`에서 Next 16 dev가 개발 리소스를 막아 화면이 hydration되지 않는 문제를 브라우저 검사에서 발견 |
| 2026-11-07 | T03 | demo 지연 | `DEMO_STAGE_DELAY_SECONDS`(기본 1.0초, `.env.example`에는 없음) | 1초 조회·재접속 동작이 화면에 보이도록. 테스트는 0초 |
| 2026-11-07 | T02 | S1 back 오류 | 422 `INVALID_PAYLOAD` | AC-17이 422를 요구하나 workflow.json에 해당 코드가 없어 422인 기존 코드 사용 |
| 2026-11-07 | T03 | 업로드 중복 재전송 응답 | 같은 client_upload_id·같은 내용이면 기존 Run을 201로 반환 | OpenAPI에 201만 정의됨 |
| 2026-11-07 | T03 | 업로드 내용 비교 | 파싱한 JSON을 키 정렬 직렬화한 SHA-256으로 비교 | 공백·키 순서만 다른 같은 내용을 중복으로 인식 |
| 2026-11-07 | T03 | S5 경고 | 업로드 `config.fit_warnings`, `config.interpretation_limit`, `synthetic_demo` 여부를 evidence.warnings로 복사 | 수렴 경고·한계를 숨기지 않기 위해 (stage_prompts S5) |
| 2026-11-07 | T03 | 수치 표기 | 원본 float를 `repr` 그대로 표시하고 단위를 괄호·별도 열로 표시 | 0.9666…을 97%로 바꾸지 않기 위해 |
| 2026-11-07 | T03 | 생성 실패 후 상태 | failed/interrupted 작업 뒤 Stage는 workflow.json대로 needs_review. 이전 승인본과 current가 같으면 승인 불가이며 재생성 필요 | 계약 그대로. 기존 승인본을 새 결과처럼 승인하지 않음 |
| 2026-11-07 | T05 | arXiv 검색어 | 모델 검색어에서 영문 키워드 최대 5개를 `all:` AND로 결합, 결과 최대 5개 중 확인된 3편 채택, https 엔드포인트 | arXiv API 문법. http는 리다이렉트되어 https 사용 |
| 2026-11-07 | T05 | 프롬프트 출처 | system·단계·보정 지시를 런타임에 `handoff/prompts/stage_prompts.md`에서, 출력 schema를 `artifacts.schema.json`에서($ref 인라인) 읽음 | 계획 문서와 앱의 프롬프트를 한 곳에서 관리 |
| 2026-11-07 | T07 | 브라우저 검사 도구 | `scripts/browser_demo_check.py` (Playwright 1.49.1, 앱 의존성 아님) | 실제 화면 조작 확인용. Ubuntu 20.04에서 동작하는 마지막 계열 |
| 2026-11-07 | T04 | UI/UX 기획안 v0.2 반영 (배치·스타일만) | 기획안 디자인 캔버스(`docs/uiux/UIUX_v0.2_canvas.html`)의 Sidebar·CheckpointBar 컴포넌트와 UI-01·UI-04·UI-08 목업 값을 따름: 배경 `#F7F7F8`, 테두리 없는 흰 카드 24px, 안쪽 카드 18px(`#F2F2F5`·`#F5F6FF`), 알약 버튼(radius 69, 46/50px), 인디고 `#5661F6`, 검정 표 머리행, 상태 표기(승인 검정·검토 필요 인디고 점·대기 빈 원·오래됨 점선). 화면 구조: 왼쪽 사이드바 카드(R2P+, 새 프로젝트, 내 프로젝트, 연구 단계), 단계 헤더(참조한 승인본 버전), 산출물 왼쪽·결정 근거 카드 오른쪽, 아래 고정 알약 결정 바, Research Brief는 오른쪽 끝 탭으로 여닫는 패널(현재 Brief/변경 이력), 대시보드는 프로젝트 카드와 6단계 막대 | `handoff/CLAUDE.md`가 기획안 도착 후 배치·스타일 조정을 허용. API·승인 조건·버전 규칙은 그대로라 DEVIATIONS 대상 아님. 대시보드 단계 막대는 기존 `GET /projects/{id}`를 프로젝트마다 호출 |
| 2026-11-07 | T04 | 오래됨 원인 표시 | 결과의 `input_snapshot.upstream_artifact_ids`와 상위 단계의 현재 승인본을 비교해 "S3 실험 설계 승인본이 v2 → v3로 바뀌었습니다"처럼 표시. 기존 API(`GET artifact`)만 사용 | 기획안 UI-08 "상위 변경 영향"(RQ-10)을 서버 변경 없이 보여 주기 위해 |
| 2026-11-07 | T04 | S5 가설 판정 카드, 경고 상자 | `hypothesis_verdicts`를 지지/부분 지지/기각/판단 보류 배지 카드로, `evidence.warnings`를 본문 위 경고 상자로 표시 (본문 Markdown은 그대로) | 기획안 UI-06 ②(ONRQ-5), UI-03 미검증 인용(ONRQ-1) 표시 방식 |
| 2026-11-07 | T04 | 폰트 | Pretendard(본문)·Outfit(로고·단계 코드)·JetBrains Mono(버전·코드)를 `frontend/public/fonts/`에 직접 포함 (기획안 캔버스에 들어 있던 파일, SIL OFL 1.1, 라이선스 원문 동봉) | 기획안 폰트를 오프라인 localhost에서도 같게 보이도록. 외부 CDN 의존 없음 |
| 2026-11-07 | T04 | 화면 문구 | 상태 "승인됨"→"승인", "생성 중"→"진행 중", 버튼 "코멘트로 재생성"→"재생성 요청" (기획안 표기). Research Brief 패널은 기본 접힘, 여닫은 상태는 브라우저 localStorage에만 저장 | 기획안 p.07 상태 표기와 CheckpointBar 문구. `scripts/browser_demo_check.py`와 README 시연 문구도 같이 바꿈 |

## 계획 자료 검사

검사일: 2026-11-07. 이 절은 계획 자료와 동봉 참조 실행의 기록이며 웹 앱의 완료 판정과 구분한다.

계획팩 폴더에서 다음 명령을 실행한다. 결과는 PASS다.

```bash
python scripts/check_handoff.py
```

- 첨부 SSRD·SSAD와 동봉 사본의 SHA-256 일치.
- SSRD DOCX XML과 요구사항 55개·필드 478개 직접 대조 일치. 공란 26개 보존.
- 부분 구현 36개·보류 19개가 요구사항 ID 전체를 중복 없이 나누며 선택 항목이 AC에 연결됨.
- 요구사항 표 밖 본문·일반 표 110개 블록, UI 정의 10개, 미검증 고객 가정 7개, A.II 규격 8개 필드·예시 보존.
- N-01~N-09 보완 항목과 실제 파일·기존 AC의 연결 확인.
- 여섯 단계 fixture의 스키마, 가설 대응·Ablation 계획, 지표·인용·이유의 근거 ID 연결 확인.
- 정상 업로드 수락·잘못된 업로드 거부와 원문 A.II 예시의 추가 필수 필드 세 곳 거부 확인. 원문 무변환 호환은 지원하지 않음.
- OpenAPI operation 16개와 로컬 schema 참조, S6 여섯 섹션 순서 확인.
- SQLite 여섯 테이블 생성과 프로젝트당 active Job 한 개 제약 확인.
- 참조 train.py의 SHA-256과 실측 JSON의 code_version 일치. S4 코드 fixture가 참조 코드와 동일하고 문법 검사 통과.

동봉 checker는 이 팩에서 사용하는 JSON Schema 키워드를 검사하는 표준 라이브러리 도구다. 범용 Draft 2020-12 인증 도구나 실제 앱 테스트는 아니다. 앱에서는 Pydantic과 서버 의미 검증을 함께 구현한다.

## 동봉한 실측 자료

작성자가 `reference_experiment/train.py`를 CPU에서 실행해 `fixtures/experiment_result.valid.json`을 만들었다. 정확한 실행 시각·환경·시간은 해당 JSON에 있다.

- Iris의 계층화 split·학습 데이터에만 fit한 전처리·고정 seed·작은 MLP를 사용했다.
- SGD·Adam의 accuracy와 macro F1, 총 네 측정값을 기록했다. 두 accuracy는 같았다.
- 두 학습의 최대 iteration 도달 수렴 경고를 config.fit_warnings에 보존했다.
- 단일 실행으로 통계적 우위나 재현성 목표 달성을 주장하지 않는다. 이 측정이 웹 앱의 구현·시험을 뜻하지도 않는다.

## 앱 검사 결과 (AC-01~20)

검사일 2026-11-07. "자동"은 `backend/tests`의 pytest이고, "브라우저"는 `scripts/browser_demo_check.py`(헤드리스 Chromium, 실제 Next·FastAPI 서버)다.

| AC | 결과 | 근거 |
| --- | --- | --- |
| AC-01 오프라인 시작 | PASS | 키 없이 demo 기동·프로젝트 생성·목록·선택 (브라우저). demo 표시가 화면·zip·paper.md·bib에 있음 (자동·브라우저) |
| AC-02 승인 전 차단 | PASS | S1 미승인 시 S2 run 409 PREDECESSOR_NOT_APPROVED (자동), 버튼 잠김 (브라우저) |
| AC-03 입력 연결 | PASS | Recorder Gateway 인자에 새 S3 본문·S3 artifact ID·코멘트 포함 (자동) |
| AC-04 편집과 승인 분리 | PASS | 편집은 새 버전과 edit Decision만 남김. 두 번 승인한 S1을 Decision 목록으로 열람해도 상태·Decision 수가 그대로 (자동). 이력 모달 읽기 전용 (브라우저) |
| AC-05 변경 전파 | PASS | S3 새 승인 → S4~S6만 stale, 과거 포인터 보존, S4 재승인 전 S5 거부 (자동·브라우저) |
| AC-06 재접속 보존 | PASS (API) | 지연 작업 중 project 상세 재조회 시 같은 active_job, 결과 1개 (자동). UI는 재접속 때 active_job으로 다시 조회하도록 구현. 브라우저 창을 닫았다 여는 조작은 수행하지 않음 |
| AC-07 서버 재시작 | PASS | running Job을 만든 뒤 startup 복구 → interrupted·needs_review·승인본 보존·수동 재시도 성공 (자동). 실제 프로세스 kill 재시작은 수행하지 않음 |
| AC-08 인용 경계 | PASS (오프라인) | 미등록 cite 채택 거부, 0편이면 NO_VERIFIED_REFERENCES와 사유, 일부 제외 경고가 S2→S6에 보존, live 실패에 fixture 대체 없음 (자동) |
| AC-09 실험 업로드 | PASS | valid 수락. invalid·NaN·Infinity·중복 키·문자열 수치·bool seed·중복 metric·미등록 E ID·필수 지표 누락·범위 위반·타 프로젝트 Run 거부. 원문 A.II 예시 422 (schema_version, data_origin, metrics.0.unit)와 정상 예시 안내 (자동) |
| AC-10 실측 값 분석 | PASS | 네 값 원본 일치, 같은 accuracy·수렴 경고 유지, H 판정 누락·중복·미등록 거부 (자동·브라우저) |
| AC-11 지표 토큰 | PASS | 표·토큰은 Artifact evidence로 렌더링, 미등록 토큰 422, 새 업로드 뒤에도 과거 초안·paper.md 불변 (자동) |
| AC-12 코드 내보내기 | PASS | zip 정상, `../../escape.py`·절대경로·역슬래시·.env·NUL 거부, 앱 코드에 실행 경로 없음 (자동). 브라우저에서 zip 다운로드 |
| AC-13 초안 내보내기 | PASS | 여섯 섹션·참고문헌·지표 표·demo 표식이 있는 paper.md와 references.bib (자동·브라우저) |
| AC-14 중복 요청 | PASS | run·approve·edit·regenerate 재전송 시 같은 결과, 다른 내용이면 409 (자동) |
| AC-15 LLM Gateway | PASS (오프라인) / live NOT RUN | 모든 live 호출이 `llm_gateway.py` 하나만 거침 (anthropic import 1곳), timeout·거절·잘림·HTTP 오류 failed, 보정 1회 상한 (Fake client) |
| AC-16 작업 잠금 | PASS | 작업 중 같은 프로젝트 쓰기 409, 조회·다른 프로젝트 가능, 종료 후 해제 (자동) |
| AC-17 이전 단계 이동 | PASS | back Decision과 navigate만, 상태 불변, S1 back 422 (자동) |
| AC-18 사용량 | PASS (오프라인) / live NOT RUN | 토큰·호출 수·비용(단가 있을 때만)·모델 기록, demo calls=0·null (자동). LLM 데이터 조건은 DOCUMENTS_REVIEWED이며 계정 조건은 미확인 |
| AC-19 계획·이유 | PASS | S3 가설 누락·중복·미등록 H·Ablation 누락 거부, 모르는 근거 ID 거부 (자동). 근거 칩으로 논문·지표 원본 행·버전 열람, 빈 근거에 "근거 없음: 사용자 확인 필요" 표시 (UI 구현, 브라우저에서는 이력 모달만 조작) |
| AC-20 제출 재현 | PASS | lockfile 두 개, `.env.example`, README, 이 문서. Docker/Redis/DB 서버 없이 실행 |

## 깨끗한 설치 재현

2026-11-07에 커밋된 제출물을 `git archive HEAD`로 빈 폴더(`/tmp/fresh`)에 풀고, 루트 README 명령 그대로 실행했다. uv는 쓰지 않고 표준 `venv`와 `pip`를 사용했다.

| 단계 | 명령 | 결과 |
| --- | --- | --- |
| 제출물 구성 | `git archive HEAD` | `dockerfile_1Kyrus/`가 빠짐 (`.gitattributes` export-ignore). `.env`·`.venv`·`node_modules`·`data/`도 들어가지 않음 |
| 환경 파일 | `cp handoff/.env.example .env` | PASS |
| 백엔드 설치·테스트 | `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.lock && .venv/bin/python -m pytest -q` | **49 passed** |
| 프런트 설치·빌드 | `npm ci && npm run build` | PASS (Compiled, TypeScript 통과) |
| 계획 자료 검사 | `python3.11 handoff/scripts/check_handoff.py` | PASS |
| 기동 | `BACKEND_PORT=8100 .venv/bin/python -m app` → `GET /api/health` | `{"status":"ok","default_mode":"demo","live_configured":false}`. reload 없이 1 프로세스. `data/prototype.db` 자동 생성 |

이 검사에서 결함 하나를 찾아 고쳤다. `.gitignore`의 `data/` 규칙이 `backend/tests/data/`까지 제외해서, 기록된 arXiv 응답이 커밋에서 빠져 있었다. 첫 재현 시도에서 pytest 수집 오류가 났고, 규칙을 `/data/`로 고친 뒤 위 결과를 얻었다.

## 아직 수행하지 않은 확인

- 실제 API 키로 하는 live 생성(여섯 단계), 실제 arXiv 조회를 거친 S2 생성. 키가 없어 NOT RUN.
- LLM 입력 데이터 사용 조건의 실제 계정 적용 여부. 공식 문서 검토까지만 했다 (`LLM_DATA_POLICY.md`).
- 브라우저 창을 닫았다 다시 여는 AC-06 조작, 실제 프로세스를 죽이는 AC-07 재시작.
- 사람이 직접 하는 브라우저 시연. 자동화한 헤드리스 조작만 수행했다.
- SUS·고객 평가·가용률·기관용 보안·모든 자유 서술 수치의 정확성 평가.

## live 검사

NOT RUN. 사용 가능한 API 키가 없다. live 경로의 동작은 Fake/Recorder Gateway와 기록된 arXiv 응답으로만 오프라인 검사했으며, 이것을 실제 모델 품질이나 검색 성능 검증으로 보고하지 않는다. 키가 생기면 `.env`에 `APP_MODE=live`, `ANTHROPIC_API_KEY`, `LLM_MODEL`을 넣고 새 프로젝트에서 실행해 결과(모델명, 단계, PASS/FAIL)를 여기에 적는다. 키 값은 적지 않는다.
