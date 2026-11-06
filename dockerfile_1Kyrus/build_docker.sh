#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="${IMAGE_NAME:-jwpark/1kyrus:latest}"
CONTAINER_USER="${CONTAINER_USER:-jwpark}"

docker build \
    --file "${SCRIPT_DIR}/Dockerfile" \
    --build-arg "USERNAME=${CONTAINER_USER}" \
    --build-arg "UID=$(id -u)" \
    --build-arg "GID=$(id -g)" \
    --tag "${IMAGE_NAME}" \
    "${SCRIPT_DIR}"

printf 'Built image: %s\n' "${IMAGE_NAME}"
