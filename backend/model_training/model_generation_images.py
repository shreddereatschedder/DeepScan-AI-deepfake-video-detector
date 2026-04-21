"""Image-based Deepfake Detection Model Training.
Restored version using static images dataset (train/valid with real/fake directories).
"""
import os
import sys
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

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

IMG_SIZE = (150, 150)
BATCH_SIZE = 32
EPOCHS_BASE = 15
EPOCHS_FINE_TUNE = 5
VALIDATION_SPLIT = 0.1

DATASET_ROOT = os.path.join(PROJECT_ROOT, "dataset")
IMAGE_DATASET_DIR = os.path.join(DATASET_ROOT, "image_dataset")
MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "deepfake_detector_images.h5")
PLOT_SAVE_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "training_history_images.png")
METRICS_SAVE_PATH = os.path.join(PROJECT_ROOT, "backend", "model_training", "models", "training_metrics_images.json")

os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)

print("=" * 70)
print("Deepfake Detection Model — Static Images Version")
print("=" * 70)
print(f"Image dataset path: {IMAGE_DATASET_DIR}")
print(f"Model save path: {MODEL_SAVE_PATH}")
print("=" * 70)

# GPU check
gpus = tf.config.list_physical_devices('GPU')
if gpus:
	print(f"[SUCCESS] Using GPU: {gpus[0]}")
else:
	print(" No GPU detected. Training on CPU may be slow.")


# Data augmentation / preprocessing
train_datagen = ImageDataGenerator(
	rescale=1.0 / 255,
	rotation_range=25,
	width_shift_range=0.2,
	height_shift_range=0.2,
	brightness_range=[0.7, 1.3],
	shear_range=0.15,
	zoom_range=0.2,
	horizontal_flip=True,
	fill_mode='nearest'
)
val_datagen = ImageDataGenerator(rescale=1.0 / 255)


def ensure_dataset_structure(base_dir: str):
	"""Ensure dataset directory exists with train/validation (and valid) subfolders.

	Will create the following structure if missing:
	  dataset/image_dataset/train/{real,fake}
	  dataset/image_dataset/validation/{real,fake}
	  dataset/image_dataset/valid/{real,fake}  # created as a convenience alias
	"""
	os.makedirs(base_dir, exist_ok=True)
	train_dir = os.path.join(base_dir, 'train')
	validation_dir = os.path.join(base_dir, 'validation')
	valid_dir = os.path.join(base_dir, 'valid')

	for d in (train_dir, validation_dir, valid_dir):
		for cls in ('real', 'fake'):
			os.makedirs(os.path.join(d, cls), exist_ok=True)

	print(f"[INFO] Ensured dataset structure under: {base_dir}")
	print("[INFO] Expected image placement: train/real, train/fake, validation/real, validation/fake (or valid/..)")
	return train_dir, validation_dir, valid_dir


