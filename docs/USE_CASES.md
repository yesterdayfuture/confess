# Use Cases

**English** | [中文](USE_CASES.zh-CN.md)

End-to-end scenarios for Confess v0.1. The package is **not on PyPI** yet — install from a local checkout:

```bash
cd /path/to/confess
pip install -e .                 # or: pipx install .
# optional MCP: pip install -e ".[mcp]"
```

---

## 1. Happy path — gate blocks, then allows

```bash
# Prepare a throwaway repo + bare remote
git init /tmp/confess-demo && cd /tmp/confess-demo
git config user.email "dev@example.com"
git config user.name "Dev"
git commit --allow-empty -m "init"
git init --bare /tmp/confess-demo-remote.git
git remote add origin /tmp/confess-demo-remote.git
git branch -M main

confess init
# ✓ Confess hook installed at .git/hooks/pre-push

echo "print('hello')" > app.py
git add app.py
git commit -m "add greeting

Co-Authored-By: Claude <noreply@anthropic.com>"

# First push: blocked after you answer in $EDITOR
export EDITOR=vim   # or nano
git push -u origin main
# → CONFESSIONS.md staged; push exits non-zero

git commit -m "confess: explain $(git rev-parse --short HEAD~1)"
git push
# → allowed (SHA already in CONFESSIONS.md)
```

**Expect:** first push records three answers; second push passes without re-asking.

---

## 2. Switch the answer editor

Confess uses `$EDITOR`, then `$VISUAL`, then `nano` / `vim` / `vi`.

```bash
# Current shell only
export EDITOR=vim
# GUI options (block until you close the file):
# export EDITOR="code --wait"
# export EDITOR="subl -w"

git push
```

Persist in `~/.zshrc` / `~/.bashrc`:

```bash
export EDITOR=vim
```

| Editor | Answer | Save & quit |
|---|---|---|
| nano | ↓ to the blank line under the comment, type | `Ctrl+O`, Enter, `Ctrl+X` (**Control**, not ⌘) |
| vim | `i` … `Esc` | `:wq` Enter |
| VS Code | edit the temp `.md` | save + close tab (`code --wait`) |

If nano shortcuts fail in Cursor’s integrated terminal, use macOS Terminal.app or switch to `vim` / `code --wait`. Stuck: `pkill -f nano` in another window, then push again.

Full notes: [README — Choosing / switching the editor](../README.md#choosing--switching-the-editor).

---

## 3. Skip path — hotfix with audit trail

```bash
echo "x=1" > b.py && git add b.py
git commit -m "tweak

Co-Authored-By: Copilot <noreply@github.com>"

CONFESS_SKIP=1 CONFESS_SKIP_REASON="hotfix" git push
```

**Expect:** push succeeds immediately; `CONFESSIONS.md` gains a `**SKIPPED**: hotfix` entry (staged by the hook — commit it when convenient).

---

## 4. Non-AI commit — no prompt

```bash
echo "# note" >> README.md
git add README.md
git commit -m "docs: note"
git push
```

**Expect:** no Confession UI; push proceeds normally.

---

## 5. Install / check / uninstall

```bash
confess check      # ✓ Confess hook is installed.
confess uninstall  # removes hook; restores *.confess-bak if present
confess check      # ✗ Not installed.
confess init       # reinstall
```

If a previous `pre-push` existed, `init` copies it to `pre-push.confess-bak`, and `uninstall` restores it.

---

## 6. MCP — proactive confession from an agent

```bash
cd /path/to/confess
pip install -e ".[mcp]"
python -m confess.mcp_server
```

From an MCP client:

1. Call `confess_diff` with `scope="staged"` or `"unpushed"`.
2. After a human reviews the diff, call `confess_record` with `what` / `risk` / `verify`.
3. Commit `CONFESSIONS.md` with the feature commit (or as a follow-up).

**Expect:** entry marked `(MCP-recorded)` in `CONFESSIONS.md`. Note: MCP-recorded SHAs use `HEAD` at record time; for push-gate matching, prefer answering during `git push` so the AI commit SHA is written.

---

## 7. Sample CONFESSIONS.md entry

```markdown
## 2026-10-20T16:00:00+00:00 — `a1b2c3d4e5f6`

**Files**: app.py

### What does this code do? (your own words, not a paste of comments)
Prints a greeting when the script runs.

### If this breaks in production tomorrow, what is the most likely cause?
Someone imports the module expecting a function instead of side effects.

### How would you verify it's correct in under 5 minutes?
Run `python app.py` and confirm stdout is `hello`.
```

---

## Design notes (why it behaves this way)

| Behavior | Reason |
|---|---|
| Match SHA prefix in `CONFESSIONS.md` | Avoid infinite block after you commit the confession |
| `--diff-filter=ACMR` | Deletions need no confession |
| Prefer `$EDITOR` over `input()` | Hook stdin is the ref list, not a TTY |
| Skip returns 0; normal path returns 1 | Skip truly proceeds; normal path forces a confession commit |
| Markers only in commit messages | No false positives from source content |
