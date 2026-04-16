# forensic_analyser.py
import os
import logging

# Suppress TensorFlow warnings BEFORE importing TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)

import cv2
import numpy as np
import tensorflow as tf
from keras.utils import img_to_array, load_img
from statistics import mean
import json

try:
    import mediapipe as mp  # type: ignore
except Exception:
    mp = None

IMG_SIZE = (150, 150)


def _resolve_face_mesh_module():
    """Resolve MediaPipe face_mesh module across package variants."""
    if mp is None:
        return None

    # Standard MediaPipe layout
    if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
        return mp.solutions.face_mesh

    # Some builds expose solutions under mediapipe.python.solutions (or similar).
    # Use dynamic import to avoid static analysis/flake issues (Pylance complaining
    # about unresolved 'mediapipe.python' in some environments).
    try:
        import importlib
        # try common module paths dynamically
        for mod in ("mediapipe.python.solutions", "mediapipe.solutions"):
            try:
                mp_solutions = importlib.import_module(mod)
                if hasattr(mp_solutions, "face_mesh"):
                    return mp_solutions.face_mesh
                break
            except Exception:
                mp_solutions = None
        # fallthrough if not found
    except Exception:
        pass

    return None


mp_face_mesh = _resolve_face_mesh_module()

# ------------------------------
# Helper Functions
# ------------------------------
def load_model(model_path):
    """Load the trained CNN model."""
    return tf.keras.models.load_model(model_path)

def preprocess_frame(frame_path):
    """Preprocess a single frame for CNN prediction."""
    img = load_img(frame_path, target_size=IMG_SIZE)
    arr = img_to_array(img) / 255.0
    return np.expand_dims(arr, axis=0)

def predict_frame(model, frame_path):
    """Predict probability that a frame is fake."""
    arr = preprocess_frame(frame_path)
    prob = model.predict(arr, verbose=0)[0][0]
    return prob

# ------------------------------
# Visual Forensic Metrics (enhanced)
# ------------------------------

# Key landmark indices (MediaPipe 468-point mesh)
KEY_LANDMARK_INDICES = [
    33, 160, 158, 133, 153, 144,
    362, 385, 387, 263, 373, 380,
    4, 6, 1,
    61, 291, 13, 14,
    172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397,
]

from collections import deque


