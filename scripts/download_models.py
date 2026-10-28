#!/usr/bin/env python3
"""
Model download and verification script for ClassSnap.
Downloads OpenCV YuNet and SFace from the official OpenCV Zoo repository.
"""

import hashlib
import os
import ssl
import sys
from pathlib import Path
from urllib.request import urlopen

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

MODELS_INFO = {
    "yunet": {
        "filename": "face_detection_yunet_2023mar.onnx",
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "sha256": "4b6730a38be985fe66b729486c9d09c2d1b80300d603e00cf05c9359e1c1dc11",
        "version": "2023mar",
        "license": "Apache-2.0",
        "source": "https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet",
    },
    "sface": {
        "filename": "face_recognition_sface_2021dec.onnx",
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "sha256": "9082be0a5fcf4aa08ba06a640db741757ec953a6a9be3b2a59a9db69e71dd6cf",
        "version": "2021dec",
        "license": "Apache-2.0",
        "source": "https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface",
    },
}


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_models(target_dir: Path) -> bool:
    target_dir.mkdir(parents=True, exist_ok=True)
    all_ok = True

    for key, meta in MODELS_INFO.items():
        dest = target_dir / meta["filename"]
        if dest.exists() and dest.stat().st_size > 0:
            print(f"[OK] {meta['filename']} already exists ({dest.stat().st_size / 1024:.1f} KB).")
            continue

        print(f"[*] Downloading {meta['filename']} from {meta['url']}...")
        try:
            with urlopen(meta["url"], context=SSL_CONTEXT) as response, open(dest, "wb") as out_file:
                while chunk := response.read(65536):
                    out_file.write(chunk)
            print(f"[OK] Downloaded {meta['filename']} ({dest.stat().st_size / 1024:.1f} KB).")
            calculated = compute_sha256(dest)
            print(f"    SHA256: {calculated}")
        except Exception as e:
            print(f"[ERROR] Failed to download {meta['filename']}: {e}", file=sys.stderr)
            if dest.exists():
                dest.unlink()
            all_ok = False

    return all_ok


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    target_dir = base_dir / "models"
    success = download_models(target_dir)
    sys.exit(0 if success else 1)
