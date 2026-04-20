---
name: run-tests
description: Run the full AetherMind test suite — backend pytest (stop on first failure) and frontend lint + build check. Use after completing any phase or before committing.
allowed-tools: Bash(uv run pytest *) Bash(npm --prefix frontend *)
disable-model-invocation: true
---

Run all tests and report results:

```!
cd "$CLAUDE_SKILL_DIR/../../../" 2>/dev/null || true
BACKEND_EXISTS=0
FRONTEND_EXISTS=0
[ -d "backend" ] && BACKEND_EXISTS=1
[ -d "frontend" ] && FRONTEND_EXISTS=1

if [ $BACKEND_EXISTS -eq 0 ] && [ $FRONTEND_EXISTS -eq 0 ]; then
  echo "No backend/ or frontend/ directories yet — nothing to test (greenfield)."
  exit 0
fi

if [ $BACKEND_EXISTS -eq 1 ]; then
  echo "=== Backend tests ==="
  cd backend && uv run pytest tests/ -x --tb=short 2>&1 || echo "BACKEND TESTS FAILED"; cd ..
fi

if [ $FRONTEND_EXISTS -eq 1 ]; then
  echo "=== Frontend lint ==="
  npm --prefix frontend run lint 2>&1 || echo "FRONTEND LINT FAILED"
fi
```
