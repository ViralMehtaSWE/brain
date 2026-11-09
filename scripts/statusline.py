#!/usr/bin/env python3
import sys
import json
import os

def format_tokens(n):
    if not n or n < 0:
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))

def shorten_path(p):
    if not p:
        return "~"
    home = os.path.expanduser("~")
    if p == home:
        return "~"
    if p.startswith(home + "/"):
        return "~/" + p[len(home) + 1:]
    return p

try:
    raw_input = sys.stdin.read()
    if raw_input.strip():
        data = json.loads(raw_input)
    else:
        data = {}
except Exception:
    data = {}

# 1. Current Working Directory (handles AGY cwd and Claude workspace.current_dir)
cwd = data.get("cwd") or data.get("workspace", {}).get("current_dir") or os.getcwd()
cwd_disp = shorten_path(cwd)

# 2. Model (handles AGY and Claude models)
model_info = data.get("model") or {}
if isinstance(model_info, str):
    model_name = model_info
else:
    model_name = model_info.get("display_name") or model_info.get("id") or "Model"

# 3. Effort Level (handles AGY model.effort / effort and Claude effort.level / modelSettings)
effort = None
effort_raw = data.get("effort")
if isinstance(effort_raw, dict):
    effort = effort_raw.get("level")
elif isinstance(effort_raw, str):
    effort = effort_raw

if not effort and isinstance(model_info, dict):
    effort = model_info.get("effort") or model_info.get("effortLevel") or model_info.get("reasoning_effort")

if not effort:
    effort = "default"

# 4. Context Window: Used & Max
ctx = data.get("context_window") or {}
max_ctx = ctx.get("context_window_size") or 0

# If max context window size is not explicitly provided in payload, infer from model family
if not max_ctx:
    low = model_name.lower()
    if "claude" in low or "sonnet" in low or "opus" in low or "haiku" in low:
        max_ctx = 200_000
    elif "gpt-4" in low or "gpt-5" in low:
        max_ctx = 128_000
    elif "gemini" in low:
        max_ctx = 1_000_000

used_pct = ctx.get("used_percentage")
curr_usage = ctx.get("current_usage") or {}
curr_used = (curr_usage.get("input_tokens") or 0) + (curr_usage.get("output_tokens") or 0)

if not curr_used and max_ctx and used_pct is not None:
    curr_used = int((used_pct / 100.0) * max_ctx)
elif not curr_used:
    curr_used = (ctx.get("total_input_tokens") or 0) + (ctx.get("total_output_tokens") or 0)

if max_ctx:
    if used_pct is not None:
        ctx_disp = f"{format_tokens(curr_used)}/{format_tokens(max_ctx)} ({used_pct:.1f}%)"
    else:
        pct = (curr_used / max_ctx * 100) if max_ctx else 0
        ctx_disp = f"{format_tokens(curr_used)}/{format_tokens(max_ctx)} ({pct:.1f}%)"
elif curr_used:
    ctx_disp = format_tokens(curr_used)
else:
    ctx_disp = "0"

# 5. Tokens used so far in this session
total_in = ctx.get("total_input_tokens") or 0
total_out = ctx.get("total_output_tokens") or 0
total_session = total_in + total_out

if total_session > 0:
    session_tokens_disp = f"{format_tokens(total_session)} (in: {format_tokens(total_in)}, out: {format_tokens(total_out)})"
else:
    session_tokens_disp = "0"

# ANSI styling
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
GRAY = "\033[90m"

# Format model display: omit redundant effort tag if already present in model name (e.g. "Gemini 3.8 Flash (Medium)")
model_disp = f"{GREEN}{BOLD}🤖 {model_name}{RESET}"
if effort and effort.lower() not in ["default", "none", "null", ""] and effort.lower() not in model_name.lower():
    model_disp += f" {GRAY}({effort.capitalize()}){RESET}"

sep = f" {GRAY}│{RESET} "
line = (
    f"{CYAN}{BOLD}📁 {cwd_disp}{RESET}"
    f"{sep}"
    f"{model_disp}"
    f"{sep}"
    f"{YELLOW}{BOLD}🧠 Context:{RESET} {ctx_disp}"
    f"{sep}"
    f"{MAGENTA}{BOLD}⚡ Session Tokens:{RESET} {session_tokens_disp}"
)

print(line)
