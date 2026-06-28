"""Helpers for resolving generated media paths and URLs."""
import os
from typing import Any, Optional

RESULTS_DIR = os.path.join('backend', 'static', 'results')


def static_result_url(path: Optional[str]) -> Optional[str]:
    if not path or not os.path.exists(path):
        return None
    return f'/static/results/{os.path.basename(path)}'


def static_upload_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f'/static/uploads/{os.path.basename(path)}'


def find_gradcam_path(img: Optional[Any], pred: Optional[Any] = None) -> Optional[str]:
    candidates = []

    if pred and pred.gradcam_path:
        candidates.append(pred.gradcam_path)

    if img:
        metadata = img.metadata_json or {}
        for identifier in [
            metadata.get('result_uuid'),
            os.path.splitext(os.path.basename(img.file_path or ''))[0],
        ]:
            if identifier:
                candidates.append(os.path.join(RESULTS_DIR, f"{identifier}_gradcam.png"))

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    return None


def scan_result_url(img: Optional[Any], pred: Optional[Any] = None) -> Optional[str]:
    return static_result_url(find_gradcam_path(img, pred))
