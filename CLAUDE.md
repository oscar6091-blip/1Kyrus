# 1Kyrus 작업 안내 (루트)

Research-to-Paper 웹 프로토타입(수업 과제, 제출일 **2026-11-08 Asia/Seoul**)을 만드는 작업 폴더다.
프로젝트 설명, 범위, 계약, 구현 계획은 모두 **`handoff/`의 계획팩**에 있다.
**작업을 시작하면 먼저 `handoff/CLAUDE.md`를 읽고 그 지침을 따른다.**

## 폴더 구분

| 위치 | 내용 | 수정 |
| --- | --- | --- |
| `handoff/` | 배포받은 계획팩 원본 (`handoff/manifest.json`에 40개 파일의 SHA-256). 문서만이 아니라 **실행에도 쓰인다**: 백엔드가 `contracts/database.sql`(DB 생성), `contracts/artifacts.schema.json`(결과 검사), `fixtures/`(demo 결과), `prompts/stage_prompts.md`(live 지시)를 실행 중에 직접 읽는다 (`backend/app/config.py`). 지우면 앱이 돌지 않는다 | **수정 금지.** 예외: `IMPLEMENTATION_STATUS.md`, `LLM_DATA_POLICY.md`. 계획팩이 작업하면서 갱신하라고 지시한 기록 파일이라, 구현하는 쪽(Claude)이 T 작업을 마칠 때마다 갱신한다 |
| `backend/` | FastAPI 백엔드. `app/`(api 라우터, services, stages, schemas), `tests/`(pytest, `tests/data/`에 기록된 arXiv 응답) | 자유 |
| `frontend/` | Next.js 화면. `app/`(페이지), `components/`, `lib/`(API 클라이언트·타입), `public/fonts/`(기획안 폰트, SIL OFL) | 자유 |
| `README.md`, `.gitignore`, `.gitattributes` | 제출 README, git 제외 규칙, 제출 zip 제외 규칙 | 자유 |
| `scripts/` | 개발 검사 도구 (`browser_demo_check.py`: 헤드리스 브라우저 시연 검사). 앱 실행에는 필요 없음 | 자유 |
| `.env`, `data/` | 실행할 때 생기는 로컬 파일. `.env`는 `handoff/.env.example`을 복사해 만들고(API 키 포함), `data/prototype.db`는 SQLite DB. 둘 다 git과 제출 zip에 들어가지 않는다 | 로컬 전용 |
| `docs/` | 팀 설계 문서의 작업본. `ssrd/`(SSRD), `ssad/`(SSAD), `uiux/`(UI/UX 기획안, 같은 내용의 디자인 캔버스 html 포함). v0.1은 `handoff/sources/original/`과 같은 파일의 사본이다. 문서는 앞으로 계속 개정되며, `handoff/`는 v0.1 기준 계획으로 고정한다 | 새 버전은 덮어쓰지 않고 `SSRD_v0.2.docx`, `SSAD_v0.2.pdf`, `UIUX_v0.3.pdf`처럼 파일을 추가한다 |
| `DEVIATIONS.md` | 계획팩과 다르게 한 것의 기록 | 아래 규칙대로 추가 |
| `dockerfile_1Kyrus/` | 개발 컨테이너 | **제출할 때 제외** |

## 경로 규칙

`handoff/CLAUDE.md`는 팩을 루트에 둔 것을 전제로 경로를 쓴다. 팩이 하위 폴더에 있으므로 이렇게 읽는다.

- 계획 문서·`contracts/`·`fixtures/`·`prompts/`·`reference_experiment/`·`sources/`·`scripts/`·`.env.example`
  → 앞에 `handoff/`를 붙인다. 예: `handoff/contracts/api.openapi.json`.
- `implementation_plan.md`가 만들라고 한 앱 파일(`backend/...`, `frontend/...`, 루트 `README.md`, `.gitignore`)
  과 "저장소 루트 `.env`" → **이 루트**에 둔다.
