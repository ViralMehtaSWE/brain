---
permalink: obsidian/cli-status-line-setup
title: CLI Status Line Setup
type: note
tags:
- cli
- statusline
- agy
- claude-code
- codex
- configuration
---

# 📊 CLI Status Line Setup

Configuration and architecture for universal terminal status lines across **Antigravity CLI (`agy`)**, **Claude Code (`claude`)**, and **OpenAI Codex CLI (`codex`)**.

---

## 🎯 Overview

The custom status line displays:
- **Current Working Directory:** Shortened with `~` prefix (e.g., `📁 ~/code`).
- **Model Name & Reasoning:** Model display name with deduplicated effort tier (e.g., `🤖 Gemini 3.8 Flash (Medium)` or `🤖 Claude Opus 5.5 (Xhigh)`).
- **Context Window:** Current tokens used out of the maximum context capacity plus percentage (e.g., `🧠 Context: 54.5k/1.0M (5.2%)`).
- **Session Token Usage:** Total input and output tokens consumed in the session with breakdown (e.g., `⚡ Session Tokens: 124.0k (in: 120.0k, out: 4.0k)`).

```text
📁 ~ │ 🤖 Gemini 3.8 Flash (Medium) │ 🧠 Context: 54.5k/1.0M (5.2%) │ ⚡ Session Tokens: 124.0k (in: 120.0k, out: 4.0k)
```

---

## 🛠️ Architecture & Multi-CLI Support

| CLI | Execution Mode | Configuration File | Command / Settings |
| :--- | :--- | :--- | :--- |
| **Antigravity (`agy`)** | Shell command via `stdin` JSON | `~/.gemini/antigravity-cli/settings.json` | `"statusLine": {"type": "command", "command": "/Users/viralmehta/.gemini/scripts/statusline.py", "enabled": true}` |
| **Claude Code (`claude`)** | Shell command via `stdin` JSON | `~/.claude/settings.json` | `"statusLine": {"type": "command", "command": "/Users/viralmehta/.gemini/scripts/statusline.py", "padding": 0}` |
| **Codex CLI (`codex`)** | Native declarative identifiers | `~/.codex/config.toml` | `[tui] status_line = ["current-dir", "model-with-reasoning", "context-used", "context-window-size", "total-input-tokens", "total-output-tokens"]` |

---

## 📜 Script Source & Storage

The canonical script is maintained in:
- **Runtime Path:** `/Users/viralmehta/.gemini/scripts/statusline.py`
- **Vault Archive:** `scripts/statusline.py`

### Key Implementation Details
- **Polymorphic Ingestion:** Dynamically inspects input JSON to extract fields whether structured by AGY (`cwd`, `model.effort`, `context_window.current_usage`) or Claude Code (`workspace.current_dir`, `effort.level`, inferred context window sizes).
- **Effort Deduplication:** Detects if the effort tier (e.g., `Medium`) is already present inside `model.display_name` (like `Gemini 3.8 Flash (Medium)`) to avoid redundant printing.
- **Fast Execution:** Executes in ~40ms, well within CLI throttle intervals (300ms) and timeouts.

---

## 🔗 Related Notes

- [[Basic Memory and Git Auto-Sync Setup]]
- [[cmux and Terminal CLI Integration]]
- [[Welcome to Brain]]
