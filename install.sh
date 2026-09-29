#!/usr/bin/env bash
set -euo pipefail
project_dir="$(dirname "$(readlink -f "$0")")"
app_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icon_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
mkdir -p "$app_dir" "$icon_dir"
cp "$project_dir/assets/brother-studio.svg" "$icon_dir/brother-studio.svg"
# Escape desktop-entry reserved characters, preserving a checkout containing spaces.
exec_path="${project_dir//\\/\\\\}/run.sh"
exec_path="${exec_path//\"/\\\"}"
exec_path="${exec_path//\$/\\\$}"
exec_path="${exec_path//\`/\\\`}"
exec_path="${exec_path//%/%%}"
cat > "$app_dir/brother-studio.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Brother Studio
Comment=Scan, print and manage your Brother MFC-L2800DW
Exec="$exec_path"
Icon=brother-studio
Terminal=false
Categories=Office;Scanning;Graphics;
Keywords=Brother;Scanner;Printer;PDF;
StartupWMClass=brother-studio
EOF
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$app_dir"
fi
echo 'Brother Studio installed in your application launcher.'
