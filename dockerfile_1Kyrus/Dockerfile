# 1Kyrus 개발용 이미지 (Node 22 + Python 3.11, GPU 없음).
#
# 제출물에는 포함하지 않는다. 앱은 Docker 없이 venv + npm으로 실행되어야 한다
# (implementation_plan.md T01). 이 이미지는 Node가 없는 호스트에서 개발하기 위한 것이다.
#
# 베이스는 glibc 2.33 이하여야 한다. 호스트 Docker 20.10.2의 seccomp가 glibc 2.34+의
# clone3를 막아서, Debian bookworm·Ubuntu 22.04 이상에서는 Node가 스레드 생성 단계에서
# abort한다. Debian bullseye는 2026-08 지원 종료로 apt 보안 저장소가 404를 낸다.
# 그래서 3D_HGS와 같은 Ubuntu 20.04(glibc 2.31)에 Node 공식 바이너리를 얹는다.
FROM ubuntu:20.04

ARG USERNAME=jwpark
ARG UID=1030
ARG GID=1030
ARG TZ=Asia/Seoul
ARG UV_VERSION=0.8.17
ARG NODE_VERSION=22.23.2

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=${TZ}

RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        htop \
        iproute2 \
        procps \
        sqlite3 \
        sudo \
        tmux \
        vim \
        wget \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

# --- Node 22 (공식 바이너리) ---------------------------------------------------
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
        | tar -xJ -C /usr/local --strip-components=1 \
    && node -v && npm -v

# --- uv + Python 3.11 (Ubuntu 20.04 apt에는 3.11이 없다) ----------------------
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
ENV UV_PYTHON_PREFERENCE=only-managed
# 소스가 NAS bind mount라 캐시와 파일시스템이 달라 hardlink가 실패한다.
ENV UV_LINK_MODE=copy
RUN curl -fLsS "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" \
        | tar -xz -C /usr/local/bin --strip-components=1 \
    && uv python install 3.11 \
    && ln -s "$(uv python find 3.11)" /usr/local/bin/python3.11 \
    && chmod -R a+rX "${UV_PYTHON_INSTALL_DIR}"

# --- 호스트 UID/GID를 쓰는 non-root 사용자 ------------------------------------
RUN if getent group "${GID}" >/dev/null; then \
        USER_GROUP="$(getent group "${GID}" | cut -d: -f1)"; \
    else \
        groupadd --gid "${GID}" "${USERNAME}"; \
        USER_GROUP="${USERNAME}"; \
    fi \
    && useradd --uid "${UID}" --gid "${USER_GROUP}" --create-home --shell /bin/bash "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

RUN mkdir -p \
        "/home/${USERNAME}/.claude" \
        "/home/${USERNAME}/.codex" \
        "/home/${USERNAME}/.vscode-server" \
        "/home/Paris/jwpark/1Kyrus" \
    && chown -R "${UID}:${GID}" "/home/${USERNAME}" "/home/Paris/jwpark"

ENV HOME=/home/${USERNAME}
ENV CLAUDE_CONFIG_DIR=/home/${USERNAME}/.claude
ENV PYTHONUNBUFFERED=1
ENV NEXT_TELEMETRY_DISABLED=1

USER ${USERNAME}
WORKDIR /home/Paris/jwpark/1Kyrus

CMD ["sleep", "infinity"]
