import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app, get_cors_origins, DEFAULT_DEV_ORIGINS

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "windcast-analytics-backend"
    assert "version" in data
    assert "timestamp" in data


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_cors_origins_defaults_when_unset():
    with patch.dict(os.environ, {}, clear=True):
        origins = get_cors_origins()
        assert origins == DEFAULT_DEV_ORIGINS
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins


def test_cors_origins_custom_comma_separated():
    custom = "https://windcast-frontend.vercel.app, https://custom-domain.com , "
    with patch.dict(os.environ, {"CORS_ORIGINS": custom}, clear=True):
        origins = get_cors_origins()
        assert origins == ["https://windcast-frontend.vercel.app", "https://custom-domain.com"]


def test_cors_preflight_headers_allowed_origin():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
