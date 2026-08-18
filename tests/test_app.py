from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "Task Scheduler" in response.text


def test_submit_job_endpoint():
    payload = {
        "task": "send_email",
        "kwargs": {"to": "user@example.com", "subject": "Welcome"},
    }

    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["task"] == "send_email"
    assert data["status"] == "pending"
    assert data["kwargs"]["to"] == "user@example.com"


def test_start_worker_endpoint():
    response = client.post("/api/worker/start")
    assert response.status_code == 200
    assert response.json()["status"] in {"started", "already_running"}
