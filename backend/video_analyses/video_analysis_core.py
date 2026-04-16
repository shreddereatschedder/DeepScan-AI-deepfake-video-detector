"""
Video Analysis Module
Extracts frames from video files, runs deepfake detection, and generates results CSV.
"""

import os
import sys
import logging

# Suppress TensorFlow warnings BEFORE importing TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)

import cv2
import numpy as np
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import tensorflow as tf
from keras.models import load_model

from backend.video_analyses.forensic_analyser import analyze_video_frames


def create_temp_folder():
    """Create a temporary folder for storing extracted frames."""
    temp_dir = tempfile.mkdtemp(prefix="deepfake_analysis_")
    return temp_dir


def extract_frames(video_path, temp_folder, frame_interval=5, max_frames=None):
    """
    Extract frames from a video file.
    
    Args:
        video_path (str): Path to the video file
        temp_folder (str): Folder to save extracted frames
        frame_interval (int): Extract every nth frame (default: 5)
        max_frames (int): Maximum number of frames to extract (None = no limit)
    
    Returns:
        list: List of extracted frame file paths
    """
    print(f"[INFO] Extracting frames from: {os.path.basename(video_path)}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"   Total frames: {total_frames}, FPS: {fps:.2f}")
    
    frame_paths = []
    frame_count = 0
    extracted_count = 0
    
    frames_dir = os.path.join(temp_folder, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Extract every nth frame
        if frame_count % frame_interval == 0:
            if max_frames and extracted_count >= max_frames:
                break
            
            # Resize to model input size (150x150)
            frame_resized = cv2.resize(frame, (150, 150))
            
            frame_path = os.path.join(frames_dir, f"frame_{extracted_count:04d}.jpg")
            cv2.imwrite(frame_path, frame_resized)
            frame_paths.append(frame_path)
            extracted_count += 1
        
        frame_count += 1
    
    cap.release()
    print(f"   [SUCCESS] Extracted {extracted_count} frames")
    return frame_paths


def load_deepfake_model(model_path):
    """
    Load the trained deepfake detector model.
    
    Args:
        model_path (str): Path to the .h5 model file
    
    Returns:
        tensorflow.keras.Model: Loaded model
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    print(f"[INFO] Loading model: {os.path.basename(model_path)}")
    
    # Load with compile=False to avoid compatibility issues with older saved models
    try:
        model = load_model(model_path, compile=False)
    except Exception as e:
        print(f"   [WARNING] Failed to load with standard method, trying legacy format...")
        # Try loading as legacy format
        model = tf.keras.models.load_model(model_path, compile=False)
    
    # Recompile the model with current Keras
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    print(f"   [SUCCESS] Model loaded successfully")
    return model


def predict_frame(frame_path, model):
    """
    Predict deepfake probability for a single frame.
    
    Args:
        frame_path (str): Path to frame image
        model: The deepfake detector model
    
    Returns:
        dict: Prediction results including confidence and label
    """
    # Load and preprocess frame
    img = cv2.imread(frame_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
    img = img.astype('float32') / 255.0  # Normalize to [0, 1]
    img = np.expand_dims(img, axis=0)  # Add batch dimension
    
    # Get prediction
    prediction = model.predict(img, verbose=0)[0][0]
    
    # Confidence: probability of being fake
    confidence = float(prediction)
    label = "fake" if confidence > 0.5 else "real"
    
    return {
        "confidence": confidence,
        "label": label
    }


def analyze_video(video_path, model_path, frame_interval=1, keep_temp=False):
    """
    Complete video analysis pipeline.
    
    Args:
        video_path (str): Path to the video file to analyze
        model_path (str): Path to the trained deepfake detector model
        frame_interval (int): Extract every nth frame (default: 5)
        keep_temp (bool): Whether to keep temporary folder (caller should delete)
    
    Returns:
        dict: Analysis results containing:
            - results_csv: Path to CSV file with results
            - temp_folder: Path to temporary folder (for cleanup)
            - summary: dict with overall statistics
            - frame_results: list of per-frame results
    """
    
    temp_folder = create_temp_folder()
    print(f"\n[INFO] Starting analysis for: {os.path.basename(video_path)}")
    print(f"   Temp folder: {temp_folder}")
    
    try:
        # Step 1: Extract frames
        frame_paths = extract_frames(video_path, temp_folder, frame_interval=frame_interval)
        
        if not frame_paths:
            raise ValueError("No frames were extracted from the video")
        
        # Step 2: Load model
        model = load_deepfake_model(model_path)

        # Step 2b: Run forensic metrics on extracted frames
        frames_dir = os.path.join(temp_folder, "frames")
        forensic_result = analyze_video_frames(
            model_path=model_path,
            frames_dir=frames_dir,
            frame_step=1
        )
        
        # Step 3: Analyze each frame
        print(f"\n[INFO] Analyzing {len(frame_paths)} frames...")
        frame_results = []
        confidences = []
        
        for i, frame_path in enumerate(frame_paths):
            result = predict_frame(frame_path, model)
            frame_num = i * frame_interval
            
            frame_results.append({
                "frame_number": frame_num,
                "frame_index": i,
                "frame_path": frame_path,
                "confidence": result["confidence"],
                "label": result["label"],
                "timestamp_sec": (frame_num / 30)  # Assume 30 FPS as default
            })
            confidences.append(result["confidence"])
            
            if (i + 1) % 10 == 0:
                print(f"   Processed {i + 1}/{len(frame_paths)} frames")
        
        # Step 4: Generate summary statistics (use frame counts as primary metric)
        fake_count = sum(1 for r in frame_results if r["label"] == "fake")
        fake_percentage = (fake_count / len(frame_results) * 100)

        forensic_metrics = forensic_result.get("metrics", {})
        # Prefer the aggregated forensic_score if available (new analyzer),
        # otherwise fall back to averaging legacy metric keys.
        if "forensic_score" in forensic_metrics:
            forensic_signal_score = float(forensic_metrics.get("forensic_score", 0.0))
        else:
            forensic_signal_score = float(np.mean([
                forensic_metrics.get("warp_score", 0.0),
                forensic_metrics.get("lighting_score", 0.0),
                forensic_metrics.get("texture_score", 0.0),
                forensic_metrics.get("flicker_score", 0.0),
                forensic_metrics.get("alignment_score", 0.0),
            ]))
        # Legacy combined score removed: overall label based on fake percentage
        combined_risk_score = None
        overall_label = "fake" if fake_percentage > 50 else "real"
        
        summary = {
            "video_path": video_path,
            "total_frames_analyzed": len(frame_results),
            "fake_frames": fake_count,
            "real_frames": len(frame_results) - fake_count,
            "fake_percentage": fake_percentage,
            "overall_label": overall_label,
            "analysis_timestamp": datetime.now().isoformat(),
            "frame_interval": frame_interval,
            "label_mapping": {
                "fake": 1,
                "real": 0,
                "threshold": 0.5,
                "rule": "frame vote > 50% => fake"
            },
            "forensic_metrics": forensic_metrics,
            "forensic_factors": forensic_result.get("factors", []),
            "forensic_prediction": forensic_result.get("prediction", "UNKNOWN"),
            "forensic_confidence": forensic_result.get("confidence", 0),
            "forensic_signal_score": forensic_signal_score,
        }
        
        # Step 5: Save results to CSV
        csv_dir = os.path.join(temp_folder, "results")
        os.makedirs(csv_dir, exist_ok=True)
        
        # Save frame-level results
        results_df = pd.DataFrame(frame_results)
        results_csv_path = os.path.join(csv_dir, "frame_results.csv")
        results_df.to_csv(results_csv_path, index=False)
        print(f"\n[INFO] Frame-level results saved to: {results_csv_path}")
        
        # Save summary
        summary_df = pd.DataFrame([summary])
        summary_csv_path = os.path.join(csv_dir, "summary.csv")
        summary_df.to_csv(summary_csv_path, index=False)
        print(f"[INFO] Summary results saved to: {summary_csv_path}")
        
        print(f"\n[SUCCESS] Analysis complete!")
        print(f"   Overall verdict: {summary['overall_label'].upper()}")
        print(f"   Fake percentage: {summary['fake_percentage']:.1f}%")
        # Avg/max/min confidence removed from summary; show fake percentage instead
        print(f"   Fake percentage: {summary['fake_percentage']:.1f}%")
        
        return {
            "results_csv": results_csv_path,
            "summary_csv": summary_csv_path,
            "temp_folder": temp_folder,
            "summary": summary,
            "frame_results": frame_results,
            "keep_temp": keep_temp
        }
        
    except Exception as e:
        print(f"\n[ERROR] Error during analysis: {e}")
        if not keep_temp:
            shutil.rmtree(temp_folder, ignore_errors=True)
        raise








def cleanup_temp_folder(temp_folder):
    """
    Clean up temporary folder and all extracted frames/results.
    
    Args:
        temp_folder (str): Path to temporary folder to delete
    """
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder, ignore_errors=True)
    else:
        # Temporary folder already cleaned or not found - no action needed
        pass
