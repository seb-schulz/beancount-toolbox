#!/bin/bash

set -xeu

rootdir=$(realpath "$(dirname "$0")/..")
uv sync --directory "${rootdir}"
npm ci || true

curl -fsSL https://claude.ai/install.sh | bash
