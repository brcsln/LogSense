
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_upload_displays_correlated_events():
    log_data = (
        b"2026-07-18 10:14:00 WARNING [payment-service] Slow response\n"
        b"2026-07-18 10:15:00 ERROR [database] Connection timeout\n"
        b"2026-07-18 10:20:00 ERROR [checkout-service] Payment failed\n"
    )

    response = client.post(
        "/upload",
        files={
            "log_file": ("test.log", log_data, "text/plain")
        },
    )

    assert response.status_code == 200
    assert "Potentially Related Events" in response.text
    assert "Correlation Group 1" in response.text
    assert "Connection timeout" in response.text
