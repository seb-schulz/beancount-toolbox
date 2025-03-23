#!/bin/bash

set -xeu

rootdir=$(realpath "$(dirname "$0")/..")

python3 -m venv --clear --upgrade-deps  --prompt="$(basename ${rootdir})" "${rootdir}/venv"
"${rootdir}/venv/bin/python" -m pip install -r requirements.txt

"${rootdir}/venv/bin/python" -m pip install pytest

npm ci || true
