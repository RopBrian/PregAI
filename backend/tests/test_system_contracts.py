from types import SimpleNamespace

from sqlalchemy import func

from backend.database import crud, models


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers.get("X-Request-ID")


def test_admin_logs_return_audit_entries(admin_client, monkeypatch):
    log = SimpleNamespace(
        log_id=1,
        timestamp=__import__("datetime").datetime.utcnow(),
        severity="info",
        log_type="AUTH",
        user=SimpleNamespace(username="mother_user"),
        log_message="User login successful",
        ip_address=None,
    )

    monkeypatch.setattr(crud, "get_system_logs", lambda db, limit=100: [log])

    response = admin_client.get("/api/v1/admin/logs")

    assert response.status_code == 200
    assert response.json()[0]["module"] == "AUTH"
    assert response.json()[0]["activity"] == "User login successful"


def test_admin_stats_returns_dashboard_counts(admin_client):
    class CountQuery:
        def __init__(self, value):
            self.value = value

        def filter(self, *args):
            return self

        def scalar(self):
            return self.value

    class StatsDB:
        def __init__(self):
            self.values = iter([3, 2, 1, 4, 0, 0])

        def query(self, expression):
            return CountQuery(next(self.values))

    from backend.api.main import app
    from backend.database.database import get_db

    def override_db():
        yield StatsDB()

    app.dependency_overrides[get_db] = override_db

    response = admin_client.get("/api/v1/admin/stats")

    assert response.status_code == 200
    assert response.json() == {
        "totalUsers": 3,
        "activeAlerts": 0,
        "systemStatus": "Optimal",
        "scansToday": 1,
        "totalScans": 2,
        "validatedToday": 4,
        "validatedTotal": 0,
        "rejectedToday": 0,
        "rejectedTotal": 2,
        "predictionsToday": 4,
        "totalPredictions": 0,
    }
