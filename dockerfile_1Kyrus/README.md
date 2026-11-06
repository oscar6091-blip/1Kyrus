# 1Kyrus 개발 컨테이너

> **제출물에서 이 폴더를 뺀다.** T01은 "컨테이너를 도입하지 않는다"고 정해 두었다. 앱은
> Docker 없이 venv와 npm으로 실행되어야 하고, 루트 README에는 Docker 명령을 쓰지 않는다.
> 이 폴더는 Node와 Python 3.11이 없는 호스트(munich)에서 개발하려고 만든 것이다.
> `handoff/scripts/check_handoff.py`는 계획팩 폴더만 검사하므로 이 폴더는 검사에 영향을 주지 않는다.

`3D_HGS/dockerfile_3DHGS/`와 같은 구조다. 오래 띄워 두는 개발 컨테이너 하나를 쓰고,
`/home/Paris/jwpark`만 bind mount한다. 호스트 UID/GID를 그대로 써서 파일 소유자도 호스트 사용자로 유지된다.

## 3D_HGS와 다른 점

- GPU를 쓰지 않아서 `--gpus`와 GPU 점유 검사가 없다.
- 이미지는 `ubuntu:20.04`에 Node 22 공식 바이너리와 uv로 설치한 Python 3.11을 얹은 것이다.
  **glibc 2.34 이상인 베이스(bookworm, Ubuntu 22.04 이상, `node:22` 기본 이미지)는 쓰지 않는다.**
  호스트 Docker 20.10.2의 seccomp가 `clone3`를 막아서 Node가 바로 abort한다(2026-11-07에 직접 확인).
  `seccomp=unconfined`로 우회하는 방법은 쓰지 않는다. bullseye는 2026-08 지원 종료로 apt가 404를 낸다.
- 포트 두 개를 연다. 호스트 `127.0.0.1:<WEB>`는 컨테이너 3000, `127.0.0.1:<API>`는 컨테이너 8000으로 연결된다.
- 컨테이너에는 `BACKEND_HOST=0.0.0.0`이 환경변수로 들어 있다. 포트 포워딩을 위한 개발 전용 값이고
  `.env` 기본값(`127.0.0.1`)은 바꾸지 않는다. 그래서 백엔드는 `load_dotenv(override=False)`(기본값)로 읽어야 한다.

## 사용법

```bash
bash dockerfile_1Kyrus/build_docker.sh          # jwpark/1kyrus:latest
bash dockerfile_1Kyrus/docker_use.sh            # jwpark_kyrus_dev, 포트 3000/8000
bash dockerfile_1Kyrus/docker_use.sh dev2 3100 8100   # 호스트 포트가 사용 중일 때
```

호스트 포트를 3000/8000이 아닌 번호로 바꾸면, 노트북에서는 VS Code 포트 포워딩으로
로컬 3000과 8000을 그 원격 포트에 연결해야 한다. 프런트가 `http://127.0.0.1:8000/api`를 호출하기 때문이다.

호스트(Claude 포함)에서는 `docker exec jwpark_kyrus_dev bash -lc 'cd /home/Paris/jwpark/1Kyrus && ...'`로
컨테이너 안에서 실행한다. 컨테이너에는 Node 22.23.2, `python3.11`, `uv`가 들어 있다.

## 컨테이너 안 개발 명령

제출 README의 명령과 같다. 다만 컨테이너 밖에서 접속하기 위해 `0.0.0.0`으로 바인딩하는 점만 다르다.


```bash
# backend (서버 venv에는 scikit-learn·PyTorch를 넣지 않는다)
cd backend
uv venv -p 3.11 .venv
uv pip compile -q --python-version 3.11 requirements.in -o requirements.lock   # 의존성을 바꿀 때만
uv pip sync -p .venv requirements.lock
.venv/bin/python -m app        # 컨테이너의 BACKEND_HOST=0.0.0.0을 사용. reload·다중 worker 없음

# frontend
cd frontend && npm ci && npm run dev -- -H 0.0.0.0   # 컨테이너 안에서는 0.0.0.0으로 덮어써야 포트 포워딩됨

# 참조 실험은 별도 venv
cd handoff/reference_experiment && uv venv -p 3.11 .venv && uv pip install -p .venv -r requirements.txt
```

브라우저 화면 검사(선택): 컨테이너에 root로 Playwright 1.49.1과 Chromium을 `/opt/pw`, `/opt/pw-browsers`에 설치해 두었다.
이 설치는 컨테이너를 다시 만들면 사라진다.

```bash
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers /opt/pw/bin/python scripts/browser_demo_check.py --shots /tmp/shots
```

## 팀원이 munich에서 띄운 앱에 접속하기 (팀 내부용, 제출물 아님)

