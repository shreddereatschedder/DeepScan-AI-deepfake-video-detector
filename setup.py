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
    
    print_info("Downloading FFmpeg...")
    print_info("Two options available:")
    print_info("  1. Download from: https://ffmpeg.org/download.html")
    print_info("  2. Use Scoop: scoop install ffmpeg")
    print_info("  3. Use Chocolatey: choco install ffmpeg")
    print_info("\nAfter installation, FFmpeg should be automatically detected.")
    
    input_val = input("\nHave you installed FFmpeg? (yes/no): ").strip().lower()
    if input_val == "yes":
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            print_success(f"FFmpeg verified at: {ffmpeg_path}")
            return True
        else:
            print_error("FFmpeg still not found. Please restart your terminal after installation.")
            return False
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
        print_info("Homebrew not found.")
        print_info("Install Homebrew from: https://brew.sh")
        print_info("Then run: brew install ffmpeg")
        input_val = input("\nHave you installed FFmpeg? (yes/no): ").strip().lower()
        if input_val == "yes":
            if shutil.which("ffmpeg"):
                print_success("FFmpeg verified")
                return True
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
    
    if venv_path.exists():
        print_info(f"Virtual environment already exists at {venv_path}")
        use_existing = input("Use existing virtual environment? (yes/no, default: yes): ").strip().lower()
        if use_existing != "no":
            return True
    
    create_venv = input("Create a new virtual environment? (yes/no, default: yes): ").strip().lower()
    
    if create_venv != "no":
        print_info("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print_success(f"Virtual environment created at .venv")
            
            # Provide activation instructions
            os_name = get_os_name()
            if os_name == "windows":
                print_info("Activate virtual environment with: .venv\\Scripts\\activate")
            else:
                print_info("Activate virtual environment with: source .venv/bin/activate")
            
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to create virtual environment: {e}")
            return False
    
    return True

def install_python_packages():
    """Install Python packages from requirements.txt"""
    print_step(4, "Installing Python dependencies...")
    
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print_error("requirements.txt not found!")
        return False
    
    print_info("This may take 5-15 minutes depending on your internet connection...")
    print_info("TensorFlow is large (~500MB), please be patient...")
    
    try:
        # First, upgrade pip to prevent compatibility issues
        print_info("Upgrading pip...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True
        )
        print_success("Pip upgraded")
        
        # Install requirements
        print_info("Installing packages from requirements.txt...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print_success("All packages installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install packages: {e}")
        print_info("Try running manually: pip install -r requirements.txt")
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
    
    print(f"\n  2. {Colors.BOLD}[IMPORTANT] Set up YouTube cookie strategy (required for video downloads):{Colors.RESET}")
    print(f"     Choose ONE of these methods:")
    print(f"")
    print(f"     {Colors.YELLOW}Method A - Environment Variable:{Colors.RESET}")
    print(f"       a) Export cookies from Chrome: yt-dlp --cookies-from-browser chrome --cookies cookies.txt")
    print(f"       b) Set environment variable: set YT_DLP_COOKIES_FILE=cookies.txt (Windows)")
    print(f"          or: export YT_DLP_COOKIES_FILE=cookies.txt (Linux/macOS)")
    print(f"")
    print(f"     {Colors.YELLOW}Method B - Upload via API:{Colors.RESET}")
    print(f"       curl -F \"file=@cookies.txt\" http://localhost:8000/upload_cookies")
    print(f"")
    print(f"     {Colors.YELLOW}Method C - Per-Request:{Colors.RESET}")
    print(f"       Include cookies_text in the analyze URL request (see README for details)")
    print(f"     Read README.md for more details on cookie setup.")
    
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
    
    input("\nPress Enter to continue...")
    
    # Step 1: FFmpeg
    if not install_ffmpeg():
        print_error("Failed to install FFmpeg. Setup cannot continue.")
        return False
    
    # Step 2: Python version
    if not check_python_version():
        print_error("Python version check failed. Setup cannot continue.")
        return False
    
    # Step 3: Virtual environment
    create_virtual_environment()
    
    # Step 4: Install packages
    if not install_python_packages():
        print_error("Failed to install Python packages.")
        return False
    
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
