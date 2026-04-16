"""
Deepfake Detection Model Training
Enhanced with fine-tuning, regularization, and performance evaluation.
"""
import os
import sys
import cv2
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from keras.preprocessing.image import ImageDataGenerator
from keras.applications import Xception
from keras import layers, models, optimizers, callbacks
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

IMG_SIZE = (150, 150)
BATCH_SIZE = 32
EPOCHS_BASE = 15  # Initial frozen phase
EPOCHS_FINE_TUNE = 5  # Fine-tuning phase
VALIDATION_SPLIT = 0.1  # 10% of frames for validation
LABEL_REAL = 0
LABEL_FAKE = 1

DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
VIDEO_DATASET_DIR = os.path.join(DATASET_DIR, "video_dataset")

MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "deepfake_detector.h5")
PLOT_SAVE_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "training_history.png")
METRICS_SAVE_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "training_metrics.json")

os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)

print("="*70)
print("Deepfake Detection Model — Video Frames Version")
print("="*70)
print(f"Video dataset path: {VIDEO_DATASET_DIR}")
print(f"Model save path: {MODEL_SAVE_PATH}")
print("="*70)

# ---------------------------------------------------------
# GPU Check
# ---------------------------------------------------------
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"[SUCCESS] Using GPU: {gpus[0]}")
else:
    print(" No GPU detected. Training on CPU may be slow.")

# ---------------------------------------------------------
# Data Augmentation
# ---------------------------------------------------------
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=25,
    width_shift_range=0.2,
    height_shift_range=0.2,
    brightness_range=[0.7, 1.3],
    shear_range=0.15,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode='nearest',
    preprocessing_function=lambda x: cv2.GaussianBlur(x, (3, 3), 0)
)

val_datagen = ImageDataGenerator(rescale=1./255)

# ---------------------------------------------------------
# Custom function to load frames from folders and split train/validation
# ---------------------------------------------------------
def create_train_val_generators(fake_dir, real_dir, batch_size, val_split=0.1):
    # Collect all image paths
    fake_files = [os.path.join(fake_dir, f) for f in os.listdir(fake_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    real_files = [os.path.join(real_dir, f) for f in os.listdir(real_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    files = np.array(fake_files + real_files)
    labels = np.array([LABEL_FAKE]*len(fake_files) + [LABEL_REAL]*len(real_files))

    # Shuffle
    indices = np.arange(len(files))
    np.random.shuffle(indices)
    files, labels = files[indices], labels[indices]

    # Split into train and validation
    train_files, val_files, train_labels, val_labels = train_test_split(
        files, labels, test_size=val_split, stratify=labels, random_state=42
    )

    # Create generators using flow_from_dataframe
    import pandas as pd
    train_df = pd.DataFrame({'filename': train_files, 'label': train_labels.astype(int)})
    val_df = pd.DataFrame({'filename': val_files, 'label': val_labels.astype(int)})

    train_gen = train_datagen.flow_from_dataframe(
        dataframe=train_df,
        x_col='filename',
        y_col='label',
        target_size=IMG_SIZE,
        class_mode='raw',
        batch_size=batch_size,
        shuffle=True
    )

    val_gen = val_datagen.flow_from_dataframe(
        dataframe=val_df,
        x_col='filename',
        y_col='label',
        target_size=IMG_SIZE,
        class_mode='raw',
        batch_size=batch_size,
        shuffle=False
    )

    return train_gen, val_gen

# Set paths for video frames
VIDEO_FAKE_DIR = os.path.join(VIDEO_DATASET_DIR, "fake", "deepfake_frames")
VIDEO_REAL_DIR = os.path.join(VIDEO_DATASET_DIR, "real", "real_video_frames")

train_gen, val_gen = create_train_val_generators(VIDEO_FAKE_DIR, VIDEO_REAL_DIR, BATCH_SIZE, VALIDATION_SPLIT)

# ---------------------------------------------------------
# Build Model
# ---------------------------------------------------------
print("Building model...")
base_model = Xception(weights='imagenet', include_top=False, input_shape=(*IMG_SIZE, 3))
base_model.trainable = False

model = models.Sequential([
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dense(128, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.001)),
    layers.Dropout(0.5),
    layers.Dense(1, activation='sigmoid')
])

model.compile(
    optimizer=optimizers.Adam(learning_rate=1e-4),
    loss='binary_crossentropy',
    metrics=['accuracy']
)
print("[SUCCESS] Base model built and compiled.")

# ---------------------------------------------------------
# Callbacks
# ---------------------------------------------------------
checkpoint = callbacks.ModelCheckpoint(MODEL_SAVE_PATH, monitor='val_accuracy', save_best_only=True, verbose=1)
early_stop = callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, verbose=1)
reduce_lr = callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1)

# ---------------------------------------------------------
# Phase 1: Train Base Layers (Frozen)
# ---------------------------------------------------------
print("\n[INFO] Phase 1: Training base model layers...")
history_base = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS_BASE,
    callbacks=[checkpoint, early_stop, reduce_lr]
)

