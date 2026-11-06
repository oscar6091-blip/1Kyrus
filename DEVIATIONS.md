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
- 이유: 호스트에 Node가 없고 Python이 3.8이다. 연구실 서버라 시스템에 직접 설치하지 않는다. 호스트 Docker 20.10.2가 glibc 2.34 이상 이미지에서 Node를 죽이고(`clone3`), Debian bullseye는 지원 종료로 apt가 404를 낸다. 그래서 베이스를 Ubuntu 20.04로 정했다.
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
