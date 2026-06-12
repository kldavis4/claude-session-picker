#!/usr/bin/env bash
# Uninstaller for ccr (claude-session-picker).
# Removes the managed block from your shell rc. Leaves the repo itself alone.
#
# Overrides:
#   CCR_RC=/path/to/rc   force a specific rc file instead of auto-detecting
set -euo pipefail

BEGIN="# >>> ccr (claude-session-picker) >>>"
END="# <<< ccr (claude-session-picker) <<<"

if [ -n "${CCR_RC:-}" ]; then
  RC="$CCR_RC"
elif [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "zsh" ]; then
  RC="$HOME/.zshrc"
else
  RC="$HOME/.bashrc"
fi

if [ ! -f "$RC" ] || ! grep -qF "$BEGIN" "$RC"; then
  echo "ccr: no managed block found in $RC — nothing to do."
  exit 0
fi

tmp="$(mktemp)"
awk -v b="$BEGIN" -v e="$END" '
  $0==b {skip=1}
  !skip {print}
  $0==e {skip=0}
' "$RC" > "$tmp"
mv "$tmp" "$RC"

echo "Removed ccr block from $RC. Reload your shell to drop the function:"
echo "    exec \$SHELL -l"
