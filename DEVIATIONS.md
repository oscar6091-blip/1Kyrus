# 계획팩과 다르게 한 것

계획팩(`handoff/`)은 원본 그대로 둔다. 계획팩과 다르게 하는 일은 여기에만 기록한다.
번호는 바꾸지 않고 계속 이어서 붙인다. 취소한 항목은 지우지 않고 상태를 `철회`로 바꾼다.

**항목 형식**

```
## D-NN 제목
- 날짜:
- 원문 위치: handoff/<파일> <절 또는 줄>
- 원래 내용:
- 바꾼 내용:
- 이유:
- 영향: 제출물 / 관련 AC / 관련 T 작업
- 상태: 적용 | 철회
```

---

## D-01 개발은 Docker 컨테이너에서 한다
- 날짜: 2026-11-07
- 원문 위치: `handoff/CLAUDE.md` "환경과 실행 방식", `handoff/implementation_plan.md` T01 6항("컨테이너를 도입하지 않는다")
- 원래 내용: Node 22 이상과 Python 3.11 venv로 로컬에서 개발하고 실행한다. 컨테이너는 도입하지 않는다.
- 바꾼 내용: 개발할 때만 `dockerfile_1Kyrus/`의 컨테이너 `jwpark_kyrus_dev`(Ubuntu 20.04, Node 22.23.2, uv로 설치한 Python 3.11) 안에서 venv와 npm을 쓴다. 앱 코드와 제출 README는 Docker에 의존하지 않는다.
- 이유: 호스트에 Node가 없고 Python이 3.8이다. 연구실 공용 서버라 시스템에 직접 설치하지 않는다. 베이스 이미지를 고른 이유는 `dockerfile_1Kyrus/README.md`에 있다.
- 영향: 제출물에는 영향 없음. 제출할 때 `dockerfile_1Kyrus/`를 뺀다. T01 6항은 앱이 컨테이너를 필요로 하지 않는다는 뜻으로 읽고 그대로 지킨다.
- 상태: 적용

## D-02 계획팩을 `handoff/` 하위 폴더로 옮겼다
- 날짜: 2026-11-07
- 원문 위치: `handoff/CLAUDE.md` "기존 작업 폴더에 넣을 때"
- 원래 내용: 계획팩 전체를 프로젝트 루트에 두는 것을 기본으로 경로를 쓴다. 하위 폴더에 두면 경로에 접두어를 붙이라고 허용한다.
- 바꾼 내용: 팩 41개 파일(manifest 포함)을 내부 구조를 바꾸지 않고 `handoff/`로 옮겼다. 앱 파일과 `.env`는 루트에 둔다. 앱 코드는 fixtures와 prompts를 `handoff/fixtures/`, `handoff/prompts/`에서 읽고, `.env`는 `cp handoff/.env.example .env`로 만든다. 루트 `CLAUDE.md`에 경로 규칙을 적었다.
- 이유: 원본과 우리가 만든 파일을 폴더 단위로 나누기 위해서다.
- 확인: 옮기기 전과 후 모두 SHA-256 40개가 일치하고 `handoff/scripts/check_handoff.py`가 exit 0으로 끝났다. git 첫 커밋 `3c61cdd`가 옮기기 전 원본이다.
- 영향: 제출물의 폴더 구조가 달라진다. 제출 README에 `handoff/` 위치를 적는다. 관련 T 작업: T01(.env 복사 절차), T03(fixtures 경로), T06(prompts 경로).
- 상태: 적용

