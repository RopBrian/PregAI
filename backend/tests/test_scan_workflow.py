from types import SimpleNamespace

import numpy as np

from backend.database import crud


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_upload_rejects_non_image_file(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/analysis/upload",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_upload_returns_disabled_when_ml_is_off(authenticated_client, monkeypatch):
    from backend.api.routes import analysis

    monkeypatch.setattr(analysis.settings, "enable_ml_analysis", False)

    response = authenticated_client.post(
        "/api/v1/analysis/upload",
        files={"file": ("scan.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()


def test_upload_valid_scan_returns_prediction_context(authenticated_client, monkeypatch, session_id):
    class FakeAnalyzer:
        def analyze(self, image_bytes):
            return {
                "status": "success",
                "module_a": {"prediction": "Valid Brain", "confidence": 98.2},
                "module_b": {"prediction": "Normal", "confidence": 91.5},
                "grad_cam_overlay": np.zeros((8, 8, 3), dtype=np.uint8),
            }

    created_image = SimpleNamespace(
        image_id=101,
        user_id=1,
        file_path="backend/static/uploads/fake.png",
        original_filename="scan.png",
        format="png",
        metadata_json={"scan_name": "Week 24 scan"},
    )
    created_prediction = SimpleNamespace(prediction_id=501)
    created_session = SimpleNamespace(session_id=session_id, user_id=1)

    from backend.api.routes import analysis

    monkeypatch.setattr(analysis.settings, "enable_ml_analysis", True)
    monkeypatch.setattr(analysis, "_get_analyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr(analysis.cv2, "imdecode", lambda buffer, flags: np.zeros((8, 8, 3), dtype=np.uint8))
    monkeypatch.setattr(analysis.cv2, "imwrite", lambda path, image: True)
    monkeypatch.setattr(crud, "get_conversation_session", lambda db, sid: created_session if sid else None)
    monkeypatch.setattr(crud, "create_conversation_session", lambda db, user_id, title: created_session)
    monkeypatch.setattr(crud, "create_image", lambda **kwargs: created_image)
    monkeypatch.setattr(crud, "create_prediction", lambda **kwargs: created_prediction)
    monkeypatch.setattr(crud, "create_chat_message", lambda **kwargs: None)
    monkeypatch.setattr(crud, "create_system_log", lambda **kwargs: None)

    response = authenticated_client.post(
        "/api/v1/analysis/upload",
        data={"scan_name": "Week 24 scan", "session_id": str(session_id)},
        files={"file": ("scan.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["module_a"]["prediction"] == "Valid Brain"
    assert data["module_b"]["prediction"] == "Normal"
    assert data["ml_context"]["classification"] == "Normal"
    assert data["ml_context"]["prediction_id"] == 501
    assert data["session_id"] == str(session_id)


def test_upload_invalid_scan_does_not_return_module_b(authenticated_client, monkeypatch, session_id):
    class FakeAnalyzer:
        def analyze(self, image_bytes):
            return {
                "status": "invalid_image",
                "message": "The uploaded file is not a valid fetal brain scan.",
                "module_a": {"prediction": "Non-Ultrasound", "confidence": 96.0},
            }

    created_image = SimpleNamespace(
        image_id=102,
        user_id=1,
        file_path="backend/static/uploads/fake.png",
        original_filename="scan.png",
        format="png",
        metadata_json={"scan_name": "Wrong image"},
    )
    created_session = SimpleNamespace(session_id=session_id, user_id=1)

    from backend.api.routes import analysis

    monkeypatch.setattr(analysis.settings, "enable_ml_analysis", True)
    monkeypatch.setattr(analysis, "_get_analyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr(analysis.cv2, "imdecode", lambda buffer, flags: np.zeros((8, 8, 3), dtype=np.uint8))
    monkeypatch.setattr(analysis.cv2, "imwrite", lambda path, image: True)
    monkeypatch.setattr(crud, "get_conversation_session", lambda db, sid: created_session if sid else None)
    monkeypatch.setattr(crud, "create_conversation_session", lambda db, user_id, title: created_session)
    monkeypatch.setattr(crud, "create_image", lambda **kwargs: created_image)
    monkeypatch.setattr(crud, "create_chat_message", lambda **kwargs: None)
    monkeypatch.setattr(crud, "create_system_log", lambda **kwargs: None)

    response = authenticated_client.post(
        "/api/v1/analysis/upload",
        data={"scan_name": "Wrong image", "session_id": str(session_id)},
        files={"file": ("scan.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid_image"
    assert data["module_b"] is None
    assert data["grad_cam_url"] is None


def test_delete_scan_rejects_foreign_scan(authenticated_client, monkeypatch):
    class FakeQuery:
        def filter(self, *args):
            return self

        def first(self):
            return None

    class FakeDB:
        def query(self, model):
            return FakeQuery()

    from backend.api.main import app
    from backend.database.database import get_db

    def override_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = override_db

    response = authenticated_client.delete("/api/v1/analysis/scan/999")

    assert response.status_code == 404