def get_generators(dataset_dir: str, img_size, batch_size, val_split=0.1):
	"""Return (train_gen, val_gen).

	Supports two layouts:
	  1) explicit folders: dataset_dir/train/{real,fake} and dataset_dir/validation|valid/{real,fake}
	  2) flat class folders: dataset_dir/{real,fake}  (will perform a train/val split)
	"""
	# Prefer explicit train/validation folders
	train_dir = os.path.join(dataset_dir, 'train')
	validation_dir = os.path.join(dataset_dir, 'validation')
	valid_dir = os.path.join(dataset_dir, 'valid')
	chosen_val_dir = None
	if os.path.isdir(validation_dir):
		chosen_val_dir = validation_dir
	elif os.path.isdir(valid_dir):
		chosen_val_dir = valid_dir

	if os.path.isdir(train_dir) and chosen_val_dir is not None:
		train_gen = train_datagen.flow_from_directory(
			train_dir,
			target_size=img_size,
			batch_size=batch_size,
			class_mode='binary',
			shuffle=True
		)
		val_gen = val_datagen.flow_from_directory(
			chosen_val_dir,
			target_size=img_size,
			batch_size=batch_size,
			class_mode='binary',
			shuffle=False
		)
		return train_gen, val_gen

	# Fallback: dataset_dir contains class subfolders (real/fake). Build explicit split.
	classes = ['real', 'fake']
	files = []
	labels = []
	exts = ('.png', '.jpg', '.jpeg')
	for idx, cls in enumerate(classes):
		cls_dir = os.path.join(dataset_dir, cls)
		if not os.path.isdir(cls_dir):
			continue
		for f in os.listdir(cls_dir):
			if f.lower().endswith(exts):
				files.append(os.path.join(cls_dir, f))
				labels.append(idx)

	if len(files) == 0:
		raise FileNotFoundError(f"No images found in {dataset_dir}. Please add images under train/real, train/fake, validation/real, validation/fake or under {dataset_dir}/real and {dataset_dir}/fake")

	files = np.array(files)
	labels = np.array(labels)
	# Shuffle and split
	idxs = np.arange(len(files))
	np.random.shuffle(idxs)
	files, labels = files[idxs], labels[idxs]

	train_files, val_files, train_labels, val_labels = train_test_split(
		files, labels, test_size=val_split, stratify=labels, random_state=42
	)

	import pandas as pd
	train_df = pd.DataFrame({'filename': train_files, 'label': train_labels})
	val_df = pd.DataFrame({'filename': val_files, 'label': val_labels})

	train_gen = train_datagen.flow_from_dataframe(
		dataframe=train_df,
		x_col='filename',
		y_col='label',
		target_size=img_size,
		class_mode='raw',
		batch_size=batch_size,
		shuffle=True
	)

	val_gen = val_datagen.flow_from_dataframe(
		dataframe=val_df,
		x_col='filename',
		y_col='label',
		target_size=img_size,
		class_mode='raw',
		batch_size=batch_size,
		shuffle=False
	)

	return train_gen, val_gen


# Ensure dataset structure exists (creates dirs if missing)
ensure_dataset_structure(IMAGE_DATASET_DIR)

try:
	train_gen, val_gen = get_generators(IMAGE_DATASET_DIR, IMG_SIZE, BATCH_SIZE, VALIDATION_SPLIT)
except Exception as e:
	print(f"[ERROR] Could not create generators: {e}")
	raise


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


# Callbacks
checkpoint = callbacks.ModelCheckpoint(MODEL_SAVE_PATH, monitor='val_accuracy', save_best_only=True, verbose=1)
early_stop = callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, verbose=1)
reduce_lr = callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1)

print("\n[INFO] Phase 1: Training base model layers...")
history_base = model.fit(
	train_gen,
	validation_data=val_gen,
	epochs=EPOCHS_BASE,
	callbacks=[checkpoint, early_stop, reduce_lr]
)

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


# Combine History
def combine_history(h1, h2):
	combined = {}
	for key in h1.history.keys():
		combined[key] = h1.history[key] + h2.history[key]
	return combined

full_history = combine_history(history_base, history_finetune)


# Save Model
model.save(MODEL_SAVE_PATH)
print(f"[SUCCESS] Final model saved to: {MODEL_SAVE_PATH}")


# ---------------------------------------------------------
# Evaluate Model Performance
# ---------------------------------------------------------
val_gen.reset()
y_true = val_gen.classes if hasattr(val_gen, 'classes') else np.concatenate([y for _, y in val_gen])
y_pred_probs = model.predict(val_gen)
y_pred = (y_pred_probs > 0.5).astype(int).flatten()

cm = confusion_matrix(y_true, y_pred)
report = classification_report(y_true, y_pred, output_dict=True)

metrics_summary = {
	"total_validation_images": len(y_true),
	"confusion_matrix": cm.tolist(),
	"classification_report": report,
	"threshold": 0.5
}

with open(METRICS_SAVE_PATH, "w") as f:
	json.dump(metrics_summary, f, indent=2)

print(f"[INFO] Model evaluation metrics saved to: {METRICS_SAVE_PATH}")
print("Confusion Matrix:")
print(cm)


# Plot Training Curves
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
print(f"Validation Accuracy: {np.mean(full_history['val_accuracy'][-3:]):.3f}")
print(f"Validation Loss: {np.mean(full_history['val_loss'][-3:]):.3f}")
