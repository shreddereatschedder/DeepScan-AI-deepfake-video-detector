# Backend Organization & Migration Plan

Purpose

This document groups and maps existing backend-related scripts into clear categories so it's obvious which files are for dataset preparation, model training, service/deployment, and runtime analysis/inference. It also provides recommended `git mv` commands so you can reorganize the repository with minimal risk.

Current inventory (discovered files)

- Backend service and helpers:
  - `backend/app.py`
  - `backend/fastapi_server.py`
  - `backend/main.py`
  - `backend/setup_vm.sh`
  - `backend/.env.example`
  - `backend/downloads/` (sample downloaded videos)

- Root-level analysis / tooling scripts:
  - `deepfake_training_vids_frame_extractor.py`  # frame extraction for video datasets
  - `video_analysis_core.py`                     # core analysis / inference routines
  - `video_downloads_monitor.py`                # download & monitoring helper

- Scripts directory (training & utilities):
  - `scripts/model_generation.py`               # model training / generation
  - `scripts/test_run.py`                       # CLI test harness for inference
  - `scripts/forensic_analyser.py`              # frame-level forensic calculations
  - `scripts/validate_model_mapping.py`         # validation utilities
  - `scripts/changes.py`                        # miscellaneous changes / experiments
  - `scripts/forensic_analyser copy.py`         # duplicate; consider removing/renaming
  - `scripts/models/`                           # saved artifacts
    - `scripts/models/deepfake_detector.h5`
    - `scripts/models/training_metrics.json`
    - `scripts/models/training_history.png`

Goals / Categories

1. `backend/dataset_prep/` — frame extraction, dataset assembly, sampling utilities
2. `backend/model_training/` — training scripts, model checkpoints, training logs
3. `backend/video_analyses/` — runtime analysis pipelines, CLI inference helpers used by extension
4. `backend/service/` — FastAPI server and deployment scripts
5. `backend/utils/` — shared helpers and lightweight utilities used across the above

Recommended (non-destructive) mapping

- Dataset preparation
  - Move `deepfake_training_vids_frame_extractor.py` -> `backend/dataset_prep/`
  - Any dataset-sampling scripts -> `backend/dataset_prep/`

- Model training
  - Move `scripts/model_generation.py` -> `backend/model_training/model_generation.py`
  - Move `scripts/models/` -> `backend/model_training/models/`
  - Move training-visualization / metric utilities -> `backend/model_training/`

- Inference / Analysis
  - Move `video_analysis_core.py` -> `backend/video_analyses/video_analysis_core.py`
  - Move `scripts/forensic_analyser.py` -> `backend/video_analyses/forensic_analyser.py`
  - Move `video_downloads_monitor.py` -> `backend/video_analyses/video_downloads_monitor.py`
  - Move `scripts/test_run.py` -> `backend/video_analyses/test_run.py`

- Service / Deployment
  - Move `backend/fastapi_server.py` -> `backend/service/fastapi_server.py`
  - Move `backend/app.py` -> `backend/service/app.py`
  - Move `backend/main.py` -> `backend/service/main.py`
  - Move `backend/setup_vm.sh` -> `backend/service/setup_vm.sh`
  - Move `backend/.env.example` -> `backend/service/.env.example`

- Utilities
  - Move `scripts/validate_model_mapping.py` and `scripts/changes.py` -> `backend/utils/`
  - Consider deleting or reconciling `scripts/forensic_analyser copy.py`

Recommended `git mv` commands (run from repo root)

# create folders (if not already present)
mkdir -p backend/dataset_prep backend/model_training backend/video_analyses backend/service backend/utils

# dataset
git mv deepfake_training_vids_frame_extractor.py backend/dataset_prep/

# model training
git mv scripts/model_generation.py backend/model_training/
git mv scripts/models backend/model_training/models

# inference / analysis
git mv video_analysis_core.py backend/video_analyses/
git mv video_downloads_monitor.py backend/video_analyses/
git mv scripts/forensic_analyser.py backend/video_analyses/
git mv scripts/test_run.py backend/video_analyses/

# service
git mv backend/fastapi_server.py backend/service/
git mv backend/app.py backend/service/
git mv backend/main.py backend/service/
git mv backend/setup_vm.sh backend/service/
git mv backend/.env.example backend/service/

# utilities
git mv scripts/validate_model_mapping.py backend/utils/
git mv scripts/changes.py backend/utils/

Notes and post-move checklist

- Imports and module paths:
  - After moving modules you may need to update import paths. If your code uses relative imports, adjust the `from .` or `from backend.` paths as needed.
  - To avoid surprises, add empty `__init__.py` files in each new folder (optional) so the directories are explicit Python packages:

```
# Example
touch backend/dataset_prep/__init__.py
touch backend/model_training/__init__.py
touch backend/video_analyses/__init__.py
touch backend/service/__init__.py
touch backend/utils/__init__.py
```

- Uvicorn (service) command changes:
  - If you move `fastapi_server.py` to `backend/service/fastapi_server.py`, start the server with:

```
uvicorn backend.service.fastapi_server:app --reload
```

- Model artifact paths:
  - Update any code that references `scripts/models/` to point to `backend/model_training/models/` (or keep `scripts/models/` where it is if you prefer artifacts to remain separate).

- Extension / UI:
  - The Chrome extension communicates with the backend API endpoint; ensure `extension/config.json` still points to the correct host/port.

- Duplicates:
  - `scripts/forensic_analyser copy.py` looks like an accidental copy — decide whether to delete, rename, or merge changes.

Testing after migration

1. Activate the venv:

Windows (PowerShell):
```
& .venv\Scripts\Activate.ps1
```

macOS/Linux:
```
source .venv/bin/activate
```

2. Start the backend (adjusted path after move):
```
uvicorn backend.service.fastapi_server:app --reload
```

3. Run a quick inference smoke test:
```
python backend/video_analyses/test_run.py --video_path "path/to/sample.mp4"
```

I will not move any files automatically without your confirmation — say `yes` and I will apply the git moves and attempt to update obvious import paths.

If you want I can also: a) add `__init__.py` files automatically, b) perform the `git mv` operations, and c) run a smoke test start of `uvicorn` to verify the server still starts.
