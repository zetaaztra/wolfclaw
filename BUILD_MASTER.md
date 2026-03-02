# 🏗️ Wolfclaw Master Build Guide (v2.1)

This guide provides the official steps to build Wolfclaw for production distribution across all 5 fleets.

## 📋 Prerequisites
- **Python**: 3.11 or 3.12 (highly recommended)
- **Git**: To clone and manage versions.
- **Dependencies**: `pip install -r requirements.txt`
- **Build Tools**: `pip install pyinstaller`

---

## 1. Main Desktop EXE (Windows)
This is the primary production build. It bundles the FastAPI backend, the Streamlit UI, and the PyWebView wrapper into a single high-performance package.

**Build Command:**
```powershell
# From the project root
pyinstaller Wolfclaw.spec
```
- **Output**: Located in `dist/Wolfclaw/`
- **Note**: The first run may take several minutes as it optimizes libraries like OpenCV and Playwright.

---

## 2. Linux DEB Package (Ubuntu/Debian)
Generates a native installer for Linux users.

**Build Command:**
```bash
# Ensure script is executable
chmod +x scripts/build_deb.sh
./scripts/build_deb.sh
```
- **Output**: `dist/wolfclaw_1.0.0_amd64.deb`
- **Installation**: `sudo apt install ./dist/wolfclaw_1.0.0_amd64.deb`

---

## 3. Legacy Streamlit EXE
A lightweight version that runs Streamlit directly in your default browser.

**Build Command:**
```powershell
cd wolfclaw_legacy
pyinstaller --name "Wolfclaw_Legacy" --noconfirm --onedir --windowed --add-data "ui;ui" --add-data "core;core" --hidden-import "streamlit" app.py
```
- **Output**: `wolfclaw_legacy/dist/Wolfclaw_Legacy/`

---

## 📦 Distribution & GitHub Uploads

### Handling the 2.4GB File
GitHub has a **2GB limit** for direct file uploads.
1. **Compress**: Use 7-Zip (LZMA2 / Ultra) to compress the `dist/Wolfclaw/` folder. This often reduces the size significantly.
2. **Split-Zip**: If still over 2GB, use 7-Zip to split the archive into two parts (`.zip.001`, `.zip.002`).
3. **External Hosting**: Upload the full EXE to **Google Drive**, **OneDrive**, or **Archive.org** and put the direct link in the GitHub Release description.

### Creating a GitHub Release
1. Go to your repository → **Releases** → **Draft a new release**.
2. Upload the `.deb` and the compressed Legacy EXE directly.
3. Paste the download link for the Main EXE in the release notes.

---

## 🛠️ Troubleshooting
- **ModuleNotFoundError**: If the built EXE crashes, check the logs and add the missing module to `hiddenimports` in `Wolfclaw.spec`.
- **Path Issues**: Always run build commands from the project root unless specified.
- **Virus Flags**: Since Wolfclaw performs automation (typing/clicking), some antivirus may flag it. This is normal for automation tools.
