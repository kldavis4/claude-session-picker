#!/usr/bin/env bash
# Installs ccr's SessionStart/SessionEnd hooks into ~/.claude/settings.json so
# ccr can show which sessions are currently open. Idempotent: re-running
# replaces ccr's own entries and leaves all your other hooks untouched.
#
# Overrides:
#   CLAUDE_SETTINGS=/path/to/settings.json   (default: ~/.claude/settings.json)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
HOOK="$REPO/bin/ccr-session-hook.py"
SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required" >&2; exit 1; }
chmod +x "$HOOK"

echo "ccr hook installer"
echo "  hook     : $HOOK"
echo "  settings : $SETTINGS"

CCR_HOOK_CMD="python3 \"$HOOK\"" \
CCR_SETTINGS="$SETTINGS" \
python3 - <<'PY'
import json, os

settings = os.environ["CCR_SETTINGS"]
cmd = os.environ["CCR_HOOK_CMD"]

try:
    with open(settings) as fh:
        data = json.load(fh)
except FileNotFoundError:
    data = {}
except json.JSONDecodeError as e:
    raise SystemExit(f"ERROR: {settings} is not valid JSON: {e}")

hooks = data.setdefault("hooks", {})

def ensure(event, matcher):
    groups = hooks.get(event, [])
    # Drop any prior ccr entries so re-running doesn't duplicate them.
    groups = [g for g in groups
              if not any("ccr-session-hook" in h.get("command", "")
                         for h in g.get("hooks", []))]
    groups.append({"matcher": matcher,
                   "hooks": [{"type": "command", "command": cmd}]})
    hooks[event] = groups

# SessionStart fires at the start of every session life (new or resumed);
# SessionEnd cleans up on exit. Matchers are regex over source/reason.
ensure("SessionStart", "startup|resume|clear|compact")
ensure("SessionEnd", "prompt_input_exit|logout|other|clear|resume|bypass_permissions_disabled")

os.makedirs(os.path.dirname(settings) or ".", exist_ok=True)
with open(settings, "w") as fh:
    json.dump(data, fh, indent=4)
    fh.write("\n")
print("  updated SessionStart + SessionEnd hooks")
PY

echo "Done. New sessions (and resumes) will register; ccr marks open ones with ●."
echo "Existing already-running sessions register the next time they start/resume."
