# video_downloads_monitor.py
"""
Monitors the downloads folder for new video files and automatically:
1. Triggers deepfake analysis
2. Waits for completion
3. Saves analysis results (CSV)
4. Cleans up temporary folders and extracted frames
"""

import os
import time
import shutil
from pathlib import Path as _Path

from backend.video_analyses.video_analysis_core import analyze_video, cleanup_temp_folder

# -----------------------
# Configuration
# -----------------------
# Paths relative to repository root
PROJECT_ROOT = _Path(__file__).resolve().parents[2]
DOWNLOADS_FOLDER = os.path.join(str(PROJECT_ROOT), "backend", "downloads")
MODEL_PATH = os.path.join(str(PROJECT_ROOT), "backend", "model_training", "models", "deepfake_detector.h5")
RESULTS_FOLDER = os.path.join(str(PROJECT_ROOT), "analysis_results")

CHECK_INTERVAL = 10   # seconds between checks for new files
SUPPORTED_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")

# Create necessary folders
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# -----------------------
# Helper functions
# -----------------------
def get_video_files(folder):
    return [f for f in os.listdir(folder)
            if f.lower().endswith(SUPPORTED_EXTENSIONS)]

def process_video(video_path):
    """
    Process a single video file: analyze and save results.
    
    Args:
        video_path (str): Path to the video file
    """
    print(f"\n New video detected: {video_path}")
    try:
        # Run analysis
        result = analyze_video(
            video_path=video_path,
            model_path=MODEL_PATH,
            frame_interval=5,         # tune depending on desired accuracy/speed
            keep_temp=True           # cleanup temp folder after analysis
        )
        
        print(f"[SUCCESS] Analysis complete for {os.path.basename(video_path)}")
        
        # Copy results to persistent folder
        temp_folder = result["temp_folder"]
        results_dir = os.path.join(temp_folder, "results")
        
        if os.path.exists(results_dir):
            # Copy CSV files to results folder
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            video_results_folder = os.path.join(RESULTS_FOLDER, video_name)
            os.makedirs(video_results_folder, exist_ok=True)
            
            for file in os.listdir(results_dir):
                shutil.copy2(
                    os.path.join(results_dir, file),
                    os.path.join(video_results_folder, file)
                )
            
            print(f"   Results saved to: {video_results_folder}")
            print(f"   Summary: {result['summary']}")
        
        # Cleanup temporary folder
        cleanup_temp_folder(temp_folder)
        
        # Optional: remove the original downloaded video if desired
        # os.remove(video_path)
        # print(f"🗑️  Deleted original video: {video_path}")

    except Exception as e:
        print(f"[ERROR] Error analysing {video_path}: {e}")
        import traceback
        traceback.print_exc()

# -----------------------
# Main loop
# -----------------------
if __name__ == "__main__":
    print("="*60)
    print("Deepfake Video Analyser - Folder Monitor")
    print("="*60)
    print(f"Monitoring folder: {DOWNLOADS_FOLDER}")
    print(f"Using model: {MODEL_PATH}")
    print(f"Saving results to: {RESULTS_FOLDER}")
    print("="*60)
    
    # Verify paths exist
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] ERROR: Model not found at {MODEL_PATH}")
        print(f"   Please ensure the model exists at: {MODEL_PATH}")
        exit(1)
    
    if not os.path.exists(DOWNLOADS_FOLDER):
        print(f"⚠️  Downloads folder doesn't exist yet: {DOWNLOADS_FOLDER}")
        print(f"   It will be created when videos are downloaded.")
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
    
    processed = set()

    try:
        while True:
            # Look for new video files
            if os.path.exists(DOWNLOADS_FOLDER):
                videos = get_video_files(DOWNLOADS_FOLDER)
                
                if videos:
                    print(f"\n[INFO] Found {len(videos)} video file(s) in downloads folder")
                
                for v in videos:
                    full_path = os.path.join(DOWNLOADS_FOLDER, v)
                    if full_path not in processed:
                        process_video(full_path)
                        processed.add(full_path)
                        print(f"[SUCCESS] Video marked as processed")
            
            # Sleep before next check
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        print("="*60)