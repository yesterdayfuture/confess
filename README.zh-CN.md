# Confess

[English](README.md) | **中文**

**Confess** 是面向 AI 辅助开发的本地 Git **pre-push 门禁**：当 commit 带有 `Co-Authored-By: Claude` / Copilot / Cursor / Codex / Aider 等标记时，push 会先停住，直到你用自己的话回答三个问题——这段改动做什么、最可能怎么在线上坏掉、以及如何在五分钟内验收。答案（以及每一次主动跳过）都会追加进同仓库的 `CONFESSIONS.md`，说明与代码同行。

它不是又一个「AI Code Review」。Confess 不调用 LLM、不改写或 amend 历史、也不评判答案「对不对」。目标更窄、也更可靠：**强制人类停顿、留下人类签署的痕迹、让跳过行为可审计**——在改动离开本机之前完成。

任意语言、任意仓库可用。Hook 为纯 Python 标准库（运行时零第三方依赖）；可选 MCP Server，方便 Claude Code / Cursor 在流程更早阶段拉取 diff 摘要并写入坦白。

```bash
git clone <本仓库地址> confess
cd confess
pipx install .
# 或者: pip install -e .
confess init
```

→ 下次推送带 AI 痕迹的 commit 时，会用 `$EDITOR` 依次打开那三道问题。

> **现状：** v0.1 仅通过本仓库分发，**尚未上传到 PyPI**。请不要执行 `pip install confess-cli` / `pipx install confess-cli` 去装公共源上的包。

---

## 项目解决什么问题

AI 编程工具让人很容易合入「自己没真正写过」的大段改动。Code review 与 CI 常漏掉一种很现实的失败模式：**改动已经上线，但团队里没人能说清它做什么、会怎么坏、以及怎么在几分钟内验收。**

Confess 卡在本机最后一道关口——`git push`——把这个缺口变成习惯：三道问题、人类书写、与代码同库存档。时间长了，`CONFESSIONS.md` 会成为事故复盘、新人上手、「当时谁理解过这次改动」时的轻量证据，而不是又一个跟 LLM 抢活的语义校验器。

---

## 它具体做什么

| 组件 | 作用 |
|---|---|
| `confess` CLI | 安装 / 检查 / 卸载 Git `pre-push` hook |
| `pre-push` hook | 纯标准库 Python；扫描即将 push 的 commit |
| `CONFESSIONS.md` | 问答（与跳过）的追加式日志，与代码同库保存 |
| 可选 MCP Server | 让 Agent 提前拉取 diff 摘要并写入坦白 |

**识别方式刻意收窄：** 只在 **commit message** 里做大小写不敏感匹配，例如：

- `Co-Authored-By: Claude` / `Copilot` / `Cursor` / `Codex` / `Aider`
- `Generated-By:` / `Generated-With:` 等变体
- `🤖 Generated with`

**不扫描源码。** 你删掉 trailer，Confess 就不会拦——这是设计选择，不是缺陷。

**触发后**，优先在 `$EDITOR` 里回答（推荐；hook 的 stdin 是 ref 列表，不是 TTY）：

1. 这段代码在做什么？（用自己的话，不要粘贴注释）  
2. 如果明天线上挂了，最可能的原因是什么？  
3. 你如何在 5 分钟内验证它是对的？

答案写入 `CONFESSIONS.md` 并被 stage。你 commit 该文件后再 push。第二次会放行，因为 AI commit 的 SHA 前缀已在记录中——不会形成无限拦截。

**跳过是一等能力**（hotfix）：设置 `CONFESS_SKIP=1` 即可放行，但仍会留下 `SKIPPED` 记录。

---

## 安装（从本仓库安装 —— 非 PyPI）

需要 Python 3.9+ 与 Git。

### 方式 A — 从本地检出用 `pipx` 安装（推荐）

隔离环境，并把 `confess` 放进 `PATH`：

```bash
git clone <本仓库地址> confess
cd confess
pipx install .
```

之后在同一目录 `git pull`，再升级：

```bash
pipx install . --force
```

### 方式 B — 可编辑安装（开发）

```bash
git clone <本仓库地址> confess
cd confess
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # 需要 MCP 时再加 [mcp]
confess --help
```

### 方式 C — `uv`

```bash
git clone <本仓库地址> confess
cd confess
uv tool install .
# 或项目内虚拟环境：
uv pip install -e .
```

### 方式 D — 普通 `pip`（用户目录）

```bash
git clone <本仓库地址> confess
cd confess
pip install --user .
```

安装完成后，在**每个需要门禁的业务仓库**里执行：

```bash
cd /path/to/your-app-repo
confess init
confess check
```

