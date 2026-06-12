#!/usr/bin/env python3
"""Global Claude Code session browser.

Reads Claude Code transcripts (one JSONL file per session) and emits either a
flat, searchable list of every session across every project, or a rich preview
of a single session. Designed to be driven by fzf via the `ccr` shell function.

Transcript location defaults to ~/.claude/projects but can be overridden with
the CLAUDE_PROJECTS_DIR environment variable (useful for tests or non-standard
installs).

Modes:
  --list             one row per transcript (newest first), tab-separated:
                       sessionId \\t cwd \\t transcript_path \\t display_string
                     Only field 4 (display) is meant to be shown/searched in
                     fzf; fields 1-3 are machine-readable payload.
  --preview <path>   print a human-readable summary of one transcript for the
                     fzf preview pane: title, dir, branch, and opening prompts.
"""
import os
import sys
import json
import glob
import time

ROOT = os.environ.get("CLAUDE_PROJECTS_DIR") or os.path.expanduser("~/.claude/projects")
HOME = os.path.expanduser("~")


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


def human_age(secs):
    s = int(secs)
    if s < 3600:
        return f"{max(s // 60, 0)}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def short(p):
    return p.replace(HOME, "~", 1) if p.startswith(HOME) else p


def list_mode():
    now = time.time()
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
        label = info["title"] or (info["prompts"][0] if info["prompts"] else "(empty session)")
        label = label[:90]
        br = ""
        if info["branch"] and info["branch"] not in ("HEAD", "main", "master", ""):
            br = f"  [{info['branch']}]"
        age = human_age(now - mt)
        display = f"{age:>4}  {label}  —  {short(info['cwd'])}{br}"
        out.append("\t".join([info["sid"], info["cwd"], p, display]))
    sys.stdout.write("\n".join(out) + ("\n" if out else ""))


def preview_mode(path):
    info = scan(path, max_prompts=4)
    if not info:
        print("(unreadable transcript)")
        return
    print(f"TITLE   {info['title'] or '(none)'}")
    print(f"DIR     {short(info['cwd'])}")
    if info["branch"] and info["branch"] != "HEAD":
        print(f"BRANCH  {info['branch']}")
    print()
    if not info["prompts"]:
        print("(no user prompts)")
        return
    for i, t in enumerate(info["prompts"], 1):
        print(f"[{i}] {t[:500]}")
        print()


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--list":
        list_mode()
    elif len(sys.argv) >= 3 and sys.argv[1] == "--preview":
        preview_mode(sys.argv[2])
    else:
        sys.stderr.write("usage: claude-sessions.py --list | --preview <transcript>\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
