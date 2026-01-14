#!/usr/bin/env bash
set -euo pipefail

missing=0

check_agent_header() {
  local path="$1"
  if ! rg -n "^## Agent" "$path" >/dev/null 2>&1; then
    echo "[missing] Agent header in $path"
    missing=1
  else
    echo "[ok] Agent header in $path"
  fi
}

for path in docs/logs/DEVELOPMENT_LOG.md; do
  if [[ -f "$path" ]]; then
    check_agent_header "$path"
  fi
 done

if compgen -G "docs/archive/conversations/CONVERSATION_LOG_ISSUE*.md" > /dev/null; then
  for path in docs/archive/conversations/CONVERSATION_LOG_ISSUE*.md; do
    check_agent_header "$path"
  done
fi

if compgen -G "docs/handover/HANDOVER_*.md" > /dev/null; then
  for path in docs/handover/HANDOVER_*.md; do
    check_agent_header "$path"
  done
fi

if [[ $missing -ne 0 ]]; then
  echo "\nTemplate compliance issues detected."
  exit 1
fi

echo "\nAll checked documents include Agent header."
