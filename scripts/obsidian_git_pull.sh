#!/usr/bin/env bash

VAULT_DIR="/Users/viralmehta/.brain/brain"

# Helper to format injectSteps JSON cleanly
emit_message() {
    local text="$1"
    local md="$2"
    if [ -z "$md" ]; then
        md="$text"
    fi

    if command -v jq >/dev/null 2>&1; then
        jq -n --arg t "$text" --arg m "$md" '{
          injectSteps: [
            {
              systemMessage: {
                systemMessage: $t,
                metadata: {
                  user_markdown: $m
                }
              }
            }
          ]
        }'
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c '
import json, sys
t, m = sys.argv[1], sys.argv[2]
print(json.dumps({
    "injectSteps": [
        {
            "systemMessage": {
                "systemMessage": t,
                "metadata": {"user_markdown": m}
            }
        }
    ]
}))' "$text" "$md"
    else
        echo '{"injectSteps": []}'
    fi
    exit 0
}

emit_empty() {
    echo '{"injectSteps": []}'
    exit 0
}

# 1. Ensure vault directory exists and is a git repo
if [ ! -d "$VAULT_DIR/.git" ]; then
    emit_message \
        "⚠️ Obsidian Git Auto-Pull Warning: '$VAULT_DIR' is not a Git repository." \
        "⚠️ **Obsidian Git Auto-Pull Warning:** \`$VAULT_DIR\` is not a Git repository."
fi

cd "$VAULT_DIR"

# 2. Ensure remote 'origin' is configured
if ! git remote get-url origin >/dev/null 2>&1; then
    emit_message \
        "⚠️ Obsidian Git Auto-Pull Warning: Remote 'origin' is not configured for '$VAULT_DIR'." \
        "⚠️ **Obsidian Git Auto-Pull Warning:** Remote \`origin\` is not configured for \`$VAULT_DIR\`."
fi

# 3. Check for lingering unresolved merge conflicts
if git status --porcelain 2>/dev/null | grep -E '^([UDA]{2}|DD|AU|UD|UA|DU|AA|UU)' >/dev/null 2>&1; then
    emit_message \
        "⚠️ Obsidian Git Auto-Pull Warning: Vault has unresolved merge conflicts. Please resolve them." \
        "⚠️ **Obsidian Git Auto-Pull Warning:** Vault at \`$VAULT_DIR\` has unresolved merge conflicts. Please resolve them."
fi

# 4. Fetch from origin with non-interactive flags
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5"

FETCH_ERR=""
if ! FETCH_ERR=$(git fetch origin 2>&1); then
    emit_message \
        "⚠️ Obsidian Git Auto-Pull Notice: Failed to fetch from origin (offline or network error):
$FETCH_ERR" \
        "⚠️ **Obsidian Git Auto-Pull Notice:** Failed to fetch from origin (offline or network error):
\`\`\`text
$FETCH_ERR
\`\`\`"
fi

# 5. Determine remote tracking branch
REMOTE_BRANCH=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "origin/main")
LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE=$(git rev-parse "$REMOTE_BRANCH" 2>/dev/null || echo "")
BASE=$(git merge-base HEAD "$REMOTE" 2>/dev/null || echo "")

if [ -z "$LOCAL" ] || [ -z "$REMOTE" ]; then
    emit_empty
fi

# If already up to date
if [ "$LOCAL" = "$REMOTE" ]; then
    emit_empty
fi

# If local is ahead of remote (unpushed commits), nothing to pull
if [ "$REMOTE" = "$BASE" ]; then
    emit_empty
fi

# 6. Pull remote updates using --autostash
PULL_OUTPUT=""
PULL_STATUS=0

if [ "$LOCAL" = "$BASE" ]; then
    # Local is strictly behind remote (fast-forwardable)
    PULL_OUTPUT=$(git pull --ff-only --autostash 2>&1) || PULL_STATUS=$?
else
    # Diverged: attempt rebase pull with autostash
    PULL_OUTPUT=$(git pull --rebase --autostash 2>&1) || PULL_STATUS=$?
    if [ $PULL_STATUS -ne 0 ]; then
        # Abort in-progress rebase so repository is not left in broken rebase state
        git rebase --abort >/dev/null 2>&1 || true
    fi
fi

# 7. Handle pull failure
if [ $PULL_STATUS -ne 0 ]; then
    emit_message \
        "⚠️ Obsidian Git Auto-Pull Error: Failed to pull remote changes into '$VAULT_DIR':
$PULL_OUTPUT" \
        "⚠️ **Obsidian Git Auto-Pull Error:** Failed to pull remote changes into \`$VAULT_DIR\`:
\`\`\`text
$PULL_OUTPUT
\`\`\`"
fi

# 8. Check if autostash produced merge conflicts
if echo "$PULL_OUTPUT" | grep -qi "conflicts" || git status --porcelain 2>/dev/null | grep -E '^([UDA]{2}|DD|AU|UD|UA|DU|AA|UU)' >/dev/null 2>&1; then
    emit_message \
        "⚠️ Obsidian Git Auto-Pull Warning: Pulled latest changes from remote, but applying autostashed changes resulted in merge conflicts in '$VAULT_DIR':
$PULL_OUTPUT
Please resolve conflicts in the vault." \
        "⚠️ **Obsidian Git Auto-Pull Warning:** Pulled latest changes from remote, but applying autostashed changes resulted in merge conflicts in \`$VAULT_DIR\`:
\`\`\`text
$PULL_OUTPUT
\`\`\`
Please resolve conflicts in the vault."
fi

# 9. Successful pull - trigger background re-indexing
uvx basic-memory project index obsidian --no-wait >/dev/null 2>&1 || true

emit_message \
    "Notice: Pulled latest changes from remote for Obsidian vault (~/.brain/brain)." \
    "Notice: Pulled latest changes from remote for Obsidian vault (\`~/.brain/brain\`)."