## D-03 계약 목록에 없는 오류 코드 세 개를 추가했다
- 날짜: 2026-11-07
- 원문 위치: `handoff/contracts/workflow.json` `error_http`, `async_error_codes`
- 원래 내용: 동기 오류 코드 12개와 비동기 오류 코드 8개(LLM_TIMEOUT, LLM_REFUSAL, LLM_TRUNCATED 등)를 나열한다.
- 바꾼 내용: 목록에 맞는 코드가 없는 경우에만 다음 세 코드를 쓴다. 오류 응답 형식 `{error:{code,message,fields,retryable}}`은 그대로다.
  - `LLM_API_ERROR`: 모델 API가 401·429·5xx 같은 HTTP 오류를 반환한 경우. 비동기 Job 오류다.
  - `INTERNAL_ERROR`: 예상하지 못한 서버 예외. 500이다.
  - `HTTP_ERROR`: 404가 아닌 프레임워크 HTTP 예외(예: 405).
- 이유: HTTP 상태 오류를 `LLM_REFUSAL`(모델의 거절)이나 `LLM_TIMEOUT`으로 기록하면 원인을 잘못 알리게 된다.
- 영향: 응답 스키마(code는 문자열)는 바뀌지 않는다. AC-15의 failed 처리와 보정 상한도 그대로다.
- 상태: 적용

## D-04 프로젝트 삭제 기능을 추가했다
- 날짜: 2026-11-07
- 원문 위치: `handoff/contracts/api.openapi.json` paths (`/projects`에 DELETE 없음), `handoff/scope.json` deferred LOR-7 ("7일 백업 삭제는 제외")
- 원래 내용: 프로젝트를 만들고 조회만 한다. 삭제 API와 화면이 없다.
- 바꾼 내용: `DELETE /api/projects/{id}` (성공 204, 없으면 404 `NOT_FOUND`, 작업이 queued/running이면 409 `PROJECT_BUSY`). 한 트랜잭션에서 Brief·단계 포인터를 비운 뒤 그 프로젝트의 decisions, jobs, artifact_versions, experiment_runs, stages, projects 행을 지운다. 다른 프로젝트는 건드리지 않는다. 커밋 직후 `VACUUM`과 `PRAGMA wal_checkpoint(TRUNCATE)`를 실행해, 지운 내용이 DB 파일의 빈 페이지나 `-wal` 파일에 남지 않게 한다(`backend/app/db.py` `compact()`). 이 정리가 실패해도(예: 5초 넘게 DB 잠김) 삭제는 유지하고 경고 로그만 남긴다. 대시보드 프로젝트 카드에 "삭제" 버튼과 확인 창을 두었다. 오류 응답 형식과 기존 오류 코드는 그대로 쓴다.
- 이유: 사용자 지시. 시연·연습용 프로젝트가 같은 DB에 쌓여 정리할 방법이 필요했다. 스키마에 ON DELETE CASCADE가 없어 서비스에서 순서대로 지운다(`database.sql`은 바꾸지 않음).
- 영향: 계약 OpenAPI에 없는 경로 하나가 늘었다. 기존 API·테이블·승인 규칙은 그대로다. LOR-7의 7일 백업 삭제·기관용 삭제 절차를 구현한 것은 아니다(로컬 SQLite에서 즉시 삭제하고 파일을 다시 쓴다. 이미 내려받은 파일이나 백업은 대상이 아님). 테스트 `backend/tests/test_projects_manage.py`(행 삭제, 파일 바이트에 지운 글자가 남지 않음, 정리 실패 시에도 삭제 유지), 브라우저 검사 마지막 단계. 관련 T: T02, T04.
- 상태: 적용

