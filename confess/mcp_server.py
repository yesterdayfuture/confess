"""Confess MCP server — lets coding agents trigger the confession gate."""
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit(
        "MCP dependencies not installed.\n"
        "Install with:  pip install 'confess-cli[mcp]'"
    )

server = FastMCP("confess")


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-c", "core.quotepath=false", *args],
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
        ).strip()
    except subprocess.CalledProcessError:
        return ""


@server.tool()
def confess_diff(scope: str = "staged") -> str:
    """Return the current staged or unpushed diff summary.

    Args:
        scope: "staged" for staged changes, "unpushed" for commits ahead of origin.
    """
    if scope == "staged":
        output = _git("diff", "--cached", "--stat")
    elif scope == "unpushed":
        branch = _git("rev-parse", "--abbrev-ref", "HEAD")
        log = _git("log", f"origin/{branch}..HEAD", "--oneline")
        diff = _git("diff", f"origin/{branch}..HEAD", "--stat")
        output = f"{log}\n\n{diff}".strip()
    else:
        return f"Unknown scope: {scope!r}. Use 'staged' or 'unpushed'."
    return output or f"No {scope} changes detected."


@server.tool()
def confess_record(what: str, risk: str, verify: str) -> str:
    """Record a human-signed confession entry in CONFESSIONS.md.

    Args:
        what: What the code does, in the human's own words.
        risk: Most likely production failure cause.
        verify: 5-minute verification step.
    """
    if not (what and risk and verify):
        return "All three answers are required."
    sha = _git("rev-parse", "--short=12", "HEAD") or "unknown"
    entry = (
        f"\n## {datetime.now(timezone.utc).isoformat()} — `{sha}` (MCP-recorded)\n\n"
        f"### What does this code do?\n{what}\n\n"
        f"### If this breaks in production tomorrow, what is the most likely cause?\n{risk}\n\n"
        f"### How would you verify it's correct in under 5 minutes?\n{verify}\n"
    )
    with Path("CONFESSIONS.md").open("a", encoding="utf-8") as f:
        f.write(entry)
    return f"Confession recorded for {sha}. Commit CONFESSIONS.md with your changes."


if __name__ == "__main__":
    server.run()  # stdio transport by default
