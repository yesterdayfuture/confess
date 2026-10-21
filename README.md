# Confess

**English** | [中文](README.zh-CN.md)

**Confess** is a local Git **pre-push gate** for AI-assisted work: when a commit carries markers such as `Co-Authored-By: Claude` / Copilot / Cursor / Codex / Aider, the push pauses until you answer three short questions in your own words—what the change does, how it is most likely to break, and how you would verify it in five minutes. Answers (and every deliberate skip) are appended to `CONFESSIONS.md` in the same repository, so the explanation travels with the code.

It is not another AI reviewer. Confess never calls an LLM, never amends your history, and never scores whether the answer is “right.” Its job is narrower and more reliable: **force a human pause, capture a human-signed trace, and make skips auditable**—before the change leaves your machine.

Works with any language and any repo. The hook is pure Python stdlib (zero runtime dependencies); an optional MCP server lets Claude Code / Cursor pull a diff summary and record a confession earlier in the loop.

```bash
git clone <this-repo-url> confess
cd confess
pipx install .
# or: pip install -e .
confess init
```

→ the next `git push` of an AI-assisted commit opens your `$EDITOR` for those three questions.

> **Status:** v0.1 is distributed from this repository only. It is **not** published to PyPI yet — do not run `pip install confess-cli` / `pipx install confess-cli` from the registry.

---

## Why Confess exists

AI coding tools make it easy to land large diffs you did not fully author. Reviews and CI still miss a practical failure mode: **the change ships, but nobody on the team can explain what it does, how it fails, or how to check it in minutes.**

Confess sits at the last local checkpoint—`git push`—and turns that gap into a habit: three questions, written by a human, stored next to the code. Over time `CONFESSIONS.md` becomes a lightweight evidence format for incident review, onboarding, and “who understood this change?”—not another semantic checker competing with LLMs.

---

## What it does

| Piece | Role |
|---|---|
| `confess` CLI | Install / verify / remove the Git `pre-push` hook |
| `pre-push` hook | Pure stdlib Python; scans commits about to be pushed |
| `CONFESSIONS.md` | Append-only log of answers (and skips) next to your code |
| Optional MCP server | Lets agents fetch a diff summary and record a confession early |

**Detection** is intentionally narrow: the hook looks for known trailers / markers in the **commit message** (case-insensitive), for example:

- `Co-Authored-By: Claude` / `Copilot` / `Cursor` / `Codex` / `Aider`
- `Generated-By:` / `Generated-With:` variants
- `🤖 Generated with`

It does **not** scan source files. If you strip the trailer, Confess stays silent — that is a deliberate choice, not a bug.

**When it fires**, you answer in `$EDITOR` (recommended; hook stdin is the ref list, not a TTY):

1. What does this code do? (your words, not a paste of comments)  
2. If this breaks in production tomorrow, what is the most likely cause?  
3. How would you verify it in under 5 minutes?

Answers are written to `CONFESSIONS.md` and staged. You commit that file, then push again. The second push succeeds because the AI commit’s SHA prefix is already on record — no infinite block loop.

**Skip is first-class** for hotfixes: set `CONFESS_SKIP=1` and the push proceeds, but a `SKIPPED` line is still recorded.

---

## Install (from this repo — not PyPI)

Requires Python 3.9+ and Git.

### Option A — `pipx` from a local checkout (recommended)

Keeps Confess in an isolated environment and puts `confess` on your `PATH`:

```bash
git clone <this-repo-url> confess
cd confess
pipx install .
```

Upgrade later from the same directory after `git pull`:

```bash
pipx install . --force
```

### Option B — editable install (development)

```bash
git clone <this-repo-url> confess
cd confess
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # add [mcp] if you want the MCP server
confess --help
```

### Option C — `uv`

```bash
git clone <this-repo-url> confess
cd confess
uv tool install .
# or for a project venv:
uv pip install -e .
```

### Option D — plain `pip` (user site)

```bash
git clone <this-repo-url> confess
cd confess
pip install --user .
```

After any of the above, in **each application repository** where you want the gate:

```bash
cd /path/to/your-app-repo
confess init
confess check
```

`confess init` writes `.git/hooks/pre-push` with a shebang set to the **absolute path** of the Python that installed Confess (so pipx / uv / pyenv setups keep working). On Windows it forces LF line endings so Git Bash does not treat `\r` as part of the interpreter path.

