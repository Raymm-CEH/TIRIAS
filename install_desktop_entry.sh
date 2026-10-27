#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$APPLICATIONS_DIR"
cat > "$APPLICATIONS_DIR/tirias-control-center.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TIRIAS Control Center
Comment=Local dashboard for TIRIAS AI assistant
Exec=bash "$ROOT/run_control_center.sh"
Icon=utilities-terminal
Terminal=false
Categories=Utility;Accessibility;
StartupNotify=true
EOF
chmod 644 "$APPLICATIONS_DIR/tirias-control-center.desktop"
printf 'Desktop entry installed at: %s\n' "$APPLICATIONS_DIR/tirias-control-center.desktop"
printf 'Find “TIRIAS Control Center” in your desktop applications menu.\n'