## D-05 프로젝트를 만들 때 demo/live를 고를 수 있게 했다 (임시)
- 날짜: 2026-11-07
- 원문 위치: `handoff/CLAUDE.md` "구현하면서 유지할 구분"(프로젝트 mode는 생성 때 고정), `handoff/contracts/domain.schema.json` `ProjectCreate`(name, idea만), `handoff/implementation_plan.md` T01 (mode는 `APP_MODE`)
- 원래 내용: 새 프로젝트의 mode는 서버 `.env`의 `APP_MODE`로 정해진다. 생성 요청에는 mode가 없다.
- 바꾼 내용: `POST /api/projects`에 선택 필드 `mode`("demo" | "live")를 받는다. 생략하면 지금처럼 `APP_MODE`를 쓴다. 사용자가 **직접 live를 고른** 경우에만 서버에 API 키·모델 설정이 없으면 503 `LIVE_NOT_CONFIGURED`로 생성을 거부한다(생략 + `APP_MODE=live`일 때는 원래 계약대로 생성되고 실행 시 503). 만든 뒤에는 바꿀 수 없다는 규칙과 demo/live 동작 규칙(`scope.json` mode_rules)은 그대로다. 생성 화면에 demo/live 선택을 두었고, live 설정이 없으면 live를 고를 수 없다.
- 이유: 사용자 지시(임시). 서버를 재시작하지 않고 같은 서버에서 demo 연습과 live 시연을 함께 하기 위해서다.
- 영향: 요청 스키마에 선택 필드 하나가 늘었다. 응답 형식은 같다. 기존 클라이언트(필드 생략)는 영향 없음. 테스트 `backend/tests/test_projects_manage.py`. 관련 T: T01, T04.
- 상태: 적용

## D-06 live 단계 프롬프트를 루트 `prompts/`의 사본에서 읽는다
- 날짜: 2026-11-08
- 원문 위치: `handoff/prompts/stage_prompts.md` S3·S4·S5·S6 절, `backend/app/config.py` `PROMPTS_FILE`
- 원래 내용: 앱이 `handoff/prompts/stage_prompts.md`를 직접 읽는다. S3는 실험 설계만 쓰고 방법론 지시가 없다. S4는 결과 형식을 파일 이름(`contracts/upload.schema.json`)으로만 가리키고 내용은 모델에 주지 않는다.
- 바꾼 내용: 루트 `prompts/stage_prompts.md`가 있으면 그것을 읽고, 없으면 원본을 읽는다(`handoff/`는 수정 금지라 사본을 둠). 사본에서 바꾼 점: S3 body_md를 `## 방법론`(아이디어에서 방법론으로, 전체 구조, 구성 요소, 기존 방법과의 차이, 구현 방식) 절로 시작하게 함. S4에 결과 run 형식(최상위 필드, metrics 다섯 키, unit 선택 기준, run당 지표 100개 이내)과 예시, 실험별 결과 파일과 묶음 파일 저장을 직접 적음. S5에 여러 Run일 때 `## E<n>` 절과 `## 전체 요약` 작성 지시를 추가. S6 methods가 S3 방법론에 근거하도록 함. 공통 입력 목록에 `selected_experiment_runs` 추가.
- 이유: live 실행 시험에서 확인한 문제. S3에 핵심 방법론 설명이 없었다(SSRD RQ-3 제목·설명은 "방법론 및 실험 설계"). S4 코드가 서버가 받지 않는 결과 형식(임의 최상위 필드), 범위를 벗어난 ratio 단위, 100개를 넘는 지표를 만들어 업로드가 422로 거부됐다.
- 영향: demo 결과(fixtures)와 API는 바뀌지 않는다. live 결과 내용만 달라진다. 관련 문서: SSRD RQ-3, A.II.
- 추가 변경: 같은 날 live 시험 후 루트 사본의 S1·S3 절을 다시 고쳤다. D-09 참고.
- 상태: 적용

