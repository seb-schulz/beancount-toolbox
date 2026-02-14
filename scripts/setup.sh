#!/bin/bash

set -xeu

rootdir=$(realpath "$(dirname "$0")/..")
uv sync --directory "${rootdir}" --group dev
uv pip install -e '.[dev]'
npm ci || true
