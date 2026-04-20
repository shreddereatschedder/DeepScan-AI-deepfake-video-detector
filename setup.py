#!/usr/bin/env python3
"""
Automated Setup Script for Deepfake Credibility Checker
Installs FFmpeg and all Python dependencies in one command
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import re
import importlib.util
import tempfile
import time

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_step(step_num, text):
    """Print a numbered step"""
    print(f"{Colors.BOLD}{Colors.CYAN}[Step {step_num}]{Colors.RESET} {text}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}[SUCCESS] {text}{Colors.RESET}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.YELLOW}[INFO] {text}{Colors.RESET}")

def get_os_name():
    """Get operating system name"""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    else:
        return "linux"

def check_ffmpeg():
    """Check if FFmpeg is already installed"""
    print_step(1, "Checking for FFmpeg...")
    
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print_success(f"FFmpeg found at: {ffmpeg_path}")
        return True
    
    print_info("FFmpeg not found in system PATH")
    return False

def install_ffmpeg_windows():
    """Install FFmpeg on Windows"""
    print_step(1, "Installing FFmpeg on Windows...")

    target = Path(r"C:/ffmpeg/bin/ffmpeg.exe")
    if target.exists():
        print_success(f"FFmpeg already installed at: {target.parent}")
        return True

    print_info("FFmpeg not found at C:\\ffmpeg; attempting automated download and install...")

    ps_script = r"""
