from types import SimpleNamespace

import pytest

from backend.chatbot.safety_layer import SafetyLayer
from backend.database import crud


def test_safety_layer_blocks_reported_emergency():
    safety = SafetyLayer()

    assert safety.detect_emergency("I am bleeding heavily and have severe pain") == "emergency_query"
    is_safe, category = safety.check_medical_safety("I am bleeding", "emergency_query")
    assert is_safe is False
    assert category == "emergency_query"


def test_safety_layer_allows_educational_emergency_context():
    safety = SafetyLayer()

    assert safety.detect_emergency("Can you explain how seizures affect fetal brain development?") is None


def test_safety_layer_rejects_unsafe_output():
    safety = SafetyLayer()

    assert safety.validate_output("You should take this medicine twice daily.") is False
    assert safety.validate_output("Please discuss symptoms with a qualified healthcare provider.") is True


def test_chat_endpoint_returns_session_and_intent(authenticated_client, monkeypatch, session_id):
    class FakeOrchestrator:
        async def chat(self, user_id, db, message, session_id=None, ml_context=None):
            return "Educational response", "general_pregnancy_education", 0.91, session_id or globals_session_id

    globals_session_id = session_id

    from backend.chatbot import orchestrator

    monkeypatch.setattr(orchestrator, "get_orchestrator", lambda: FakeOrchestrator())

    response = authenticated_client.post(
        "/api/v1/chat/",
        json={"message": "What foods are helpful during pregnancy?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["intent"] == "general_pregnancy_education"
    assert data["session_id"] == str(session_id)


def test_chat_session_messages_are_owner_protected(authenticated_client, monkeypatch, session_id):
    foreign_session = SimpleNamespace(session_id=session_id, user_id=999)

    monkeypatch.setattr(crud, "get_conversation_session", lambda db, requested_id: foreign_session)

    response = authenticated_client.get(f"/api/v1/chat/sessions/{session_id}/messages")

    assert response.status_code == 403


def test_user_can_rename_own_chat_session(authenticated_client, monkeypatch, session_id):
    own_session = SimpleNamespace(session_id=session_id, user_id=1, title="Old title")

    monkeypatch.setattr(crud, "get_conversation_session", lambda db, requested_id: own_session)
    monkeypatch.setattr(
        crud,
        "update_session_title",
        lambda db, requested_id, title, is_custom=True: SimpleNamespace(
            session_id=requested_id,
            user_id=1,
            title=title,
            is_custom_title=is_custom,
        ),
    )

    response = authenticated_client.patch(
        f"/api/v1/chat/sessions/{session_id}",
        json={"title": "Appointment questions"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Appointment questions"