## D-07 실험 여러 개의 결과를 한 번에 올리고 S5에서 함께 분석한다
- 날짜: 2026-11-08
- 원문 위치: `handoff/contracts/upload.schema.json`(run 하나), `handoff/contracts/domain.schema.json` `RunRequest`·`DecisionRequest`(`run_id` 하나), `handoff/implementation_plan.md` S5 "선택 Run 하나"
- 원래 내용: 업로드 파일 하나 = Run 하나. S5는 Run 하나만 분석하고, 그 실험에 대응하지 않는 가설은 inconclusive로 남는다.
- 바꾼 내용:
  - 업로드: 기존 단일 run 파일에 더해 묶음 파일 `{"schema_version": "1.1", "runs": [run, ...]}`(최대 10개, 같은 실험 ID 중복 금지)을 받는다. 각 run은 기존 규칙으로 검사하고 실험마다 ExperimentRun 한 줄로 저장한다. 하나라도 틀리면 아무것도 저장하지 않고 오류 위치를 `runs.<i>.…`로 알려 준다. 응답은 단일 파일이면 기존과 같고, 묶음이면 `{"bundle": true, "runs": [...]}`.
  - S5 실행·재생성: 선택 필드 `run_ids`(최대 10개, 실험당 하나)를 받는다. 없으면 기존 `run_id`를 쓴다. snapshot에 `run_ids`를 저장하고 `run_id`에는 첫 번째를 남긴다.
  - 근거 ID: Run이 하나면 기존처럼 `m0, m1, …`, 여러 개면 `E1.m0, E2.m0, …`이고 binding에 `experiment_id`가 붙는다. 경고 앞에 `[E1]`을 붙인다. 판정 가능한 가설은 선택한 모든 실험의 가설 합집합이다.
  - 검증: Run이 여러 개면 S5 body_md에 실험마다 `## E<n>` 절이 있어야 한다.
  - 화면: S5에서 실험별로 Run을 고른다(기본값은 실험별 최신 Run). S5 결과가 `## E<n>` 절을 가지면 "전체 요약 / E1 / E2 …" 탭으로 나눠 보여 주고, 실험 탭에는 그 실험의 지표 표를 함께 보인다. 원본 지표 표에 실험 열이 생긴다. S6은 S5 근거를 그대로 쓰므로 모든 실험 지표를 받는다.
- 이유: live 시험에서 S3가 실험 E1~E5를 만들었고 S4 코드가 실험별 결과 파일 5개를 만들었는데, S5가 그중 하나만 분석해 나머지 가설이 inconclusive가 됐다. SSRD RQ-5("설계서의 모든 실험이 기록된다")·RQ-6("가설–실험 대응표에 따라 결과를 정리한다")에 맞춘다.
- 영향: 기존 단일 run 업로드, demo 흐름, 기존 테스트 57개는 그대로 통과한다. 새 테스트 `backend/tests/test_multi_runs.py`(5개). DB 스키마는 바뀌지 않는다. 계약 JSON 파일(`handoff/contracts/`)은 고치지 않았으므로 묶음 형식과 `run_ids`는 이 항목이 기준이다.
- 상태: 적용

## D-08 모델 입력 상한을 150,000자로 올리고, S5·S6 입력에서 큰 데이터를 뺀다
- 날짜: 2026-11-08
- 원문 위치: `handoff/architecture.md` 106행(모델 입력이 80,000자를 넘으면 `CONTEXT_TOO_LARGE`), `backend/app/services/context.py` `MAX_MODEL_INPUT_CHARS`
- 원래 내용: 구성한 모델 입력이 80,000자를 넘으면 `CONTEXT_TOO_LARGE`로 실패한다.
- 바꾼 내용:
  - 상한을 150,000자로 올렸다. 넘으면 실패하는 동작과 오류 코드는 그대로다. 자동 요약·RAG는 여전히 만들지 않는다.
  - 모델에 보내는 입력에서만 다음을 줄인다(저장된 결과·Run·근거는 그대로). S5·S6에서는 승인 S4의 `files[].content`를 빼고 경로와 글자 수만 보낸다. 업로드 Run의 `config` 값 중 JSON 2,000자를 넘는 값(seed별 원값, step 표 등)은 "생략: N자" 문구로 바꾼다. Run이 여러 개면 `selected_experiment_runs`의 `metrics`를 빼고 `metric_bindings`를 보라는 문구로 바꾼다(같은 값이 binding에 이미 있다).