---

## Usage

```bash
cd your-repo
confess init      # install pre-push hook (backs up any existing hook)
confess check     # verify installation
confess uninstall # remove Confess; restore previous hook if backed up
```

### Choosing / switching the editor

The hook opens **three** temporary files in sequence (one per question). It picks an editor in this order:

1. `$EDITOR`
2. `$VISUAL`
3. first available of `nano`, `vim`, `vi`

**Switch for the current shell** (recommended before `git push`):

```bash
export EDITOR=vim          # or: nano, code --wait, subl -w, ...
git push
```

**Make it permanent** (add to `~/.zshrc` or `~/.bashrc`):

```bash
export EDITOR=vim
```

| Editor | Write your answer | Save & exit |
|---|---|---|
| **nano** | Arrow keys ↓ to the blank line under the HTML comment, then type | `Ctrl+O`, `Enter`, then `Ctrl+X` (use **Control**, not ⌘ on macOS) |
| **vim** | Press `i`, type, then `Esc` | `:wq` then `Enter` |
| **VS Code** | `export EDITOR="code --wait"` | Save the tab (`⌘S` / `Ctrl+S`), close the tab/window |
| **Sublime** | `export EDITOR="subl -w"` | Save and close the window |

Notes:

- Git hook stdin is the ref list, **not** a TTY — do not rely on interactive `input()`; always set an editor.
- If `Ctrl+X` does nothing in nano inside Cursor/VS Code’s terminal, finish the push in **Terminal.app**, or switch to `vim` / `code --wait`.
- Stuck editor: open another terminal and run `pkill -f nano` (or `vim`), then `git push` again.

### Skipping

```bash
CONFESS_SKIP=1 CONFESS_SKIP_REASON="hotfix" git push
```

The skip is written to `CONFESSIONS.md` and the push proceeds immediately. **Every skip is on record.**

---

## How the gate works (flow)

```text
git push
  → pre-push reads refs from stdin
  → for each commit: commit message match AI markers?
       no  → allow
       yes → SHA already in CONFESSIONS.md?
                yes → allow
                no  → CONFESS_SKIP set?
                         yes → append SKIPPED, stage file, allow (exit 0)
                         no  → open $EDITOR × 3 questions
                                incomplete → block (exit 1)
                                complete   → append answers, stage, block (exit 1)
                                             so you commit CONFESSIONS.md then push again
```

Design choices worth knowing:

- **SHA prefix match** in `CONFESSIONS.md` prevents re-blocking after you commit the confession.  
- **`--diff-filter=ACMR`** — deletions are ignored (nothing executable to confess).  
- **No LLM, no amend** — Confess never rewrites your history or scores answers.

---

## MCP server (optional)

Install the optional extra from the same checkout:

```bash
cd /path/to/confess
pip install -e ".[mcp]"
python -m confess.mcp_server
```

Claude Code / Cursor MCP config (point `command` at the interpreter that has the package):

```json
{
  "mcpServers": {
    "confess": {
      "command": "python",
      "args": ["-m", "confess.mcp_server"]
    }
  }
}
```

Tools:

- `confess_diff(scope)` — `"staged"` or `"unpushed"` diff summary  
- `confess_record(what, risk, verify)` — append a confession entry  

---

## Use cases & examples

- End-to-end scenarios (gate, skip, uninstall, MCP): [docs/USE_CASES.md](docs/USE_CASES.md)  
- Sample log: [examples/CONFESSIONS.sample.md](examples/CONFESSIONS.sample.md)

---

## What Confess deliberately does not do

- Judge whether your answer is “correct” (that would reintroduce LLM-shaped unreliability).  
- Rewrite or amend your commits.  
- Call an LLM — the point is a **human-signed** trace.  
- Guess AI authorship from source code; only commit-message markers count.

---

## Project layout

```text
confess/
├── pyproject.toml          # package: confess-cli
├── confess/
│   ├── cli.py              # init / check / uninstall
│   ├── mcp_server.py       # optional MCP
│   └── data/pre-push       # hook template (stdlib only)
├── docs/                   # bilingual use cases
├── examples/               # sample CONFESSIONS.md
└── tests/
```

---

## License

MIT
