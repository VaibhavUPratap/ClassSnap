# ClassSnap Real-World Classroom Image Verification Report

**Audit date:** 2026-11-22  
**Photograph:** `/Users/vaibhav/Documents/Projects/ClassSnap/uploads/class_photos/WhatsApp Image 2026-11-22 at 11.52.15.jpeg`  
**Test database:** `/tmp/classsnap_real_photo_verification.db` (separate from official database)

## 1. Executive summary

- **Photograph processed successfully:** PASS.
- **Baseline full-image detections:** 44.
- **Baseline raw tiled detections:** 44.
- **Baseline unique/deduplicated detections:** 44.
- **Post-fix integrated detections:** 23 usable embeddings.
- **Baseline low-quality detections:** 21 candidates below 24 px minimum dimension.
- **Recognition:** 4 matched-pending-review proposals and 19 unknown proposals among 23 usable detections. These are not independently verified identities.
- **Attendance workflow:** PASS in an isolated test database through processing, human-review marking, confirmation, CSV export, and XLSX export.
- **Deployment readiness:** **Controlled pilot only**, pending ground-truth annotation and independent identity verification.

## 2. Test photograph metadata

| Property | Value |
|---|---|
| Exists/readable | Yes |
| Original SHA-256 | `6d875a8890010df4a485815309386711917a781a329e334adada39ca43cac8eb` |
| File size | 160,616 bytes |
| Format | JPEG, progressive |
| Dimensions | 1280 × 960 pixels |
| Channels | 3 (BGR decoded) |
| dtype | uint8 |
| EXIF orientation | Not present (no correction needed for this exact file) |
| Decode | PASS |
| Original overwritten | No |

## 3. Repository and implementation audit

- Backend: FastAPI/uvicorn, database status connected.
- Frontend: React/Vite production build, served through `/review/`.
- Detection: OpenCV `cv2.FaceDetectorYN` loading YuNet.
- Recognition: OpenCV `cv2.FaceRecognizerSF` loading SFace.
- YuNet model: 232,589 bytes, SHA-256 `8f2383e4dd3cfbb4553ea871810fc0423210dc964f9f4280604804ed2552fa4` (verified model registry value).
- SFace model: 38,696,353 bytes, SHA-256 `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79`.
- Active official roster at audit start: 9 students.
- Compatible enrolled face templates: 9.
- Tiled detector: implemented and integrated with full-image pass, overlapping tiles, coordinate transformation, NMS, and classroom sorting.
- Matching: cosine similarity, 0.38 accept threshold, 0.06 ambiguity gap, and one-to-one conflict resolution.
- The exact-photo API and standalone pipeline are real model executions, not mock detections.

## 4. Model and dependency verification

| Component | Result |
|---|---|
| Python | 3.14.6 |
| OpenCV | 5.0.0 |
| NumPy | 2.5.1 |
| FastAPI | 0.162.7 |
| SQLAlchemy | 2.1.6 |
| YuNet API | Available and loaded |
| SFace API | Available and loaded |
| 128-D embeddings | Verified by model and tests |

## 5. Full-image detection results

Baseline full-image detector score threshold: 0.40.  
Full-image detections: **44**.  
Post-fix detector threshold: **0.65**.  
Post-fix integrated candidate list: **23 usable detections** after the shared quality-floor and deduplication pass.

No ground-truth annotation was available, so precision/recall/F1 cannot be calculated honestly.

## 6. Tiled detection results

Raw tiled pass baseline: **44 detections**.  
The isolated baseline full and tiled counts were identical, indicating that for this image the tiled pass did not add new unique candidates beyond the full-image pass after deduplication.

Tile implementation details:
- Configured tile size: 640 px.
- Configured overlap: 25%.
- Coordinate transformation and tile-origin metadata: implemented.
- Post-fix integrated processing used tiling, threshold 0.65, and the quality floor.

## 7. Duplicate detection analysis

Baseline 44 detections did not reduce in the baseline NMS result, indicating excessive candidates were not properly separated as duplicates and require human/ground-truth review. Post-fix filtering removed 21 sub-24 px candidates, but duplicate/false-face risk remains for small, dense detections.

## 8. Face-quality analysis

Baseline final quality distribution:
- 23 usable.
- 21 low-quality candidates below 24 px minimum dimension.
- 23 embeddings extracted baseline.
- 21 low-quality candidates would not be suitable for reliable recognition.

Post-fix result:
- 23 candidates retained.
- 23 usable.
- 23 embeddings extracted.
- 0 low-quality candidates in the returned integrated result.

## 9. Recognition results

Recognition ran against 9 compatible official enrolled templates using SFace 2021dec and the existing 0.38/0.06 thresholds.

Post-fix result:
- 4 `MATCHED_PENDING_REVIEW` proposals.
- 19 `UNKNOWN` proposals.
- 0 low-quality proposals.

These matches are **preliminary system proposals only**. No independent identity ground truth was available; no names were verified as correct.

## 10. Attendance logic results

An isolated SQLite database copied the roster/templates but did not modify the official database.

