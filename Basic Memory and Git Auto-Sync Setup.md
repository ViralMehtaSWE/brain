---
title: Basic Memory and Git Auto-Sync Setup
type: note
permalink: obsidian/basic-memory-and-git-auto-sync-setup
tags:
- system
- git
- hooks
- basic-memory
- configuration
---

# Basic Memory and Git Auto-Sync Setup

Summary of the system configuration connecting Obsidian, Basic Memory, and Antigravity lifecycle hooks for automated bidirectional Git synchronization.

---

## 1. Basic Memory Configuration

- **Target Vault:** Configured project `obsidian` to use `/Users/viralmehta/.brain/brain` as its root directory.
- **Search & Embeddings:** Built local full-text search and FastEmbed vector embeddings (`bge-small-en-v1.5`) for semantic note retrieval.
- **Config Path:** `~/.basic-memory/config.json`

---

## 2. Git Hygiene & Ignore Rules

Created `.gitignore` in `~/.brain/brain` to prevent Obsidian's volatile workspace layout state from polluting Git history:
- Excluded `.obsidian/workspace.json`, `.obsidian/workspace-mobile.json`, `.obsidian/cache/`, `.trash/`, and `.DS_Store`.

---

## 3. Auto-Push Script (Post-Tool Execution)

**Path:** `~/.gemini/scripts/obsidian_git_sync.sh`

**Logic:**
1. Checks for uncommitted additions, modifications, or deletions via `git status --porcelain`.
2. If changes exist:
   - Stages all files: `git add -A`
   - Creates a timestamped commit: `auto: vault update at <timestamp>`
   - Pushes to GitHub: `git push` to `origin main` (`git@github.com:ViralMehtaSWE/brain.git`)
3. If clean:
   - Exits immediately (~40ms) with `{}` satisfying the Antigravity hook contract without slowing down execution.

---

## 4. Auto-Pull Script (Session Startup)

**Path:** `~/.gemini/scripts/obsidian_git_pull.sh`

**Logic:**
1. Runs `git fetch origin` once at conversation session startup (`SessionStart`).
2. Compares local `HEAD` against remote tracking branch (`origin/main`).
3. If new commits exist on remote:
   - Fast-forwards / pulls latest changes: `git pull --ff-only`
   - Triggers background re-indexing of Basic Memory (`uvx basic-memory project index obsidian --no-wait`)
   - Injects an ephemeral notice to the agent: `"Notice: Pulled latest changes from remote for Obsidian vault (~/.brain/brain)."`
4. If already up to date:
   - Exits cleanly returning `{"injectSteps": []}`.

---

## 5. Antigravity Lifecycle Hooks

**Configured in:**
- `~/.gemini/config/hooks.json`
- `~/.gemini/config/plugins/obsidian/hooks.json`

```json
{
  "obsidian-vault-sync": {
    "PostToolUse": [
      {
        "matcher": "write_file|edit_file|call_mcp_tool",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/viralmehta/.gemini/scripts/obsidian_git_sync.sh",
            "timeout": 30
          }
        ]
      }
    ]
  },
  "obsidian-vault-pull": {
    "SessionStart": [
      {
        "type": "command",
        "command": "/Users/viralmehta/.gemini/scripts/obsidian_git_pull.sh",
        "timeout": 15
      }
    ]
  }
}
```