- 이유: live 시험에서 S4 재생성이 85,549자로 실패했다. 재생성 입력에 이전 S4 결과(실행 코드 포함 약 43,000자)가 들어가고, D-06으로 S3에 방법론 절이 생겨 상위 결과도 커졌다. 사용자 코멘트는 한 단어라 사용자가 줄일 방법이 없었다. 이어서 S5에 Run 5개를 넣자 233,608자가 됐다. S5가 쓰지 않는 S4 코드(약 37,000자), binding과 중복된 metrics(약 26,000자), config의 step 표(약 47,000자)가 대부분이었다. 줄인 뒤 같은 입력은 120,846자다. 설정 모델의 컨텍스트 창 안에 충분히 들어가는 크기다(이전 S4 실행 입력 49,517토큰).
- 영향: 요청 한 번의 입력 토큰과 비용이 커질 수 있다. API와 demo 흐름은 바뀌지 않는다.
- 상태: 적용

## D-09 S1 확인 질문 범위와 S3 분량 규칙을 프롬프트에 넣었다
- 날짜: 2026-11-08
- 원문 위치: `handoff/prompts/stage_prompts.md` S1·S3 절 (앱은 D-06에 따라 루트 `prompts/stage_prompts.md`를 읽음)
- 원래 내용: S1은 "불확실한 점은 최대 3개 clarification_questions로 질문한다"만 있고, 언제 멈출지와 무엇까지 물을지 기준이 없다. S3(D-06 사본)는 `## 방법론` 하위 절 다섯 개와 SVG 그림을 요구하지만 분량 제한이 없다. 사본에는 원래 S3 지시 목록과 D-06의 새 목록이 함께 들어 있어 "body_md에는 가설–실험 대응…을 설명한다"와 "body_md는 `## 방법론` 절로 시작한다"가 겹쳤다.
- 바꾼 내용:
  - S1: 확인 질문은 답에 따라 연구 문제·가설·평가 범위가 바뀌는 것만 묻는다. 모델 구조, 성분 수, 하이퍼파라미터 값, 노이즈 크기, seed 수 같은 실험 세부는 S3로 넘긴다. 이미 답한 것은 다시 묻지 않고, 더 물을 것이 없으면 빈 배열로 둔다. 평가 계획은 지표, 비교의 성격, 가설별 판정 기준과 범위까지만 쓴다. 각 가설에는 지지·기각을 가를 방향과 기준을 쓴다.
  - S3: 겹쳐 있던 원래 지시 목록을 지우고 D-06의 새 목록만 남겼다. `### 전체 구조`의 따옴표 오타를 고쳤다. 분량 규칙을 추가했다. body_md는 10,000자 이내(계약 상한은 20,000자)로 쓰되 수식, 하이퍼파라미터 값, 모듈 이름, 지표 이름은 줄이지 않는다. Brief의 가설·조건은 H ID로만 가리킨다. 구성 요소와 실험 설계는 표로 쓰고 실험은 가능하면 세 개 이하로 묶는다. SVG는 상자와 화살표 12개 이내, rationale은 5개 이내다.
  - S3의 SVG 그림은 화면에서 그림으로 표시한다. 표시만 바뀌므로 `handoff/IMPLEMENTATION_STATUS.md` "구현 선택"에 기록했다.
- 이유: live 시험(INR 외삽 주제)에서 확인한 문제다. S1은 재생성할 때마다 질문 3개를 채우며 점점 S3 세부를 물었고, Brief 평가 계획에 모델 목록·seed 수가 들어갔다(재생성별 Brief 1,970 → 2,655 → 3,564 → 2,815자). "어느 쪽인지 실험 전에 가정하지 않는다"처럼 어떤 결과도 지지되는 가설이 나와 S5에서 판정할 수 없었다. S3는 입력 18,235토큰, 출력 16,000토큰에서 잘려 `LLM_TRUNCATED`로 실패했다. 원래 프롬프트의 S3(SMOTE 주제)는 출력 10,704토큰이었으므로 늘어난 필수 항목과 분량 제한 부재가 주원인으로 본다.
- 영향: live 결과의 형식과 길이만 바뀐다. API, 계약, demo 결과(fixtures)는 그대로다. 수정한 프롬프트로 S1·S3를 다시 실행한 live 검증은 아직 하지 않았다. 관련 T 작업: T06.
- 상태: 적용

