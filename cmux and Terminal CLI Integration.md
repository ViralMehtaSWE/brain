---
title: cmux and Terminal CLI Integration
type: system
permalink: obsidian/cmux-and-terminal-cli-integration
tags:
- cmux
- zsh
- terminal
- cli
- antigravity
- claude
- codex
- configuration
---

# cmux and Terminal CLI Integration

Documentation of the terminal integration and shell wrapper setup in `~/.zshrc` ensuring AI agent CLIs (`agy`, `claude`, `codex`) always run with auto-approval and permissions-skipping flags across both **cmux** and external terminals (**iTerm2**, Terminal.app, etc.).

- [relation] Part of [[README]] #system #terminal
- [relation] Related to [[Basic Memory and Git Auto-Sync Setup]] #system #configuration

---

## 1. Problem Context

In `~/.zshrc`, aliases were originally defined as:
```zsh
alias agy="agy --dangerously-skip-permissions"
alias codex="codex --dangerously-bypass-approvals-and-sandbox"
alias claude="claude --allow-dangerously-skip-permissions"
```

However, inside **cmux** tabs:
- cmux injects its shell integration script (`/Applications/cmux.app/Contents/Resources/shell-integration/cmux-zsh-integration.zsh`).
- During shell startup and on the first prompt (`_cmux_fix_path` in `precmd`), cmux explicitly executes `builtin unalias agy` and replaces it with a shell function (`agy() { "${_CMUX_AGY_WRAPPER}" "$@"; }`).
- This stripped `--dangerously-skip-permissions` and caused `type agy` to report `agy is a shell function`.

---

## 2. Solution: Universal Shell Function Wrapper

To ensure CLI flags are always passed while preserving cmux's background UI hooks, socket events, and compatibility with external terminals (iTerm2, Alacritty, Terminal.app), the configuration in `~/.zshrc` was updated with:

```zsh
# Agent CLI wrappers (compatible with cmux, iTerm2, Terminal.app, etc.)
_setup_agent_cli_overrides() {
    # Antigravity CLI
    agy() {
        if [[ -n "${_CMUX_AGY_WRAPPER:-}" ]]; then
            "$_CMUX_AGY_WRAPPER" --dangerously-skip-permissions "$@"
        else
            command agy --dangerously-skip-permissions "$@"
        fi
    }

    # Claude CLI
    claude() {
        if [[ -n "${_CMUX_CLAUDE_WRAPPER:-}" ]]; then
            "$_CMUX_CLAUDE_WRAPPER" --allow-dangerously-skip-permissions "$@"
        else
            command claude --allow-dangerously-skip-permissions "$@"
        fi
    }

    # Codex CLI
    codex() {
        command codex --dangerously-bypass-approvals-and-sandbox "$@"
    }
}

# Initialize immediately for standard terminals (iTerm2, Terminal.app, etc.)
_setup_agent_cli_overrides

# Hook into precmd so cmux shell-integration cannot overwrite them on prompt load
autoload -Uz add-zsh-hook
add-zsh-hook precmd _setup_agent_cli_overrides
```

---

## 3. How It Works

- **In cmux:** When `_CMUX_AGY_WRAPPER` or `_CMUX_CLAUDE_WRAPPER` is present, commands route through `/Applications/cmux.app/Contents/Resources/bin/agy`, preserving cmux tab status, notification hooks, and session tracking, while appending the required permission-skipping flags.
- **In iTerm2 / external terminals:** When wrapper variables are unset, it falls back to `command agy` / `command claude` / `command codex` directly without recursion.
- **Prompt lifecycle:** `add-zsh-hook precmd` guarantees that cmux's `_cmux_fix_path` cannot destroy the wrapper functions when a new prompt renders.