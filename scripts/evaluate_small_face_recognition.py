"""Measure SFace recognition at classroom face sizes using enrolled portraits.

Each enrollment photo is shrunk so the face is N px wide and JPEG-compressed
(quality 70, similar to messaging apps), then matched against clean templates
built from all photos. Reports rank-1 accuracy, genuine/impostor similarity and
the impostor tail used to choose the auto-accept threshold.

Two probe paths are compared, both detecting the face on the degraded photo:
  detect@1x  - YuNet on the small photo, align from it (previous pipeline)
  detect@up  - YuNet on the bicubic upscale chosen by CVEngine.detection_upscale,
               align with align_for_recognition (current pipeline)
Most of the gain comes from more precise landmarks on tiny faces.

Probes come from the same photo as their template, so genuine scores are an
optimistic upper bound; impostor statistics are unaffected.

Usage:  PYTHONPATH=. python scripts/evaluate_small_face_recognition.py [photo_dir]
"""

import glob
import sys
from unittest.mock import MagicMock

import cv2
import numpy as np

from classsnap.cv.engine import CVEngine
from classsnap.services.enrollment_service import EnrollmentService


def main(photo_dir: str = "uploads/students") -> None:
    engine = CVEngine.from_settings()
    service = EnrollmentService(cv_engine=engine)
    photos = sorted(glob.glob(f"{photo_dir}/*"))
    gallery, base = {}, {}
    for path in photos:
        image = engine.load_image(path)
        det = service._select_enrollment_face(image, MagicMock(student_id=path))
        gallery[path] = engine.embedder.extract_embedding(engine.aligner.align(image, det))
        base[path] = (image, det)

    print("face px | method        | rank-1 | genuine | max impostor")
    impostors = []
    for size in (16, 20, 24, 32, 48):
        for method in ("detect@1x", "detect@up"):
            top1, genuine, worst = 0, [], []
            for path, (image, det) in base.items():
                s = size / det.bbox.w
                small = cv2.resize(image, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
                small = cv2.imdecode(cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])[1], 1)
                cx, cy = (det.bbox.x + det.bbox.w / 2) * s, (det.bbox.y + det.bbox.h / 2) * s
                factor = engine.detection_upscale(small) if method == "detect@up" else 1.0
                work = small if factor == 1.0 else cv2.resize(small, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
                found = [
                    engine._rescale_detection(d, 1.0 / factor)
                    for d in engine.detector.detect(work, score_threshold=0.5)
                ]
                found = [d for d in found if abs(d.bbox.x + d.bbox.w / 2 - cx) < d.bbox.w and abs(d.bbox.y + d.bbox.h / 2 - cy) < d.bbox.h]
                if not found:
                    continue
                probe = max(found, key=lambda d: d.confidence)
                align = engine.align_for_recognition if method == "detect@up" else engine.aligner.align
                v = engine.embedder.extract_embedding(align(small, probe))
                scores = {k: float(v @ g) for k, g in gallery.items()}
                top1 += max(scores, key=scores.get) == path
                genuine.append(scores[path])
                others = [sc for k, sc in scores.items() if k != path]
                worst.append(max(others))
                if method == "detect@up":
                    impostors.extend(others)
            print(f"{size:7d} | {method:13s} | {top1:2d}/{len(photos):<3d} | {np.mean(genuine) if genuine else 0:.3f}   | {np.mean(worst) if worst else 0:.3f}   (detected {len(genuine)})")
    imp = np.array(impostors)
    print(f"\nimpostor pairs={imp.size} p95={np.percentile(imp, 95):.3f} p99={np.percentile(imp, 99):.3f} "
          f">=0.38: {(imp >= 0.38).mean():.1%}  >=0.42: {(imp >= 0.42).mean():.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:])
