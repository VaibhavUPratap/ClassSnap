# ClassSnap Face Detection and Recognition Models

## Summary

ClassSnap uses two ONNX models through OpenCV's DNN APIs:

| Role | Model | Version | ONNX file | OpenCV API | Output |
|---|---|---|---|---|---|
| Face detection | YuNet | `2023mar` | `models/face_detection_yunet_2023mar.onnx` | `cv2.FaceDetectorYN` | Bounding boxes, confidence, and five facial landmarks |
| Face recognition / embedding | SFace | `2021dec` | `models/face_recognition_sface_2021dec.onnx` | `cv2.FaceRecognizerSF` | Unit-normalized 128-dimensional float32 embedding |

YuNet finds candidate faces. SFace does not directly identify a named person: it converts an aligned face into a numerical embedding. ClassSnap compares that embedding with consented student templates using cosine similarity and then requires human review before attendance is confirmed.

Both known models are Apache-2.0 licensed. The model registry identifies the official OpenCV Zoo/Hugging Face sources:

- YuNet: <https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet>
- SFace: <https://huggingface.co/opencv/face_recognition_sface>

## End-to-End Pipeline

```text
BGR image
  -> load and validate
  -> YuNet face detection
  -> optional high-resolution tiling
  -> duplicate-box suppression
  -> face quality assessment
  -> five-landmark similarity-transform alignment
  -> SFace 128D embedding extraction
  -> unit-L2 normalization
  -> cosine similarity against enrolled student templates
  -> threshold and one-to-one assignment logic
  -> proposed attendance requiring reviewer action
```

The orchestration lives in `CVEngine`, while the concrete classes are `YuNetFaceDetector`, `SimilarityTransformAligner`, and `SFaceEmbeddingExtractor`.

## 1. YuNet Face Detection

### Implementation

`YuNetFaceDetector` wraps `cv2.FaceDetectorYN.create()` and uses the `face_detection_yunet_2023mar.onnx` model.

For each image pass, the detector:

1. Sets the OpenCV input size to the exact image or tile dimensions.
2. Applies the requested detection score threshold.
3. Runs YuNet through `FaceDetectorYN.detect()`.
4. Reads a 15-value result per face:
   - values `0:4`: `(x, y, width, height)`
   - values `4:14`: five landmark coordinate pairs
   - value `14`: confidence score

YuNet returns these five landmarks:

1. Right eye
2. Left eye
3. Nose tip
4. Right mouth corner
5. Left mouth corner

These landmarks are used to align the face before SFace embedding extraction.

### Detection configuration

| Setting | Default | Effect |
|---|---:|---|
| Detection score threshold | `0.65` | Default threshold in application settings and classroom processing |
| Small-face upscale target | `3840` px, max `3x` | Photos whose longest side is under 2560 px are bicubically upscaled before detection (see below) |
| Minimum face size | `12` px | Measured in the original photo; smaller boxes are discarded |
| Enrollment threshold | `0.40` | Used while searching for a usable portrait for enrollment |
| NMS threshold | `0.30` | YuNet's internal NMS threshold |
| Top-K candidates | `5000` | Maximum candidates considered by YuNet |

The score threshold can be overridden when calling `CVEngine.process_image()` or `detect()`.

### High-resolution tiled detection

For large images, `TiledFaceDetector` can combine a full-image pass with overlapping tile passes. It is configured with:

- tile size: `640` pixels
- overlap: `25%`
- tile merge IoU threshold: `0.40`
- containment threshold: `0.60`

Overlapping detections are deduplicated using IoU and containment. The remaining faces are sorted in classroom order: top-to-bottom rows and left-to-right within each row.

The attendance processing endpoint calls `CVEngine.process_image(..., score_threshold=0.65, use_tiling=True)`.

### Small-face recovery

Messaging apps shrink classroom photos to about 1280 px, which leaves back-row faces 12-24 px wide.
YuNet localises such faces and their landmarks poorly, and the previous 24 px quality floor discarded
them, so on a real 1280 x 960 classroom photo only 23 of roughly 48 visible faces reached recognition.

