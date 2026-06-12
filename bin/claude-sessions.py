#!/usr/bin/env python3
"""Global Claude Code session browser.

Reads Claude Code transcripts (one JSONL file per session) and emits either a
flat, searchable list of every session across every project, or a rich preview
of a single session. Designed to be driven by fzf via the `ccr` shell function.

Two live signals come from Claude Code's own per-session registry at
~/.claude/sessions/<pid>.json (sessionId, pid, status, and `name` set by
`/rename`):
  - the picker marks sessions that are currently running with ●
  - it shows the live `/rename` title, which is NOT written to the transcript
    while the session is open (the transcript only carries the auto `aiTitle`)

Transcript location defaults to ~/.claude/projects (override: CLAUDE_PROJECTS_DIR).
Claude dir defaults to ~/.claude (override: CLAUDE_CONFIG_DIR).

Exclusions live under the config dir (~/.config/ccr, or $CCR_CONFIG_DIR /
$XDG_CONFIG_HOME):
  excluded           tool-managed list of session IDs hidden via `ctrl-x`
  exclude-patterns   user-editable case-insensitive substrings; any session
                     whose title or first prompt contains one is hidden
`--all` shows everything, marking hidden rows with a leading ✕.

Modes:
  --list [--all]     one row per transcript (newest first), tab-separated:
                       sessionId \\t cwd \\t transcript_path \\t display_string
  --preview <path>   human-readable summary of one transcript.
  --toggle-exclude <sessionId>
                     add the id to `excluded`, or remove it if already present.
"""
import os
import sys
import json
import glob
import time
import subprocess

CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
ROOT = os.environ.get("CLAUDE_PROJECTS_DIR") or os.path.join(CLAUDE_DIR, "projects")
SESSIONS_DIR = os.path.join(CLAUDE_DIR, "sessions")
HOME = os.path.expanduser("~")

CONFIG_DIR = (os.environ.get("CCR_CONFIG_DIR")
              or os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "ccr"))
EXCLUDED_FILE = os.path.join(CONFIG_DIR, "excluded")
PATTERNS_FILE = os.path.join(CONFIG_DIR, "exclude-patterns")


def _read_lines(path):
    """Yield stripped, non-blank, non-comment lines from a config file."""
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s and not s.startswith("#"):
                    yield s
    except OSError:
        return


def load_excluded():
    return set(_read_lines(EXCLUDED_FILE))


def load_patterns():
    return [s.lower() for s in _read_lines(PATTERNS_FILE)]


def _live_claude_pids():
    """PIDs of all running `claude` processes (one ps call)."""
    try:
        r = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True)
    except Exception:
        return set()
    pids = set()
    for line in r.stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and "claude" in parts[1]:
            try:
                pids.add(int(parts[0]))
            except ValueError:
                pass
    return pids


def load_registry():
    """Claude Code's live session registry: sessionId -> {pid, name, status}.

    Only entries whose PID is a live `claude` process are kept, so a stale file
    left by a crash never reports a closed session as open. The `name` is the
    /rename title, authoritative for a running session (the transcript's
    aiTitle is the auto-generated one and isn't updated by /rename)."""
    reg = {}
    try:
        files = glob.glob(os.path.join(SESSIONS_DIR, "*.json"))
    except OSError:
        return reg
    if not files:
        return reg
    live = _live_claude_pids()
    for f in files:
        try:
            with open(f, errors="replace") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        sid = d.get("sessionId")
        pid = d.get("pid")
        if not sid or pid not in live:
            continue
        reg[sid] = {"pid": pid, "name": d.get("name"), "status": d.get("status")}
    return reg


def _text_from_user(d):
    """Return cleaned user prompt text, or None if this is a meta/system turn."""
    msg = d.get("message")
    if not isinstance(msg, dict):
        return None
    c = msg.get("content")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    if not isinstance(c, str):
        return None
    t = " ".join(c.split()).strip()
    if not t:
        return None
    # Skip tool-result envelopes, system reminders, and CLI command echoes.
    if t.startswith("<") or t.startswith("Caveat") or "system-reminder" in t[:60]:
        return None
    return t


def scan(path, max_prompts=4):
    """Single pass over a transcript. Returns dict with title/cwd/branch/prompts."""
    sid = os.path.splitext(os.path.basename(path))[0]
    title = cwd = branch = None
    prompts = []
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                # Cheap string gate before paying for json.loads on every line.
                if '"ai-title"' in line:
                    try:
                        title = json.loads(line).get("aiTitle") or title
                    except ValueError:
                        pass
                    continue
                if '"type":"user"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "user":
                    continue
                if not cwd and d.get("cwd"):
                    cwd = d["cwd"]
                if not branch and d.get("gitBranch"):
                    branch = d["gitBranch"]
                if len(prompts) < max_prompts:
                    t = _text_from_user(d)
                    if t:
                        prompts.append(t)
    except OSError:
        return None
    return {"sid": sid, "title": title, "cwd": cwd or "?",
            "branch": branch or "", "prompts": prompts}


