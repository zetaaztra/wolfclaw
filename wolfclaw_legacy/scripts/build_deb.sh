#!/bin/bash
# scripts/build_deb.sh

set -e

echo "Building Wolfclaw Legacy for Ubuntu/Debian (Win 7/8 Parity)..."

# Navigate to project root
cd "$(dirname "$0")/.."

# 1. Build with PyInstaller
echo "Step 1: Running PyInstaller..."
staging_dir="build/wolfclaw_app"
mkdir -p "$staging_dir"
cp -r core auth channels api static "$staging_dir/"

pyinstaller --noconfirm --onedir --windowed --name Wolfclaw_Legacy --clean \
    --add-data "$staging_dir:wolfclaw_app" \
    --hidden-import uvicorn --hidden-import fastapi --hidden-import pydantic \
    --collect-data litellm \
    --collect-all uvicorn --collect-all fastapi \
    --hidden-import webview \
    --hidden-import pyautogui --hidden-import playwright --hidden-import PIL --hidden-import webview \
    desktop_launcher.py

# 1b. Build CLI with PyInstaller
echo "Step 1b: Running PyInstaller for CLI..."
pyinstaller --noconfirm --onefile --console --name Wolfclaw_Legacy_CLI --clean \
    --add-data "$staging_dir:wolfclaw_app" \
    --hidden-import typer --hidden-import rich \
    --collect-data litellm \
    cli.py

# 2. Setup DEB directory structure
echo "Step 2: Preparing DEBIAN architecture..."
DEB_DIR="dist/wolfclaw_deb"
rm -rf "$DEB_DIR"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/opt/wolfclaw"
mkdir -p "$DEB_DIR/usr/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"

# 3. Create control file
cat <<EOF > "$DEB_DIR/DEBIAN/control"
Package: wolfclaw-legacy
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: python3, libgtk-3-0, libwebkit2gtk-4.1-0 | libwebkit2gtk-4.0-37
Maintainer: Wolfclaw
Description: Wolfclaw AI (Legacy Support)
 A locally executable AI agent that can control your computer, terminal, and browser.
EOF

# 4. Copy build files and icons
echo "Step 3: Copying binaries and icons..."
cp -r dist/Wolfclaw_Legacy/* "$DEB_DIR/opt/wolfclaw/"
cp dist/Wolfclaw_Legacy_CLI "$DEB_DIR/opt/wolfclaw/"
cp static/img/wolfclaw-logo.png "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/wolfclaw.png"

# 5. Create symlink
ln -s /opt/wolfclaw/Wolfclaw_Legacy "$DEB_DIR/usr/bin/wolfclaw-legacy"
ln -s /opt/wolfclaw/Wolfclaw_Legacy_CLI "$DEB_DIR/usr/bin/wolfclaw-legacy-cli"

# 6. Create Desktop entry
cat <<EOF > "$DEB_DIR/usr/share/applications/wolfclaw.desktop"
[Desktop Entry]
Name=Wolfclaw AI (Legacy)
Comment=AI Command Center
Exec=/opt/wolfclaw/Wolfclaw_Legacy
Icon=wolfclaw
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
EOF

chmod +x "$DEB_DIR/usr/share/applications/wolfclaw.desktop"

# 7. Build the DEB
echo "Step 4: Building final .deb file..."
dpkg-deb --build "$DEB_DIR" "dist/wolfclaw-legacy_1.0.0_amd64.deb"

echo "Build complete! DEB package is at dist/wolfclaw_1.0.0_amd64.deb"