## D-10 live 실행 권장값을 출력 32,000토큰, 응답 대기 600초로 정했다
- 날짜: 2026-11-08
- 원문 위치: `handoff/.env.example` 10~11행
- 원래 내용: `LLM_TIMEOUT_SECONDS=60`, `LLM_MAX_OUTPUT_TOKENS=8192`. 코드 기본값(`backend/app/config.py`)도 8192다.
- 바꾼 내용: 루트 README의 live 준비 절에서 `LLM_TIMEOUT_SECONDS=600`, `LLM_MAX_OUTPUT_TOKENS=32000`을 권한다. `.env.example`과 코드 기본값은 바꾸지 않았다. README는 이전에 300초·16,000토큰을 권하고 있었는데 그 차이도 기록되지 않았었다.
- 이유: live 시험에서 16,000토큰으로도 S4(SMOTE 주제, 2회)와 S3(INR 주제, 1회)가 출력 한도에서 잘렸다. 16,000토큰 생성에 약 2분이 걸렸으므로 32,000토큰이면 4분 가까이 걸릴 수 있어 timeout도 함께 올렸다. 클라이언트에 timeout을 직접 넘기므로 SDK의 "10분 넘는 요청은 streaming 필요" 검사에는 걸리지 않는다.
- 영향: 출력이 한도까지 차면 호출 1회 비용이 약 0.32달러(출력 100만 토큰당 10달러 기준)가 된다. 실패를 기다리는 시간도 길어진다. 근본 해결은 아니며 D-09의 분량 규칙과 함께 쓴다. API와 demo 흐름은 바뀌지 않는다.
- 상태: 적용

## D-11 arXiv 결과가 3편보다 적으면 검색어를 줄여 다시 찾는다
- 날짜: 2026-11-08
- 원문 위치: `handoff/architecture.md` 114행 (live S2: 모델이 `search_query` 문자열을 만들고 서버가 arXiv 검색 API를 호출해 최대 3개를 채택)
- 원래 내용: 모델 검색어 하나로 arXiv를 한 번 조회한다. 구현(T05)은 영문 단어 최대 5개를 모두 `all:` AND로 묶었다.
- 바꾼 내용: 확인된 논문이 3편보다 적으면 서버가 검색어 끝 단어를 하나씩 빼며 두 단어까지 다시 조회한다. 요청은 한 연결씩 3초 간격 규칙을 지킨다. 앞 검색 결과부터 중복 없이 합쳐 최대 3편을 채택한다. 다시 조회했으면 사용한 검색어들을 S2 evidence 경고에 남긴다. 추가 조회가 네트워크 오류면 이미 확인한 논문으로 진행한다. 끝까지 0편이면 기존처럼 `NO_VERIFIED_REFERENCES`다.
- 이유: live 시험에서 모델 검색어 `implicit neural representation extrapolation 1D`가 다섯 단어 AND로 0편이 되어 S2가 두 번 실패했다. 같은 조건에서 `1D`만 빼면 39편이었다. 검색어를 바꾼 재실행도 1편만 채택됐다.
- 영향: S2 한 번에 arXiv 요청이 최대 4번(약 12초 추가)까지 늘 수 있다. 서버가 확인한 arXiv 결과만 쓰는 원칙, fixture로 대체하지 않는 원칙은 그대로다. 관련성이 좋은 논문을 고르는 문제는 해결하지 않는다. 테스트: `backend/tests/test_references.py`(재검색 4개 추가). 관련 AC: AC-08. 관련 T 작업: T05.
- 상태: 적용
