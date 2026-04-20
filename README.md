# DeepFake Credibility Checker

A Chrome browser extension that analyzes videos from YouTube to detect potential deepfakes using advanced forensic analysis. Get real-time credibility assessments with detailed breakdowns of suspicious artifacts.

---

## Table of Contents
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [How to Run](#how-to-run-the-project)
- [Usage](#usage-guide)
- [Results & Metrics](#understanding-the-results)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## Features

- **Real-time Analysis**: Analyze YouTube videos instantly
- **Forensic Metrics**: 9 advanced artifact detection methods:
  - **Warping & Geometric Distortion** (landmark displacement + optical flow)
  - **Lighting Inconsistency** (frame-to-frame shadow direction variance)
  - **Texture Anomalies** (skin texture on face region)
  - **Temporal Flicker** (inter-frame intensity changes)
  - **High-Frequency Artifacts** (DFT/DCT signatures on face region)
  - **Chrominance Discontinuities** (Cr/Cb channel edge artifacts)
  - **Compression Artifacts** (JPEG/H.264 blockiness)
- **Temporal Stability**: 120-frame rolling window (reduced noise, stable baselines)
- **Face Region Masking**: Analyzes facial area only, eliminates background noise
- **Visual Dashboard**: Color-coded confidence gauge and factor breakdown
- **Detailed Reports**: Frame statistics and forensic scoring
- **Local Processing**: All analysis happens on your machine (privacy-first)

---

## System Requirements

### Software
- **Python 3.11** (3.11 is most compatible with Tensorflow)
- **Google Chrome** or **Chromium-based browser** (Edge, Brave, etc.)
- **Git** (optional, for cloning the repository)

### Hardware
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: Multi-core processor
- **Disk**: 500MB free space

### Operating Systems
- Windows 10+
- macOS 10.14+
- Linux (Ubuntu 18.04+)

---

## Python Virtual Environment

A Python virtual environment is an automated isolated directory that keeps your project dependencies separate. The setup script handles all of this for you automatically.

---

## Installation

### Quickest Way (Recommended)

Run the automated setup script that handles everything:

```bash
# Windows
python setup.py

# macOS/Linux
python3 setup.py
```

This single command will:
- Check/install FFmpeg (system dependency)
- Verify Python 3.9+ is installed +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
- Create a virtual environment (`.venv`)
- Install all required packages from requirements.txt
- Verify the installation

**Expected duration:** 10-20 minutes (mostly TensorFlow download)

### What Happens After Setup

Your terminal will show success messages like:
```
[SUCCESS] FFmpeg found in system PATH
[SUCCESS] Virtual environment created at .venv
[SUCCESS] All packages installed successfully!
[SUCCESS] TensorFlow is installed
[SUCCESS] Setup Complete!
```

---

## How to Run the Project

### Step 1: Activate Virtual Environment (if starting fresh terminal)

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

You should see `(.venv)` prefix in your terminal prompt.

### Step 2: Start the Backend Server

```bash
uvicorn backend.fastapi_server:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

Keep this terminal window open. The server is now running.

### Step 3: Load the Chrome Extension

1. Open Chrome and go to: `chrome://extensions`
2. Enable **"Developer mode"** (toggle in top-right corner)
3. Click **"Load unpacked"**
4. Select the `extension/` folder from your project
5. You should see the extension with a "DS" icon in Chrome toolbar

### Step 4: You're All Set!

Everything is configured and ready. Head to the [Usage Guide](#usage-guide) below for detailed step-by-step instructions on analyzing videos.

---

## Setup & Configuration

### Custom API Endpoint

If running on a non-standard port or remote server:

**Edit `extension/config.json`:**
```json
{
  "API_ENDPOINT": "http://127.0.0.1:8000"
}
```

Examples:
- **Local (default)**: `http://127.0.0.1:8000`
- **Custom port**: `http://127.0.0.1:5000`
- **Remote server**: `http://YOUR_SERVER_IP:8000`

Then reload the extension in Chrome.

### Custom Server Port/Host

```bash
# With environment variables
$env:API_PORT = "5000"  # Windows PowerShell
export API_PORT=5000    # Mac/Linux

uvicorn backend.fastapi_server:app --reload
```

Then update `extension/config.json` to match.

### Deactivating Virtual Environment

When done working:
```bash
deactivate
```

---

## Usage Guide

### Analyzing a YouTube Video

1. **Open a YouTube video** in Chrome
2. **Right-click on the video** → Select "Check video for deepfake" (context menu)
   - OR click the extension icon (DS) in the toolbar

3. **Wait for analysis** (30 seconds - 2 minutes depending on video):
   - Real-time progress: Face detection → Temporal analysis → Artifact scanning

4. **View Results**:
   - **Deepfake Score** (circular gauge): 0-100% probability
     - 0-30% (Green): Likely Real
     - 30-60% (Orange): Possibly Manipulated  
     - 60-100% (Pink): Likely Fake
   - **Contributing Factors**: Detailed breakdown of detected artifacts
   - **Frame Heatmap**: Statistics on real vs fake frames

---

## Understanding the Results

### Deepfake Score Interpretation

| Score Range | Risk Level | Meaning |
|------------|-----------|---------|
| 0-30% | Low Risk | Likely genuine content |
| 30-60% | Medium Risk | Suspicious, possible manipulation |
| 60-100% | High Risk | Likely deepfake or heavily manipulated |

### Forensic Metrics Explained

| Metric | What It Checks | High Value Means |
|--------|---------------|------------------|
| **Warping Artifacts** | Geometric distortions in face | Unnatural face morphing |
| **Lighting Inconsistency** | Frame-to-frame lighting changes | Inconsistent lighting (deepfake indicator) |
| **Texture Anomalies** | Skin texture unnatural blending | Blending artifacts from generation |
| **Temporal Flicker** | Abrupt inter-frame changes | Temporal instability |
| **Facial Alignment** | Landmark shifting | Misaligned facial features |
| **Blinking Patterns** | Unnatural blink frequency | Missing or abnormal blinks |
| **Compression Artifacts** | Video compression inconsistencies | Suspicious encoding patterns |

---

## Advanced Usage

### Batch Analysis (Command Line - No Extension)

For analysing multiple videos without the Chrome extension:

```python
python backend/video_analyses/test_run.py --video_path "/path/to/video.mp4" --frames 30
```

### View Saved Analysis Results

All results are stored in `analysis_results/` folder:
```
analysis_results/
├── video_name/
│   ├── status.json          # Analysis status and summary
│   ├── frame_results.csv    # Frame-level forensic metrics
│   └── summary.csv          # Overall verdict
```

### Re-run Setup Script

To verify dependencies are still installed or update FFmpeg:

```bash
python setup.py
```

---

## Troubleshooting

### "Failed to connect to backend" error

1. Check if FastAPI server is running: Open `http://localhost:8000` in browser (should see JSON response)
2. Verify server terminal shows "Application startup complete"
3. Restart the server: Stop it (Ctrl+C) and run again:
   ```bash
   uvicorn backend.fastapi_server:app --reload
   ```

### YouTube Video Won't Download (HTTP 429 "Too Many Requests" error)

YouTube blocks automated requests to prevent scraping. The system requires browser cookies to pass YouTube's bot-check.

**Solution: Provide Browser Cookies**

The setup script now attempts a best-effort automatic cookie export (using `yt-dlp --cookies-from-browser`) during installation. Note:

- If your browser (Chrome/Edge/Firefox) is running, automatic export may fail because the browser locks/encrypts its cookie database. Close the browser completely and re-run `python setup.py` (or re-run the `yt-dlp --cookies-from-browser` command) to allow the automatic export to succeed.
- If automatic export still fails, use one of the manual options below.

Manual options (fallback):

**Option 1: Environment Variable (Easiest for Local Development)**
```bash
# First, export cookies from your browser (close browser if necessary)
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --skip-download https://www.youtube.com

# Then set environment variable and start server
# Windows PowerShell:
$env:YT_DLP_COOKIES_FILE="C:\full\path\to\cookies.txt"
python -m uvicorn backend.fastapi_server:app --reload

# macOS/Linux:
export YT_DLP_COOKIES_FILE=/full/path/to/cookies.txt
uvicorn backend.fastapi_server:app --reload
```

**Option 2: Upload Cookies via API**
```bash
# Export cookies first (as above), then upload:
curl -F "file=@cookies.txt" http://127.0.0.1:8000/upload_cookies

# Response: {"status":"ok","cookies_file":"/path/to/cookies.txt"}
```

**Option 3: Include Cookies in Analysis Request**
```bash
curl -X POST -H "Content-Type: application/json" \
   -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","cookies_text":"# Netscape format cookies..."}' \
   http://127.0.0.1:8000/analyze_url
```

**Why This Happens:**
YouTube uses bot-detection (JavaScript challenges, rate-limiting) to prevent automated access. Browser cookies prove you're a real user and bypass these checks.

### Extension doesn't appear in Chrome

1. Verify you're in Developer mode: `chrome://extensions`
2. Click "Load unpacked" and select the `extension/` folder
3. Refresh Chrome (Ctrl+R)

### Analysis stuck or timing out

1. Wait 2-3 minutes for completion (depends on video length)
2. Check the backend terminal for error messages
3. Reload extension: Click the refresh icon on extension card in `chrome://extensions`

### "ModuleNotFoundError" when starting server

1. Verify virtual environment is activated (should see `(.venv)` in terminal)
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Then start server: `uvicorn backend.fastapi_server:app --reload`

### FFmpeg not found

1. If setup.py showed an error, manually install:
   - **Windows**: Download from https://ffmpeg.org/download.html or use `scoop install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg`
2. Restart the backend server

### Video won't load in extension

- Ensure HTTPS video URLs are used
- Try with a different YouTube video
- Check your internet connection

---

## 📁 Project Structure

```
credibility_checker/
├── extension/                       # Chrome extension files
│   ├── manifest.json              # Extension configuration
│   ├── background.js              # Background/context menu script
│   ├── content.js                 # Content injection script
│   ├── results.js                 # Results UI logic & interaction
│   ├── results.html               # Results display (static)
│   ├── style.css                  # Styling
│   └── overlay.css                # Overlay styling
│
├── backend/                         # Backend API and analysis
│   ├── fastapi_server.py          # FastAPI server (main entry point)
│   ├── downloads/                 # Temporary video staging folder
│   │   └── cookies_*.txt          # User-uploaded cookies
│   │
│   ├── video_analyses/            # Runtime analysis modules
│   │   ├── video_analysis_core.py # Frame extraction & pipeline
│   │   ├── forensic_analyser.py   # All 9 forensic metrics
│   │   └── __init__.py
│   │
│   ├── model_training/            # Training scripts and artifacts
│   │   ├── models/
│   │   │   └── deepfake_detector.h5
│   │   └── training_metrics.json
│   │
│   └── analysis_results/          # Per-video analysis output
│       └── {video_name}/
│           ├── status.json        # Analysis status & summary
│           ├── frame_results.csv  # Frame-level metrics
│           └── summary.csv        # Overall verdict
│
├── dataset/                         # Training data (not included here due to size of dataset)
│   ├── image_dataset/             # Static image data (spatial artifacts)
│   └── video_dataset/             # Video data (temporal artifacts)
│
├── My_Dev_Diary/                    # Development journal entries
│   └── #1 through #10 (tracking)
│
├── requirements.txt                 # Python dependencies
├── setup.py                         # Script to set up dependencies
└── README.md                        # This file
```

---

## requirements.txt

The project requires the following dependencies:

```
fastapi==0.104.1
uvicorn==0.24.0
opencv-python==4.8.1
numpy==1.24.3
pillow==10.0.0
mediapipe==0.10.0           # Face detection & landmarks (optional fallback: Haar cascade)
scipy==1.11.3
scikit-image==0.21.0
tensorflow==2.13.0          # CNN deepfake model
yt-dlp==2023.12.30          # YouTube video downloading (requires cookies for bot-check)
```

All these are automatically installed with:
```bash
pip install -r requirements.txt
```

**Note on MediaPipe**: MediaPipe is optional; if unavailable, the system falls back to OpenCV Haar cascade for face detection (slightly less accurate but fully functional).

---

## 🔐 Privacy & Security

- **Local Processing**: All analysis happens on your computer
- **No Data Collection**: Results are not sent to external servers
- **No User Tracking**: The extension doesn't track your browsing
- **Open Source**: Code is auditable and transparent

---

## 🤝 Contributing

Found a bug or have a suggestion? Please open an issue or submit a pull request!

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 📧 Support

For issues, questions, or suggestions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review recent analysis logs in `analysis_results/`
3. Open an issue on GitHub with:
   - Description of the problem
   - Steps to reproduce
   - Browser version and OS
   - Error messages from console (F12 → Console tab)

---

## 🎓 How It Works

The extension uses a sophisticated multi-stage forensic pipeline:

### Pipeline Stages

1. **Frame Extraction** (video_analysis_core.py)
   - Extracts frames from downloaded video at configurable interval
   - Limits analysis to first 30-60 frames for speed

2. **Face Detection** (forensic_analyser.py)
   - Detects faces using MediaPipe 468-point mesh
   - Falls back to Haar cascade (OpenCV) if MediaPipe unavailable

3. **Face Region Masking**
   - Isolates facial area to avoid background noise
   - Uses landmarks to compute precise face bounding box with padding

4. **Forensic Analysis** (9 metrics computed on face region)
   - **Spatial Artifacts**: Warping (landmark + optical flow), Texture, Compression
   - **Temporal Artifacts**: Flicker, Lighting consistency, Alignment stability
   - **Frequency Domain**: High-frequency artifacts, Chrominance discontinuities


5. **Temporal Stability**
   - 120-frame rolling history window reduces frame-to-frame noise
   - Z-score anomaly detection against baseline for robust thresholding
   - Distinguishes natural motion from deepfake artifacts

6. **Scoring & Interpretation**
   - Combines 9 metrics with learned weights
   - CNN prediction (per-frame) aggregated with forensic factors
   - Generates factor descriptions & severity levels

7. **Visualization** (results.js)
   - Displays gauge, factor breakdown, timeline chart, heatmap
   - Interactive expandable factor details with explanations

**Key Innovations**:
- Optical flow analysis (Farneback algorithm) detects unnatural motion patterns
- 120-frame buffer enables reliable baseline detection (vs. 30-frame baseline)
- Face-only analysis eliminates background-induced false positives
- Combined warping detection merges landmark and optical flow signals

For technical details, see:
- `backend/video_analyses/video_analysis_core.py` — Frame extraction
- `backend/video_analyses/forensic_analyser.py` — All forensic metrics
- `extension/results.js` — UI rendering & interaction

---

## Getting Started (Quick Start)

```bash
# 1. Activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or .venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn backend.fastapi_server:app --reload

# 4. Load extension in Chrome
# Go to chrome://extensions → Developer mode (ON) → Load unpacked → select extension/

# 5. Analyze a YouTube video
# Open YouTube, click extension icon, choose "Check Authenticity"
```

That's it! You're ready to use the DeepFake Checker!

---

**Last Updated:** April 2026  
**Version:** 1.0.0