- 계획 검사: `python3.11 handoff/scripts/check_handoff.py`.

## 어디에 기록하나 (필수)

계획팩 원본은 고치지 않는다. 기록은 성격에 따라 아래 자리에 나눠 그때그때 남긴다.

| 성격 | 기록 위치 |
| --- | --- |
| 계획팩(문서, 계약, 구현 계획, 안내)과 **다르게** 했다. 이유가 환경이든, 자료끼리 모순이든, 사용자 지시든 같다 | `DEVIATIONS.md`에 D-NN 항목 추가 |
| 계획팩이 **정하지 않은 것**을 정했다(버전, 라이브러리, 경로 해석 같은 일반 구현 선택) | `handoff/IMPLEMENTATION_STATUS.md` "구현 선택" 절 |
| `docs/`의 SSRD·SSAD·UI/UX 문서를 앱에 반영하면서 **동작**(API, 상태·승인 규칙, 필수 입력)이 계획팩과 달라졌다 | `DEVIATIONS.md`에 D-NN 항목 추가. 원문 위치에 반영한 문서와 버전(예: `docs/ssrd/SSRD_v0.2.docx` 3.1)을 적는다 |
| UI/UX 기획안에 맞춰 **배치·스타일·표시만** 바꿨다 (`handoff/CLAUDE.md`가 허용) | `handoff/IMPLEMENTATION_STATUS.md` "구현 선택"에 한 줄. 기획안 대비 범위는 `README.md` "UI/UX 기획안 대비 구현 범위" 표를 갱신 |
| T 작업 진행 상황, 실행 명령, PASS/FAIL/NOT RUN | `handoff/IMPLEMENTATION_STATUS.md` 작업 표·검사 절 (차이가 있었다면 D 번호만 언급) |

## 제출

`git archive --format=zip -o ../1Kyrus_submit.zip HEAD`로 만든다. `.gitattributes`의 export-ignore 때문에
`dockerfile_1Kyrus/`와 `docs/`가 빠지고, git에 올리지 않은 `.env`·`.venv`·`node_modules`·`data/`도 들어가지 않는다.
그래서 **커밋한 내용만 제출된다.** 만들기 전에 `git status`가 깨끗한지 확인한다.

## 개발 환경

- 실행·설치·테스트는 전부 컨테이너 `jwpark_kyrus_dev` 안에서 한다(호스트에는 Node가 없다).
  자세한 내용은 `dockerfile_1Kyrus/README.md`를 본다. 제출 README에는 Docker 명령을 쓰지 않는다.
- 이 폴더가 git 저장소다. 첫 커밋 `3c61cdd`가 계획팩 원본(당시 루트에 있었음)이다. 팩을 `handoff/`로 옮겼기 때문에
  `git diff 3c61cdd -- handoff/`는 모든 파일을 새 파일로 보여 줘서 쓸 수 없다. 원본이 바뀌었는지는 옛 경로와 새 경로를 함께 넘겨 본다.
  ```bash
  git diff -M --name-status 3c61cdd HEAD -- handoff/ $(git ls-tree --name-only 3c61cdd) | grep -v '^R100'
  ```
  정상이면 다음 줄만 나온다. 이 밖의 줄이 있으면 원본이 바뀐 것이다.
  - `M CLAUDE.md`, `A handoff/CLAUDE.md`: 원본 안내를 `handoff/`로 옮기고(내용 동일) 루트에 이 안내를 새로 둠
  - `IMPLEMENTATION_STATUS.md`, `LLM_DATA_POLICY.md`의 `D`/`A` 짝: 갱신이 허용된 두 파일
  - `A scripts/browser_demo_check.py`: 옛 팩의 `scripts/`와 이름이 겹치는 우리 검사 도구
- 원격 저장소: GitHub `oscar6091-blip/1Kyrus` (팀 공유용, munich의 저장소 전용 deploy key로 push). 제출물은 여전히 위 `git archive` zip이다.
