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
git clone <your-fork-url> ~/projects/claude-session-picker
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
ccr                # browse all sessions, newest first
ccr proxy oz       # open the picker pre-filtered by a query
```

Inside the picker:

- **Type** to fuzzy-filter across title + directory + branch.
- **↑/↓** to move; the right pane previews the session's opening prompts.
- **Enter** to resume — `ccr` `cd`s into the session's original directory and
  runs `claude --resume <id>`.
- **Esc** to cancel.

## How it works

| Piece                    | Role                                                             |
| ------------------------ | --------------------------------------------------------------- |
| `bin/claude-sessions.py` | Scans `~/.claude/projects/*/*.jsonl`, extracts title/cwd/branch. |
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
