import os
import subprocess
import sys
import shutil
from pathlib import Path

def build_windows_exe():
    """Build the Wolfclaw Desktop Engine into a standalone Windows executable."""
    print("Building Wolfclaw Legacy for Windows 7/8...")
    
    project_root = Path(__file__).resolve().parent.parent
    launcher_script = project_root / "desktop_launcher.py"
    
    if not launcher_script.exists():
        print(f"Error: Could not find {launcher_script}")
        sys.exit(1)

    # Create a staging directory with all the wolfclaw source files
    # PyInstaller only bundles Python imports - our app.py and modules
    # need to be included explicitly as data files.
    staging_dir = project_root / "build" / "wolfclaw_app"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all source files needed at runtime
    source_items = ["core", "auth", "channels", "api", "static"]
    for item in source_items:
        src = project_root / item
        dst = staging_dir / item
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            shutil.copy2(src, dst)
        else:
            print(f"Warning: {item} not found, skipping.")
    
    # Copy .env if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        shutil.copy2(env_file, staging_dir / ".env")
    
    print(f"Staged source files to: {staging_dir}")
    
    # Use os.pathsep for Windows path separator in --add-data
    sep = ";"  # Windows uses ; as the PyInstaller add-data separator

    # PyInstaller command
    command = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",  # MUST DO PRODUCTION RUN HIDDEN
        "--name", "Wolfclaw_Legacy",
        "--clean",
        
        # Bundle the entire Wolfclaw source tree into _internal/wolfclaw_app
        # This copies everything we just staged above (including api/ and static/)
        f"--add-data", f"{staging_dir}{sep}wolfclaw_app",
        
        # Collect FastAPI, Uvicorn, and LiteLLM runtime dependencies
        "--collect-all", "litellm",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "pydantic",
        "--hidden-import", "uvicorn",
        "--hidden-import", "fastapi",
        "--hidden-import", "starlette",

        # Hidden imports for all our existing dependencies
        "--hidden-import", "webdriver_manager",
        "--hidden-import", "selenium",
        "--hidden-import", "playwright",
        "--hidden-import", "pyautogui",
        "--hidden-import", "PIL",
        "--hidden-import", "webview",
        
        "--icon", str(project_root / "static" / "img" / "wolfclaw-logo.ico"),
        str(launcher_script)
    ]
    
    os.chdir(project_root)
    try:
        print(f"Running PyInstaller for GUI...")
        subprocess.run(command, check=True)
        
        # --- CLI BUILD PASS ---
        print("\nBuilding Wolfclaw Legacy CLI...")
        cli_script = project_root / "cli.py"
        cli_command = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--onefile", "--console",
            "--name", "Wolfclaw_Legacy_CLI",
            "--clean",
            f"--add-data", f"{staging_dir}{sep}wolfclaw_app",
            "--collect-all", "litellm",
            "--hidden-import", "typer",
            "--hidden-import", "rich",
            str(cli_script)
        ]
        subprocess.run(cli_command, check=True)
        print("\n" + "="*50)
        print("  BUILD SUCCESSFUL!")
        print("="*50)
        print(f"Executable folder: {project_root / 'dist' / 'Wolfclaw_Legacy'}")
        print(f"GUI: dist\\Wolfclaw_Legacy\\Wolfclaw_Legacy.exe")
        print(f"CLI: dist\\Wolfclaw_Legacy_CLI.exe")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)

    # --- INNO SETUP STEP ---
    iscc = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    iss_script = project_root / "scripts" / "installer.iss"
    
    if os.path.exists(iscc) and iss_script.exists():
        print(f"\nFound Inno Setup at {iscc}")
        print("Building Setup Wizard...")
        try:
            subprocess.run([iscc, str(iss_script)], check=True)
            print("\n" + "="*50)
            print("  WIZARD BUILD SUCCESSFUL!")
            print("="*50)
            print(f"Setup file: {project_root / 'dist' / 'Wolfclaw_Legacy_Setup_v1.0.exe'}")
        except Exception as e:
            print(f"Wizard build failed: {e}")
    else:
        print("\nSkipping Inno Setup (ISCC.exe not found or installer.iss missing).")
        print("Note: Install Inno Setup 6 to generate a professional .exe wizard.")

if __name__ == "__main__":
    build_windows_exe()

