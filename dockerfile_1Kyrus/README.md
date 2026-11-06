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
