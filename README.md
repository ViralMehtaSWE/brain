---
permalink: obsidian/readme
title: brain
type: note
tags:
- brain
- overview
- documentation
---

# 🧠 Brain

A personal knowledge management (PKM) vault and long-term semantic memory system for **Viral Mehta**, seamlessly integrating **Obsidian**, **Antigravity AI**, **Basic Memory MCP**, and **Git**.

---

## 🎯 Purpose & Capabilities

- **Personal Knowledge Graph:** Acts as a second brain for capturing notes, concepts, technical systems, and relationship networks using Obsidian Flavored Markdown and wikilinks.
- **AI Long-Term Memory:** Serves as the primary data store for the **Basic Memory** MCP server (`obsidian` project). Every note is indexed with local full-text search and vector embeddings (`FastEmbed / bge-small-en-v1.5`) for fast, context-aware semantic retrieval.
- **Automated Git Synchronization:** Antigravity lifecycle hooks ensure bidirectional auto-sync:
  - **Auto-Pull:** Fast-forwards remote changes at session start (`SessionStart`) and triggers background re-indexing.
  - **Auto-Push:** Automatically stages, commits, and pushes updates to GitHub on file modifications (`PostToolUse`).

---

## 📂 Key Notes & Structure

| File | Description |
| :--- | :--- |
| [Welcome to Brain.md](Welcome%20to%20Brain.md) | High-level vault introduction and welcome note. |
| [Basic Memory and Git Auto-Sync Setup.md](Basic%20Memory%20and%20Git%20Auto-Sync%20Setup.md) | Technical setup of the Basic Memory MCP and lifecycle hook scripts. |
| [CLI Status Line Setup.md](CLI%20Status%20Line%20Setup.md) | Unified status line script and configuration across AGY, Claude Code, and Codex. |
| [cmux and Terminal CLI Integration.md](cmux%20and%20Terminal%20CLI%20Integration.md) | Shell wrappers and precmd hook setup for CLI permissions across cmux & iTerm2. |
| [Viral Mehta.md](Viral%20Mehta.md) | Personal profile, career timeline (Stripe, Amazon, Google, Microsoft, incoming Staff SWE at LinkedIn), skills, and contact details. |
| [Rahul Banerji.md](Rahul%20Banerji.md) | Contact note and relation record (best friend). |

---

## 🛠️ System Architecture

```text
┌──────────────────────┐         ┌──────────────────────┐
│  Obsidian Desktop    │ ◄─────► │   ~/.brain/brain     │
│   (Markdown GUI)     │         │    (Local Vault)     │
└──────────────────────┘         └──────────┬───────────┘
                                            │
                   ┌────────────────────────┼────────────────────────┐
                   ▼                        ▼                        ▼
       ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
       │     Basic Memory     │ │  Antigravity Hooks   │ │    GitHub Remote     │
       │    Semantic Search   │ │ Auto-Sync / Auto-Pull│ │   origin / main      │
       │  (FastEmbed Vector)  │ │   (Lifecycle Hooks)  │ │(ViralMehtaSWE/brain) │
       └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

---

## ⚙️ Conventions

- **Frontmatter:** Standard YAML frontmatter including `title`, `type`, `permalink`, and `tags`.
- **Knowledge Atoms:**
  - Observations: `- [category] fact #tag`
  - Relations: `- [relation] Relationship [[Entity]] #tag`
- **Git Hygiene:** Local `.gitignore` excludes volatile Obsidian workspace state (`.obsidian/workspace.json`, `.obsidian/cache/`, `.trash/`, `.DS_Store`).