$zip="$env:TEMP\ffmpeg.zip"; $url="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip";
Write-Host "Downloading $url to $zip";
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;
Remove-Item -Recurse -Force C:\ffmpeg -ErrorAction SilentlyContinue;
Expand-Archive -LiteralPath $zip -DestinationPath C:\ffmpeg;
$dir=(Get-ChildItem -Directory C:\ffmpeg | Select-Object -First 1).FullName;
New-Item -ItemType Directory -Force -Path C:\ffmpeg\bin | Out-Null;
Move-Item -Force "$dir\bin\*" C:\ffmpeg\bin;
Remove-Item $zip -Force;
[Environment]::SetEnvironmentVariable("FFMPEG_PATH","C:\ffmpeg\bin\ffmpeg.exe","User");
$oldPath=[Environment]::GetEnvironmentVariable("PATH","User");
if($oldPath -notlike "*C:\ffmpeg\bin*"){ [Environment]::SetEnvironmentVariable("PATH", $oldPath + ";C:\ffmpeg\bin","User") };
Write-Host "ffmpeg installed to C:\ffmpeg\bin";
C:\ffmpeg\bin\ffmpeg.exe -version
"""

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(ps_script)
            tmp_path = f.name

        print_info("Running PowerShell to download and install FFmpeg (this may take a minute)...")
        subprocess.run([
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            tmp_path
        ], check=True)

        # Give the system a moment to settle and check presence
        time.sleep(1)
        if target.exists():
            print_success(f"FFmpeg installed at: {target.parent}")
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return True
        else:
            print_error("FFmpeg install completed but ffmpeg not found at expected location C:\\ffmpeg\\bin\\ffmpeg.exe")
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return False

    except subprocess.CalledProcessError as e:
        print_error(f"Automated FFmpeg install failed: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False
    except Exception as e:
        print_error(f"Unexpected error during FFmpeg install: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False

def install_ffmpeg_macos():
    """Install FFmpeg on macOS"""
    print_step(1, "Installing FFmpeg on macOS...")
    
    # Check if Homebrew is installed
    if shutil.which("brew"):
        print_info("Homebrew found. Installing FFmpeg via Homebrew...")
        try:
            subprocess.run(["brew", "install", "ffmpeg"], check=True)
            print_success("FFmpeg installed successfully via Homebrew")
            return True
        except subprocess.CalledProcessError:
            print_error("Failed to install FFmpeg via Homebrew")
            return False
    else:
        print_error("Homebrew not found - cannot auto-install FFmpeg on macOS. Please install Homebrew and re-run the script.")
        return False

def install_ffmpeg_linux():
    """Install FFmpeg on Linux"""
    print_step(1, "Installing FFmpeg on Linux...")
    
    distro = "ubuntu"  # Default assumption
    try:
        # Try to detect distribution
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "ubuntu" in content or "debian" in content:
                    distro = "debian"
                elif "fedora" in content or "rhel" in content:
                    distro = "fedora"
                elif "arch" in content:
                    distro = "arch"
    except:
        pass
    
    if distro == "debian":
        print_info("Detected Debian/Ubuntu. Installing FFmpeg...")
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)
            print_success("FFmpeg installed successfully")
            return True
        except subprocess.CalledProcessError:
            print_error("Failed to install FFmpeg")
            return False
    elif distro == "fedora":
        print_info("Detected Fedora/RHEL. Installing FFmpeg...")
        try:
            subprocess.run(["sudo", "dnf", "install", "-y", "ffmpeg"], check=True)
            print_success("FFmpeg installed successfully")
            return True
        except subprocess.CalledProcessError:
            print_error("Failed to install FFmpeg")
            return False
    elif distro == "arch":
        print_info("Detected Arch. Installing FFmpeg...")
        try:
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"], check=True)
            print_success("FFmpeg installed successfully")
            return True
        except subprocess.CalledProcessError:
            print_error("Failed to install FFmpeg")
            return False
    else:
        print_error(f"Unknown Linux distribution. Please install FFmpeg manually.")
        return False

def install_ffmpeg():
    """Install FFmpeg based on OS"""
    if check_ffmpeg():
        return True
    
    os_name = get_os_name()
    print_info(f"Detected OS: {platform.system()}")
    
    if os_name == "windows":
        return install_ffmpeg_windows()
    elif os_name == "macos":
        return install_ffmpeg_macos()
    else:
        return install_ffmpeg_linux()

def get_python_version():
    """Get Python version"""
    return f"{sys.version_info.major}.{sys.version_info.minor}"

def check_python_version():
    """Check if Python version is compatible"""
    print_step(2, "Checking Python version...")
    
    version = get_python_version()
    major, minor = sys.version_info.major, sys.version_info.minor
    
    print_info(f"Python version: {version}")
    
    if major == 3 and minor >= 9:
        print_success(f"Python {version} is compatible (3.11 recommended for best TensorFlow support)")
        return True
    else:
        print_error(f"Python {version} is not supported. Please install Python 3.9 or higher (3.11 recommended)")
        return False

def create_virtual_environment():
    """Optionally create a virtual environment"""
    print_step(3, "Virtual Environment Setup...")
    
    venv_path = Path(".venv")
    # If running inside an active virtual environment, skip creation
    in_venv = (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or os.environ.get('VIRTUAL_ENV'))
    if in_venv:
        print_info("Detected active virtual environment; skipping creation.")
        return True

    if venv_path.exists():
        print_info(f"Using existing virtual environment at {venv_path}")
        return True

    # Create .venv automatically
    print_info("Creating virtual environment at .venv...")
    try:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_success(f"Virtual environment created at .venv")
        os_name = get_os_name()
        if os_name == "windows":
            print_info("Activate virtual environment with: .venv\\Scripts\\activate")
        else:
            print_info("Activate virtual environment with: source .venv/bin/activate")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        return False

def install_python_packages():
    """Install Python packages from requirements.txt"""
    print_step(4, "Installing Python dependencies...")
    
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print_error("requirements.txt not found!")
        return False
    
    print_info("This may take 5-15 minutes depending on your internet connection...")
    print_info("TensorFlow is large (~500MB), please be patient...")
    
    # Read and normalize requirements
    with requirements_file.open("r", encoding="utf-8") as fh:
        raw_lines = [ln.strip() for ln in fh.readlines()]
    reqs = []
    for ln in raw_lines:
        if not ln or ln.startswith("#"):
            continue
        # remove environment markers after ';'
        ln = ln.split(';', 1)[0].strip()
        reqs.append(ln)

    # Ensure essential extras are present
    extras = ["uvicorn[standard]", "yt-dlp", "opencv-contrib-python", "mediapipe"]
    for ex in extras:
        base_ex = re.split(r"[<>=~!]+", ex)[0].split('[')[0].lower()
        if not any(re.split(r"[<>=~!]+", r)[0].split('[')[0].lower() == base_ex for r in reqs):
            reqs.append(ex)

    # Mapping from pip package base name -> importable module name
    import_map = {
        'uvicorn': 'uvicorn',
        'fastapi': 'fastapi',
        'pydantic': 'pydantic',
        'python-multipart': 'multipart',
        'python_multipart': 'multipart',
        'yt-dlp': 'yt_dlp',
        'yt_dlp': 'yt_dlp',
        'opencv-contrib-python': 'cv2',
        'opencv-python': 'cv2',
        'mediapipe': 'mediapipe',
        'tensorflow': 'tensorflow',
        'keras': 'keras',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scikit-learn': 'sklearn',
        'matplotlib': 'matplotlib',
        'tqdm': 'tqdm',
        'requests': 'requests',
    }

    # Upgrade pip first
    try:
        print_info("Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        print_success("Pip upgraded")
    except subprocess.CalledProcessError:
        print_error("Failed to upgrade pip; continuing with installation")

    # Helper to check import
    def is_importable(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except Exception:
            return False

    # Iterate and install missing packages individually
    for spec in reqs:
        # Extract base package name before any version or extras
        base = re.split(r"[<>=~!]+", spec)[0].split('[')[0].strip()
        base_lower = base.lower()
        import_name = import_map.get(base_lower, base_lower)

        if is_importable(import_name):
            print_info(f"{import_name} already installed; skipping {spec}")
            continue

        # Special handling: if installing opencv-contrib-python but opencv-python is present, uninstall it first
        if base_lower == 'opencv-contrib-python':
            try:
                if subprocess.run([sys.executable, '-m', 'pip', 'show', 'opencv-python'], capture_output=True).returncode == 0:
                    print_info('Detected opencv-python; uninstalling to avoid conflict')
                    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'opencv-python'], check=False)
            except Exception:
                pass

        try:
            print_info(f"Installing {spec}...")
            subprocess.run([sys.executable, "-m", "pip", "install", spec], check=True)
            print_success(f"Installed {spec}")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install {spec}: {e}")
            print_info("Continuing with remaining packages...")

    print_success("Finished attempting to install required Python packages")
    return True


def auto_setup_cookies():
    """Try to auto-export browser cookies using yt-dlp and set YT_DLP_COOKIES_FILE.

    Strategy:
    - Try common browsers (chrome, chromium, edge, firefox)
    - Use yt-dlp (executable or python -m yt_dlp) to export cookies to backend/downloads
    - If successful, set `YT_DLP_COOKIES_FILE` persistently for the user
    """
    print_step(6, "Auto-configuring yt-dlp cookies (best-effort)")
    downloads_dir = Path("backend") / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    browsers = ["chrome", "chromium", "edge", "firefox"]
    # map browser names to process name patterns to detect running browsers
    browser_procs = {
        'chrome': ['chrome.exe', 'chrome'],
        'chromium': ['chromium', 'chromium-browser'],
        'edge': ['msedge.exe', 'msedge', 'edge.exe'],
        'firefox': ['firefox.exe', 'firefox'],
    }

    def is_process_running(patterns: list[str]) -> bool:
        try:
            if os.name == 'nt':
                # Use tasklist on Windows
                proc = subprocess.run(["tasklist"], capture_output=True, text=True)
                out = proc.stdout.lower()
                for p in patterns:
                    if p.lower() in out:
                        return True
                return False
            else:
                # Use pgrep on Unix-like systems
                for p in patterns:
                    res = subprocess.run(["pgrep", "-f", p], capture_output=True)
                    if res.returncode == 0:
                        return True
                return False
        except Exception:
            return False
    yt_dlp_exec = shutil.which("yt-dlp")

    for browser in browsers:
        target = downloads_dir / f"cookies_auto_{browser}.txt"
        # Skip if already exists and non-empty
        try:
            if target.exists() and target.stat().st_size > 0:
                print_info(f"Found existing cookies for {browser}: {target}")
                # Persist env var
                abs_path = str(target.resolve())
                try:
                    if os.name == 'nt':
                        subprocess.run(["setx", "YT_DLP_COOKIES_FILE", abs_path], check=False)
                    else:
                        rc = Path.home() / ".bashrc"
                        line = f'export YT_DLP_COOKIES_FILE="{abs_path}"'
                        content = rc.read_text(encoding='utf-8') if rc.exists() else ''
                        if line not in content:
                            with open(rc, 'a', encoding='utf-8') as fh:
                                fh.write('\n# added by credibility_checker setup\n')
                                fh.write(line + '\n')
                    os.environ['YT_DLP_COOKIES_FILE'] = abs_path
                except Exception:
                    pass
                return True
        except Exception:
            pass

        # If the browser is running, skip the automatic export and notify the user
        procs = browser_procs.get(browser, [browser])
        if is_process_running(procs):
            print_info(f"Detected running {browser} process. Close {browser} completely and re-run setup to enable automatic cookie export for this browser.")
            continue

        # Build command
        url = "https://www.youtube.com/"
        if yt_dlp_exec:
            cmd = [yt_dlp_exec, "--cookies-from-browser", browser, "--cookies", str(target), "--skip-download", url]
        else:
            cmd = [sys.executable, "-m", "yt_dlp", "--cookies-from-browser", browser, "--cookies", str(target), "--skip-download", url]

        print_info(f"Attempting to export cookies from browser '{browser}' using yt-dlp...")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.CalledProcessError as e:
            # export failed for this browser; try next
            print_info(f"yt-dlp cookie export for {browser} failed: {e}")
            continue
        except Exception as e:
            print_info(f"yt-dlp cookie export for {browser} encountered an error: {e}")
            continue

        # Verify target file
        try:
            if target.exists() and target.stat().st_size > 0:
                abs_path = str(target.resolve())
                print_success(f"Exported cookies from {browser} to {abs_path}")
                # Persist for user
                try:
                    if os.name == 'nt':
                        subprocess.run(["setx", "YT_DLP_COOKIES_FILE", abs_path], check=False)
                    else:
                        rc = Path.home() / ".bashrc"
                        line = f'export YT_DLP_COOKIES_FILE="{abs_path}"'
                        content = rc.read_text(encoding='utf-8') if rc.exists() else ''
                        if line not in content:
                            with open(rc, 'a', encoding='utf-8') as fh:
                                fh.write('\n# added by credibility_checker setup\n')
                                fh.write(line + '\n')
                    os.environ['YT_DLP_COOKIES_FILE'] = abs_path
                except Exception:
                    pass
                return True
        except Exception:
            continue

    print_info("Auto cookie export did not succeed for any browser. You can still upload cookies or set YT_DLP_COOKIES_FILE manually.")
    return False

def verify_installation():
    """Verify that key packages are installed"""
    print_step(5, "Verifying installation...")
    
    packages_to_check = [
        ("tensorflow", "TensorFlow"),
        ("cv2", "OpenCV"),
        ("fastapi", "FastAPI"),
        ("yt_dlp", "yt-dlp"),
        ("mediapipe", "MediaPipe"),
        ("pandas", "Pandas"),
    ]
    
    all_ok = True
    for package, name in packages_to_check:
        try:
            __import__(package)
            print_success(f"{name} is installed")
        except ImportError:
            print_error(f"{name} is not installed")
            all_ok = False
    
    return all_ok

def print_completion_message():
    """Print completion message with next steps"""
    print_header("Setup Complete!")
    
    print(f"{Colors.GREEN}Everything is installed and ready to go!{Colors.RESET}\n")
    
    print(f"{Colors.BOLD}Next steps:{Colors.RESET}")
    print(f"  1. Activate virtual environment (if created):")
    
    os_name = get_os_name()
    if os_name == "windows":
        print(f"     .venv\\Scripts\\activate")
    else:
        print(f"     source .venv/bin/activate")
    
    print(f"\n  2. YT-DLP cookies:")
    print(f"     The setup attempts a best-effort automatic cookie export for yt-dlp.")
    print(f"     If downloads fail, see README.md for manual cookie setup options.")
    
    print(f"\n  3. Start the backend server:")
    print(f"     uvicorn backend.fastapi_server:app --reload")
    
    print(f"\n  4. Load the extension in Chrome:")
    print(f"     - Open chrome://extensions")
    print(f"     - Enable Developer Mode")
    print(f"     - Click 'Load unpacked'")
    print(f"     - Select the 'extension' folder")
    
    print(f"\n  5. Read README.md for detailed usage instructions")
    
    print(f"\n{Colors.BOLD}Troubleshooting:{Colors.RESET}")
    print(f"  - HTTP 429 'Too Many Requests' error: Set up cookies using one of the methods above")
    print(f"  - If you see any import errors, try: pip install --upgrade --force-reinstall -r requirements.txt")
    print(f"  - For TensorFlow errors on GPU: Check CUDA/cuDNN installation")
    print(f"  - For FFmpeg errors: Make sure FFmpeg is in your system PATH")
    print(f"\n{Colors.CYAN}Happy analyzing!{Colors.RESET}\n")

def main():
    """Main setup function"""
    print_header("Deepfake Credibility Checker - Automated Setup")
    
    print(f"{Colors.BOLD}This script will:{Colors.RESET}")
    print(f"  [1] Install/verify FFmpeg")
    print(f"  [2] Verify Python version")
    print(f"  [3] Create virtual environment (optional)")
    print(f"  [4] Install all Python dependencies (TensorFlow, OpenCV, etc.)")
    print(f"  [5] Verify installation")
    
    print_info("This may take a few minutes. Please don't interrupt...")
    
    # Run non-interactively: proceed automatically
    
    # Step 1: FFmpeg (attempt but do not abort on failure)
    if not install_ffmpeg():
        print_error("Automated FFmpeg installation failed or FFmpeg not present. Continuing anyway.")
    
    # Step 2: Python version
    if not check_python_version():
        print_error("Python version check failed. Setup cannot continue.")
        return False
    
    # Step 3: Virtual environment (auto)
    if not create_virtual_environment():
        print_error("Virtual environment setup failed; continuing in current environment.")
    
    # Step 4: Install packages
    if not install_python_packages():
        print_error("Failed to install Python packages.")
        return False

    # Step 4.5: Attempt to auto-export cookies for yt-dlp (best-effort)
    try:
        auto_setup_cookies()
    except Exception as e:
        print_info(f"Auto cookie setup encountered an error: {e}")
    
    # Step 5: Verify
    if not verify_installation():
        print_error("Some packages may not be installed correctly.")
        print_info("Try running: pip install -r requirements.txt")
        return False
    
    print_completion_message()
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
