import os
import cv2
import random
from pathlib import Path

SOURCE_ROOT = "dataset/video_dataset"
MAX_PER_CATEGORY = 200

REAL_FOLDER = "real/real_videos"

FAKE_FOLDERS = [
    "DeepFakeDetection",
    "Deepfakes",
    "Face2Face",
    "FaceShifter",
    "FaceSwap",
    "NeuralTextures"
]

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def get_video_files(input_folder):
    if not input_folder.exists():
        return []

    return sorted(
        [
            path for path in input_folder.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
        ]
    )


def extract_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Could not open video: {video_path}")
        return 0

    frame_id = 0
    video_name = Path(video_path).stem
    category_name = Path(video_path).parent.name

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_name = f"{category_name}_{video_name}_frame_{frame_id:06d}.jpg"
        cv2.imwrite(os.path.join(output_folder, frame_name), frame)

        frame_id += 1

    cap.release()
    return frame_id


def process_collection(video_files, output_folder, collection_name):
    os.makedirs(output_folder, exist_ok=True)

    print(f"\nProcessing {collection_name}")
    print(f"Output folder: {output_folder}")

    total_frames = 0
    for video_path in video_files:
        print(f"Extracting frames from: {video_path}")
        extracted = extract_frames(video_path, output_folder)
        total_frames += extracted

    print(f"Finished {collection_name}: {len(video_files)} video(s), {total_frames} frame(s)")


def process_real_videos(source_root):
    real_input_folder = source_root / REAL_FOLDER
    real_output_folder = source_root / "real" / "real_video_frames"

    real_videos = get_video_files(real_input_folder)
    process_collection(real_videos, real_output_folder, "real videos")


def process_fake_videos(source_root):
    fake_root_folder = source_root / "fake"
    fake_output_folder = fake_root_folder / "deepfake_frames"
    fake_output_folder.mkdir(parents=True, exist_ok=True)

    for fake_folder in FAKE_FOLDERS:
        fake_input_folder = fake_root_folder / fake_folder
        if not fake_input_folder.exists():
            print(f"Skipping missing folder: {fake_input_folder}")
            continue

        candidate_items = [
            fake_input_folder / name
            for name in os.listdir(fake_input_folder)
            if (fake_input_folder / name).is_file() and name.lower().endswith(".mp4")
        ]
        if len(candidate_items) > MAX_PER_CATEGORY:
            fake_videos = random.sample(candidate_items, MAX_PER_CATEGORY)
        else:
            fake_videos = candidate_items

        print(
            f"\nProcessing folder {fake_folder}: "
            f"{len(fake_videos)} video(s) selected (cap={MAX_PER_CATEGORY})"
        )

        total_frames = 0
        for video_path in fake_videos:
            print(f"Extracting frames from: {video_path}")
            extracted = extract_frames(video_path, fake_output_folder)
            total_frames += extracted

        print(
            f"Finished fake folder {fake_folder}: "
            f"{len(fake_videos)} video(s), {total_frames} frame(s)"
        )


def main():
    source_root = Path(SOURCE_ROOT)

    if not source_root.exists():
        raise FileNotFoundError(f"Source root not found: {source_root}")

    # Intentionally process fake videos only.
    process_fake_videos(source_root)
    # process_real_videos(source_root)

if __name__ == "__main__":
    main()