class OpticalFlowAnalyzer:
    """
    Track motion using optical flow to detect unnatural motion patterns.
    Higher scores indicate more anomalous motion (characteristic of deepfakes).
    Uses 120-frame temporal window for robust detection.
    """
    
    def __init__(self, history_len: int = 120):
        self._prev_gray = None
        self._history = deque(maxlen=history_len)
    
    def analyze(self, frame):
        """Compute optical flow anomalies (0-1 score)."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self._prev_gray is None:
                self._prev_gray = gray
                return 0.0
            
            # Compute dense optical flow using Farneback algorithm
            flow = cv2.calcOpticalFlowFarneback(
                self._prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            
            # Calculate magnitude of motion vectors
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            
            # Detect anomalous motion: regions with unusually high motion
            mean_mag = np.mean(mag)
            std_mag = np.std(mag) + 1e-8
            z_scores = np.abs((mag - mean_mag) / std_mag)
            anomaly_ratio = np.sum(z_scores > 3.0) / max(mag.size, 1)
            
            # Higher anomaly ratio = higher warping likelihood
            flow_anomaly = float(np.clip(anomaly_ratio * 5.0, 0, 1))
            self._history.append(flow_anomaly)
            self._prev_gray = gray
            
            return flow_anomaly
        except Exception:
            return 0.0


class WarpingAnalyzer:
    """
    Rolling baseline landmark motion analyzer — reduces false positives
    from normal head movements by using longer-term history and z-score.
    Uses 120-frame temporal window for stable detection.
    """

    def __init__(self, history_len: int = 120):
        self._history = deque(maxlen=history_len)
        self._prev_landmarks = None

    def update(self, frame, face_mesh):
        if face_mesh is None:
            return 0.0, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return 0.0, None

        all_lm = results.multi_face_landmarks[0].landmark
        landmarks = np.array([(all_lm[i].x, all_lm[i].y) for i in KEY_LANDMARK_INDICES], dtype=np.float32)

        if self._prev_landmarks is None:
            self._prev_landmarks = landmarks
            return 0.0, landmarks

        per_point_dist = np.linalg.norm(landmarks - self._prev_landmarks, axis=1)
        mean_disp = float(np.mean(per_point_dist))
        self._prev_landmarks = landmarks
        self._history.append(mean_disp)

        if len(self._history) < 5:
            return float(np.clip(mean_disp * 10, 0, 1)), landmarks

        arr = np.array(self._history)
        mu, sigma = arr.mean(), arr.std() + 1e-8
        z = (mean_disp - mu) / sigma
        warp_score = float(np.clip((z - 2.0) / 3.0, 0, 1))
        return warp_score, landmarks


def analyze_warping(frame, prev_landmarks, face_mesh):
    """Stateless convenience wrapper keeping the original signature."""
    if face_mesh is None:
        return 0.0, None

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        return 0.0, None

    all_lm = results.multi_face_landmarks[0].landmark
    landmarks = np.array([(all_lm[i].x, all_lm[i].y) for i in KEY_LANDMARK_INDICES], dtype=np.float32)

    if prev_landmarks is None:
        return 0.0, landmarks

    diff = np.linalg.norm(landmarks - prev_landmarks, axis=1)
    warp_score = float(np.clip(np.mean(diff) * 10, 0, 1))
    return warp_score, landmarks


def extract_face_region(frame, landmarks=None):
    """
    Extract face region to avoid background artifacts.
    Uses landmarks if available, otherwise falls back to cascade classifier.
    
    Args:
        frame: The image frame (BGR format)
        landmarks: Normalized landmark coordinates (if available)
    
    Returns:
        face_region: Cropped face region for analysis
    """
    try:
        if landmarks is not None and len(landmarks) > 0:
            # Use landmarks to compute face bounding box
            x_coords = landmarks[:, 0]
            y_coords = landmarks[:, 1]
            
            x_min = int(x_coords.min() * frame.shape[1])
            x_max = int(x_coords.max() * frame.shape[1])
            y_min = int(y_coords.min() * frame.shape[0])
            y_max = int(y_coords.max() * frame.shape[0])
            
            # Add padding around face
            pad = int(max(x_max - x_min, y_max - y_min) * 0.1)
            x_min = max(0, x_min - pad)
            x_max = min(frame.shape[1], x_max + pad)
            y_min = max(0, y_min - pad)
            y_max = min(frame.shape[0], y_max + pad)
            
            return frame[y_min:y_max, x_min:x_max]
        else:
            # Fallback: detect face with cascade classifier
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) > 0:
                x, y, w, h = faces[0]
                pad = int(max(w, h) * 0.1)
                return frame[max(0, y-pad):min(frame.shape[0], y+h+pad),
                           max(0, x-pad):min(frame.shape[1], x+w+pad)]
            else:
                return frame  # Return full frame if no face detected
    except Exception:
        return frame  # Fallback to full frame on any error


def analyze_lighting(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2) + 1e-8
    weights = magnitude / magnitude.sum()

    wx = float(np.sum(grad_x * weights))
    wy = float(np.sum(grad_y * weights))
    return float(np.arctan2(wy, wx))


def lighting_inconsistency(light_dirs):
    if len(light_dirs) < 2:
        return 0.0
    diffs = np.abs(np.diff(light_dirs))
    diffs = np.where(diffs > np.pi, 2 * np.pi - diffs, diffs)
    return float(np.clip(mean(diffs) / np.pi, 0, 1))


def analyze_texture(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    lap_var = lap.var()
    mean_intensity = float(gray.mean()) + 1e-8
    relative_sharpness = lap_var / (mean_intensity ** 2)
    texture_score = float(np.clip(1.0 - (relative_sharpness / 2.0), 0, 1))
    return texture_score


def analyze_temporal_flicker(prev_frame, current_frame, face_bbox=None):
    if prev_frame is None or current_frame is None:
        return 0.0
    
    try:
        if face_bbox is not None:
            x, y, w, h = face_bbox
            prev_frame = prev_frame[y: y + h, x: x + w]
            current_frame = current_frame[y: y + h, x: x + w]

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        # Handle frames of different sizes (common when face regions vary)
        if prev_gray.shape != curr_gray.shape:
            # Resize current to match previous
            curr_gray = cv2.resize(curr_gray, (prev_gray.shape[1], prev_gray.shape[0]))

        diff = np.abs(curr_gray - prev_gray)
        flicker_score = float(np.clip(diff.mean() / 25.0, 0, 1))
        return flicker_score
    except Exception:
        return 0.0


def analyze_frequency_artifacts(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dft = np.fft.fft2(gray)
    dft_shift = np.fft.fftshift(dft)
    magnitude = np.log1p(np.abs(dft_shift))

    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    r_min, r_max = w * 0.3, w * 0.48
    hf_mask = (dist >= r_min) & (dist <= r_max)
    lf_mask = dist < w * 0.15

    hf_energy = magnitude[hf_mask].mean()
    lf_energy = magnitude[lf_mask].mean() + 1e-8
    ratio = hf_energy / lf_energy
    freq_score = float(np.clip((ratio - 0.5) / 0.3, 0, 1))
    return freq_score


def analyze_skin_chrominance(frame):
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]

    h, w = cr.shape
    Y, X = np.mgrid[0:h, 0:w]
    gauss = np.exp(-((X - w / 2) ** 2 + (Y - h / 2) ** 2) / (2 * (w * 0.3) ** 2))

    def weighted_std(channel, weight):
        wsum = weight.sum() + 1e-8
        mu = (channel * weight).sum() / wsum
        variance = ((channel - mu) ** 2 * weight).sum() / wsum
        return float(np.sqrt(variance))

    cr_std = weighted_std(cr, gauss)
    cb_std = weighted_std(cb, gauss)
    combined = (cr_std + cb_std) / 2.0
    chroma_score = float(np.clip((combined - 5.0) / 15.0, 0, 1))
    return chroma_score


def analyze_compression_artifacts(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape

    v_diffs = []
    for col in range(7, w - 1, 8):
        diff = np.abs(gray[:, col].astype(float) - gray[:, col + 1].astype(float))
        v_diffs.append(diff.mean())

    h_diffs = []
    for row in range(7, h - 1, 8):
        diff = np.abs(gray[row, :].astype(float) - gray[row + 1, :].astype(float))
        h_diffs.append(diff.mean())

    if not v_diffs or not h_diffs:
        return 0.0

    block_edge_mean = (np.mean(v_diffs) + np.mean(h_diffs)) / 2.0

    interior_diffs = []
    for col in range(3, w - 1, 8):
        diff = np.abs(gray[:, col].astype(float) - gray[:, col + 1].astype(float))
        interior_diffs.append(diff.mean())
    interior_mean = np.mean(interior_diffs) + 1e-8

    ratio = block_edge_mean / interior_mean
    compression_score = float(np.clip((ratio - 1.0) / 1.5, 0, 1))
    return compression_score


def aggregate_scores(scores: dict, weights: dict | None = None) -> float:
    default_weights = {
        "warp": 0.20,
        "lighting": 0.10,
        "texture": 0.15,
        "flicker": 0.15,
        "frequency": 0.20,
        "chrominance": 0.10,
        "compression": 0.10,
    }
    w = weights or default_weights
    total, denom = 0.0, 0.0
    for key, score in scores.items():
        weight = w.get(key, 0.1)
        total += score * weight
        denom += weight
    return float(total / denom) if denom > 0 else 0.0

# ------------------------------
# Face Alignment Stability
# ------------------------------
def analyze_alignment(prev_landmarks, current_landmarks):
    if prev_landmarks is None or current_landmarks is None:
        return 0
    shift = np.linalg.norm(current_landmarks - prev_landmarks, axis=1)
    return np.clip(np.mean(shift) * 8, 0, 1)

# ------------------------------
# Interpret Metrics
# ------------------------------
def interpret_metrics(metrics):
    factors = []

    # Warping (combined landmark + optical flow)
    if metrics.get("warp_score", 0) > 0.5:
        factors.append({
            "label": "Facial Warping Detected",
            "severity": "high" if metrics.get("warp_score", 0) > 0.75 else "medium",
            "description": f"Irregular geometry changes in {metrics.get('warp_frames', 0)} frames",
            "icon": "warping"
        })

    # Lighting
    if metrics.get("lighting_score", 0) > 0.35:
        factors.append({
            "label": "Lighting Inconsistencies",
            "severity": "medium",
            "description": "Shadow direction mismatches across frames",
            "icon": "lighting"
        })

    # Texture / Sharpness
    if metrics.get("texture_score", 0) > 0.45:
        factors.append({
            "label": "Texture Mismatches",
            "severity": "medium",
            "description": "Unnatural smoothness detected in face region",
            "icon": "texture"
        })

    # Temporal flicker
    if metrics.get("flicker_score", 0) > 0.25:
        factors.append({
            "label": "Temporal Flickering",
            "severity": "low",
            "description": "Frame-to-frame inconsistency detected",
            "icon": "temporal"
        })

    # Alignment
    if metrics.get("alignment_score", 0) > 0.4:
        factors.append({
            "label": "Unstable Face Alignment",
            "severity": "medium",
            "description": "Face position shifts unnaturally between frames",
            "icon": "alignment"
        })

    # Frequency artifacts
    if metrics.get("frequency_score", 0) > 0.45:
        factors.append({
            "label": "High-frequency Artifacts",
            "severity": "high",
            "description": "High-frequency artifacts in DCT/DFT analysis",
            "icon": "frequency"
        })

    # Chrominance discontinuities
    if metrics.get("chrominance_score", 0) > 0.35:
        factors.append({
            "label": "Chrominance Discontinuities",
            "severity": "medium",
            "description": "Skin colour inconsistencies around face boundaries",
            "icon": "chrominance"
        })

    # Compression artifacts
    if metrics.get("compression_score", 0) > 0.4:
        factors.append({
            "label": "Compression / Re-encoding Artifacts",
            "severity": "low",
            "description": "Double-JPEG/blocking patterns detected",
            "icon": "compression"
        })

    return factors

# ------------------------------
# Main Analyzer Function
# ------------------------------
def analyze_video_frames(model_path, frames_dir, frame_step=1):
    """
    Analyze all frames in a folder and return deepfake metrics.
    Enhanced with optical flow analysis and face region masking.
    frame_step: skips frames for faster analysis (e.g., frame_step=2 uses every other frame)
    """
    model = load_model(model_path)

    probs, warp_scores, light_dirs = [], [], []
    textures, flickers, alignments = [], [], []
    freqs, chromas, comps = [], [], []

    prev_landmarks, prev_frame = None, None
    warp_frames = 0

    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(('.jpg', '.png'))])[::frame_step]

    face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True) if mp_face_mesh else None
    # Use analyzers with 120-frame temporal history
    warper = WarpingAnalyzer(history_len=120)
    flow_analyzer = OpticalFlowAnalyzer(history_len=120)

    try:
        for f in frame_files:
            frame_path = os.path.join(frames_dir, f)
            frame = cv2.imread(frame_path)
            if frame is None:
                continue

            # CNN Prediction
            prob = predict_frame(model, frame_path)
            probs.append(prob)

            # Face analysis with optical flow
            warp_score, landmarks = warper.update(frame, face_mesh) if face_mesh else (0.0, None)
            
            # Opticalflow analysis
            flow_score = flow_analyzer.analyze(frame)
            # Combine landmark and optical flow warping
            combined_warp = (warp_score + flow_score) / 2.0
            warp_scores.append(combined_warp)
            if combined_warp > 0.5:
                warp_frames += 1

            # Alignment
            alignment_score = analyze_alignment(prev_landmarks, landmarks)
            alignments.append(alignment_score)

            prev_landmarks = landmarks

            # Lighting direction
            light_dirs.append(analyze_lighting(frame))

            # Extract face region for analysis (avoid background artifacts)
            face_region = extract_face_region(frame, landmarks)
            
            # Texture / sharpness (analyzed on face region)
            textures.append(analyze_texture(face_region))

            # Flicker (face-region sensitive)
            face_prev_frame = extract_face_region(prev_frame, None) if prev_frame is not None else None
            flickers.append(analyze_temporal_flicker(face_prev_frame, face_region))

            # Frequency, chroma, compression (all on face region)
            try:
                freq = analyze_frequency_artifacts(face_region)
            except Exception:
                freq = 0.0

            try:
                chroma = analyze_skin_chrominance(face_region)
            except Exception:
                chroma = 0.0

            try:
                comp = analyze_compression_artifacts(face_region)
            except Exception:
                comp = 0.0

            # store metrics in dedicated lists
            freqs.append(freq)
            chromas.append(chroma)
            comps.append(comp)

            prev_frame = frame
    finally:
        if face_mesh is not None:
            face_mesh.close()

    metrics = {
        "avg_prob": float(np.mean(probs)) if probs else 0,
        "warp_score": float(np.mean(warp_scores)) if warp_scores else 0,
        "warp_frames": warp_frames,
        "lighting_score": float(lighting_inconsistency(light_dirs)) if light_dirs else 0,
        "texture_score": float(np.mean(textures)) if textures else 0,
        "flicker_score": float(np.mean(flickers)) if flickers else 0,
        "alignment_score": float(np.mean(alignments)) if alignments else 0,
        "frequency_score": float(np.mean(freqs)) if freqs else 0,
        "chrominance_score": float(np.mean(chromas)) if chromas else 0,
        "compression_score": float(np.mean(comps)) if comps else 0
    }

    factors = interpret_metrics(metrics)

    result = {
        "prediction": "FAKE" if metrics["avg_prob"] > 0.5 else "REAL",
        "confidence": round(metrics["avg_prob"], 3),
        "metrics": metrics,
        "factors": factors
    }

    return result
