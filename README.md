# ccr — global Claude Code session picker

Resume **any** [Claude Code](https://claude.com/claude-code) session from **any**
directory with one command. Fuzzy-search across every session you've ever run —
by title, working directory, or git branch — preview the conversation, and drop
straight back into it in its original directory.

```
$ ccr
session> proxy oz
  3h  reland-mesh-origin-shield  —  ~/projects/proxy  [kd/cachd-oz-connection-warmth]
  5m  cachd-cross-region-shield  —  ~/projects/proxy  [kd/06-02-shielded-read-endpoint]
  ...
┌─ preview ───────────────────────────────┐
│ TITLE   reland-mesh-origin-shield         │
│ DIR     ~/projects/proxy                  │
│ BRANCH  kd/cachd-oz-connection-warmth     │
│                                           │
│ [1] let's reland the mesh origin shield…  │
└───────────────────────────────────────────┘
```

## Why

Claude Code persists every session to disk and lets you resume it
(`claude --resume`). But the built-in picker has two gaps:

1. **It's scoped to the current directory.** If you don't remember which
   directory you launched a session from, you can't easily find it.
2. **The list lacks context.** Rows are hard to tell apart, so identifying the
   session you want is guesswork.

`ccr` fixes both by reading the data Claude Code already writes but doesn't
surface globally:

- Every transcript embeds its own `cwd` and `gitBranch` → the directory is
  **recovered from the transcript**; you never need to remember it.
- Claude Code writes an AI-generated `aiTitle` for sessions → shown as the row
  label (falling back to the first real prompt when absent).

The key reframe: **closing a session never loses it.** Transcripts are
persisted and resumable — `ccr` just makes finding the right one trivial, so
you can close sessions freely without any "context dump" ritual.

## Requirements

- [`claude`](https://claude.com/claude-code) CLI on your `PATH`
- `python3` (standard library only — no pip installs)
- [`fzf`](https://github.com/junegunn/fzf)
- zsh or bash

## Install

```sh
git clone https://github.com/kldavis4/claude-session-picker.git ~/projects/claude-session-picker
cd ~/projects/claude-session-picker
./install.sh
```

The installer appends a single `source` line to your shell rc (`~/.zshrc` or
`~/.bashrc`) inside a managed block, and checks for `fzf`/`python3`. It is
idempotent — re-running it replaces the block rather than duplicating it.

Then reload your shell:

```sh
source ~/.zshrc   # or ~/.bashrc
```

If `fzf` is missing:

| OS     | Command                  |
| ------ | ------------------------ |
| macOS  | `brew install fzf`       |
| Debian | `sudo apt install fzf`   |
| Fedora | `sudo dnf install fzf`   |
| Arch   | `sudo pacman -S fzf`     |

## Usage

```sh
ccr                # browse active sessions, newest first
ccr proxy oz       # open the picker pre-filtered by a query
ccr -a             # start in show-all mode (includes excluded sessions)
```

Inside the picker:

- **Type** to fuzzy-filter across title + directory + branch.
- **↑/↓** to move; the right pane previews the session's opening prompts.
- **Enter** to resume — `ccr` `cd`s into the session's original directory and
  runs `claude --resume <id>`.
- **Ctrl-X** to hide the highlighted session (toggles — press again to un-hide).
- **Ctrl-A** to toggle between the active view and show-all (hidden sessions
  appear marked with `✕`).
- **Esc** to cancel.

## Excluding noisy sessions

Automated or repetitive sessions (cron jobs, scripted prompts) clutter the list.
Two ways to hide them, both stored under `~/.config/ccr/`:

- **Per session** — highlight it and press **Ctrl-X**. The session id is added
  to `~/.config/ccr/excluded`. Press Ctrl-X again on it (in show-all view) to
  un-hide.
- **By pattern** — add lines to `~/.config/ccr/exclude-patterns`. Each line is a
  **case-insensitive substring** matched against a session's title and first
  prompt; any match is hidden. For example:

  ```
  Generate a diary entry for
  You are an elite PR reviewer
  ```

  See [`config/exclude-patterns.example`](config/exclude-patterns.example).

Hidden sessions are never deleted — `ccr -a` or Ctrl-A always brings them back.

## Knowing which sessions are open

`ccr` can mark sessions that are **currently running** with a `●`, so you don't
resume one you already have open in another terminal. This is opt-in because it
needs two Claude Code hooks:

```sh
./install-hooks.sh        # merges SessionStart/SessionEnd hooks into ~/.claude/settings.json
```

The installer is idempotent and leaves your other hooks untouched (override the
target with `CLAUDE_SETTINGS=/path/to/settings.json`).

How it works:

- On **SessionStart** (new or resumed), the hook records the owning `claude`
  process PID under `~/.config/ccr/active/<session-id>`.
- A session is shown as open only if that **PID is still a live `claude`
  process** — so a crash or `kill` that skips `SessionEnd` can't leave a session
  falsely marked open. `ccr` prunes dead records as it lists.
- **SessionEnd** removes the record on a clean exit (best-effort cleanup).

Notes:

- Only sessions that **start or resume after** installing the hooks are tracked
  — already-running sessions register the next time they launch.
- There is no first-class "is this session open" flag in Claude Code; the
  transcript isn't held open and the session id isn't in the process
  environment, so this hook-based registry is the reliable way to know.

## How it works

| Piece                    | Role                                                             |
| ------------------------ | --------------------------------------------------------------- |
| `bin/claude-sessions.py` | Scans `~/.claude/projects/*/*.jsonl`, extracts title/cwd/branch. |
| `shell/ccr.sh`           | Defines the `ccr` function; pipes the list through `fzf`.        |
| `install.sh`             | Wires `ccr.sh` into your shell rc.                               |
| `bin/ccr-session-hook.py`| SessionStart/SessionEnd hook that records open sessions (optional). |
| `install-hooks.sh`       | Merges the open-session hooks into `~/.claude/settings.json`.    |

The helper does a single cheap pass per transcript (string-gated `json.loads`),
so listing hundreds of sessions takes ~2s.

## Configuration

Both are optional environment variables:

| Variable              | Default                | Purpose                                      |
| --------------------- | ---------------------- | -------------------------------------------- |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects`   | Where transcripts live (override for tests). |
| `CCR_HELPER`          | `<repo>/bin/...py`     | Path to the helper if you relocate it.       |
| `CCR_CONFIG_DIR`      | `~/.config/ccr`        | Exclusion files (`excluded`, `exclude-patterns`) and the `active/` open-session registry; honors `XDG_CONFIG_HOME`. |

## Uninstall

```sh
./uninstall.sh        # removes the managed block from your rc
```

The repo itself is untouched — delete the clone to fully remove.

## Limitations

- `aiTitle` is a relatively recent Claude Code feature, so older sessions fall
  back to showing their first prompt instead of a clean title. Both are
  searchable; older rows are just less polished.
- Listing is sorted by transcript file mtime (last activity), not creation time.

## License

MIT — see [LICENSE](LICENSE).
