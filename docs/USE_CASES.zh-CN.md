# 用例

[English](USE_CASES.md) | **中文**

Confess v0.1 端到端场景。包**尚未上传 PyPI**——请从本地检出安装：

```bash
cd /path/to/confess
pip install -e .                 # 或: pipx install .
# 可选 MCP: pip install -e ".[mcp]"
```

---

## 1. 主路径 — 先拦后放

```bash
# 准备临时仓库 + bare remote
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

# 第一次 push：在 $EDITOR 里答完后被拦截
export EDITOR=vim   # 或 nano
git push -u origin main
# → CONFESSIONS.md 被 stage；push 以非零退出

git commit -m "confess: explain $(git rev-parse --short HEAD~1)"
git push
# → 放行（SHA 已在 CONFESSIONS.md）
```

**预期：** 第一次 push 写入三条问答；第二次不再追问。

---

## 2. 切换答题编辑器

Confess 依次使用 `$EDITOR`、`$VISUAL`，再回退到 `nano` / `vim` / `vi`。

```bash
# 仅当前终端
export EDITOR=vim
# 图形界面（关掉文件后才继续）：
# export EDITOR="code --wait"
# export EDITOR="subl -w"

git push
```

写入 `~/.zshrc` / `~/.bashrc` 可长期生效：

```bash
export EDITOR=vim
```

| 编辑器 | 填写 | 保存退出 |
|---|---|---|
| nano | ↓ 移到注释下方空行再输入 | `Ctrl+O`，Enter，`Ctrl+X`（用 **Control**，不是 ⌘） |
| vim | `i` … `Esc` | `:wq` Enter |
| VS Code | 编辑临时 `.md` | 保存并关闭标签（需 `code --wait`） |

若 Cursor 内置终端里 nano 快捷键无效，改用系统「终端.app」，或换成 `vim` / `code --wait`。卡死时可另开窗口执行 `pkill -f nano`，再重新 push。

完整说明见：[README — 选择 / 切换编辑器](../README.zh-CN.md#选择--切换编辑器)。

---

## 3. 跳过路径 — hotfix 但留痕

```bash
echo "x=1" > b.py && git add b.py
git commit -m "tweak

Co-Authored-By: Copilot <noreply@github.com>"

CONFESS_SKIP=1 CONFESS_SKIP_REASON="hotfix" git push
```

**预期：** push 立刻成功；`CONFESSIONS.md` 增加 `**SKIPPED**: hotfix`（由 hook stage，稍后自行 commit 即可）。

---

## 4. 非 AI 提交 — 不打扰

```bash
echo "# note" >> README.md
git add README.md
git commit -m "docs: note"
git push
```

**预期：** 无 Confession 界面，正常 push。

---

## 5. 安装 / 检查 / 卸载

```bash
confess check      # ✓ Confess hook is installed.
confess uninstall  # 移除 hook；若有 *.confess-bak 则恢复
confess check      # ✗ Not installed.
confess init       # 重新安装
```

若原先已有 `pre-push`，`init` 会备份为 `pre-push.confess-bak`，`uninstall` 会还原。

---

## 6. MCP — 由 Agent 主动记录坦白

```bash
cd /path/to/confess
pip install -e ".[mcp]"
python -m confess.mcp_server
```

在 MCP 客户端中：

1. 调用 `confess_diff`，`scope` 取 `"staged"` 或 `"unpushed"`。
2. 人类审过 diff 后，调用 `confess_record`，传入 `what` / `risk` / `verify`。
3. 将 `CONFESSIONS.md` 与功能改动一并 commit（或单独跟进一次）。

**预期：** `CONFESSIONS.md` 中出现带 `(MCP-recorded)` 的条目。注意：MCP 记录的是当时的 `HEAD` SHA；若要与 push 门禁前缀匹配，更稳妥的是在 `git push` 时回答，这样写入的是 AI commit 的 SHA。

---

## 7. CONFESSIONS.md 示例条目

```markdown
## 2026-10-20T16:00:00+00:00 — `a1b2c3d4e5f6`

**Files**: app.py

### What does this code do? (your own words, not a paste of comments)
脚本运行时打印一句问候。

### If this breaks in production tomorrow, what is the most likely cause?
有人把模块当库 import，却触发了副作用。

### How would you verify it's correct in under 5 minutes?
运行 `python app.py`，确认 stdout 为 `hello`。
```

---

## 设计说明（为何如此）

| 行为 | 原因 |
|---|---|
| 用 `CONFESSIONS.md` 里的 SHA 前缀匹配 | 避免坦白 commit 后再 push 被无限拦截 |
| `--diff-filter=ACMR` | 删除文件无需坦白 |
| 优先 `$EDITOR` 而非 `input()` | hook 的 stdin 是 ref 列表，不是 TTY |
| skip 返回 0；正常路径返回 1 | skip 真正放行；正常路径强制留下坦白 commit |
| 只扫 commit message 标记 | 不因源码内容误报 |
