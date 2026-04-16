import subprocess
import os
import sys
import json
import shutil
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to Python path for imports
from pathlib import Path as _Path
PROJECT_ROOT = _Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.video_analyses.video_analysis_core import analyze_video, cleanup_temp_folder, load_deepfake_model
import threading

app = FastAPI()

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
            model = load_deepfake_model(MODEL_PATH)
            # try a tiny random pixel input to confirm predict works
            import numpy as np
            dummy = np.random.rand(1,150,150,3).astype('float32')
            p = model.predict(dummy, verbose=0)[0][0]
            print(f"   [SUCCESS] Model predict OK (sanity prob={float(p):.4f})")
        else:
            print(f"   [WARNING] Model not found at startup: {MODEL_PATH}")
    except Exception as e:
        print(f"   [WARNING] Startup sanity check failed: {e}")


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


def download_youtube_video(url: str) -> str:
    """Download a YouTube video and return its local path."""
    # Clean up old downloads first
    for f in os.listdir(DOWNLOAD_DIR):
        if f.endswith(".mp4"):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
            except:
                pass
    
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    command = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",  # 720p max
        "--merge-output-format", "mp4",
        "-o", output_path,
    ]

    if ffmpeg_location:
        command.extend(["--ffmpeg-location", ffmpeg_location])

    command.append(url)

    try:
        print(f"Downloading video from: {url}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout)

        # Find the downloaded file
        for f in os.listdir(DOWNLOAD_DIR):
            if f.endswith(".mp4"):
                return os.path.join(DOWNLOAD_DIR, f)

        raise FileNotFoundError("Download completed but no .mp4 file found.")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Download failed:", e.stderr)
        raise HTTPException(status_code=500, detail=f"Failed to download video: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class VideoRequest(BaseModel):
    url: str


def analyze_video_background(video_path):
    """Run video analysis in background thread"""
    try:
        print(f"\n[INFO] Starting analysis for: {os.path.basename(video_path)}")
        write_status(video_path, "processing")
        
        # Run analysis
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
        cleanup_temp_folder(temp_folder)

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


@app.post("/analyze_url")
async def analyze_url(request: VideoRequest):
    """Download and analyze a YouTube video."""
    video_path = download_youtube_video(request.url)
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
