import importlib, importlib.util, sys

modules = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "starlette",
    "cv2",
    "numpy",
    "pandas",
    "tensorflow",
    "keras",
    "mediapipe",
    "yt_dlp",
    "sklearn",
    "matplotlib",
    "tqdm",
    "requests",
]

print("Checking imports (using current Python interpreter):\n")
for m in modules:
    try:
        spec = importlib.util.find_spec(m)
        if spec is None:
            print(f"{m}: MISSING")
            continue
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", getattr(mod, "VERSION", "unknown"))
        print(f"{m}: OK ({ver})")
    except Exception as e:
        print(f"{m}: IMPORT ERROR: {e}")

print('\nDone.')
