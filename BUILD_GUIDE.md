# Wolfclaw Build Guide

This guide provides step-by-step instructions for building Wolfclaw binaries from source for various platforms.

## Prerequisites

Before building any distribution, ensure you have the core dependencies installed:
- **Python 3.11+**
- `pip install -r requirements.txt`
- `pip install pyinstaller`

---

## 1. Building for Windows (.exe)

The Windows build creates a standalone folder with both a GUI and a CLI version.

### Steps:
1.  Open PowerShell or Command Prompt in the project root.
2.  Run the build script:
    ```powershell
    python scripts/build_exe.py
    ```
3.  **Output**: The binary folder will be in `dist/Wolfclaw/`.
4.  **Installer (Optional)**: If you have **Inno Setup 6** installed at the default path, the script will automatically generate `dist/Wolfclaw_Setup_v1.0.exe`.

---

## 2. Building for Linux (.deb)

The Debian build generates a native `.deb` package for Ubuntu, Debian, and Mint.

### Steps (Ubuntu/Linux):
1.  Ensure you have `dpkg-deb` installed (`sudo apt install dpkg`).
2.  Make the script executable:
    ```bash
    chmod +x scripts/build_deb.sh
    ```
3.  Run the script:
    ```bash
    ./scripts/build_deb.sh
    ```
4.  **Output**: The package will be created at `dist/wolfclaw_1.0.0_amd64.deb`.

---

## 3. Building the Legacy Version

The Legacy version is built using the same scripts but must be executed from the `wolfclaw_legacy` directory.

### Windows Legacy (.exe):
1.  Navigate to the legacy folder:
    ```powershell
    cd wolfclaw_legacy
    ```
2.  Run the legacy build script:
    ```powershell
    python scripts/build_exe.py
    ```

### Linux Legacy (.deb):
1.  Navigate to the legacy folder:
    ```bash
    cd wolfclaw_legacy
    ```
2.  Run the legacy deb build:
    ```bash
    bash scripts/build_deb.sh
    ```

---

## Troubleshooting

- **Missing Data Files**: Ensure the `static/`, `api/`, and `core/` folders are present in the root before building.
- **Hidden Imports**: If the `.exe` crashes with a `ModuleNotFoundError`, add the missing module to the `--hidden-import` list in the respective `build_exe.py` or `build_deb.sh` script.
- **Antivirus**: Some antivirus software may flag PyInstaller-generated executables as false positives. Signing the executable is recommended for official distribution.
