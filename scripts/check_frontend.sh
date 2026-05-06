#!/usr/bin/env bash
# Syntax check for the HACS panel's frontend JS. Run before committing any
# change to custom_components/ha_llm_automation/frontend/*.js. Catches the
# class of bug that whitescreened v2.6 (unescaped ASCII " inside string
# literals — SyntaxError at module load → customElements.define never runs).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/custom_components/ha_llm_automation/frontend"

if ! command -v node >/dev/null 2>&1; then
  echo "error: node not found on PATH. Install Node.js (any 18+)." >&2
  exit 127
fi

fail=0
shopt -s nullglob
for js in "$FRONTEND_DIR"/*.js; do
  if node --check "$js"; then
    echo "ok: $js"
  else
    fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  echo "FAIL: at least one frontend JS file has a syntax error." >&2
  exit 1
fi
echo "All frontend JS files parse cleanly."