`CVEngine.detection_upscale()` now picks a factor that brings the longest side to about 3840 px
(at most 3x; photos already at 2560 px or more are left alone). Detection runs on the bicubic
upscale, boxes and landmarks are mapped back to original coordinates, quality is judged on the
original pixels, and `align_for_recognition()` aligns each face from an upscaled local region.

Measured with `scripts/evaluate_small_face_recognition.py` (16 enrolled portraits shrunk and
JPEG-compressed to classroom face sizes, matched against clean templates):

| Face width | Previous rank-1 / genuine similarity | Upscaled detection rank-1 / genuine similarity |
|---:|---|---|
| 16 px | 13/16 / 0.410 | 15/16 / 0.441 |
| 20 px | 16/16 / 0.549 | 16/16 / 0.590 |
| 24 px | 16/16 / 0.650 | 16/16 / 0.683 |
| 32 px | 16/16 / 0.728 | 16/16 / 0.768 |

Probes come from the same photo as their template, so these genuine scores are an upper bound.
Most of the gain comes from more precise landmarks; resampling alone adds about 0.015 at 16 px.
On the real classroom photo, usable faces rose from 23 to 42 and confident matches from 4 to 8,
in about 0.6 s instead of 0.2 s.

## 2. Face Quality Assessment

Detection and recognition are separate from face quality. `OpenCVFaceQualityAssessor` evaluates the detected face crop using OpenCV and NumPy heuristics:

- minimum face size: `12` pixels in classroom processing (`min_face_size_px`)
- Laplacian variance sharpness: at least `15`
- mean brightness: between `25` and `245`
- grayscale contrast: at least `12`
- combined quality score: size, sharpness, brightness, and contrast

The quality assessor marks unusable detections as `low_quality`; unusable detections do not receive recognition embeddings in normal CV-engine processing.

Enrollment is stricter: it rejects a usable detected face smaller than `80` pixels and requires exactly one detected face in the enrollment photograph after overlapping detections are grouped.

## 3. Face Alignment

`SimilarityTransformAligner` uses YuNet's five landmarks and `cv2.estimateAffinePartial2D()` to map the detected face to a standard `112 x 112` crop. The transform supports rotation, uniform scale, and translation.

The target crop uses the standard five-point 112-pixel reference layout:

- right eye
- left eye
- nose tip
- right mouth corner
- left mouth corner

If landmarks are unavailable or cannot form a transform, the aligner falls back to a padded, aspect-ratio-preserving bounding-box crop and resizes it to `112 x 112`.

## 4. SFace Recognition and Embedding

### Implementation

`SFaceEmbeddingExtractor` wraps `cv2.FaceRecognizerSF.create()` and uses `face_recognition_sface_2021dec.onnx`.

Before inference, the aligned face is resized to `112 x 112` if necessary. SFace then produces a feature vector that is:

- flattened to one dimension
- converted to `float32`
- normalized to unit L2 length

The result is therefore:

```text
dimension = 128
dtype = float32
norm = approximately 1.0
```

The embedding is a biometric feature representation, not a human-readable face image or class label.

### Enrollment templates

During consented enrollment, ClassSnap:

1. Detects exactly one sufficiently large face.
2. Runs quality checks.
3. Aligns the face.
4. Extracts the 128D SFace vector.
5. Stores the vector as a normalized `float32` binary blob.
6. Stores the model name and version (`SFace:2021dec`) with the template.
7. Stores a small aligned-face JPEG preview for reviewer use.

Multiple templates for a student are averaged component-wise and then unit-normalized before matching. The original enrollment photograph is not retained by the default workflow.

## 5. Identity Matching

SFace vectors are compared with cosine similarity:

```text
similarity = dot(query, reference) / (norm(query) * norm(reference))
```

SFace vectors are stored and extracted as unit-normalized vectors, so this is computationally equivalent to a dot product for compatible vectors.

### Default thresholds

The default `MatchingThresholds` are:

| Rule | Default | Meaning |
|---|---:|---|
| Acceptance | `0.38` | Below this the face is `unknown` |
| Auto-accept | `0.42` | Between 0.38 and 0.42 the best candidate is only flagged for review |
| Ambiguity gap | `0.06` | Top-minus-second score must be at least this value |

Matching decisions:

