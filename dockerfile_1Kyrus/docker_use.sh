#!/usr/bin/env bash
# 1Kyrus 개발 컨테이너를 띄우거나 재사용하고 셸을 연다.
# Usage: docker_use.sh [LABEL] [WEB_PORT] [API_PORT]   (기본: dev 3000 8000)
# NO_SHELL=1 이면 컨테이너만 띄우고 셸은 열지 않는다.
set -euo pipefail

LABEL="${1:-dev}"
WEB_PORT="${2:-3000}"
API_PORT="${3:-8000}"

if [[ ! "${LABEL}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "LABEL may contain only letters, numbers, dot, underscore, and dash." >&2
    exit 1
fi
for p in "${WEB_PORT}" "${API_PORT}"; do
    if [[ ! "${p}" =~ ^[0-9]+$ ]] || (( p < 1 || p > 65535 )); then
        echo "PORT must be an integer between 1 and 65535: ${p}" >&2
        exit 1
    fi
done

IMAGE_NAME="${IMAGE_NAME:-jwpark/1kyrus:latest}"
HOST_ROOT="/home/Paris/jwpark"
WORKSPACE="${HOST_ROOT}/1Kyrus"
CONTAINER_NAME="jwpark_kyrus_${LABEL}"
CODEX_VOLUME="jwpark_kyrus_codex"
CLAUDE_VOLUME="jwpark_kyrus_claude"

if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "Docker image is missing: ${IMAGE_NAME}" >&2
    echo "Build it first with: $(dirname "$0")/build_docker.sh" >&2
    exit 1
fi

if docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    EXPECTED_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "${IMAGE_NAME}")"
    EXISTING_IMAGE_ID="$(docker inspect --format '{{.Image}}' "${CONTAINER_NAME}")"
    if [[ "${EXISTING_IMAGE_ID}" != "${EXPECTED_IMAGE_ID}" ]]; then
        echo "Container ${CONTAINER_NAME} uses an older image." >&2
        echo "Remove it or use another LABEL before attaching." >&2
        exit 1
    fi
    EXISTING_PORTS="$(docker inspect --format '{{ index .Config.Labels "kyrus.ports" }}' "${CONTAINER_NAME}")"
    if [[ "${EXISTING_PORTS}" != "${WEB_PORT},${API_PORT}" ]]; then
        echo "Container ${CONTAINER_NAME} was created with ports ${EXISTING_PORTS}, not ${WEB_PORT},${API_PORT}." >&2
        echo "Use a different LABEL or remove the existing container first." >&2
        exit 1
    fi
    if [[ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}")" != "true" ]]; then
        docker start "${CONTAINER_NAME}" >/dev/null
    fi
    echo "Reusing container: ${CONTAINER_NAME}"
else
    # 공유 서버라 다른 사람이 이미 쓰는 호스트 포트인지 먼저 본다.
    for p in "${WEB_PORT}" "${API_PORT}"; do
        if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${p}\$"; then
            echo "Host port ${p} is already in use. Pick other ports." >&2
            exit 1
        fi
    done
    # 컨테이너 안 포트는 3000/8000 고정, 호스트 쪽은 127.0.0.1에만 연다.
    # BACKEND_HOST=0.0.0.0은 포트 포워딩용 개발 전용 값이다(.env 기본값은 그대로 둔다).
    docker run --detach \
        --init \
        --user jwpark \
        --mount "type=bind,src=${HOST_ROOT},dst=${HOST_ROOT}" \
        --mount "type=volume,src=${CODEX_VOLUME},dst=/home/jwpark/.codex" \
        --mount "type=volume,src=${CLAUDE_VOLUME},dst=/home/jwpark/.claude" \
        --env "BACKEND_HOST=0.0.0.0" \
        --name "${CONTAINER_NAME}" \
        --hostname "${CONTAINER_NAME}" \
        --workdir "${WORKSPACE}" \
        --publish "127.0.0.1:${WEB_PORT}:3000" \
        --publish "127.0.0.1:${API_PORT}:8000" \
        --label "kyrus.role=dev" \
        --label "kyrus.ports=${WEB_PORT},${API_PORT}" \
        "${IMAGE_NAME}" >/dev/null
    echo "Started container: ${CONTAINER_NAME}"
fi

cat <<EOF

Ports (host 127.0.0.1 -> container):
  web ${WEB_PORT} -> 3000,  api ${API_PORT} -> 8000

VS Code:
  1. Dev Containers: Attach to Running Container... -> ${CONTAINER_NAME}
  2. Open: ${WORKSPACE}

Verification:
  node -v            # v22.x
  python3.11 -V      # 3.11.x
  uv --version
EOF

if [[ "${NO_SHELL:-0}" == "1" ]]; then
    exit 0
fi
echo "Opening container shell now."
docker exec --interactive --tty --workdir "${WORKSPACE}" "${CONTAINER_NAME}" /bin/bash --login
