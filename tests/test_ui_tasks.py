import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ui_tasks_match_the_cli():
    """ui.json names real commands and options: fails when the CLI changes under it."""
    r = subprocess.run([str(ROOT / "ui.sh"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "tasks OK" in r.stdout
