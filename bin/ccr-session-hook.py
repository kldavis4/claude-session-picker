#!/usr/bin/env python3
"""Claude Code SessionStart / SessionEnd hook for ccr.

Maintains a registry of currently-open sessions so `ccr` can show which ones
are live. On SessionStart it writes ~/.config/ccr/active/<session_id>
containing the owning `claude` process PID; on SessionEnd it removes that file.

Correctness does NOT depend on SessionEnd firing (it can't block and may be
skipped on crash/kill): ccr treats a record as "open" only if its PID is still
a live `claude` process, and prunes dead records. SessionEnd is just prompt
cleanup.

The hook payload (including hook_event_name and session_id) arrives as JSON on
stdin — see the Claude Code hooks docs.
"""
import os
import sys
import json
import subprocess

CONFIG_DIR = (os.environ.get("CCR_CONFIG_DIR")
              or os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "ccr"))
ACTIVE_DIR = os.path.join(CONFIG_DIR, "active")


def owning_claude_pid():
    """Walk up the process tree from this hook to the nearest `claude` process."""
    pid = os.getppid()
    for _ in range(8):
        if pid <= 1:
            break
        try:
            r = subprocess.run(["ps", "-o", "ppid=,command=", "-p", str(pid)],
                               capture_output=True, text=True)
        except Exception:
            break
        line = r.stdout.strip()
        if not line:
            break
        parts = line.split(None, 1)
        cmd = parts[1] if len(parts) > 1 else ""
        if "claude" in cmd and "ccr-session-hook" not in cmd:
            return pid
        try:
            pid = int(parts[0])
        except (ValueError, IndexError):
            break
    return os.getppid()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    sid = data.get("session_id")
    # Guard against path traversal from an unexpected id shape.
    if not sid or "/" in sid or sid in (".", ".."):
        return
    path = os.path.join(ACTIVE_DIR, sid)

    if data.get("hook_event_name") == "SessionEnd":
        try:
            os.remove(path)
        except OSError:
            pass
        return

    # SessionStart (any source): record the owning claude PID.
    try:
        os.makedirs(ACTIVE_DIR, exist_ok=True)
        with open(path, "w") as fh:
            fh.write(str(owning_claude_pid()))
    except OSError:
        pass


if __name__ == "__main__":
    main()
