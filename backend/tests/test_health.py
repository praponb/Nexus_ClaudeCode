import pytest

pytest.importorskip("django")
pytest.importorskip("rest_framework")


def test_liveness_is_public(api_client):
    response = api_client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_reports_ready(api_client):
    response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
