"""confess CLI — install and manage the pre-push confession gate."""
import argparse
import os
import re
import shutil
import sys
from importlib.resources import files


def _hook_source() -> str:
    """Load the hook template from package data."""
    return files("confess").joinpath("data", "pre-push").read_text(encoding="utf-8")


def _git_dir() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("✗ Not inside a git repository.")


def cmd_init(_args) -> None:
    hook_dest = os.path.join(_git_dir(), "hooks", "pre-push")
    os.makedirs(os.path.dirname(hook_dest), exist_ok=True)

    if os.path.exists(hook_dest):
        backup = f"{hook_dest}.confess-bak"
        shutil.copy2(hook_dest, backup)
        print(f"⚠  Backed up existing pre-push to {backup}")

    content = _hook_source()
    # Replace shebang with the absolute path to *this* Python interpreter.
    # Guarantees the hook uses the same venv / system Python that installed
    # confess-cli, which matters under pipx / uv / pyenv.
    content = re.sub(r"^#![^\n]*", f"#!{sys.executable}", content, count=1)

    # newline="\n" keeps LF even on Windows (shebang line must not end in CRLF).
    with open(hook_dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.chmod(hook_dest, 0o755)

    print(f"✓ Confess hook installed at {hook_dest}")
    print("  Next `git push` involving AI-assisted commits will trigger the gate.")


def cmd_check(_args) -> None:
    hook_dest = os.path.join(_git_dir(), "hooks", "pre-push")
    if not os.path.exists(hook_dest):
        print("✗ Not installed. Run `confess init`.")
        sys.exit(1)
    content = open(hook_dest, encoding="utf-8", errors="ignore").read()
    if "CONFESS" in content:
        print("✓ Confess hook is installed.")
    else:
        print("⚠ pre-push exists but does not look like Confess.")


def cmd_uninstall(_args) -> None:
    hook_dest = os.path.join(_git_dir(), "hooks", "pre-push")
    backup = f"{hook_dest}.confess-bak"
    if not os.path.exists(hook_dest):
        print("Nothing to uninstall.")
        return
    os.unlink(hook_dest)
    print("✓ Confess hook removed.")
    if os.path.exists(backup):
        shutil.move(backup, hook_dest)
        print("  Previous pre-push restored from backup.")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="confess",
        description="Explain AI-assisted code before it ships. A Git pre-push gate.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Install the pre-push hook")
    sub.add_parser("check", help="Verify installation")
    sub.add_parser("uninstall", help="Remove the Confess hook")
    args = parser.parse_args(argv)

    {"init": cmd_init, "check": cmd_check, "uninstall": cmd_uninstall}.get(
        args.command, lambda _: parser.print_help()
    )(args)


if __name__ == "__main__":
    main()