def best_label(info, reg_name):
    """Title precedence: live /rename name > transcript aiTitle > first prompt."""
    return (reg_name or info["title"]
            or (info["prompts"][0] if info["prompts"] else "(empty session)"))


def exclusion_reason(label, sid, prompts, excluded, patterns):
    """Return 'id', 'pattern', or None for why a session is hidden by default."""
    if sid in excluded:
        return "id"
    if patterns:
        hay = (label + " " + " ".join(prompts)).lower()
        for p in patterns:
            if p in hay:
                return "pattern"
    return None


def human_age(secs):
    s = int(secs)
    if s < 3600:
        return f"{max(s // 60, 0)}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def short(p):
    return p.replace(HOME, "~", 1) if p.startswith(HOME) else p


TITLE_W = 46  # title column width; directory/branch align after it


def _truncate(s, w):
    return s if len(s) <= w else s[:w - 1] + "…"


def list_mode(show_all=False):
    now = time.time()
    excluded = load_excluded()
    patterns = load_patterns()
    reg = load_registry()

    rows = []
    for p in glob.glob(os.path.join(ROOT, "*", "*.jsonl")):
        try:
            rows.append((os.path.getmtime(p), p))
        except OSError:
            continue
    rows.sort(reverse=True)

    out = []
    for mt, p in rows:
        info = scan(p, max_prompts=1)
        # Skip unreadable transcripts and sessions with no real user turn.
        if not info or (info["cwd"] == "?" and not info["prompts"]):
            continue
        sid = info["sid"]
        reg_name = reg.get(sid, {}).get("name")
        label = best_label(info, reg_name)
        reason = exclusion_reason(label, sid, info["prompts"], excluded, patterns)
        if reason and not show_all:
            continue
        br = ""
        if info["branch"] and info["branch"] not in ("HEAD", "main", "master", ""):
            br = f"  [{info['branch']}]"
        age = human_age(now - mt)
        # status col: ● open beats ✕ excluded (the latter only shows in --all).
        if sid in reg:
            status = "●"
        elif show_all and reason:
            status = "✕"
        else:
            status = " "
        # Fixed-width columns so directory/branch align across rows.
        title_col = _truncate(label, TITLE_W).ljust(TITLE_W)
        display = f"{status}  {age:>4}  {title_col}  {short(info['cwd'])}{br}"
        out.append("\t".join([sid, info["cwd"], p, display]))
    sys.stdout.write("\n".join(out) + ("\n" if out else ""))


def preview_mode(path):
    info = scan(path, max_prompts=4)
    if not info:
        print("(unreadable transcript)")
        return
    reg = load_registry().get(info["sid"], {})
    label = best_label(info, reg.get("name"))
    print(f"TITLE   {label}")
    print(f"DIR     {short(info['cwd'])}")
    if info["branch"] and info["branch"] != "HEAD":
        print(f"BRANCH  {info['branch']}")
    if reg:
        st = reg.get("status")
        print(f"OPEN    ● running now{(' (' + st + ')') if st else ''}")
    if info["sid"] in load_excluded():
        print("EXCLUDED  yes (ctrl-x to un-hide)")
    print()
    if not info["prompts"]:
        print("(no user prompts)")
        return
    for i, t in enumerate(info["prompts"], 1):
        print(f"[{i}] {t[:500]}")
        print()


def toggle_exclude(sid):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    cur = load_excluded()
    if sid in cur:
        cur.discard(sid)
    else:
        cur.add(sid)
    with open(EXCLUDED_FILE, "w") as fh:
        fh.write("\n".join(sorted(cur)) + ("\n" if cur else ""))


def main():
    argv = sys.argv
    if len(argv) >= 2 and argv[1] == "--list":
        list_mode(show_all="--all" in argv[2:])
    elif len(argv) >= 3 and argv[1] == "--preview":
        preview_mode(argv[2])
    elif len(argv) >= 3 and argv[1] == "--toggle-exclude":
        toggle_exclude(argv[2])
    else:
        sys.stderr.write(
            "usage: claude-sessions.py --list [--all] | --preview <transcript> "
            "| --toggle-exclude <sessionId>\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
