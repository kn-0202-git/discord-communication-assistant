#!/usr/bin/env bash
set -euo pipefail

issue="${1:-}"
missing=0

check_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "[missing] $path"
    missing=1
  else
    echo "[ok] $path"
  fi
}

check_file "docs/logs/DEVELOPMENT_LOG.md"
check_file "docs/planning/DEVELOPMENT_PLAN.md"
check_file "docs/planning/ISSUES_STATUS.md"

if [[ -n "$issue" ]]; then
  conv="docs/archive/conversations/CONVERSATION_LOG_ISSUE${issue}.md"
  check_file "$conv"

  if [[ -f "docs/logs/DEVELOPMENT_LOG.md" ]]; then
    if rg -n "Issue #${issue}" docs/logs/DEVELOPMENT_LOG.md >/dev/null 2>&1; then
      echo "[ok] docs/logs/DEVELOPMENT_LOG.md contains Issue #${issue}"
    else
      echo "[warn] docs/logs/DEVELOPMENT_LOG.md missing Issue #${issue}"
      missing=1
    fi
  fi
fi

if [[ $missing -ne 0 ]]; then
  echo "\nSome required records are missing."
  exit 1
fi

echo "\nAll required records are present."
