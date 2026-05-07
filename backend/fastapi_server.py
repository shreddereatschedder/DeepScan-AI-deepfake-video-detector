import subprocess
import os
import sys
import json
import shutil
import threading
from pathlib import Path
import warnings
import logging

# Suppress TensorFlow/Keras warnings BEFORE any TensorFlow imports
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TensorFlow output (0=all, 1=info, 2=warn, 3=error)
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'  # Prevent TensorFlow from allocating all GPU memory
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Suppress TensorFlow logger before any imports
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)
logging.getLogger('tensorflow.python').setLevel(logging.ERROR)
logging.getLogger('tensorflow.python.framework').setLevel(logging.ERROR)
logging.getLogger('tensorflow.python.util').setLevel(logging.ERROR)

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

 # Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import glob
import uuid

app = FastAPI()

# Helper function for cleanup
def _clear_dir(path: str):
    """Remove all files and directories in the given path."""
    if not os.path.exists(path):
        return
    for name in os.listdir(path):
        full = os.path.join(path, name)
        try:
            if os.path.islink(full) or os.path.isfile(full):
                os.remove(full)
            elif os.path.isdir(full):
                shutil.rmtree(full)
        except Exception as e:
            print(f"[WARN] Failed to remove {full}: {e}")

# Startup event - clean up temporary files
@app.on_event("startup")
async def startup_event():
    """Clean up downloads and analysis_results folders when server starts."""
    _clear_dir(DOWNLOAD_DIR)
    _clear_dir(RESULTS_FOLDER)

