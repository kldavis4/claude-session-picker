#!/usr/bin/env bash
# Installer for ccr (claude-session-picker).
# Adds a `source .../shell/ccr.sh` line to your shell rc, idempotently.
#
# Overrides:
#   CCR_RC=/path/to/rc   force a specific rc file instead of auto-detecting
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SRC_LINE="source \"$REPO/shell/ccr.sh\""
BEGIN="# >>> ccr (claude-session-picker) >>>"
END="# <<< ccr (claude-session-picker) <<<"

# Choose the rc file to modify.
if [ -n "${CCR_RC:-}" ]; then
  RC="$CCR_RC"
elif [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "zsh" ]; then
  RC="$HOME/.zshrc"
else
  RC="$HOME/.bashrc"
fi

echo "ccr installer"
echo "  repo : $REPO"
echo "  rc   : $RC"

# Dependency checks.
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required but was not found." >&2
  exit 1
fi
if ! command -v fzf >/dev/null 2>&1; then
  echo "WARNING: fzf not found — ccr needs it. Install one of:" >&2
  echo "    macOS : brew install fzf" >&2
  echo "    Debian: sudo apt install fzf" >&2
  echo "    Fedora: sudo dnf install fzf" >&2
  echo "    Arch  : sudo pacman -S fzf" >&2
fi

chmod +x "$REPO/bin/claude-sessions.py"

# Idempotent: strip any prior managed block, then append a fresh one.
touch "$RC"
if grep -qF "$BEGIN" "$RC"; then
  tmp="$(mktemp)"
  awk -v b="$BEGIN" -v e="$END" '
    $0==b {skip=1}
    !skip {print}
    $0==e {skip=0}
  ' "$RC" > "$tmp"
  mv "$tmp" "$RC"
  echo "  (replaced existing ccr block)"
fi
{
  echo "$BEGIN"
  echo "$SRC_LINE"
  echo "$END"
} >> "$RC"

echo
echo "Installed. Reload your shell:"
echo "    source \"$RC\""
echo "Then run:  ccr"
