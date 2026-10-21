"""Unit-style tests for hook helpers (loaded from package data)."""
import importlib.machinery
import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "confess" / "data" / "pre-push"


def load_hook():
    # Hook file is extensionless (Git hook name); load via SourceFileLoader.
    loader = importlib.machinery.SourceFileLoader("confess_pre_push", str(HOOK_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def hook():
    return load_hook()


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def test_is_ai_assisted_detects_trailers(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    subprocess.run(
        [
            "git",
            "commit",
            "--allow-empty",
            "-m",
            "feat\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
        ],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=git_repo, text=True
    ).strip()
    assert hook.is_ai_assisted(sha) is True


def test_is_ai_assisted_ignores_plain_commits(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=git_repo, text=True
    ).strip()
    assert hook.is_ai_assisted(sha) is False


def test_already_confessed_prefix_match(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    sha = "abcdef0123456789deadbeef"
    (git_repo / "CONFESSIONS.md").write_text(
        f"## 2026-01-01T00:00:00+00:00 — `{sha[:12]}`\n\n**SKIPPED**: test\n",
        encoding="utf-8",
    )
    found = hook.already_confessed([sha, "0000000000000000ffffffff"])
    assert found == {sha}


def test_decode_git_path_octal_chinese(hook):
    quoted = r'"\346\234\252\345\221\275\345\220\215 2.txt"'
    assert hook.decode_git_path(quoted) == "未命名 2.txt"
    assert hook.decode_git_path("plain.py") == "plain.py"


def test_changed_files_keeps_unicode_names(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    name = "未命名 2.txt"
    (git_repo / name).write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add chinese name"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    local = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=git_repo, text=True
    ).strip()
    parent = subprocess.check_output(
        ["git", "rev-parse", "HEAD~1"], cwd=git_repo, text=True
    ).strip()
    files = hook.changed_files(local, parent)
    assert name in files
    assert not any("\\346" in f for f in files)

    # Even if git quotes paths, the decoder recovers UTF-8.
    assert hook.decode_git_path(r'"\346\234\252\345\221\275\345\220\215 2.txt"') == name


def test_append_confession_writes_unicode_filenames(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    sha = "c" * 40
    hook.append_confession(sha, ["未命名 2.txt", "app.py"], answers={
        "what": "x", "risk": "y", "verify": "z",
    })
    text = (git_repo / "CONFESSIONS.md").read_text(encoding="utf-8")
    assert "未命名 2.txt" in text
    assert "\\346" not in text


def test_append_confession_skip(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    sha = "a" * 40
    hook.append_confession(sha, ["a.py"], skipped=True, skip_reason="hotfix")
    text = (git_repo / "CONFESSIONS.md").read_text(encoding="utf-8")
    assert f"`{sha[:12]}`" in text
    assert "**SKIPPED**: hotfix" in text


def test_append_confession_answers(hook, git_repo, monkeypatch):
    monkeypatch.chdir(git_repo)
    sha = "b" * 40
    answers = {"what": "does X", "risk": "Y fails", "verify": "run tests"}
    hook.append_confession(sha, ["x.py"], answers=answers)
    text = (git_repo / "CONFESSIONS.md").read_text(encoding="utf-8")
    assert "does X" in text
    assert "Y fails" in text
    assert "run tests" in text
    assert re.search(rf"—\s*`{sha[:12]}`", text)


def test_skip_env_allows_push_simulation(hook, git_repo, monkeypatch):
    """Simulate skip path: AI commit + CONFESS_SKIP=1 → exit 0 and record."""
    monkeypatch.chdir(git_repo)
    (git_repo / "app.py").write_text("print(1)\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=git_repo, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "add\n\nCo-Authored-By: Cursor <cursor@example.com>",
        ],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    local = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=git_repo, text=True
    ).strip()
    remote = "0" * 40
    stdin = f"refs/heads/main {local} refs/heads/main {remote}\n"
    monkeypatch.setenv("CONFESS_SKIP", "1")
    monkeypatch.setenv("CONFESS_SKIP_REASON", "ci")
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    rc = hook.main()
    assert rc == 0
    assert (git_repo / "CONFESSIONS.md").exists()
    assert "SKIPPED" in (git_repo / "CONFESSIONS.md").read_text(encoding="utf-8")
