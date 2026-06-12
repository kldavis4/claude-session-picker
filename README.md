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
ccr                      # browse active sessions, newest first
ccr proxy oz             # open the picker pre-filtered by a query
ccr -a                   # start in show-all mode (includes excluded sessions)
ccr foo -- --model opus  # pass args after `--` straight to `claude --resume`
```

### Passing flags to `claude`

`ccr` resumes with `claude --resume <id>` plus:

- **`CCR_CLAUDE_ARGS`** — flags applied to *every* resume. Set this in your rc to
  match how you normally launch Claude Code, e.g.:

  ```sh
  export CCR_CLAUDE_ARGS="--dangerously-skip-permissions"
  ```

- **`-- <args>`** — anything after a literal `--` on the `ccr` line is passed
  through for that one resume (appended after `CCR_CLAUDE_ARGS`).

Inside the picker:

- **Type** to fuzzy-filter across title + directory + branch.
- **↑/↓** to move; the right pane previews the session's opening prompts.
- **Enter** to resume — `ccr` `cd`s into the session's original directory and
  runs `claude --resume <id>`.
- **Space** to toggle the highlighted session as a **favorite** (`★`).
- **Ctrl-X** to hide the highlighted session (toggles — press again to un-hide).
- **Ctrl-A** to toggle between the active view and show-all (hidden sessions
  appear marked with `✕`).
- **Esc** to cancel.

> Because **Space** toggles favorites, it can't be typed in the search box (fzf
> would treat it as a term separator). Single-term substring filtering still
> works.

## Favorites

Sessions you keep coming back to can be pinned. Press **Space** on a row to
toggle it as a favorite (stored in `~/.config/ccr/favorites`). Favorites:

- are marked with a leading `★`,
- **sort to the top** of the list, ordered by last activity among themselves,
- with all non-favorites below, also newest-first,
- and are always shown (a favorite is never hidden by an exclude rule).

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

A **currently-running** session (`●`) is always shown, even if it matches an
exclude rule — so you can never lose track of a session you have open.

## Open sessions and live titles

Claude Code keeps a per-session registry at `~/.claude/sessions/<pid>.json`
(session id, pid, status, and the `/rename` name). `ccr` reads it — no setup,
no hooks — to give you two things:

- **`●` open marker** on sessions that are running right now, so you don't
  resume one you already have open in another terminal. A session counts as open
  only if its registered PID is still a live `claude` process, so crashes never
  leave a stale "open" mark.
- **Live `/rename` titles.** When you `/rename` a *running* session, the new
  name is written to this registry, not to the transcript — so `ccr` shows the
  rename immediately. (The transcript only carries the auto-generated `aiTitle`,
  which is what `ccr` falls back to for sessions that aren't running.)

Title precedence in the list: **live `/rename` name → transcript `aiTitle` →
first prompt**.

## How it works

| Piece                    | Role                                                             |
| ------------------------ | --------------------------------------------------------------- |
| `bin/claude-sessions.py` | Scans `~/.claude/projects/*/*.jsonl` (titles/cwd/branch) and `~/.claude/sessions/*.json` (open state + live names). |
| `shell/ccr.sh`           | Defines the `ccr` function; pipes the list through `fzf`.        |
| `install.sh`             | Wires `ccr.sh` into your shell rc.                               |

The helper does a single cheap pass per transcript (string-gated `json.loads`),
so listing hundreds of sessions takes ~2s.

## Configuration

Both are optional environment variables:

| Variable              | Default                | Purpose                                      |
| --------------------- | ---------------------- | -------------------------------------------- |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects`   | Where transcripts live (override for tests). |
| `CCR_HELPER`          | `<repo>/bin/...py`     | Path to the helper if you relocate it.       |
| `CCR_CONFIG_DIR`      | `~/.config/ccr`        | Exclusion files (`excluded`, `exclude-patterns`); honors `XDG_CONFIG_HOME`. |
| `CLAUDE_CONFIG_DIR`   | `~/.claude`            | Claude dir holding `projects/` and `sessions/`.        |

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