앱(웹 3000, API 8000)은 munich의 컨테이너 `jwpark_kyrus_dev` 안에서 실행된다. munich 호스트의
`127.0.0.1:3000`, `127.0.0.1:8000`으로 열려 있다. 팀원은 **munich에 SSH로 접속한 뒤 이 두 포트를 자기 컴퓨터로
포워딩**하면 된다. 컨테이너에 들어가거나 서버를 다시 띄울 필요는 없다.

### 접속 경로는 두 가지다. 포워딩 방법은 같다

| 경로 | 언제 | SSH 설정 |
| --- | --- | --- |
| A. 내 노트북 → VPN → singapore → munich | 학교 밖. singapore는 VPN 사용자용 중간 서버 | `~/.ssh/config`에 `ProxyJump`로 singapore를 거치게 한다 (아래 예시) |
| B. 연구실 컴퓨터 → munich | 연구실 안 | munich에 바로 접속. ProxyJump 없음 |

`~/.ssh/config` 예시 (주소·계정은 각자 것으로 바꾼다):

```
# 경로 A: 학교 밖 (VPN을 켠 상태에서)
Host munich-via-sg
    HostName <munich 주소>
    User <내 계정>
    ProxyJump <내 계정>@<singapore 주소>

# 경로 B: 연구실 안
Host munich
    HostName <munich 주소>
    User <내 계정>
```

### VS Code로 접속하는 경우 (추천)

1. `Ctrl+Shift+P`(macOS `Cmd+Shift+P`) → `Remote-SSH: Connect to Host...` → 경로에 맞는 별칭을 고른다 (`munich-via-sg` 또는 `munich`).
2. 접속되면 아래 패널의 **PORTS** 탭을 연다. 안 보이면 `Ctrl+Shift+P` → `Ports: Focus on Ports View`.
3. **Forward a Port** → `3000`, 다시 **Forward a Port** → `8000`. **둘 다** 필요하다. 화면(3000)이 브라우저에서 API(8000)를 직접 부른다.
4. **Local Address**가 `localhost:3000`, `localhost:8000`으로 정확히 같은 번호인지 확인한다.
   - 다른 번호(3001 등)로 잡히면 내 컴퓨터에서 그 포트를 쓰는 프로그램을 끄고 포워딩을 다시 추가한다.
5. **내 컴퓨터의 브라우저**에서 http://127.0.0.1:3000 을 연다.

### 터미널만 쓰는 경우

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 munich-via-sg   # 경로 A
ssh -N -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 munich          # 경로 B
```

이 터미널을 열어 둔 채 http://127.0.0.1:3000 을 연다.

### 안 될 때

| 증상 | 원인과 조치 |
| --- | --- |
| 브라우저에서 아예 안 열림 | 3000 포워딩이 없음. 또는 서버가 꺼져 있음. munich에서 `curl -s http://127.0.0.1:3000 -o /dev/null -w '%{http_code}'`로 확인한다 |
| 화면은 뜨는데 "불러오는 중…"이나 "API 서버에 연결할 수 없습니다" | 8000 포워딩이 없거나 다른 번호로 잡혔음. 내 브라우저에서 http://127.0.0.1:8000/api/health 가 열리는지 본다 |
| 서버가 꺼져 있음 | 컨테이너 주인(jwpark)이 아래 "서버 띄우기"로 다시 띄운다 |

### 주의

- 모두 **같은 DB를 함께 본다**(사용자 구분 없는 단일 사용자 프로토타입). 남이 시연 중인 프로젝트를 승인·수정하지 않는다. 각자 새 프로젝트를 만들어 쓴다.
- 현재 `.env`는 `APP_MODE=live`라 새 프로젝트는 실제 API를 호출하고 비용이 든다. demo로 연습하려면 컨테이너 주인에게 `APP_MODE=demo`로 바꿔 재시작해 달라고 한다.

### 서버 띄우기 (컨테이너 주인)

```bash
docker exec -d jwpark_kyrus_dev bash -lc 'cd /home/Paris/jwpark/1Kyrus/backend && exec .venv/bin/python -m app > /tmp/backend.log 2>&1'
docker exec -d jwpark_kyrus_dev bash -lc 'cd /home/Paris/jwpark/1Kyrus/frontend && exec npm run dev -- -H 0.0.0.0 > /tmp/frontend.log 2>&1'
curl -s http://127.0.0.1:8000/api/health    # {"status":"ok",...}
```

`.env`를 바꾸면 백엔드만 다시 띄운다: `docker exec jwpark_kyrus_dev bash -c 'pkill -f "[p]ython -m app"'` 후 첫 줄을 다시 실행한다.
