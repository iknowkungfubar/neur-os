#!/bin/bash
# NeurOS — One-Command Installer
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
NAME="NeurOS"
BIN="$HOME/.local/bin"
DATA="$HOME/.local/share/neur-os"
DESKTOP="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"
SERVICE="$HOME/.config/systemd/user"

echo "==> Installing $NAME..."

# 1. Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is required. Install it first."
  exit 1
fi
echo "  ✓ Python $(python3 --version | cut -d' ' -f2)"

# 1b. Check Tauri desktop binary
TAURI_SRC="$DIR/desktop/src-tauri/target/release/neur-os"
HAVE_TAURI=false
if [ -f "$TAURI_SRC" ]; then
  HAVE_TAURI=true
  echo "  ✓ Desktop binary found ($(du -h "$TAURI_SRC" | cut -f1))"
else
  echo "  - No desktop binary — using web launcher"
fi

# 2. Install Python deps
echo "  → Installing Python packages..."
python3 -m pip install fastapi uvicorn httpx pydantic --quiet 2>&1 || \
python3 -m pip install fastapi uvicorn httpx pydantic --quiet --user 2>/dev/null
echo "  ✓ Dependencies installed"

# 3. Create directories
mkdir -p "$BIN" "$DATA" "$DESKTOP" "$AUTOSTART" "$SERVICE"

# 4. Copy project files
echo "  → Copying project files..."
mkdir -p "$DATA/backend" "$DATA/frontend"
cp -r "$DIR/backend" "$DATA/"
cp -r "$DIR/frontend" "$DATA/"
echo "  ✓ Project files copied"

# 5a. Install launcher script (backend)
cat > "$BIN/neur-os" << 'LAUNCHER'
#!/bin/bash
DIR="$HOME/.local/share/neur-os"
cd "$DIR"
exec python3 -m uvicorn backend.main:app --port 7447 --host 127.0.0.1
LAUNCHER
chmod +x "$BIN/neur-os"
echo "  ✓ Backend launcher installed at $BIN/neur-os"

# 5b. Copy desktop binary
if [ "$HAVE_TAURI" = true ]; then
  cp "$TAURI_SRC" "$BIN/neur-os-desktop"
  echo "  ✓ Desktop binary installed at $BIN/neur-os-desktop"
fi

# 6. Install .desktop entry (desktop binary if available, else web)
if [ "$HAVE_TAURI" = true ]; then
  DESKTOP_EXEC="$BIN/neur-os-desktop"
else
  DESKTOP_EXEC="xdg-open http://localhost:7447"
fi
cat > "$DESKTOP/$NAME.desktop" << DESKTOP
[Desktop Entry]
Name=NeurOS
Comment=Neuro-Affirming Cognitive Prosthetic
Exec=$DESKTOP_EXEC
Type=Application
Categories=Utility;
Terminal=false
StartupNotify=false
DESKTOP
echo "  ✓ Desktop entry installed"

# 7. Install systemd user service (backend auto-start)
mkdir -p "$SERVICE"
cat > "$SERVICE/neur-os.service" << SERVICE
[Unit]
Description=NeurOS — Neuro-Affirming Cognitive Prosthetic
After=network.target

[Service]
Type=simple
ExecStart=$BIN/neur-os
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
SERVICE
systemctl --user daemon-reload 2>/dev/null || true
echo "  ✓ Systemd service installed"

# 8. Start now
echo "  → Starting NeurOS..."
cd "$DATA"
python3 -m uvicorn backend.main:app --port 7447 --host 127.0.0.1 &
sleep 2

echo ""
echo "==> $NAME is running at http://localhost:7447"
echo "  - Start manually: $BIN/neur-os"
echo "  - Auto-start: systemctl --user enable neur-os"
if [ "$HAVE_TAURI" = true ]; then
  echo "  - Desktop app: $BIN/neur-os-desktop"
fi
echo "  - Open now: xdg-open http://localhost:7447"
echo ""
