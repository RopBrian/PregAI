import os

import pytest

from backend.chatbot.image_analyzer import ImageAnalyzer
from backend.config.settings import settings


@pytest.mark.parametrize(
    ("model_version", "expected_module_a", "expected_module_b"),
    [
        ("v1", "module_a_3class_enhanced.pth", "abnormal_classifier.pth"),
        ("v2", "module_a_3class_enhanced_v2.pth", "abnormal_classifier_v2.pth"),
        (
            "v3",
            "module_a_3class_leakage_checked.pth",
            "abnormal_classifier_leakage_checked.pth",
        ),
        (
            "leakage_checked",
            "module_a_3class_leakage_checked.pth",
            "abnormal_classifier_leakage_checked.pth",
        ),
        (
            "leakage-check",
            "module_a_3class_leakage_checked.pth",
            "abnormal_classifier_leakage_checked.pth",
        ),
    ],
)
def test_image_analyzer_uses_configured_model_version(
    monkeypatch,
    model_version,
    expected_module_a,
    expected_module_b,
):
    monkeypatch.setattr(settings, "ml_model_version", model_version)

    analyzer = ImageAnalyzer()

    assert analyzer.model_version in {"v1", "v2", "v3", "leakage_checked"}
    assert os.path.basename(analyzer.path_a) == expected_module_a
    assert os.path.basename(analyzer.path_b) == expected_module_b


def test_image_analyzer_rejects_unknown_model_version(monkeypatch):
    monkeypatch.setattr(settings, "ml_model_version", "unknown")

    with pytest.raises(ValueError, match="Unsupported ML_MODEL_VERSION"):
        ImageAnalyzer()