- **`matched_pending_review`**: the top score passes acceptance and is sufficiently separated from the second candidate.
- **`ambiguous`**: the top score passes acceptance, but the top-two gap is too small, or the score is in the 0.38-0.42 review band. The candidate is shown to the reviewer as NEEDS REVIEW and is never auto-marked present.

The review band comes from measured impostor scores at classroom resolution: 2.4% of
different-person pairs reach 0.38 (99th percentile 0.40), but only 0.7% reach 0.42. With a
20-student roster, a 0.38 cut-off gives an unknown face a substantial chance of resembling
someone. On the real classroom photo, non-matching faces ran continuously up to 0.39, while
confident matches started at 0.44.
- **`unknown`**: the top score is below the acceptance threshold or a unique assignment cannot be made.
- **`low_quality`**: quality checks or embedding extraction prevented matching.
- **`no_candidate`**: the roster has no compatible template or no template of the requested model version.

### One-to-one assignment

`MatchingService.match_all()` prevents two detections from claiming the same student. It ranks candidates and resolves conflicts in descending similarity, assigning each student to at most one detection. Duplicate detections that overlap a positive match can also have their unknown proposals suppressed.

Matching is a rule-based biometric lookup. It is not a separate trained classifier for the roster.

### Threshold calibration

The matching module also provides a labeled-pair calibration function. When supplied with genuine and impostor embeddings, it can calculate an acceptance threshold for a requested false-accept percentile. Calibration requires both:

- at least one same-identity pair
- at least one different-identity pair

It also rejects a threshold that is not lower than the minimum genuine similarity. In the current application, the default static threshold is `0.38`; calibration is available as an API/module capability rather than as an automatically loaded runtime threshold.

## 6. Model and Version Integrity

The model registry in `classsnap/cv/model_registry.py` records model name, version, filename, license, source, and declared SHA-256 metadata. YuNet and SFace are loaded by the paths in application settings:

- `yunet_model_path`: `./models/face_detection_yunet_2023mar.onnx`
- `sface_model_path`: `./models/face_recognition_sface_2021dec.onnx`

The startup validation checks that a model file exists, is readable, and is larger than 1000 bytes. The known registry entries provide provenance and version metadata, but the current validator does not yet compare the file's actual SHA-256 with `expected_sha256`.

The repository also includes `scripts/download_models.py`. It downloads the two official model files and prints calculated hashes, but it does not currently enforce those download hashes after download. The declaration also differs between the registry and download script, so a future integrity implementation should verify one consistently maintained hash for each file rather than comparing conflicting constants.

## 7. Relevant Source Files

- [model_registry.py](../classsnap/cv/model_registry.py): model metadata and basic file validation
- [detector.py](../classsnap/cv/detector.py): YuNet wrapper
- [quality.py](../classsnap/cv/quality.py): face quality heuristics
- [aligner.py](../classsnap/cv/aligner.py): five-landmark alignment
- [embedder.py](../classsnap/cv/embedder.py): SFace embedding extraction
- [engine.py](../classsnap/cv/engine.py): end-to-end CV orchestration
- [tiler.py](../classsnap/cv/tiler.py): tiled detection
- [deduplication.py](../classsnap/cv/deduplication.py): duplicate box suppression
- [matching_service.py](../classsnap/services/matching_service.py): cosine matching and uncertainty rules
- [enrollment_service.py](../classsnap/services/enrollment_service.py): consented enrollment workflow
- [download_models.py](../scripts/download_models.py): model acquisition script

## Privacy and Operational Notes

- Enrollment should occur only with explicit consent.
- Face embeddings are sensitive biometric-derived data.
- Store only the minimum required template and preview data.
- Do not use model-specific vectors from another model version for comparison.
- Keep the model and threshold configuration reproducible for evaluation and audit.
- Attendance proposals are not final until a human reviewer approves the session.

## Getting the best results from classroom photos

Resolution is the largest single factor. A face 48 px wide scores about 0.88 against its own
template; at 16 px it scores about 0.44, close to the acceptance line. Messaging apps typically
resize photos to 1280 px, which shrinks every face about 3x. Upload the original camera file
(for example, send it as a document or upload it directly) so back-row faces stay recognisable.
Enroll every student with a clear frontal portrait; one student enrolled from a bad crop can
never be matched reliably.
