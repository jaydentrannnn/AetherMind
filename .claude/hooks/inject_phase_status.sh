#!/usr/bin/env bash
# Injects current build phase status into Claude's context on every UserPromptSubmit.
# Stdout is added as context by Claude Code when this hook exits 0.

PLAN_FILE="${CLAUDE_PROJECT_DIR}/.cursor/plans/aethermind_research_agent_plan_2dc943b3.plan.md"

if [[ ! -f "$PLAN_FILE" ]]; then
  exit 0
fi

PENDING=$(grep -E '^\s+status: pending' "$PLAN_FILE" -B 3 | grep -E '^\s+id:' | sed 's/.*id: //' | tr '\n' ', ' | sed 's/, $//')
DONE=$(grep -E '^\s+status: done' "$PLAN_FILE" -B 3 | grep -E '^\s+id:' | sed 's/.*id: //' | tr '\n' ', ' | sed 's/, $//')

if [[ -z "$PENDING" && -z "$DONE" ]]; then
  exit 0
fi

echo "[AetherMind build status]"
[[ -n "$DONE" ]]    && echo "  Completed phases: ${DONE}"
[[ -n "$PENDING" ]] && echo "  Pending phases:   ${PENDING}"
echo "  Next: implement the first pending phase in order. Run /phase <id> to start."
