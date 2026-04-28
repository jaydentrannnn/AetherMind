"""Migration sanity checks for Alembic revisions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

def test_alembic_upgrade_head_on_fresh_sqlite(tmp_path: Path) -> None:
    """Run Alembic upgrade against a fresh sqlite database file."""
    db_path = tmp_path / "phase3.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    scripts_dir = Path(sys.executable).resolve().parent / "Scripts"
    alembic_exe = scripts_dir / "alembic.exe"
    command_path = str(alembic_exe) if alembic_exe.exists() else shutil.which("alembic")
    if command_path is None:
        pytest.skip("alembic CLI is not available in this Python environment")

    result = subprocess.run(
        [command_path, "upgrade", "head"],
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
