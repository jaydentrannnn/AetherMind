"""Migration sanity checks for Alembic revisions."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_alembic_upgrade_head_on_fresh_sqlite(tmp_path: Path) -> None:
    """Run Alembic upgrade against a fresh sqlite database file."""
    db_path = tmp_path / "phase3.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    result = subprocess.run(
        [".venv/Scripts/alembic.exe", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Alembic upgrade failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
