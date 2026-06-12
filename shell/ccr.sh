#!/usr/bin/env bash
# ccr — global Claude Code session picker.
#
# Source this file from your shell rc (the installer does this for you):
#   source /path/to/claude-session-picker/shell/ccr.sh
#
# Usage:
#   ccr                  fuzzy-pick an active session and resume it in its cwd
#   ccr <query>          same, with the picker pre-filtered by <query>
#   ccr -a | --all       start in "show all" mode (includes excluded sessions)
#   ccr <query> -- ARGS  pass ARGS straight to `claude --resume` (e.g. --model opus)
#
# In the picker:
#   type        fuzzy-filter across title + directory + branch (no spaces — see below)
#   space       toggle favorite (★) — favorites sort to the top by last activity
#   ctrl-x      toggle exclude on the highlighted session (hide / un-hide)
#   ctrl-a      toggle between active view and show-all (excluded marked ✕)
#   enter       resume the session in its original directory
#
# Note: space is bound to favorite, so it can't be typed in the search query
# (fzf would otherwise treat it as a term separator). Single-term substrings
# still match fine.
#
# Overrides:
#   CCR_HELPER           path to claude-sessions.py (default: ../bin relative to this file)
#   CCR_CLAUDE_ARGS      flags appended to every `claude --resume` (e.g.
#                        export CCR_CLAUDE_ARGS="--dangerously-skip-permissions")
#   CLAUDE_PROJECTS_DIR  transcript root (default: ~/.claude/projects)
#   CCR_CONFIG_DIR       exclusion config dir (default: ~/.config/ccr)

# Resolve the directory of THIS file, whether sourced from bash or zsh.
if [ -n "${ZSH_VERSION:-}" ]; then
  _ccr_self="${(%):-%x}"
else
  _ccr_self="${BASH_SOURCE[0]:-$0}"
fi
_ccr_root="$(cd "$(dirname "$_ccr_self")/.." >/dev/null 2>&1 && pwd)"
unset _ccr_self

: "${CCR_HELPER:=$_ccr_root/bin/claude-sessions.py}"
export CCR_HELPER   # exported so fzf's bind/preview subshells can reference it
unset _ccr_root

ccr() {
  if ! command -v fzf >/dev/null 2>&1; then
    echo "ccr: fzf not found — install it (brew install fzf / apt install fzf)" >&2
    return 1
  fi
  if [ ! -f "$CCR_HELPER" ]; then
    echo "ccr: helper not found at $CCR_HELPER (set CCR_HELPER)" >&2
    return 1
  fi

  # Parse args: [-a|--all] [query...] [-- claude-args...]
  # Everything after a literal `--` is passed straight through to claude.
  local all=0 sep=0 a
  local -a query_parts claude_extra
  for a in "$@"; do
    if [ "$sep" -eq 1 ]; then claude_extra+=("$a"); continue; fi
    case "$a" in
      --)       sep=1 ;;
      -a|--all) all=1 ;;
      *)        query_parts+=("$a") ;;
    esac
  done

  # Default claude flags from CCR_CLAUDE_ARGS, word-split portably (zsh/bash).
  local -a envargs
  if [ -n "${CCR_CLAUDE_ARGS:-}" ]; then
    if [ -n "${ZSH_VERSION:-}" ]; then envargs=(${=CCR_CLAUDE_ARGS}); else envargs=($CCR_CLAUDE_ARGS); fi
  fi

  local prompt
  local -a feed
  if [ "$all" -eq 1 ]; then
    prompt='all> '; feed=(--list --all)
  else
    prompt='session> '; feed=(--list)
  fi

  local sel sid cwd
  sel=$(python3 "$CCR_HELPER" "${feed[@]}" | fzf \
    --delimiter='\t' --with-nth=4 \
    --no-sort --reverse --height=85% \
    --prompt="$prompt" \
    --query="${query_parts[*]}" \
    --header='space ★fav · ctrl-x hide · ctrl-a all · enter resume   (★ favorite, ● open)' \
    --preview="python3 \"\$CCR_HELPER\" --preview {3}" \
    --preview-window='down:33%:wrap:border-top' \
    --bind="ctrl-x:execute-silent(python3 \"\$CCR_HELPER\" --toggle-exclude {1})+transform:[ \"\$FZF_PROMPT\" = 'all> ' ] && echo 'reload(python3 \"\$CCR_HELPER\" --list --all)' || echo 'reload(python3 \"\$CCR_HELPER\" --list)'" \
    --bind="ctrl-a:transform:[ \"\$FZF_PROMPT\" = 'all> ' ] && echo 'change-prompt(session> )+reload(python3 \"\$CCR_HELPER\" --list)' || echo 'change-prompt(all> )+reload(python3 \"\$CCR_HELPER\" --list --all)'" \
    --bind="space:execute-silent(python3 \"\$CCR_HELPER\" --toggle-favorite {1})+transform:[ \"\$FZF_PROMPT\" = 'all> ' ] && echo 'reload(python3 \"\$CCR_HELPER\" --list --all)' || echo 'reload(python3 \"\$CCR_HELPER\" --list)'") || return
  [ -z "$sel" ] && return

  sid=$(printf '%s' "$sel" | cut -f1)
  cwd=$(printf '%s' "$sel" | cut -f2)
  if [ -d "$cwd" ]; then
    cd "$cwd" || return
  fi
  claude --resume "$sid" "${envargs[@]}" "${claude_extra[@]}"
}
