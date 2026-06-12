#!/usr/bin/env bash
# ccr — global Claude Code session picker.
#
# Source this file from your shell rc (the installer does this for you):
#   source /path/to/claude-session-picker/shell/ccr.sh
#
# Then run `ccr` (optionally with a query: `ccr proxy oz`) to fuzzy-pick any
# Claude Code session across all directories and resume it in its original cwd.
#
# Overrides:
#   CCR_HELPER           path to claude-sessions.py (default: ../bin relative to this file)
#   CLAUDE_PROJECTS_DIR  transcript root (default: ~/.claude/projects), read by the helper

# Resolve the directory of THIS file, whether sourced from bash or zsh.
if [ -n "${ZSH_VERSION:-}" ]; then
  _ccr_self="${(%):-%x}"
else
  _ccr_self="${BASH_SOURCE[0]:-$0}"
fi
_ccr_root="$(cd "$(dirname "$_ccr_self")/.." >/dev/null 2>&1 && pwd)"
unset _ccr_self

: "${CCR_HELPER:=$_ccr_root/bin/claude-sessions.py}"
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

  local sel sid cwd
  sel=$(python3 "$CCR_HELPER" --list | fzf \
    --delimiter='\t' --with-nth=4 \
    --no-sort --reverse --height=85% \
    --prompt='session> ' \
    --query="$*" \
    --preview="python3 '$CCR_HELPER' --preview {3}" \
    --preview-window='right:52%:wrap') || return
  [ -z "$sel" ] && return

  sid=$(printf '%s' "$sel" | cut -f1)
  cwd=$(printf '%s' "$sel" | cut -f2)
  if [ -d "$cwd" ]; then
    cd "$cwd" || return
  fi
  claude --resume "$sid"
}
