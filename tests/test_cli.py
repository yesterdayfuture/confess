"""CLI smoke tests for confess init / check / uninstall."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd, cwd, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    _run(["git", "commit", "--allow-empty", "-m", "init"], repo)
    return repo


def test_init_check_uninstall(git_repo):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    r = _run([sys.executable, "-m", "confess", "init"], git_repo, env)
    assert r.returncode == 0, r.stderr
    assert "Confess hook installed" in r.stdout

    hook = git_repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file()
    content = hook.read_text(encoding="utf-8")
    assert content.startswith(f"#!{sys.executable}")
    assert "CONFESS" in content
    # Shebang line must stay LF-only (no CR) for Git bash on Windows.
    assert "\r" not in content.splitlines(keepends=True)[0]

    r = _run([sys.executable, "-m", "confess", "check"], git_repo, env)
    assert r.returncode == 0
    assert "installed" in r.stdout.lower()

    r = _run([sys.executable, "-m", "confess", "uninstall"], git_repo, env)
    assert r.returncode == 0
    assert not hook.exists()


def test_init_backs_up_existing_hook(git_repo):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    hook = git_repo / ".git" / "hooks" / "pre-push"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\necho old\n", encoding="utf-8", newline="\n")

    r = _run([sys.executable, "-m", "confess", "init"], git_repo, env)
    assert r.returncode == 0
    assert "Backed up" in r.stdout
    bak = Path(str(hook) + ".confess-bak")
    assert bak.exists()
    assert "old" in bak.read_text(encoding="utf-8")

    _run([sys.executable, "-m", "confess", "uninstall"], git_repo, env)
    assert hook.exists()
    assert "old" in hook.read_text(encoding="utf-8")
