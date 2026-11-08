# Research-to-Paper 워크플로 프로토타입

연구 아이디어를 입력하면 여섯 단계를 순서대로 진행하는 수업 과제용 로컬 웹 프로토타입입니다.

**S1 연구 Brief → S2 관련 연구 → S3 실험 설계 → S4 실행 코드 → S5 결과 분석 → S6 영어 논문 초안**

각 단계의 결과는 사용자가 직접 검토·수정·재생성·승인합니다. 승인된 결과만 다음 단계의 입력이 됩니다.

이번 구현에서 우선 확인하는 것은 AI 결과의 품질이 아니라 다음 규칙들이 **서버에서 실제로 지켜지는지**입니다.

- 승인 게이트와 입력 버전 연결
- 상위 단계를 새로 승인했을 때의 변경 전파(오래됨, stale)
- 실험 결과 업로드와 원본 지표 연결
- 코드·초안·참고문헌 내보내기

**관련 문서** (폴더별 의미와 규칙은 아래 [폴더 구조](#폴더-구조)에 정리되어 있습니다)

- 계획·계약·원문 자료: [`handoff/`](handoff/) (배포받은 계획팩 원본. 시작점은 [`handoff/CLAUDE.md`](handoff/CLAUDE.md))
- 구현·검사 상태: [`handoff/IMPLEMENTATION_STATUS.md`](handoff/IMPLEMENTATION_STATUS.md)
- 계획과 다르게 한 점: [`DEVIATIONS.md`](DEVIATIONS.md)
- 작업 규칙 원문(무엇을 어디에 기록하나): [`CLAUDE.md`](CLAUDE.md)

> SQLite, S1 승인 때만 Brief 갱신, 화면 이동만 하는 back, Markdown 초안 출력은 SSAD와 별도로 둔 **프로토타입 전용 임시 baseline**입니다. SSAD의 확정 사항이나 원문 준수의 증거가 아닙니다.


<br>


## 목차

- [준비물](#준비물)
  - [Python 3.11·Node 22가 없을 때 (root·Docker 없이)](#python-311node-22가-없을-때-rootdocker-없이)
- [설치](#설치)
- [실행 (터미널 두 개)](#실행-터미널-두-개)
  - [3000·8000 포트가 이미 쓰이고 있을 때](#30008000-포트가-이미-쓰이고-있을-때)
  - [서버가 원격 머신에 있을 때 (내 컴퓨터 브라우저로 접속)](#서버가-원격-머신에-있을-때-내-컴퓨터-브라우저로-접속)
  - [테스트](#테스트)
- [demo와 live](#demo와-live)
- [5분 기본 시연 (demo)](#5분-기본-시연-demo)
- [변경 전파 시연](#변경-전파-시연)
- [live 시연 (주제 고정: 불균형 분류에서 SMOTE 뒤 확률 보정)](#live-시연-주제-고정-불균형-분류에서-smote-뒤-확률-보정)
- [업로드 형식 (prototype_json_v1)](#업로드-형식-prototype_json_v1)
- [하지 않는 것 (제한)](#하지-않는-것-제한)
- [UI/UX 기획안 대비 구현 범위](#uiux-기획안-대비-구현-범위)
- [폴더 구조](#폴더-구조)
  - [폴더별 의미](#폴더별-의미)
  - [폴더 간 관계](#폴더-간-관계)
  - [규약과 관례](#규약과-관례)
- [실제 수행한 검사](#실제-수행한-검사)


<br>


## 준비물

- Python **3.11**
- Node.js **22 이상** (npm 포함)
- Docker, Redis, 별도 DB 서버는 필요하지 않습니다.
- API 키와 네트워크가 없어도 demo 모드는 끝까지 동작합니다. 단, 처음 설치할 때는 패키지를 받아야 하므로 네트워크가 필요합니다.

`python3.11 -V`와 `node -v`로 먼저 확인합니다. 둘 중 하나라도 없으면 아래 절차로 **내 홈 폴더에만** 설치합니다.


### Python 3.11·Node 22가 없을 때 (root·Docker 없이)

공용 서버에서 `sudo apt install`을 쓰지 않는 방법입니다. 모두 `~/.local` 아래에 설치되고 다른 사용자에게 영향을 주지 않습니다. Ubuntu 20.04(x86_64) 서버에서 이 절차 그대로 설치·실행·테스트를 확인했습니다.

```bash
# 1) uv(파이썬 설치 도구)와 Python 3.11
curl -LsSf https://astral.sh/uv/install.sh | sh        # ~/.local/bin/uv
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11

# 2) Node 22 (공식 바이너리를 내 폴더에 풀기)
mkdir -p ~/.local/node22
curl -fsSL https://nodejs.org/dist/v22.23.2/node-v22.23.2-linux-x64.tar.xz | tar -xJ -C ~/.local/node22 --strip-components=1
export PATH="$HOME/.local/node22/bin:$PATH"

# 3) 다음 로그인부터도 쓰도록 등록
echo 'export PATH="$HOME/.local/node22/bin:$HOME/.local/bin:$PATH"' >> ~/.bashrc

uv --version && node -v && npm -v                      # node는 v22.x
```

이 경우 아래 "설치" 2)의 `python3.11 -m venv .venv` 줄을 **`uv venv --seed -p 3.11 .venv`** 로 바꿔 실행합니다. 나머지는 같습니다.


<br>


## 설치

저장소 루트에서 실행합니다.

```bash
# 1) 환경 설정: 루트 .env를 백엔드가 읽는다 (API 키는 live 모드에만 필요)
cp handoff/.env.example .env

# 2) 백엔드: 버전 고정 lockfile로 설치 (scikit-learn·PyTorch는 서버에 설치하지 않음)
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.lock      # Windows: .venv\Scripts\pip install -r requirements.lock
cd ..

# 3) 프런트엔드: package-lock.json 그대로 설치
cd frontend
npm ci
cd ..
```


<br>


## 실행 (터미널 두 개)

```bash
# 터미널 1 — API: http://127.0.0.1:8000/api  (프로세스 1개, 자동 reload·다중 worker 없음)
cd backend
.venv/bin/python -m app

# 터미널 2 — 웹: http://127.0.0.1:3000
cd frontend
npm run dev
```

브라우저에서 **http://127.0.0.1:3000** 에 접속합니다. 백엔드 상태는 http://127.0.0.1:8000/api/health 에서 확인할 수 있습니다.

- `python -m app`은 `.env`의 `BACKEND_HOST`(기본 127.0.0.1)와 `BACKEND_PORT`(기본 8000)를 씁니다.
- SQLite 파일은 `.env`의 `DATABASE_URL`(기본 `./data/prototype.db`)에 생깁니다. 경로는 저장소 루트 기준이며, 파일이 없으면 자동으로 만듭니다. 처음부터 다시 시작하려면 `data/` 폴더를 지우면 됩니다.
- 운영 빌드로 확인하려면 `npm run build && npm run start`를 씁니다.
- 프런트가 호출하는 API 주소는 기본 `http://127.0.0.1:8000/api`입니다. 바꾸려면 `frontend/.env.local`에 `NEXT_PUBLIC_API_BASE_URL`을 넣습니다. 루트 `.env`에 있는 같은 이름의 줄은 프런트가 읽지 않습니다.


### 3000·8000 포트가 이미 쓰이고 있을 때

공용 서버에서는 다른 사람이 같은 포트를 쓰고 있을 수 있습니다. `ss -ltn | grep -E ':(3000|8000) '`에 결과가 나오면 다른 번호(예: 웹 3200, API 8200)를 씁니다. **네 군데를 같은 번호로 맞춥니다.**

1. 루트 `.env`: `BACKEND_PORT=8200`, `FRONTEND_ORIGIN=http://127.0.0.1:3200`

2. `frontend/.env.local` 파일을 만들고 한 줄: `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8200/api`

3. 웹 실행 명령: `npm run dev -- -p 3200`

4. 아래 포트 포워딩도 `3200`, `8200`으로, **내 컴퓨터 쪽 번호도 똑같이** 연결하고 브라우저에서 http://127.0.0.1:3200 을 엽니다.

`.env`와 `.env.local`을 바꾼 뒤에는 백엔드와 웹을 둘 다 다시 시작합니다. 이후 문서의 3000·8000은 바꾼 번호로 읽습니다.


### 서버가 원격 머신에 있을 때 (내 컴퓨터 브라우저로 접속)

서버를 SSH로 접속한 원격 머신에서 실행했다면, 내 컴퓨터 브라우저에서 `127.0.0.1:3000`을 열어도 아무것도 뜨지 않습니다. `127.0.0.1`은 **내 컴퓨터 자신**을 가리키기 때문입니다. 원격 머신의 포트를 내 컴퓨터로 연결(포트 포워딩)해야 합니다.

**반드시 3000(웹)과 8000(API) 두 포트를 같은 번호로 연결합니다.** 화면은 3000에서 받지만, 브라우저가 API를 `http://127.0.0.1:8000/api`로 직접 호출합니다. 8000이 빠지거나 다른 번호로 연결되면 화면만 뜨고 "API 서버에 연결할 수 없습니다" 오류가 납니다.

**먼저 접속 경로에 맞게 내 컴퓨터의 `~/.ssh/config`를 적습니다** (Windows는 `C:\Users\<나>\.ssh\config`). 주소와 계정은 각자 것으로 바꿉니다.

```
# 경로 a: 학교 밖. VPN을 켠 뒤 VPN 사용자용 중간 서버(singapore)를 거쳐 연구실 서버로
Host lab-via-sg
    HostName <연구실 서버 주소>
    User <내 계정>
    ProxyJump <내 계정>@<singapore 주소>

# 경로 b: 연구실 컴퓨터에서 연구실 서버로 바로
Host lab
    HostName <연구실 서버 주소>
    User <내 계정>
```

두 경로 모두 앱은 **연구실 서버에서** 설치·실행하고, 화면은 **내 컴퓨터 브라우저로** 봅니다. 아래 단계는 경로와 상관없이 같습니다.

**방법 1: VS Code Remote-SSH (추천)**

1. VS Code에서 `Ctrl+Shift+P`(macOS `Cmd+Shift+P`) → `Remote-SSH: Connect to Host...` → `lab-via-sg`(경로 a) 또는 `lab`(경로 b)을 고릅니다. 저장소 폴더를 열고, VS Code 터미널 두 개에서 위 "실행"의 두 명령을 띄웁니다.

2. 아래쪽 패널의 **PORTS** 탭을 엽니다. 안 보이면 `Ctrl+Shift+P`(macOS `Cmd+Shift+P`)를 누르고 `Ports: Focus on Ports View`를 실행합니다.

3. **Forward a Port**로 `3000`을 추가하고, 같은 방법으로 `8000`도 추가합니다.

4. 표의 **Local Address**가 정확히 `localhost:3000`, `localhost:8000`인지 확인합니다.
   - 내 컴퓨터에서 그 번호를 이미 다른 프로그램이 쓰면 VS Code가 `3001` 같은 다른 번호를 배정합니다. 이 경우 API 연결이 실패합니다.
   - 그 프로그램을 끄고 포워딩을 지웠다가 다시 추가하거나, Local Address를 우클릭해 포트를 `3000`/`8000`으로 바꿉니다.

5. 내 컴퓨터 브라우저에서 **http://127.0.0.1:3000** 을 엽니다. `http://localhost:3000`도 됩니다.

**방법 2: 터미널 SSH만 쓸 때**

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 lab-via-sg   # 경로 a
ssh -N -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 lab          # 경로 b
```

이 터미널을 열어 둔 채로 브라우저에서 http://127.0.0.1:3000 을 엽니다. 서버 실행은 별도 SSH 터미널에서 합니다.

VS Code 창이나 SSH 연결을 닫으면 그 터미널에서 띄운 서버도 꺼집니다. 연결을 끊고도 계속 띄워 두려면 `tmux` 안에서 실행합니다.

**접속 문제 확인 순서**

1. 원격 머신에서 `curl http://127.0.0.1:8000/api/health`가 응답하는지 봅니다 (서버가 떠 있는지).

2. 내 컴퓨터 브라우저에서 http://127.0.0.1:8000/api/health 가 열리는지 봅니다 (8000 포워딩).

3. 화면이 "불러오는 중…"에서 멈추면 대개 8000 포워딩 문제입니다. 화면 자체가 안 뜨면 3000 포워딩 문제입니다.

여러 사람이 같은 원격 서버 인스턴스에 접속하면 **같은 DB를 함께 보게 됩니다.** 로컬 단일 사용자용 프로토타입이라 사용자 구분이 없으니, 시연할 프로젝트를 서로 건드리지 않도록 합니다.


### 테스트

```bash
cd backend && .venv/bin/python -m pytest -q        # 57개, 실제 임시 SQLite 파일 사용, 네트워크 불필요
cd frontend && npm run build                       # 타입 검사 포함
```

`.env`에 실제 API 키가 있으면 `test_health` 하나가 실패합니다. 이 테스트는 live 설정이 없는 상태를 전제로 하기 때문이며 코드 문제가 아닙니다. 키를 비운 상태로 돌리려면 `ANTHROPIC_API_KEY= LLM_MODEL= .venv/bin/python -m pytest -q`를 씁니다.


<br>


## demo와 live

| | demo (기본값) | live |
| --- | --- | --- |
| 단계 결과 | `handoff/fixtures/stages/s1~s6.json` 사전 작성본 | Anthropic API로 생성 |
| 관련 연구 | 동봉 snapshot `handoff/fixtures/references.snapshot.json` | arXiv에서 조회·확인한 논문 1~3편 (초록 기반) |
| 필요 설정 | 없음 | `.env`의 `ANTHROPIC_API_KEY`, `LLM_MODEL` (`ANTHROPIC_WORKSPACE_ID`는 선택) |
| 실패 시 | — | 실패로 표시. demo 결과로 바꾸지 않음 |

- 모드는 **프로젝트를 만들 때** 정해지고, 이후에는 바뀌지 않습니다. 생성 화면에서 demo/live를 고를 수 있고(임시 기능, `DEVIATIONS.md` D-05), 기본 선택은 `.env`의 `APP_MODE`입니다. live를 고르려면 `.env`에 `ANTHROPIC_API_KEY=...`, `LLM_MODEL=...`을 설정하고 백엔드를 다시 시작해야 합니다. 설정이 없으면 live 선택이 막혀 있습니다.
- 대시보드의 프로젝트 카드에서 **삭제**를 누르고 확인하면 그 프로젝트의 단계 결과·버전·결정 기록·업로드한 실험 결과가 DB에서 지워지고, 지운 내용이 DB 파일에 남지 않도록 SQLite 파일을 바로 다시 정리합니다(되돌릴 수 없음, `DEVIATIONS.md` D-04). 작업이 진행 중이면 끝난 뒤에 삭제할 수 있습니다.
- demo에서도 저장, 승인, 버전, 오래됨, 업로드, 내보내기는 실제 앱 코드로 처리합니다. 화면과 내보낸 파일에는 "데모 모드: 사전 작성 산출물 사용"이 표시됩니다.
- demo의 생성 지연은 `DEMO_STAGE_DELAY_SECONDS`(기본 1초)로 조절합니다. 진행 상태 조회를 보여 주기 위한 값입니다.
- 비용 추정은 `LLM_INPUT_USD_PER_MILLION`, `LLM_OUTPUT_USD_PER_MILLION`이 둘 다 설정됐을 때만 계산합니다. 설정이 없으면 null입니다.
- 비밀키는 백엔드만 읽습니다. 브라우저, 소스, 내보내기 파일에는 들어가지 않습니다.


<br>


## 5분 기본 시연 (demo)

1. 서버 두 개를 시작하고 http://127.0.0.1:3000 에 접속합니다. 키가 없어도 열리고 "demo 모드" 표시가 보입니다.

2. `handoff/fixtures/project_input.json`의 `name`과 `idea`를 붙여 넣고 **프로젝트 만들기**를 누릅니다.

3. **S1 실행**을 누르고 Brief를 읽습니다.
   - 왼쪽에서 S2를 누르면 **S2 실행**이 잠겨 있습니다 (승인 전 차단).
   - S1으로 돌아가 **승인**합니다. 오른쪽 끝 **Research Brief** 탭을 열면 "현재 Brief"에 표시됩니다.

4. **S2 실행**을 누르고 논문 카드의 출처와 확인일을 확인한 뒤 승인합니다.

5. **S3 실행**을 누릅니다.
   - 실험 E1, 가설 H1, 필수 지표 4개, `## Ablation 계획`을 확인합니다.
   - 코멘트를 적고 **재생성 요청**을 누르면 v2가 생기고, Decision 기록이 남습니다.
   - 승인합니다.

6. **S4 실행**을 누릅니다. 코드 파일과 "서버 미실행" 표시를 확인하고 승인한 뒤 **코드 zip 다운로드**를 누릅니다.

7. S5에서 `handoff/fixtures/experiment_result.valid.json`을 **업로드**합니다.
   - 지표 4개, 환경 정보, 수렴 경고가 원본 값 그대로 표시됩니다.
   - **S5 실행** 후 판정이 inconclusive인지 확인하고 승인합니다.

8. **S6 실행**을 누르고 여섯 섹션, 실험 수치, 참고문헌을 확인한 뒤 승인합니다. **논문 Markdown**과 **BibTeX**를 다운로드합니다.

9. 데모 표시가 있는 생성 본문과 실제 측정 파일(`data_origin: measured`)은 출처가 다르다는 점을 설명합니다.
   - 측정 파일은 `handoff/reference_experiment/train.py`를 CPU에서 실행해 만든 것입니다.

오른쪽 **결정 근거** 카드의 `ref:`, `metric:`, `artifact:` 칩을 누르면 원본 근거(논문, 업로드 원본 행, 특정 버전)가 읽기 전용으로 열립니다. 근거가 비어 있으면 "근거 없음 · 사용자 확인 필요"가 표시됩니다.


<br>


## 변경 전파 시연

1. 여섯 단계를 모두 승인한 프로젝트에서 S3 → **직접 수정**을 엽니다.

2. 반복 seed 관련 문구를 고쳐 **새 버전으로 저장**합니다. 저장만으로는 승인되지 않아 S3가 "검토 필요"로 바뀝니다.

3. S3를 **승인**하면 S4·S5·S6가 **오래됨**으로 바뀝니다. 과거 결과와 승인 기록은 그대로 열람할 수 있습니다.

4. S4에서 코멘트를 적고 **재생성 요청**을 누릅니다. 오른쪽 **Research Brief** 탭의 "입력 버전"이 새 S3 버전을 가리키는지 확인합니다.

5. S4를 다시 승인하기 전에는 S5 실행 버튼이 잠겨 있습니다. API로 직접 요청해도 서버가 409로 거부합니다.

demo의 재생성 본문은 사전 작성본이라 코멘트의 의미가 본문에 반영되지는 않습니다. 입력 연결은 snapshot과 recorder Gateway 테스트로 확인했습니다.


<br>


## live 시연 (주제 고정: 불균형 분류에서 SMOTE 뒤 확률 보정)

실제 모델(Anthropic API)과 실제 arXiv 조회로 여섯 단계를 진행합니다. demo와 달리 결과 본문이 입력과 코멘트에 따라 실제로 바뀝니다.


### 주제와 고른 이유

**질문:** 불균형 데이터에서 SMOTE 오버샘플링은 F1을 올리지만 확률 보정(Brier score, ECE)을 해친다는 주장이 있습니다. 그렇다면 **SMOTE 뒤에 확률 보정 단계를 붙이면 F1 이득은 유지하면서 보정 손실을 되찾을 수 있는가?**

- **답이 열려 있는 질문입니다.** SMOTE와 보정의 관계는 문헌마다 결론이 엇갈리고 데이터 조건에 따라 달라집니다. 그래서 문헌 요약으로 끝나지 않고, 이번 실험이 특정 조건에서 새 측정값을 만듭니다.
- **SSRD가 상정한 사용자에 가깝습니다.** 연구 경험이 적은 대학원생이 "이렇게 하면 나아지지 않을까"라는 자기 제안을 들고 오는 형태입니다. 그래서 차별점 분석(RQ-2), 실제 ablation(N-05), 가설 기각 처리(ONRQ-5)를 시연할 수 있습니다.
- **PR-3의 "예제 아이디어 1건"에 해당합니다.** 원 정의의 예제 규모 연구(PyTorch, 단일 GPU)보다 작은 CPU·scikit-learn 규모인 것은 주제 때문이 아니라 프로토타입 범위를 축소했기 때문입니다.


### 이 시연으로 보여 주는 것

| 요구사항 | 어디서 보이나 |
| --- | --- |
| RQ-8 단계 간 연결, RQ-10 변경 전파 | S3를 고쳐 승인하면 S4~S6가 오래됨. S4를 재생성하면 새 코드에 반영됨 |
| RQ-9 체크포인트 | 단계마다 승인 전에는 다음 단계가 잠김 |
| RQ-2·LOR-1 실존 인용 | S2의 논문이 실제 arXiv 조회 결과 (`arxiv_live`) |
| RQ-3·N-05 가설–실험 대응, ablation | S3에 세 조건과 "보정 단계 유무" ablation |
| LOR-2 수치 정확성 | S5·S6의 수치가 업로드 원본 행으로 연결 |
| RQ-12 판단 근거 | 단계마다 근거 칩(`ref:`, `metric:`, `artifact:`)으로 원본 열람 |
| ONRQ-5 가설 기각 | 결과가 불리하면 그대로 기각 또는 inconclusive로 판정 |
| LOR-8 생성 이력 | 버전별 "AI 생성 (claude-sonnet-5-5)" 또는 "사용자 수정", 입력 버전 목록 |


### 0. 준비 (한 번)

1. 루트 `.env`를 다음처럼 설정합니다. 키는 **각자 본인 계정**의 Console에서 발급하고 크레딧을 충전한 API 키를 씁니다. 키를 다른 사람과 공유하거나 파일로 주고받지 않습니다. `.env`는 git과 제출 zip에 들어가지 않습니다.
   ```
   APP_MODE=live                 # 생성 화면의 기본 선택. demo로 두고 화면에서 live를 골라도 됨
   ANTHROPIC_API_KEY=<API 키>
   LLM_MODEL=claude-sonnet-5-5
   LLM_TIMEOUT_SECONDS=600
   LLM_MAX_OUTPUT_TOKENS=32000
   LLM_INPUT_USD_PER_MILLION=2
   LLM_OUTPUT_USD_PER_MILLION=10
   ```
   - 출력이 긴 단계(S3·S4)는 16,000토큰에서도 잘린 적이 있어 출력 상한을 32000으로 둡니다. 다 쓰면 2~5분 걸릴 수 있어 timeout도 600초로 둡니다(`DEVIATIONS.md` D-10). 계획팩 `.env.example`의 기본값(60초, 8192)으로는 live S3·S4가 잘릴 가능성이 큽니다.
   
2. 백엔드를 다시 시작하고 http://127.0.0.1:8000/api/health 에서 `"live_configured":true`인지 확인합니다. `default_mode`는 `APP_MODE` 값이라 demo여도 됩니다.

3. 브라우저를 새로고침하고 대시보드의 새 프로젝트 폼에서 **live**를 고를 수 있는지 확인합니다. 키나 모델 설정이 없으면 live가 막혀 있습니다.

4. 비용: Sonnet 5.5 기준 여섯 단계 1회에 대략 $0.3~0.5입니다. 재생성할 때마다 그 단계 비용이 더 듭니다.


### 1. 프로젝트 만들기

- 이름
  ```
  불균형 분류: SMOTE 뒤 확률 보정의 효과
  ```
- 아이디어
  ```
  클래스 불균형이 있는 작은 표 형식 데이터(sklearn breast_cancer에서 양성 클래스를 줄여 불균형을 만든 설정)에서, SMOTE 오버샘플링은 F1을 올리지만 확률 보정(Brier score, ECE)을 해친다는 주장이 있다. 나는 SMOTE 뒤에 별도 검증 세트로 확률 보정(Platt scaling 또는 isotonic)을 붙이면 F1 이득은 유지하면서 보정 손실을 회복할 수 있다고 생각한다. class_weight 방식, SMOTE 단독, SMOTE+보정을 비교하고, 보정 단계의 기여를 ablation으로 확인하고 싶다. CPU에서 scikit-learn으로 실행 가능한 범위로 한다.
  ```
- 대시보드 새 프로젝트 폼의 **생성 모드**에서 **live**를 고르고 만듭니다. 만든 뒤에는 왼쪽 사이드바 아래와 대시보드 카드에 **live 모드**가 표시됩니다. 모드와 아이디어는 만든 뒤 바뀌지 않습니다.

각 단계 생성은 수십 초~1분 남짓 걸립니다. 화면은 1초마다 상태를 확인하고, 창을 닫아도 작업은 계속됩니다.


### 2. S1 연구 Brief

1. **S1 실행** 후 연구 문제, 가설, 평가 계획, 확인 질문을 읽습니다.

2. 가설이 다음 두 가지로 나뉘어 있는지 봅니다. 하나로 뭉쳐 있으면 **직접 수정**으로 나누고 저장합니다. 저장은 승인이 아닙니다.
   - H1: SMOTE가 class_weight보다 F1이 높다
   - H2: SMOTE에 확률 보정을 붙이면 F1을 크게 잃지 않고 Brier·ECE가 SMOTE 단독보다 좋아진다

3. 확인 질문(최대 3개)에 대한 답을 반영하고 싶으면 코멘트로 적고 **재생성 요청**합니다. 예: "불균형 비율은 1:9, seed는 5개".

4. **승인**합니다. 오른쪽 끝 **Research Brief** 탭을 열면 "현재 Brief"에 표시됩니다.
   - 시연 포인트: 승인 전에는 S2 실행이 잠겨 있습니다.


### 3. S2 관련 연구와 차별점 (실제 arXiv 조회)

1. **S2 실행**: 모델이 영어 검색어를 만들고 → 서버가 arXiv에서 조회·확인한 논문 1~3편만 → 모델이 그 초록으로 정리합니다. 결과가 3편보다 적으면 서버가 검색어 끝 단어를 하나씩 빼며 다시 찾고, 그때 쓴 검색어를 경고 상자에 남깁니다(`DEVIATIONS.md` D-11).

2. 확인할 것
   - 논문 카드의 확인 출처가 `arxiv_live`이고 확인일이 오늘인지. 저자·연도·제목은 모델이 아니라 arXiv 응답에서 온 값입니다.
   - 본문이 "이 제안(SMOTE+보정)과 기존 연구의 차이"를 짚는지
   - 메타데이터가 부족해 제외된 후보가 있으면 "경고" 절에 대상과 이유가 나옵니다.

3. 관련성이 약하면 다음처럼 적고 **재생성 요청**합니다. 재생성하면 arXiv를 다시 조회합니다.
   > SMOTE와 probability calibration(Platt, isotonic) 관련 논문 위주로 찾고, 이 제안과의 차별점을 분명히 적어 주세요.

4. **승인**합니다.
   - `ARXIV_UNAVAILABLE`이면 arXiv 일시 장애이니 잠시 후 다시 실행합니다.
   - `NO_VERIFIED_REFERENCES`이면 확인된 논문이 0편이라는 뜻입니다. 코멘트로 검색 방향을 바꿔 재생성합니다.


### 4. S3 실험 설계

1. **S3 실행** 후 확인합니다.
   - 실험 목록이 H1·H2를 모두 다루는지. 예: E1은 class_weight vs SMOTE(H1), E2는 SMOTE vs SMOTE+보정(H2)
   - 필수 지표 이름. 예: `f1`, `brier`, `ece`처럼 결과 파일에 그대로 쓸 이름
   - 본문 `## Ablation 계획`에 **보정 단계 유무 비교**가 들어 있는지. 이 주제에서는 "해당 없음"이 아니어야 합니다.

2. **이 프로토타입의 S5는 Run 하나를 분석합니다.** 그래서 세 조건과 ablation이 한 번 실행에 모두 들어가도록 다음 코멘트로 **재생성 요청**하는 것을 권합니다.
   > 세 조건(class_weight, SMOTE, SMOTE+보정)을 하나의 실험 E1으로 묶어 한 번 실행에서 모두 측정해 주세요. seed 5개를 반복하고 조건별 f1, brier, ece의 평균과 표준편차를 각각 별도 지표 이름으로 기록해 주세요. 불균형 비율은 1:9로 고정해 주세요.
   - 이렇게 하지 않으면 실험이 E1·E2로 나뉩니다. 그러면 Run을 하나만 분석하는 S5에서 다른 실험의 가설은 inconclusive로 남습니다(계약상 정상 동작).

3. **승인**합니다. 서버는 가설 누락, 실험 안 가설 중복, Ablation 절 누락이 있으면 승인 전에 거부합니다.


### 5. S4 실행 코드

1. **S4 실행** 후 파일(예: `train.py`, `requirements.txt`, `README.md`)과 "서버 미실행" 표시를 확인합니다.
   - `requirements.txt`에 `imbalanced-learn`(SMOTE)이 있는지
   - 보정을 **학습 데이터와 분리된 검증 세트**로 하는지(`CalibratedClassifierCV` 등). 테스트 세트로 보정하면 결과가 부풀려집니다.
   - 결과를 `prototype_json_v1` 형식으로 저장하고, `experiment_id`와 지표 이름이 S3와 같은지

2. 문제가 있으면 코멘트로 적어 **재생성 요청**합니다.

3. **승인**한 뒤 **코드 zip 다운로드**를 누릅니다.


### 6. 실험 실행 (서비스 밖)

웹 서버는 생성 코드를 실행하지 않습니다. 원 설계(SSRD RQ-5)의 격리 샌드박스 자동 실행은 이번 범위에서 빠졌습니다. 그래서 zip을 받아 **웹 서버와 분리된 환경**에서 실행합니다.

```bash
mkdir exp && cd exp && unzip ../code.zip
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
# 실행 명령은 zip 안 README.md를 따릅니다. 보통 다음과 같습니다.
.venv/bin/python train.py --output result.json
```

- CPU에서 수 초~1분이면 끝납니다.
- `result.json`의 `experiment_id`, 지표 이름, `data_origin: measured`를 확인합니다.
- **실행이 실패해도 코드를 몰래 고치거나 숫자를 손대지 않습니다.** S4에서 오류 내용을 코멘트로 적어 **재생성 요청**하거나 **직접 수정**하고, 다시 승인한 뒤 zip을 새로 받아 실행합니다. 그래야 업로드 결과가 승인된 코드와 일치합니다.
- 서버가 원격 머신이면 `result.json`을 내 컴퓨터로 받아 둡니다. VS Code 탐색기에서 우클릭 → **Download**를 쓰면 됩니다.


### 7. S5 결과 분석

1. **실험 결과 업로드**에서 `result.json`을 올립니다. 지표 표, 환경 정보, 경고가 원본 값 그대로 표시됩니다.
   - 형식이 맞지 않으면 422와 함께 문제 필드 위치가 표시됩니다. 예를 들어 S3에 없는 실험 ID이거나 필수 지표가 빠진 경우입니다.

2. 분석할 Run을 선택하고 **S5 실행**을 누릅니다.

3. 확인할 것
   - H1·H2가 각각 한 번씩 판정됐는지
   - 판정 이유의 수치가 `metric:` 근거 칩으로 원본 행까지 열리는지
   - 결과가 제안에 불리해도(예: 보정 후 F1이 크게 떨어짐) **그대로 기각 또는 inconclusive로 기록**되는지(ONRQ-5). seed 5개 평균·표준편차라도 통계 검정은 아니라는 한계가 본문에 남는지

4. **승인**합니다.


### 8. S6 영어 논문 초안

1. **S6 실행** 후 여섯 섹션(Abstract~Conclusion)을 확인합니다.
   - Related Work의 인용이 S2 논문과 같은지
   - Experiments의 수치와 측정 표가 업로드 원본과 같은지. 모델이 새로 쓴 숫자가 아니라 원본에서 렌더링한 값입니다.
   - 결론이 S5 판정과 맞는지. 기각된 가설을 성공처럼 쓰지 않았는지

2. **승인**한 뒤 **논문 Markdown**과 **BibTeX**를 다운로드합니다.


### 9. 변경 전파 (live에서 의미가 큰 부분)

1. S3를 **직접 수정**해 조건 하나를 바꿉니다. 예: 불균형 비율 1:9 → 1:19, 또는 보정 방법을 Platt에서 isotonic으로.

2. 저장하면 S3가 "검토 필요"가 되고, 아직 하위 단계는 그대로입니다. **승인**하면 S4~S6가 **오래됨**으로 바뀝니다. 과거 결과는 읽기 전용으로 남습니다.

3. S4를 **재생성 요청**하면, demo와 달리 **새 코드에 바뀐 조건이 실제로 반영**됩니다. 오른쪽 **Research Brief** 탭의 "입력 버전"이 새 S3를 가리키는지 확인합니다.

4. S4를 다시 승인하기 전에는 S5 실행이 막혀 있습니다.


### 시연 때 설명할 한계

이 주제에만 해당하는 것:

- seed 반복은 한 번의 실행 안에서 한 것이고, 통계 검정은 하지 않았습니다. 결과는 이 데이터·불균형 비율 조건에서의 관측이지 일반적 결론이 아닙니다.
- 규모는 CPU·scikit-learn으로, 원 정의의 PyTorch·GPU 예제 규모보다 작습니다.
- LLM 입력 데이터 조건은 공식 문서만 검토한 상태입니다 (`handoff/LLM_DATA_POLICY.md`). 각자 자기 키를 쓰므로 계정 조건은 키 주인이 확인합니다.

서버가 실험을 실행하지 않는 점, S2가 초록 기반인 점, 로그인·공유가 없는 점 같은 전체 범위 제한은 아래 "하지 않는 것"을 그대로 설명합니다.


<br>


## 업로드 형식 (prototype_json_v1)

`handoff/contracts/upload.schema.json` 형식만 받습니다. 원문 SSRD A.II 형식과 비교하면 아래 필드가 더 필요하며, 자동 변환이나 CSV 입력은 지원하지 않습니다.

- `schema_version`
- `data_origin`
- `metrics[].unit`

다음과 같은 파일은 422로 거부하고, 문제가 있는 필드 위치를 함께 보여 줍니다.

- NaN·Infinity가 들어 있음
- 같은 키가 중복됨
- 수치가 문자열이거나 seed가 bool임
- 같은 지표(name, split, step)가 중복됨
- 승인된 S3에 없는 실험 ID를 씀
- 필수 지표가 빠짐


<br>


## 하지 않는 것 (제한)

- 서버는 생성 코드나 실험을 **실행하지 않습니다.** S4 코드는 Python 문법 검사만 합니다.
- 사용자 공유, 로그인, 다중 사용자는 없습니다. 로컬 단일 사용자 전용입니다.
- LaTeX/PDF 출력은 없고, 초안은 Markdown으로만 내보냅니다.
- 다음 기능은 없습니다: 전체 버전 diff·복원, 섹션별 재생성, 논문 수동 추가, 통계 검정, 자유 서술 수치 전체에 대한 의미 검증.
- S2는 초록 기반 정리입니다. 논문 전문을 검토한 novelty 판정이 아닙니다.
- 동봉 실측은 단일 seed·단일 split이고 수렴 경고가 있어, 알고리즘 우위의 근거가 되지 않습니다.
- 고객 가정 A-1~A-7, SUS, 가용률, 사용자 평가는 검증하지 않았습니다.


<br>


## UI/UX 기획안 대비 구현 범위

UI/UX 기획안 v0.2(UI-01~UI-10)는 SSRD·SSAD 전체를 기준으로 그렸고, 이 프로토타입은 그중 `handoff/scope.json`이 고른 범위만 구현합니다. 화면 배치와 색은 기획안의 단계 검토 화면 공통 구조를 따랐습니다.

| 화면 | 이 프로토타입 |
| --- | --- |
| 공통 단계 검토 구조 (사이드바·단계 헤더·산출물·결정 근거·결정 바·연구 맥락 패널)와 디자인 값 | 반영. 기획안 캔버스의 폰트(Pretendard·Outfit·JetBrains Mono), 색, 카드·알약 모양, 상태 표기를 따름. 헤더에 참조한 승인본 버전, 근거 없음은 "사용자 확인 필요" |
| UI-01 대시보드 | 프로젝트 카드(6단계 상태 막대, 이어서 하기)와 생성. 비용·알림 없음 |
| UI-02 아이디어 구체화 | Brief 폼과 확인 질문, 코멘트 재생성. 대화형 질문·파일 첨부 없음 |
| UI-03 관련 연구 | 확인된 논문 카드와 미검증 후보 제외 경고. 포함/제외·수동 추가·차별성 부족 시 중단(ONRQ-2) 없음 |
| UI-04 실험 설계 | 가설–실험 대응과 ablation 계획. 예상 시간·비용과 축소안 없음 |
| UI-05 코드 | 파일 보기·편집·zip 다운로드. smoke test·자동 수정·diff·GitHub push 없음 |
| UI-06 실험·분석 | 외부 실행 결과 JSON 업로드, 가설 판정 카드(기각 포함). 서비스 내 실험 실행·실시간 진행 없음 |
| UI-07 논문 에디터 | 섹션 편집, Markdown·BibTeX. LaTeX 편집기·PDF 미리보기·섹션별 재생성 없음 |
| UI-08 연구 맥락 패널 | 오른쪽 끝 탭으로 여닫음. 현재 Brief, 입력 버전, Brief 승인 이력, 오래됨 원인(어느 상위 승인본이 몇 버전으로 바뀌었는지). Brief는 S1 승인 때만 갱신 |
| UI-09 공유·코멘트, UI-10 로그인 | 없음 (로컬 단일 사용자) |

기획안과 동작이 다른 두 가지: Brief는 단계마다가 아니라 **S1 승인 때만** 바뀌고, **이전 단계로**는 상태를 바꾸지 않고 이동만 기록합니다. 둘 다 위 "프로토타입 전용 임시 baseline"입니다.


<br>


## 폴더 구조


### 폴더별 의미

```
1Kyrus/
├── README.md                이 문서 (설치·실행·시연·제한·검사 결과)
├── CLAUDE.md                작업 규칙 원문 (폴더 구분, 기록 위치, 제출 방법)
├── DEVIATIONS.md            계획팩과 다르게 한 것 (D-01, D-02 …)
│
├── handoff/                 배포받은 계획팩 원본. 계획·계약·원문·demo 자료
│   ├── contracts/           API·DB·결과 형식·상태 규칙 (앱이 실행 중에 읽음)
│   ├── fixtures/            demo 단계 결과, 예시 업로드 파일 (앱이 실행 중에 읽음)
│   ├── prompts/             live 단계 지시문 (앱이 실행 중에 읽음)
│   ├── sources/             SSRD·SSAD 원문(v0.1)과 추출본, 외부 참고 자료
│   ├── reference_experiment/  동봉 CPU 참조 실험 (서비스 밖에서 실행)
│   ├── scripts/             계획 자료 검사 (check_handoff.py)
│   ├── IMPLEMENTATION_STATUS.md   구현·검사 상태
│   └── LLM_DATA_POLICY.md         LLM 입력 데이터 조건 확인 기록
│
├── backend/                 FastAPI 서버 (Python 3.11)
│   ├── app/api/             HTTP 경로 (/api/…)
│   ├── app/services/        승인·버전 규칙, 작업 실행, 업로드, 내보내기, LLM 호출 창구
│   ├── app/stages/          S1~S6 생성 로직
│   ├── app/schemas/         요청·결과 형식 (handoff/contracts와 대응)
│   └── tests/               pytest
│
├── frontend/                Next.js 화면 (Node 22)
│   ├── app/                 페이지 (대시보드, 프로젝트 화면)
│   ├── components/          화면 구성 요소
│   ├── lib/                 API 호출 함수, 타입
│   └── public/fonts/        UI/UX 기획안 폰트 (SIL OFL)
│
├── scripts/                 개발 검사 도구 (헤드리스 브라우저 시연 검사)
│
│   ── 아래는 제출 zip에 들어가지 않음 ──
├── .env                     로컬 설정과 API 키 (handoff/.env.example을 복사해 만듦, git에도 없음)
├── data/                    SQLite DB 파일 (처음 실행할 때 자동 생성, git에도 없음)
├── docs/                    팀 설계 문서 작업본 (SSRD·SSAD·UI/UX 기획안, git에는 있음)
└── dockerfile_1Kyrus/       개발 컨테이너 (git에는 있음)
```


### 폴더 간 관계

```
 브라우저 ──(http://127.0.0.1:3000)──▶ frontend
     │
     └──(http://127.0.0.1:8000/api)──▶ backend ──▶ data/prototype.db (SQLite)
                                           │
                                           ├── 실행 중에 읽음 ──▶ handoff/contracts, fixtures, prompts
                                           ├── 설정 ──▶ 루트 .env
                                           └── live 모드만 ──▶ Anthropic API, arXiv
```

- **handoff → backend:** 계획팩이 "무엇을 만들지"를 정하고, 백엔드는 그 계약을 구현합니다. 실행 중에도 `contracts/database.sql`(DB 생성), `contracts/artifacts.schema.json`(결과 형식 검사), `fixtures/`(demo 결과), `prompts/stage_prompts.md`(live 지시문)를 직접 읽습니다. 그래서 `handoff/`는 문서 폴더이면서 실행에 꼭 필요한 폴더입니다.
- **frontend → backend:** 화면은 브라우저에서 API만 호출합니다. DB와 API 키에는 접근하지 않습니다. API 주소는 `frontend/.env.local`의 `NEXT_PUBLIC_API_BASE_URL`로 바꿉니다.
- **backend → data/:** 모든 프로젝트·단계 결과·결정 기록·업로드가 `data/prototype.db` 파일 하나에 저장됩니다. 별도 DB 서버는 없습니다.
- **docs → 앱:** `docs/`는 계속 개정되는 팀 문서입니다. 새 버전을 앱에 반영할 때만 코드가 바뀌고, 그 기록은 `DEVIATIONS.md`나 `IMPLEMENTATION_STATUS.md`에 남깁니다. `handoff/`는 v0.1 기준 계획으로 고정되어 있습니다.
- **scripts, dockerfile_1Kyrus:** 개발할 때만 씁니다. 앱 실행에는 필요 없습니다.


### 규약과 관례

| 규칙 | 내용 |
| --- | --- |
| `handoff/`는 고치지 않음 | 배포받은 원본입니다. 예외는 작업하면서 갱신하라고 지정된 `IMPLEMENTATION_STATUS.md`, `LLM_DATA_POLICY.md` 두 개입니다 |
| `handoff/` 문서 속 경로 | 계획팩은 루트에 있다고 가정하고 경로를 씁니다. `contracts/…`는 `handoff/contracts/…`로 읽습니다. 계획이 만들라고 한 앱 파일(`backend/`, `frontend/`, `README.md`, `.env`)은 루트에 있습니다 |
| 계획과 다르게 하면 | `DEVIATIONS.md`에 D-NN 항목을 추가합니다. 번호는 바꾸지 않고, 취소해도 지우지 않고 "철회"로 표시합니다 |
| 계획이 정하지 않은 구현 선택, 검사 결과 | `handoff/IMPLEMENTATION_STATUS.md`의 "구현 선택" 표와 작업·검사 절에 적습니다 |
| `docs/` 새 버전 | 덮어쓰지 않고 `SSRD_v0.2.docx`, `UIUX_v0.3.pdf`처럼 파일을 추가합니다 |
| 비밀값 | API 키는 `.env`에만 둡니다. git에 올리거나 주고받지 않습니다 |
| 제출물 | `git archive --format=zip -o ../1Kyrus_submit.zip HEAD`. **커밋한 내용만** 들어가고 `docs/`, `dockerfile_1Kyrus/`, `.env`, `data/`는 빠집니다 |

기록 규칙의 원문과 세부 사항은 [`CLAUDE.md`](CLAUDE.md)에 있습니다.


<br>


## 실제 수행한 검사

상세 내용은 [`handoff/IMPLEMENTATION_STATUS.md`](handoff/IMPLEMENTATION_STATUS.md)에 있습니다.

| 검사 | 결과 |
| --- | --- |
| 백엔드 pytest 57개 (실제 임시 SQLite 파일, live 설정을 비운 상태) | PASS |
| 깨끗한 Ubuntu 20.04 서버에서 위 "root·Docker 없이" 절차로 설치, 포트 3200/8200으로 실행, S1 실행, 테스트·build | PASS |
| `npm run build` | PASS |
| 헤드리스 Chromium으로 5분 시연과 변경 전파 시연 수행 (`scripts/browser_demo_check.py`) | PASS |
| 실제 API 키를 쓴 live 호출 | **NOT RUN** (키는 설정했지만 아직 실행하지 않음). live 경로는 Fake/Recorder Gateway와 기록된 arXiv 응답으로만 검사 |
| LLM 입력 데이터 사용 조건 ([`handoff/LLM_DATA_POLICY.md`](handoff/LLM_DATA_POLICY.md)) | DOCUMENTS_REVIEWED. 실제 계정 조건은 미확인 |
