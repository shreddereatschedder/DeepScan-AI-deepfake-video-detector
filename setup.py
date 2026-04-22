#!/usr/bin/env python3
"""
Automated Setup Script for Deepfake Credibility Checker

Behaviour (simplified per user request):
- Ensure a virtual environment exists for the project ('.venv' preferred, falls back to 'venv').
- Attempt a best-effort PowerShell activation on Windows (prints/executes the activation command).
- Re-launch this script using the venv's Python so subsequent steps run inside the venv.
- Run `python -m pip install -r requirements.txt` inside the venv.

This file intentionally avoids complex "smart" dependency ordering which previously
caused NumPy / TensorFlow conflicts. Keep `requirements.txt` controlled by the user.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import importlib.util
import sysconfig
import tempfile
import time

# ANSI color codes for terminal output (best-effort)
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
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_step(step_num, text):
    print(f"{Colors.BOLD}{Colors.CYAN}[Step {step_num}]{Colors.RESET} {text}")


def print_success(text):
    print(f"{Colors.GREEN}[SUCCESS] {text}{Colors.RESET}")


def print_error(text):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")


def print_info(text):
    print(f"{Colors.YELLOW}[INFO] {text}{Colors.RESET}")


def get_os_name():
    system = platform.system()
    if system == 'Windows':
        return 'windows'
    if system == 'Darwin':
        return 'macos'
    return 'linux'


# -------------------------- FFmpeg helpers (unchanged) --------------------------

def check_ffmpeg():
    print_step(1, 'Checking for FFmpeg...')
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        print_success(f'FFmpeg found at: {ffmpeg_path}')
        return True
    print_info('FFmpeg not found in system PATH')
    return False


def install_ffmpeg_windows():
    print_step(1, 'Installing FFmpeg on Windows...')
    target = Path('C:/ffmpeg/bin/ffmpeg.exe')
    if target.exists():
        print_success(f'FFmpeg already installed at: {target.parent}')
        return True

    print_info('FFmpeg not found at C:\\ffmpeg; attempting automated download and install...')
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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
            f.write(ps_script)
            tmp_path = f.name
        print_info('Running PowerShell to download and install FFmpeg (this may take a minute)...')
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', tmp_path], check=True)
        time.sleep(1)
        if target.exists():
            print_success(f'FFmpeg installed at: {target.parent}')
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return True
        print_error('FFmpeg install completed but ffmpeg not found at expected location C:\\ffmpeg\\bin\\ffmpeg.exe')
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return False
    except subprocess.CalledProcessError as e:
        print_error(f'Automated FFmpeg install failed: {e}')
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False
    except Exception as e:
        print_error(f'Unexpected error during FFmpeg install: {e}')
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False


def install_ffmpeg_macos():
    print_step(1, 'Installing FFmpeg on macOS...')
    if shutil.which('brew'):
        print_info('Homebrew found. Installing FFmpeg via Homebrew...')
        try:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True)
            print_success('FFmpeg installed successfully via Homebrew')
            return True
        except subprocess.CalledProcessError:
            print_error('Failed to install FFmpeg via Homebrew')
            return False
    print_error('Homebrew not found - cannot auto-install FFmpeg on macOS. Please install Homebrew and re-run the script.')
    return False


def install_ffmpeg_linux():
    print_step(1, 'Installing FFmpeg on Linux...')
    distro = 'ubuntu'
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content:
                    distro = 'debian'
                elif 'fedora' in content or 'rhel' in content:
                    distro = 'fedora'
                elif 'arch' in content:
                    distro = 'arch'
    except Exception:
        pass
    if distro == 'debian':
        print_info('Detected Debian/Ubuntu. Installing FFmpeg...')
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=False)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True)
            print_success('FFmpeg installed successfully')
            return True
        except subprocess.CalledProcessError:
            print_error('Failed to install FFmpeg')
            return False
    elif distro == 'fedora':
        print_info('Detected Fedora/RHEL. Installing FFmpeg...')
        try:
            subprocess.run(['sudo', 'dnf', 'install', '-y', 'ffmpeg'], check=True)
            print_success('FFmpeg installed successfully')
            return True
        except subprocess.CalledProcessError:
            print_error('Failed to install FFmpeg')
            return False
    elif distro == 'arch':
        print_info('Detected Arch. Installing FFmpeg...')
        try:
            subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'ffmpeg'], check=True)
            print_success('FFmpeg installed successfully')
            return True
        except subprocess.CalledProcessError:
            print_error('Failed to install FFmpeg')
            return False
    print_error('Unknown Linux distribution. Please install FFmpeg manually.')
    return False


def install_ffmpeg():
    if check_ffmpeg():
        return True
    os_name = get_os_name()
    print_info(f'Detected OS: {platform.system()}')
    if os_name == 'windows':
        return install_ffmpeg_windows()
    if os_name == 'macos':
        return install_ffmpeg_macos()
    return install_ffmpeg_linux()


# -------------------------- Python checks / venv handling --------------------------

def get_python_version():
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def check_python_version():
    print_step(2, 'Checking Python version...')
    version = get_python_version()
    major, minor = sys.version_info.major, sys.version_info.minor
    print_info(f'Python version: {version}')
    if major == 3 and minor >= 9:
        print_success(f'Python {version} is compatible (3.11 recommended for best TensorFlow support)')
        return True
    print_error(f'Python {version} is not supported. Please install Python 3.9 or higher (3.11 recommended)')
    return False


def create_virtual_environment():
    """Create or use a venv and re-launch the script inside it.

    - Prefers existing .venv, then venv. If none exist, creates .venv.
    - Attempts a best-effort PowerShell activation on Windows (this opens a new shell and does not affect this process),
      but the function will re-exec this script using the venv python so the remaining work runs inside the venv.
    - Avoids infinite re-exec via the `CRED_SETUP_IN_VENV` env var.
    """
    print_step(3, 'Virtual Environment Setup...')

    project_root = Path(__file__).resolve().parent

    # detect active venv
    in_venv = (
        hasattr(sys, 'real_prefix')
        or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        or os.environ.get('VIRTUAL_ENV')
    )
    if in_venv:
        print_info('Detected active virtual environment; skipping creation.')
        return True

    candidates = [project_root / '.venv', project_root / 'venv']
    venv_path = None
    for c in candidates:
        if c.exists():
            venv_path = c
            break

    if venv_path is None:
        venv_path = project_root / '.venv'
        print_info(f'Creating virtual environment at {venv_path}...')
        try:
            subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)
            print_success(f'Virtual environment created at {venv_path}')
        except subprocess.CalledProcessError as e:
            print_error(f'Failed to create virtual environment: {e}')
            return False
    else:
        print_info(f'Using existing virtual environment at {venv_path}')

    # Path to venv python & activation scripts
    if os.name == 'nt':
        venv_python = venv_path / 'Scripts' / 'python.exe'
        activate_ps1 = venv_path / 'Scripts' / 'Activate.ps1'
    else:
        venv_python = venv_path / 'bin' / 'python'
        activate_sh = venv_path / 'bin' / 'activate'

    if not venv_python.exists():
        print_error(f'Virtualenv python not found at {venv_python}')
        return False

    # If already running under venv python, proceed
    try:
        if Path(sys.executable).resolve() == venv_python.resolve() or os.environ.get('CRED_SETUP_IN_VENV') == '1':
            print_info('Running inside virtual environment; proceeding.')
            return True
    except Exception:
        pass

    # Best-effort: run the PowerShell activation command on Windows so the user terminal may become activated
    if os.name == 'nt' and activate_ps1.exists():
        try:
            ps_cmd = f"(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& '{str(activate_ps1)}')"
            print_info(f'Attempting PowerShell activation (best-effort): {ps_cmd}')
            subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_cmd], check=False)
        except Exception as e:
            print_info(f'PowerShell activation attempt failed: {e}')

    # Re-launch the script using the venv python so subsequent steps run inside the venv
    print_info(f'Re-launching setup.py inside virtual environment using: {venv_python}')
    new_env = os.environ.copy()
    new_env['CRED_SETUP_IN_VENV'] = '1'
    try:
        rc = subprocess.call([str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:], env=new_env)
        sys.exit(int(rc) if rc is not None else 0)
    except Exception as e:
        print_error(f'Failed to re-launch setup inside virtualenv: {e}')
        return False


def add_scripts_to_path():
    """Ensure the Python `scripts` directory is on `PATH` for this process only.

    Deliberately avoid persisting changes to user PATH or shell rc files.
    """
    try:
        scripts_path = sysconfig.get_path('scripts')
    except Exception:
        if os.name == 'nt':
            scripts_path = os.path.join(os.path.dirname(sys.executable), 'Scripts')
        else:
            scripts_path = os.path.join(os.path.dirname(sys.executable), 'bin')

    if not scripts_path:
        return

    scripts_path = os.path.normpath(scripts_path)
    cur_path = os.environ.get('PATH', '')
    parts = cur_path.split(os.pathsep) if cur_path else []
    if scripts_path not in parts:
        os.environ['PATH'] = scripts_path + os.pathsep + cur_path
        print_info(f'Added {scripts_path} to PATH for this session')


def install_python_packages():
    """Install Python packages from `requirements.txt` inside the project's virtualenv.

    This is intentionally simple: upgrade pip (best-effort) then install the user's
    requirements with `pip install -r requirements.txt` using the current interpreter.
    """
    print_step(4, 'Installing Python dependencies from requirements.txt...')

    requirements_file = Path('requirements.txt')
    if not requirements_file.exists():
        print_error('requirements.txt not found!')
        return False

    print_info('Installing packages from requirements.txt inside the virtual environment...')

    # Keep behavior minimal: do not upgrade pip or install anything else first.
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)], check=True)
        print_success('Installed packages from requirements.txt')
        return True
    except subprocess.CalledProcessError as e:
        print_error(f'Failed to install requirements: {e}')
        return False


# -------------------------- yt-dlp cookie auto-setup (best-effort) --------------------------

def auto_setup_cookies():
    print_step(6, 'Auto-configuring yt-dlp cookies (best-effort)')
    downloads_dir = Path('backend') / 'downloads'
    downloads_dir.mkdir(parents=True, exist_ok=True)

    browsers = ['chrome', 'chromium', 'edge', 'firefox']
    browser_procs = {
        'chrome': ['chrome.exe', 'chrome'],
        'chromium': ['chromium', 'chromium-browser'],
        'edge': ['msedge.exe', 'msedge', 'edge.exe'],
        'firefox': ['firefox.exe', 'firefox'],
    }

    def is_process_running(patterns: list[str]) -> bool:
        try:
            if os.name == 'nt':
                proc = subprocess.run(['tasklist'], capture_output=True, text=True)
                out = proc.stdout.lower()
                for p in patterns:
                    if p.lower() in out:
                        return True
                return False
            else:
                for p in patterns:
                    res = subprocess.run(['pgrep', '-f', p], capture_output=True)
                    if res.returncode == 0:
                        return True
                return False
        except Exception:
            return False

    yt_dlp_exec = shutil.which('yt-dlp')

    for browser in browsers:
        target = downloads_dir / f'cookies_auto_{browser}.txt'
        try:
            if target.exists() and target.stat().st_size > 0:
                print_info(f'Found existing cookies for {browser}: {target}')
                abs_path = str(target.resolve())
                try:
                    if os.name == 'nt':
                        subprocess.run(['setx', 'YT_DLP_COOKIES_FILE', abs_path], check=False)
                    else:
                        rc = Path.home() / '.bashrc'
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

        procs = browser_procs.get(browser, [browser])
        if is_process_running(procs):
            print_info(f'Detected running {browser} process. Close {browser} completely and re-run setup to enable automatic cookie export for this browser.')
            continue

        url = 'https://www.youtube.com/'
        if yt_dlp_exec:
            cmd = [yt_dlp_exec, '--cookies-from-browser', browser, '--cookies', str(target), '--skip-download', url]
        else:
            cmd = [sys.executable, '-m', 'yt_dlp', '--cookies-from-browser', browser, '--cookies', str(target), '--skip-download', url]

        print_info(f"Attempting to export cookies from browser '{browser}' using yt-dlp...")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.CalledProcessError as e:
            print_info(f'yt-dlp cookie export for {browser} failed: {e}')
            continue
        except Exception as e:
            print_info(f'yt-dlp cookie export for {browser} encountered an error: {e}')
            continue

        try:
            if target.exists() and target.stat().st_size > 0:
                abs_path = str(target.resolve())
                print_success(f'Exported cookies from {browser} to {abs_path}')
                try:
                    if os.name == 'nt':
                        subprocess.run(['setx', 'YT_DLP_COOKIES_FILE', abs_path], check=False)
                    else:
                        rc = Path.home() / '.bashrc'
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

    print_info('Auto cookie export did not succeed for any browser. You can still upload cookies or set YT_DLP_COOKIES_FILE manually.')
    return False


# -------------------------- verification and completion --------------------------

def verify_installation():
    print_step(5, 'Verifying installation...')
    packages_to_check = [
        ('tensorflow', 'TensorFlow'),
        ('cv2', 'OpenCV'),
        ('fastapi', 'FastAPI'),
        ('yt_dlp', 'yt-dlp'),
        ('mediapipe', 'MediaPipe'),
        ('pandas', 'Pandas'),
    ]
    all_ok = True
    for package, name in packages_to_check:
        try:
            __import__(package)
            print_success(f'{name} is installed')
        except Exception:
            print_error(f'{name} is not installed')
            all_ok = False
    return all_ok


def print_completion_message():
    print_header('Setup Complete!')
    print(f"{Colors.GREEN}Everything is installed and ready to go!{Colors.RESET}\n")
    print(f"{Colors.BOLD}Next steps:{Colors.RESET}")
    print('\n  1. Start the backend server:')
    print('     uvicorn backend.fastapi_server:app --reload')
    print('\n  2. Load the extension in Chrome:')
    print('     - Open chrome://extensions')
    print('     - Enable Developer Mode')
    print("     - Click 'Load unpacked'")
    print("     - Select the 'extension' folder")
    print('\n  3. Read README.md for detailed usage instructions')
    print('\nTroubleshooting:')
    print('  - If you see any import errors, try: pip install -r requirements.txt')
    print('  - For TensorFlow errors on GPU: Check CUDA/cuDNN installation')
    print('  - For FFmpeg errors: Make sure FFmpeg is in your system PATH')
    print(f"\n{Colors.CYAN}Happy analyzing!{Colors.RESET}\n")


# -------------------------- Main --------------------------

def main():
    print_header('Deepfake Credibility Checker - Automated Setup')
    print(f"{Colors.BOLD}This script will:{Colors.RESET}")
    print('  [1] Install/verify FFmpeg')
    print('  [2] Verify Python version')
    print('  [3] Create (and run) virtual environment')
    print('  [4] Install all Python dependencies via requirements.txt')
    print('  [5] Verify installation')
    print_info('This may take a few minutes. Please do not interrupt...')

    # Step 1: FFmpeg (attempt but do not abort on failure)
    if not install_ffmpeg():
        print_error('Automated FFmpeg installation failed or FFmpeg not present. Continuing anyway.')

    # Step 2: Python version
    if not check_python_version():
        print_error('Python version check failed. Setup cannot continue.')
        return False

    # Step 3: Create and (re-)enter virtual environment
    if not create_virtual_environment():
        print_error('Virtual environment setup failed; continuing in current environment.')

    # Ensure Python scripts directory is on PATH before installing packages
    try:
        add_scripts_to_path()
    except Exception:
        pass

    # Step 4: Install requirements via pip (inside venv)
    if not install_python_packages():
        print_error('Failed to install Python packages from requirements.txt.')
        return False

    # Step 4.5: Attempt to auto-export cookies for yt-dlp (best-effort)
    try:
        auto_setup_cookies()
    except Exception as e:
        print_info(f'Auto cookie setup encountered an error: {e}')

    # Step 5: Verify
    if not verify_installation():
        print_error('Some packages may not be installed correctly.')
        print_info('Try running: pip install -r requirements.txt')
        return False

    print_completion_message()
    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print('\n\nSetup interrupted by user.')
        sys.exit(1)
    except Exception as e:
        print_error(f'Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