- Exact-photo API upload: PASS.
- Processing session: PASS.
- 23 detection proposals retrieved by detail API.
- Repeated upload: PASS rejection (HTTP 422) with no duplicate proposals.
- Corrupt upload: PASS rejection (HTTP 422).
- Blank image: PASS processing with `review_required` and zero detections.
- Review: PASS in isolated database.
- Confirmation: PASS.
- CSV export: PASS, HTTP 200, 975 bytes.
- XLSX export: PASS, HTTP 200, 5,258 bytes.

## 11. Backend and frontend verification

- Backend health: PASS.
- Frontend route: PASS.
- API exact-image upload: PASS.
- Detection retrieval: PASS.
- Review interface: PASS architecture, but no browser review interaction was executed against the exact-photo session after the isolated test.
- Confirmation/export: PASS.
- Official attendance records: unchanged.

## 12. Performance measurements

| Metric | Measured |
|---|---:|
| Full-image detection baseline | 18.20 ms |
| Tiled detection baseline | 54.79 ms |
| Baseline embedding extraction total | 180.68 ms |
| Baseline embedding extraction mean | 4.11 ms |
| Post-fix integrated processing | 183.45 ms |

Machine: macOS, CPU count 12, OpenCV 5.0.0, Python 3.14.6. Peak memory was not reliably isolated because the process was shared with the editor; it is therefore not reported.

## 13. Automated test results

- Baseline: 83 passed, 2 skipped.
- Post-fix: 84 passed, 2 skipped.
- Frontend production build: PASS.
- Python compilation: PASS.
- Route smoke tests: PASS.
- Playwright desktop/mobile checks: PASS for application UI layout earlier in this session.

## 14. Defects identified

### DEF-001 — HIGH, fixed
API hardcoded 0.40 instead of the configured 0.65 detector threshold.  
**Fix:** processing API now passes 0.65.

### DEF-002 — MEDIUM, fixed
Sub-resolution detections reached the proposal pipeline.  
**Fix:** CVEngine filters below 24 px and reruns NMS before embeddings/review.

### DEF-003 — MEDIUM, fixed
EXIF orientation was not corrected.  
**Fix:** Pillow `exif_transpose` added for path and byte ingestion.

### DEF-004 — MEDIUM, fixed
Pillow PNG decode initially lost alpha.  
**Fix:** preserve RGBA/BGRA and use existing white compositing.

### DEF-005 — MEDIUM, open
23 post-fix detections are not ground-truth verified; visual inspection alone is insufficient for precision/recall.

### DEF-006 — MEDIUM, open
Four matched-pending proposals are not identity-verified.

### DEF-007 — LOW, open
Reports are unavailable until attendance confirmation, by existing design.

## 15. Fixes implemented

- Processing endpoint uses score threshold 0.65.
- Integrated CV pipeline filters `<24 px` detections and re-runs NMS.
- Pillow-based EXIF orientation correction added.
- RGBA PNG decoding/compositing corrected.
- Pillow dependency declared in `requirements.txt` and `pyproject.toml`.
- Added EXIF orientation regression test.

## 16. Baseline versus post-fix comparison

| Metric | Baseline | Post-fix |
|---|---:|---:|
| Full/tiled/final candidates | 44/44/44 | 23 returned candidates |
| Low-quality candidates | 21 | 0 |
| Embeddings | 23 | 23 |
| Unknown | 19 | 19 |
| Matched pending review | 4 | 4 |

The reduction is not an accuracy claim. It is evidence of removing sub-resolution candidates under the existing quality policy.

## 17. Outstanding limitations

- No manually labeled ground-truth faces or identities.
- Precision, recall, F1, present recall, attendance precision, false-present and false-absent metrics cannot be calculated honestly.
- The image appears to contain seated people, but visual false-positive/identity review still requires a human labeled audit.
- Database outage and failed-model-load injections were not executed.
- Missing-enrollment scenario was not separately injected.
- Recognition threshold calibration is not derived from this real photo; 0.38/0.06 remain existing product thresholds.

## 18. Final deployment-readiness assessment

**Conditionally ready for a controlled classroom pilot, not a broad production deployment.**

Recommended before pilot expansion:
1. Human-annotate at least this exact photograph with visible-face bounding boxes and unknown identities.
2. Generate a labeled genuine/impostor embedding set and validate acceptance and ambiguity thresholds.
3. Pilot under similar distance/resolution conditions and retain human review for every proposed identity.
4. Inject database outage and model-load failure scenarios.
5. Confirm the blank-image/session behavior matches institutional policy.

## Visual evidence

- [Full-image detections](classroom_image_test_results/full_image_detection.jpg)
- [Tiled detections](classroom_image_test_results/tiled_detection.jpg)
- [Final deduplicated detections](classroom_image_test_results/final_deduplicated_detection.jpg)
- [Post-fix final detections](classroom_image_test_results/post_fix_final_deduplicated_detection.jpg)
- [Four-panel comparison](classroom_image_test_results/detection_comparison.jpg)
- [Aligned face crops](classroom_image_test_results/)

## Machine-readable results

- [JSON results](classroom_image_verification_results.json)
