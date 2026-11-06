# 1Kyrus 작업 안내 (루트)

Research-to-Paper 웹 프로토타입(수업 과제, 제출일 **2026-11-08 Asia/Seoul**)을 만드는 작업 폴더다.
프로젝트 설명, 범위, 계약, 구현 계획은 모두 **`handoff/`의 계획팩**에 있다.
**작업을 시작하면 먼저 `handoff/CLAUDE.md`를 읽고 그 지침을 따른다.**

## 폴더 구분

| 위치 | 내용 | 수정 |
| --- | --- | --- |
| `handoff/` | 배포받은 계획팩 원본 (`handoff/manifest.json`에 40개 파일의 SHA-256) | **수정 금지.** 예외: `IMPLEMENTATION_STATUS.md`, `LLM_DATA_POLICY.md` (갱신하라고 만든 파일) |
| `backend/`, `frontend/`, `README.md`, `.gitignore` | 우리가 만드는 앱과 제출 README | 자유 |
| `DEVIATIONS.md` | 계획팩과 다르게 한 것의 기록 | 아래 규칙대로 추가 |
| `dockerfile_1Kyrus/` | 개발 컨테이너 | **제출할 때 제외** |

## 경로 규칙

`handoff/CLAUDE.md`는 팩을 루트에 둔 것을 전제로 경로를 쓴다. 팩이 하위 폴더에 있으므로 이렇게 읽는다.

- 계획 문서·`contracts/`·`fixtures/`·`prompts/`·`reference_experiment/`·`sources/`·`scripts/`·`.env.example`
  → 앞에 `handoff/`를 붙인다. 예: `handoff/contracts/api.openapi.json`.
- `implementation_plan.md`가 만들라고 한 앱 파일(`backend/...`, `frontend/...`, 루트 `README.md`, `.gitignore`)
  과 "저장소 루트 `.env`" → **이 루트**에 둔다.
- 계획 검사: `python3.11 handoff/scripts/check_handoff.py`.

## 계획과 달라진 점 기록 (필수)

계획팩 원본은 고치지 않는다. 계획팩(문서, 계약, 구현 계획, 안내)과 다르게 하는 일이 생기면
**그 자리에서 `DEVIATIONS.md`에 항목을 추가한다.** 환경 때문이든, 자료끼리 모순이 있어서든, 사용자 지시 때문이든 똑같이 기록한다.
`IMPLEMENTATION_STATUS.md`에는 진행 상황만 적는다. 차이가 있었다면 해당 D 번호만 언급한다.

## 개발 환경

- 호스트(munich)에는 Node가 없고 Python은 3.8뿐이다. 실행·설치·테스트는 전부 컨테이너
  `jwpark_kyrus_dev` 안에서 한다(`docker exec jwpark_kyrus_dev bash -lc '...'`).
  Node 22.23.2, Python 3.11(`python3.11`, `uv`)이 들어 있다. 자세한 내용은 `dockerfile_1Kyrus/README.md`.
- 컨테이너는 호스트 `127.0.0.1:3000`→3000(웹), `127.0.0.1:8000`→8000(API)으로 연결되어 있다.
  컨테이너에는 개발용으로 `BACKEND_HOST=0.0.0.0`이 들어 있다. `.env`가 이 값을 덮어쓰지 않게 한다.
- 제출 README에는 Docker 없이 venv와 npm으로 실행하는 명령만 쓴다(T01).
- git은 이 폴더가 저장소다. 첫 커밋이 계획팩 원본이므로, 원본이 바뀌었는지는 `git diff <첫 커밋> -- handoff/`로 확인한다.