`confess init` 会把 `.git/hooks/pre-push` 的 shebang 写成安装 Confess 时那个 Python 的**绝对路径**（pipx / uv / pyenv 下也能稳定运行）。在 Windows 上强制使用 LF，避免 Git Bash 把 `\r` 当成解释器路径的一部分。

---

## 用法

```bash
cd your-repo
confess init      # 安装 pre-push（若已有 hook 会先备份）
confess check     # 检查是否已安装
confess uninstall # 移除 Confess；有备份则恢复旧 hook
```

### 选择 / 切换编辑器

门禁触发后会**依次打开三个**临时文件（每题一次）。编辑器按以下优先级选择：

1. `$EDITOR`
2. `$VISUAL`
3. 系统中第一个可用的 `nano`、`vim`、`vi`

**仅对当前终端生效**（推荐在 `git push` 前设置）：

```bash
export EDITOR=vim          # 也可: nano、code --wait、subl -w 等
git push
```

**长期生效**（写入 `~/.zshrc` 或 `~/.bashrc`）：

```bash
export EDITOR=vim
```

| 编辑器 | 如何填写 | 保存并退出 |
|---|---|---|
| **nano** | 用方向键 ↓ 移到 HTML 注释下方空行，再输入 | `Ctrl+O`，`Enter`，再 `Ctrl+X`（macOS 用 **Control**，不是 ⌘） |
| **vim** | 按 `i` 进入插入模式，输入后按 `Esc` | 输入 `:wq` 再按 `Enter` |
| **VS Code** | `export EDITOR="code --wait"` | 保存标签页（`⌘S` / `Ctrl+S`），关闭该标签/窗口 |
| **Sublime** | `export EDITOR="subl -w"` | 保存并关闭窗口 |

说明：

- Git hook 的 stdin 是待推送的 ref 列表，**不是**交互式 TTY，请务必设置编辑器，不要依赖终端里直接 `input()`。
- 若在 Cursor / VS Code 内置终端里 nano 的 `Ctrl+X` 无响应，可改用系统「终端.app」完成 push，或换成 `vim` / `code --wait`。
- 编辑器卡死：另开一个终端执行 `pkill -f nano`（或 `vim`），再重新 `git push`。

### 跳过

```bash
CONFESS_SKIP=1 CONFESS_SKIP_REASON="hotfix" git push
```

跳过会写入 `CONFESSIONS.md`，push 立即放行。**每一次跳过都可审计。**

---

## 门禁流程

```text
git push
  → pre-push 从 stdin 读 refs
  → 对每个 commit：message 是否匹配 AI 标记？
       否 → 放行
       是 → SHA 是否已在 CONFESSIONS.md？
                是 → 放行
                否 → 是否设置了 CONFESS_SKIP？
                         是 → 追加 SKIPPED、stage、放行（exit 0）
                         否 → 用 $EDITOR 回答 3 题
                                未答完 → 拦截（exit 1）
                                答完   → 追加答案、stage、拦截（exit 1）
                                         请先 commit CONFESSIONS.md 再 push
```

关键设计：

- **`CONFESSIONS.md` 中的 SHA 前缀匹配**，避免坦白 commit 后再 push 被无限拦截。  
- **`--diff-filter=ACMR`**：删除文件不要求坦白。  
- **不调用 LLM、不 amend**：不改写历史，也不给答案打分。

---

## MCP Server（可选）

从同一份检出安装可选依赖：

```bash
cd /path/to/confess
pip install -e ".[mcp]"
python -m confess.mcp_server
```

Claude Code / Cursor 的 MCP 配置（`command` 指向已安装该包的解释器）：

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

工具：

- `confess_diff(scope)` — `"staged"` 或 `"unpushed"` 的 diff 摘要  
- `confess_record(what, risk, verify)` — 追加一条坦白  

---

## 用例与示例

- 端到端场景（门禁、跳过、卸载、MCP）：[docs/USE_CASES.zh-CN.md](docs/USE_CASES.zh-CN.md)  
- 示例日志：[examples/CONFESSIONS.sample.md](examples/CONFESSIONS.sample.md)

---

## Confess 刻意不做的事

- 不评判答案「对不对」（那会重新引入 LLM 式不可靠性）。  
- 不改写、不 amend 你的 commit。  
- 不调用 LLM——目标是留下**人类签署**的痕迹。  
- 不根据源码猜测是否 AI 写的；只认 commit message 标记。

---

## 仓库结构

```text
confess/
├── pyproject.toml          # 包名: confess-cli
├── confess/
│   ├── cli.py              # init / check / uninstall
│   ├── mcp_server.py       # 可选 MCP
│   └── data/pre-push       # hook 模板（仅标准库）
├── docs/                   # 中英用例
├── examples/               # CONFESSIONS.md 样例
└── tests/
```

---

## 许可证

MIT
