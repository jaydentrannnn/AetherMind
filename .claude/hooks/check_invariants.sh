#!/usr/bin/env bash
# Blocks writes that violate AetherMind's invariants.
# Reads tool input JSON from stdin; exits 2 to block the write.

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path','') or d.get('tool_input',{}).get('path',''))" 2>/dev/null || echo "")
CONTENT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('new_string','') or d.get('tool_input',{}).get('content',''))" 2>/dev/null || echo "")

# Only audit backend Python files
if [[ "$FILE_PATH" != *"backend/app/"* ]] && [[ "$FILE_PATH" != *"backend\\app\\"* ]]; then
  exit 0
fi

# Normalise path separators for matching
NORM_PATH="${FILE_PATH//\\//}"

# Allowlisted paths for model strings
is_allowlisted() {
  local p="$1"
  [[ "$p" == *"backend/app/llm/router.py"* ]] && return 0
  [[ "$p" == *"backend/app/llm/client.py"* ]] && return 0
  [[ "$p" == *"backend/app/config.py"* ]] && return 0
  [[ "$p" == *"backend/app/embeddings/"* ]] && return 0
  [[ "$p" == *".env"* ]] && return 0
  return 1
}

VIOLATIONS=""

# Invariant 1 — model strings outside allowlisted locations
if ! is_allowlisted "$NORM_PATH"; then
  MODEL_PATTERNS=(
    'openai/gpt-5\.4'
    'openai/gpt-5\.4-mini'
    'ollama/'
    'anthropic/claude-'
    'BAAI/bge-'
    'all-MiniLM'
    'text-embedding-3-'
    'nomic-embed-text'
  )
  for pattern in "${MODEL_PATTERNS[@]}"; do
    if echo "$CONTENT" | grep -qE "$pattern"; then
      VIOLATIONS="${VIOLATIONS}\n  INVARIANT 1 (Router authority): Model string matching '${pattern}' found in ${NORM_PATH}.\n  Model strings must only appear in router.py, client.py, config.py, embeddings/, or .env* files.\n  Reference env keys (e.g. settings.MODEL_PLANNER) via the router instead."
    fi
  done
fi

# Invariant 2 — sentence_transformers import outside embeddings/
if [[ "$NORM_PATH" != *"backend/app/embeddings/"* ]]; then
  if echo "$CONTENT" | grep -qE '(from|import)\s+sentence_transformers'; then
    VIOLATIONS="${VIOLATIONS}\n  INVARIANT 2 (Embedding isolation): Direct sentence_transformers import in ${NORM_PATH}.\n  All embedding calls must go through backend/app/embeddings/. Import EmbeddingClient instead."
  fi
  if echo "$CONTENT" | grep -qE '"(api/embeddings|/api/embeddings)"'; then
    VIOLATIONS="${VIOLATIONS}\n  INVARIANT 2 (Embedding isolation): Direct Ollama embed endpoint call in ${NORM_PATH}.\n  Use EmbeddingClient from backend/app/embeddings/ instead."
  fi
fi

if [[ -n "$VIOLATIONS" ]]; then
  echo -e "INVARIANT VIOLATION — write blocked.\n${VIOLATIONS}" >&2
  exit 2
fi

exit 0
