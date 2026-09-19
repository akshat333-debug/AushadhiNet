#!/usr/bin/env bash
# Verifies the README.md quickstart works verbatim from a fresh clone,
# with no manual edits beyond copying .env.example (modular-plan.md step
# 46's DoD). Does NOT run `docker compose up` -- see README.md's honest
# note on why (Docker daemon unavailable in the environment this project
# was built in); everything else in this script is a real, executed check.
set -euo pipefail
# Clones HEAD into a temp dir so gitignored local files (data/synthetic,
# .venv, node_modules) cannot mask a broken quickstart.
REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git clone -q "$REPO" "$WORK/clone"
cd "$WORK/clone"

echo "== 1. backend setup =="
uv sync --extra ml --extra dev
cp .env.example .env
uv run python -m eval.seal_generator

echo "== 2. backend tests =="
uv run pytest -q

echo "== 3. frontend setup =="
cd frontend
npm ci

echo "== 4. frontend build (compile check) =="
npx next build

echo "== 5. frontend e2e (starts real backend+frontend dev servers) =="
npx playwright test

echo
echo "All checks passed. Docker compose was not exercised by this script -- see README.md."
