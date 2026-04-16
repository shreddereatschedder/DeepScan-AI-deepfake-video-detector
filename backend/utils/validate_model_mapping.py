"""Quick validation script to check model outputs on small real/fake samples."""
import os
import glob
import numpy as np
import cv2
from keras.models import load_model
from pathlib import Path as _Path

PROJECT_ROOT = _Path(__file__).resolve().parents[2]
MODEL_PATH = os.path.join(str(PROJECT_ROOT), 'backend', 'model_training', 'models', 'deepfake_detector.h5')
FAKE_DIR = os.path.join(str(PROJECT_ROOT), 'dataset', 'video_dataset', 'fake', 'deepfake_frames')
REAL_DIR = os.path.join(str(PROJECT_ROOT), 'dataset', 'video_dataset', 'real', 'real_video_frames')

def sample_mean(folder, n=50):
    files = glob.glob(os.path.join(folder, '*.jpg'))[:n]
    preds = []
    for p in files:
        im = cv2.imread(p)
        if im is None:
            continue
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        im = cv2.resize(im, (150,150)).astype('float32')/255.0
        preds.append(im)
    if not preds:
        return None
    return np.stack(preds)

def main():
    if not os.path.exists(MODEL_PATH):
        print('Model not found at', MODEL_PATH)
        return

    model = load_model(MODEL_PATH, compile=False)
    model.compile(optimizer='adam', loss='binary_crossentropy')

    fake_batch = sample_mean(FAKE_DIR, n=50)
    real_batch = sample_mean(REAL_DIR, n=50)

    if fake_batch is None or real_batch is None:
        print('Not enough sample images in dataset to validate mapping.')
        return

    fake_preds = model.predict(fake_batch, verbose=0).flatten()
    real_preds = model.predict(real_batch, verbose=0).flatten()

    print('Fake samples mean prob (higher => more fake):', float(np.mean(fake_preds)))
    print('Real samples mean prob (higher => more fake):', float(np.mean(real_preds)))
    print('Sample fake preds (first 5):', fake_preds[:5].tolist())
    print('Sample real preds (first 5):', real_preds[:5].tolist())

if __name__ == '__main__':
    main()
