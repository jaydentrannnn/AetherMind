#!/usr/bin/env python3
"""stop: emit empty JSON (stdout). Reminder goes to stderr for Hooks output channel."""

from __future__ import annotations

import json
import sys


def main() -> None:
    raw = sys.stdin.read()
    if raw.strip():
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            pass

    print("{}")
    print(
        "Session ended. Reminder: mark any completed phase todos as done in the plan file, "
        "and run /run-tests to confirm nothing regressed.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
