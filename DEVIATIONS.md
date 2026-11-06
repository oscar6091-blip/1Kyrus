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
