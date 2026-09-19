#!/usr/bin/env bash
# Verifies the README.md quickstart works verbatim from a fresh clone,
# with no manual edits beyond copying .env.example (modular-plan.md step
# 46's DoD). Does NOT run `docker compose up` -- see README.md's honest
# note on why (Docker daemon unavailable in the environment this project
# was built in); everything else in this script is a real, executed check.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1. backend setup =="
uv sync --extra ml --extra dev --extra gcp
[ -f .env ] || cp .env.example .env

echo "== 2. backend tests =="
uv run pytest -q

echo "== 3. frontend setup =="
cd frontend
[ -d node_modules ] || npm install

echo "== 4. frontend build (compile check) =="
npx next build

echo "== 5. frontend e2e (starts real backend+frontend dev servers) =="
npx playwright test

echo
echo "All checks passed. Docker compose was not exercised by this script -- see README.md."