# Shutdown event - clean up temporary files
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up downloads and analysis_results folders when server shuts down."""
    _clear_dir(DOWNLOAD_DIR)
    _clear_dir(RESULTS_FOLDER)

# CORS for cloud deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your extension ID
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cross-platform ffmpeg detection
def get_ffmpeg_path():
    """
    Detect ffmpeg path for Windows or Linux.
    
    Priority order:
    1. FFMPEG_PATH environment variable (set this if ffmpeg is in custom location)
    2. System PATH (ffmpeg available globally)
    3. Common installation locations
    
    To set FFMPEG_PATH on your machine:
    - Windows: set FFMPEG_PATH=C:\\path\\to\\ffmpeg.exe
    - Mac/Linux: export FFMPEG_PATH=/path/to/ffmpeg
    """
    # Priority 1: Check if FFMPEG_PATH env var is explicitly set
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        print(f"[SUCCESS] Using FFMPEG_PATH from environment: {env_path}") 
        return env_path
    
    # Priority 2: Try to find ffmpeg in system PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"[SUCCESS] FFmpeg found in system PATH: {ffmpeg}") 
        return ffmpeg
    
    # Priority 3: Common Windows installation paths
    if os.name == 'nt':
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                print(f"[SUCCESS] FFmpeg found at: {path}")
                return path
    
    # Priority 4: Common Linux paths
    if os.name != 'nt':
        common_paths = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/ffmpeg/bin/ffmpeg",
        ]
        for path in common_paths:
            if os.path.exists(path):
                print(f"[SUCCESS] FFmpeg found at: {path}")
                return path
    
    return None

ffmpeg_location = get_ffmpeg_path()
if not ffmpeg_location:
    print("[ERROR] FFmpeg not found!")
    print("   Install ffmpeg or set FFMPEG_PATH environment variable")
    print("   Windows: set FFMPEG_PATH=C:\\path\\to\\ffmpeg.exe")
    print("   Mac/Linux: export FFMPEG_PATH=/path/to/ffmpeg")
else:
    print(f"[SUCCESS] Using ffmpeg: {ffmpeg_location}")

# Save downloads inside your project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
MODEL_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "deepfake_detector.h5")
RESULTS_FOLDER = os.path.join(PROJECT_ROOT, "analysis_results")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)


# Startup sanity check (runs in background so server starts quickly)
def _startup_sanity_check():
    try:
        print("[INFO] Running model startup sanity check...")
        # try to load model and run a tiny predict if dataset exists
        if os.path.exists(MODEL_PATH):
            try:
                from backend.video_analyses.video_analysis_core import load_deepfake_model
                model = load_deepfake_model(MODEL_PATH)
                # try a tiny random pixel input to confirm predict works
                import numpy as np
                dummy = np.random.rand(1,150,150,3).astype('float32')
                p = model.predict(dummy, verbose=0)[0][0]
                print(f"   [SUCCESS] Model predict OK (sanity prob={float(p):.4f})")
            except Exception as e:
                print(f"   [WARNING] Model load/predict failed at startup: {e}")
        else:
            print(f"   [WARNING] Model not found at startup: {MODEL_PATH}")
        
        # Display ready banner after sanity check
        print("\n" + "="*70)
        print("🎬 DEEPFAKE DETECTOR - READY FOR YOUTUBE VIDEO ANALYSIS 🎬")
        print("="*70 + "\n")
    except Exception as e:
        print(f"   [WARNING] Startup sanity check failed: {e}")
        # Still display ready banner even if sanity check fails
        print("\n" + "="*70)
        print("🎬 DEEPFAKE DETECTOR - READY FOR YOUTUBE VIDEO ANALYSIS 🎬")
        print("="*70 + "\n")


threading.Thread(target=_startup_sanity_check, daemon=True).start()


def get_video_results_folder(video_path: str) -> str:
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join(RESULTS_FOLDER, video_name)


def write_status(video_path: str, status: str, payload: dict | None = None) -> str:
    results_folder = get_video_results_folder(video_path)
    os.makedirs(results_folder, exist_ok=True)
    status_path = os.path.join(results_folder, "status.json")
    data = {
        "status": status,
        "video_path": video_path,
    }
    if payload:
        data.update(payload)
    with open(status_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return status_path


def download_youtube_video(url: str, cookies_file_override: str | None = None) -> str:
    """Download a YouTube video and return its local path."""
    # Clean up old downloads first
    for f in os.listdir(DOWNLOAD_DIR):
        if f.endswith(".mp4"):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
            except:
                pass

    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    # Base command
    base_command = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
        "--merge-output-format", "mp4",
        "-o", output_path,
    ]

    if ffmpeg_location:
        base_command.extend(["--ffmpeg-location", ffmpeg_location])

    # Default user agent and headers (makes requests look more like a real browser)
    default_ua = os.getenv("YT_DLP_USER_AGENT") or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    base_command.extend(["--user-agent", default_ua])
    base_command.extend(["--add-header", "Accept-Language: en-US,en;q=0.9"])

    # Extra arguments from environment (optional)
    extra_args = []
    extra_env = os.getenv("YT_DLP_EXTRA_ARGS")
    if extra_env:
        try:
            import shlex
            extra_args = shlex.split(extra_env)
        except Exception:
            extra_args = [extra_env]

    # Cookie configuration via environment (no new installs required)
    cookies_file = cookies_file_override or os.getenv("YT_DLP_COOKIES_FILE")
    cookies_from_browser = os.getenv("YT_DLP_COOKIES_FROM_BROWSER")
    # if a cookies file was uploaded into DOWNLOAD_DIR, prefer it
    if not cookies_file:
        candidate = os.path.join(DOWNLOAD_DIR, "cookies.txt")
        if os.path.exists(candidate):
            cookies_file = candidate
        else:
            matches = glob.glob(os.path.join(DOWNLOAD_DIR, "cookies_*.txt"))
            if matches:
                # pick the most recent by name (they contain uuid; pick last)
                cookies_file = matches[-1]

    # Retry/backoff policy (simple, avoids installing runtimes)
    attempts = int(os.getenv("YT_DLP_ATTEMPTS", "2"))
    backoff_seconds = int(os.getenv("YT_DLP_BACKOFF_SECONDS", "2"))

    tried_cookies = False
    last_err = None

    for attempt in range(1, attempts + 1):
        # build command for this attempt
        cmd = list(base_command) + list(extra_args) + [url]

        # On fallback attempts, try using cookies if available or attempt to read from browser
        if attempt > 1 and not tried_cookies:
            if cookies_file:
                cmd = list(base_command) + ["--cookies", cookies_file] + list(extra_args) + [url]
                tried_cookies = True
            elif cookies_from_browser:
                cmd = list(base_command) + ["--cookies-from-browser", cookies_from_browser] + list(extra_args) + [url]
                tried_cookies = True
            else:
                # Do NOT attempt an automatic `--cookies-from-browser chrome` fallback here.
                # Copying Chrome's cookie DB often fails in headless/service contexts
                # (locked DB, permissions, or platform-specific encryption). Instead,
                # retry without cookies and provide clear guidance to the user
                # to set `YT_DLP_COOKIES_FILE` or `YT_DLP_COOKIES_FROM_BROWSER`.
                print("[INFO] No YT_DLP_COOKIES_FILE or YT_DLP_COOKIES_FROM_BROWSER set; skipping automatic cookies-from-browser fallback.")

        try:
            print(f"[INFO] Downloading video from: {url} (attempt {attempt}/{attempts})")
            # Attempt to run yt-dlp; if executable missing, fallback to running as a module
            try:
                # Primary attempt: run the `yt-dlp` executable directly
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            except FileNotFoundError as e:
                # Fallback: try running yt-dlp as a Python module (avoids missing exe in PATH)
                try:
                    fallback_cmd = [sys.executable, "-m", "yt_dlp"] + list(base_command[1:]) + list(extra_args) + [url]
                    print("[WARN] yt-dlp executable not found; using python module fallback")
                    result = subprocess.run(fallback_cmd, check=True, capture_output=True, text=True)
                except Exception:
                    # Re-raise to be handled by outer logic
                    raise
            # Suppress verbose yt-dlp output; not printed to console

            # Find the downloaded file
            for f in os.listdir(DOWNLOAD_DIR):
                if f.endswith(".mp4"):
                    video_file = os.path.join(DOWNLOAD_DIR, f)
                    print(f"[SUCCESS] Downloaded video: {f}")
                    return video_file

            raise FileNotFoundError("Download completed but no .mp4 file found.")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or e.stdout or str(e)
            print("[ERROR] Download failed:", stderr)
            last_err = stderr
            # if not last attempt, wait and retry
            if attempt < attempts:
                import time
                sleep_for = backoff_seconds * attempt
                print(f"[INFO] Retrying in {sleep_for}s...")
                time.sleep(sleep_for)
                continue
            # final failure -> provide helpful hints without requiring new installs
            hints = (
                "yt-dlp failed to download. Common remedies:\n"
                " - Export your browser cookies and set YT_DLP_COOKIES_FILE to the cookies.txt path,\n"
                "   or set YT_DLP_COOKIES_FROM_BROWSER=chrome (or chromium/firefox) to let yt-dlp read them.\n"
                " - If you can run yt-dlp locally, try: yt-dlp --cookies-from-browser chrome --cookies cookies.txt <URL>\n"
                " - You may also set YT_DLP_USER_AGENT to mimic a different browser if needed.\n"
            )
            detail_msg = f"Failed to download video: {str(last_err)[:1000]}\n\n{hints}"
            raise HTTPException(status_code=500, detail=detail_msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


class VideoRequest(BaseModel):
    url: str
    # Optional: include cookies text (Netscape format) to be used for this request
    cookies_text: str | None = None


def analyze_video_background(video_path):
    """Run video analysis in background thread"""
    try:
        print(f"\n[INFO] Starting analysis for: {os.path.basename(video_path)}")
        write_status(video_path, "processing")
        
        # Run analysis
        try:
            from backend.video_analyses.video_analysis_core import analyze_video, cleanup_temp_folder
        except Exception as e:
            write_status(video_path, "error", {"error": f"missing analysis dependencies: {e}"})
            print(f"[ERROR] Missing analysis dependencies: {e}")
            return

        result = analyze_video(                                                                            
            video_path=video_path,
            model_path=MODEL_PATH,
            frame_interval=5,
            keep_temp=False
        )
        
        print(f"[SUCCESS] Analysis complete for: {os.path.basename(video_path)}")
        
        # Copy results to persistent folder
        temp_folder = result["temp_folder"]
        results_dir = os.path.join(temp_folder, "results")
        
        video_results_folder = get_video_results_folder(video_path)
        if os.path.exists(results_dir):
            
            # Copy CSV results
            for file in os.listdir(results_dir):
                shutil.copy2(
                    os.path.join(results_dir, file),
                    os.path.join(video_results_folder, file)
                )
            
            print(f"[INFO] Results saved to: {video_results_folder}")
            print(f"   Summary: Fake={result['summary']['fake_percentage']:.1f}%")
        
        # Cleanup temporary folder
        try:
            cleanup_temp_folder(temp_folder)
        except NameError:
            # cleanup function missing (dependencies failed to import earlier)
            pass

        write_status(
            video_path,
            "done",
            {
                "summary": result.get("summary"),
                "results_folder": video_results_folder,
            },
        )
        
    except Exception as e:
        write_status(video_path, "error", {"error": str(e)})
        print(f"[ERROR] Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Deepfake Detector API",
        "ffmpeg": ffmpeg_location or "system default"
    }


@app.get("/analysis_status")
async def analysis_status(video_path: str = Query(..., min_length=1)):
    """Return analysis status for a given video path."""
    results_folder = get_video_results_folder(video_path)
    status_path = os.path.join(results_folder, "status.json")
    if not os.path.exists(status_path):
        return {"status": "pending", "video_path": video_path}
    with open(status_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


@app.post("/cleanup_results")
async def cleanup_results():
    """Remove contents of the downloads and analysis_results folders.

    This is a destructive operation intended for local testing. It clears files
    and subfolders inside the configured `DOWNLOAD_DIR` and `RESULTS_FOLDER`.
    """
    def clear_dir(path: str):
        removed_files = 0
        removed_dirs = 0
        if not os.path.exists(path):
            return removed_files, removed_dirs
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                if os.path.islink(full) or os.path.isfile(full):
                    os.remove(full)
                    removed_files += 1
                elif os.path.isdir(full):
                    shutil.rmtree(full)
                    removed_dirs += 1
            except Exception as e:
                print(f"[WARN] Failed to remove {full}: {e}")
        return removed_files, removed_dirs

    try:
        d_files, d_dirs = clear_dir(DOWNLOAD_DIR)
        r_files, r_dirs = clear_dir(RESULTS_FOLDER)
        return {
            "status": "ok",
            "downloads_removed_files": d_files,
            "downloads_removed_dirs": d_dirs,
            "results_removed_files": r_files,
            "results_removed_dirs": r_dirs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_cookies")
async def upload_cookies(file: UploadFile | None = File(None), cookies_text: str | None = None):
    """Upload a cookies file (multipart/form-data) or post cookies text (Netscape format).

    Returns the path to the saved cookies file which will be used by subsequent downloads.
    """
    if file is None and not cookies_text:
        raise HTTPException(status_code=400, detail="No cookies provided")

    try:
        fname = f"cookies_{uuid.uuid4().hex}.txt"
        dest = os.path.join(DOWNLOAD_DIR, fname)
        if file is not None:
            content = await file.read()
            with open(dest, "wb") as fh:
                fh.write(content)
        else:
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(cookies_text)

        print(f"[INFO] Saved uploaded cookies to: {dest}")
        return {"status": "ok", "cookies_file": dest}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze_url")
async def analyze_url(request: VideoRequest, http_request: Request):
    """Download and analyze a YouTube video."""
    # If cookies content was provided in the request, write it to a temporary cookies file
    cookies_path = None
    try:
        if getattr(request, 'cookies_text', None):
            fname = f"cookies_{uuid.uuid4().hex}.txt"
            cookies_path = os.path.join(DOWNLOAD_DIR, fname)
            with open(cookies_path, "w", encoding="utf-8") as fh:
                fh.write(request.cookies_text)
            print(f"[INFO] Saved request cookies to: {cookies_path}")
    except Exception as e:
        print(f"[WARN] Failed to write cookies from request: {e}")

    video_path = download_youtube_video(request.url, cookies_file_override=cookies_path)
    print(f"Video downloaded to: {video_path}")

    # Trigger analysis in background thread (non-blocking)
    analysis_thread = threading.Thread(
        target=analyze_video_background,
        args=(video_path,),
        daemon=True
    )
    analysis_thread.start()
    print(f"[INFO] Analysis started in background thread")

    result = {
        "status": "success",
        "message": "Video downloaded and analysis started in background",
        "video_path": video_path,
        "video_id": os.path.splitext(os.path.basename(video_path))[0],
        "note": "Analysis is running. Results will be saved to analysis_results/ folder when complete."
    }

    return result


if __name__ == "__main__":
    import uvicorn
    # Get host and port from environment or use defaults
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
