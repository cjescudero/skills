#!/usr/bin/env bash
# Hook base de SessionStart

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILLS_DIR="${PLUGIN_ROOT}/skills"

if [ ! -d "$SKILLS_DIR" ]; then
  cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<IMPORTANT>No se encontro la carpeta skills/</IMPORTANT>"
  }
}
JSON
  exit 0
fi

SKILL_FILES=$(
  find "$SKILLS_DIR" -type f -name "SKILL.md" ! -path "*/_templates/*" | sort
)

if [ -z "$SKILL_FILES" ]; then
  cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<IMPORTANT>No se encontraron archivos SKILL.md en skills/</IMPORTANT>"
  }
}
JSON
  exit 0
fi

CONTENT=""
while IFS= read -r SKILL_FILE; do
  [ -z "$SKILL_FILE" ] && continue
  RELATIVE_PATH="${SKILL_FILE#${PLUGIN_ROOT}/}"
  SKILL_CONTENT=$(cat "$SKILL_FILE")
  BLOCK="# Source: ${RELATIVE_PATH}"$'\n'"${SKILL_CONTENT}"
  if [ -z "$CONTENT" ]; then
    CONTENT="$BLOCK"
  else
    CONTENT+=$'\n\n'"$BLOCK"
  fi
done <<< "$SKILL_FILES"

ESCAPED=${CONTENT//$'\\'/\\\\}
ESCAPED=${ESCAPED//$'"'/\\\"}
ESCAPED=${ESCAPED//$'\n'/\\n}

cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<EXTREMELY_IMPORTANT>You have local skills.\\n\\n${ESCAPED}\\n</EXTREMELY_IMPORTANT>"
  }
}
JSON