# ---------------------------------------------------------
# Phase 2: Fine-tuning deeper layers
# ---------------------------------------------------------
print("\n[INFO] Unfreezing top layers for fine-tuning...")
for layer in base_model.layers[-40:]:
    layer.trainable = True

model.compile(
    optimizer=optimizers.Adam(learning_rate=1e-5),
    loss='binary_crossentropy',
    metrics=['accuracy']
)

print("[INFO] Phase 2: Fine-tuning...")
history_finetune = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS_FINE_TUNE,
    callbacks=[checkpoint, reduce_lr]
)

print("\n[SUCCESS] Training completed successfully!")

# ---------------------------------------------------------
# Combine History
# ---------------------------------------------------------
def combine_history(h1, h2):
    combined = {}
    for key in h1.history.keys():
        combined[key] = h1.history[key] + h2.history[key]
    return combined

full_history = combine_history(history_base, history_finetune)

# ---------------------------------------------------------
# Save Model
# ---------------------------------------------------------
model.save(MODEL_SAVE_PATH)
print(f"[SUCCESS] Final model saved to: {MODEL_SAVE_PATH}")

# ---------------------------------------------------------
# Evaluate Model Performance
# ---------------------------------------------------------
val_gen.reset()
y_true = val_gen.classes
y_pred_probs = model.predict(val_gen)
y_pred = (y_pred_probs > 0.5).astype(int).flatten()

cm = confusion_matrix(y_true, y_pred)
report = classification_report(y_true, y_pred, labels=[LABEL_REAL, LABEL_FAKE], target_names=["real", "fake"], output_dict=True)

metrics_summary = {
    "total_validation_images": len(y_true),
    "confusion_matrix": cm.tolist(),
    "classification_report": report,
    "label_mapping": {
        "real": LABEL_REAL,
        "fake": LABEL_FAKE,
        "threshold": 0.5,
        "rule": "prediction > 0.5 => fake"
    },
    "final_val_accuracy": float(np.mean(full_history['val_accuracy'][-3:])),
    "final_val_loss": float(np.mean(full_history['val_loss'][-3:]))
}

with open(METRICS_SAVE_PATH, "w") as f:
    json.dump(metrics_summary, f, indent=2)

print(f"\n[INFO] Model evaluation metrics saved to: {METRICS_SAVE_PATH}")
print("Confusion Matrix:")
print(cm)

# ---------------------------------------------------------
# Plot Training Curves
# ---------------------------------------------------------
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(full_history['accuracy'], label='Train Acc')
plt.plot(full_history['val_accuracy'], label='Val Acc')
plt.title('Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(full_history['loss'], label='Train Loss')
plt.plot(full_history['val_loss'], label='Val Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.tight_layout()
plt.savefig(PLOT_SAVE_PATH)
print(f"[SUCCESS] Training plots saved to: {PLOT_SAVE_PATH}")
plt.show()

print("\nFinal Results:")
print(f"Validation Accuracy: {metrics_summary['final_val_accuracy']:.3f}")
print(f"Validation Loss: {metrics_summary['final_val_loss']:.3f}")
print("[SUCCESS] Model ready for explainable analysis integration.")