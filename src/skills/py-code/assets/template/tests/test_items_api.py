from __future__ import annotations

import msgspec
import pytest
from litestar.testing import TestClient

H = {"x-internal-service-token": "tok"}


@pytest.mark.parametrize(
    ("name", "method", "path", "kwargs", "status", "code"),
    [
        (
            "no token",
            "post",
            "/v1/items",
            {"json": {"name": "pen"}},
            401,
            "unauthorized",
        ),
        (
            "wrong token",
            "post",
            "/v1/items",
            {
                "json": {"name": "pen"},
                "headers": {"x-internal-service-token": "x"},
            },
            401,
            "unauthorized",
        ),
        (
            "created",
            "post",
            "/v1/items",
            {"json": {"name": "pen"}, "headers": H},
            201,
            None,
        ),
        (
            "blank name",
            "post",
            "/v1/items",
            {"json": {"name": "  "}, "headers": H},
            422,
            "validation_error",
        ),
        (
            "bad body",
            "post",
            "/v1/items",
            {
                "content": b"{",
                "headers": {**H, "content-type": "application/json"},
            },
            400,
            "invalid_request",
        ),
        ("missing", "get", "/v1/items/nope", {"headers": H}, 404, "not_found"),
        ("unknown route", "get", "/nope", {}, 404, None),
    ],
)
def test_items_api(client, name, method, path, kwargs, status, code):
    res = getattr(client, method)(path, **kwargs)
    assert res.status_code == status, (name, res.text)
    body = res.json()
    if res.status_code != 404 or code:  # unknown routes use the framework 404
        assert {"success", "data", "error", "message"} <= set(body)
    if code:
        assert body["error"]["code"] == code


def test_create_then_get_and_event(client, events):
    created = client.post(
        "/v1/items", json={"name": " pen "}, headers=H
    ).json()
    assert created["success"] and created["data"]["name"] == "pen"
    got = client.get("/v1/items/id-1", headers=H).json()
    assert got["data"]["created_at"].startswith("2026-01-02T03:04:05")
    topic, key, value = events.published[0]
    assert (topic, key) == ("items.created", "id-1")
    assert msgspec.json.decode(value) == {"id": "id-1", "name": "pen"}


HEALTHZ_FIELDS = {
    "status",
    "service_name",
    "env_name",
    "node_name",
    "api_versions",
    "service_version",
    "started_at",
    "checked_at",
    "uptime_seconds",
    "config",
    "checks",
}


def test_healthz_is_open_and_names_the_service(client):
    res = client.get("/healthz")
    body = res.json()
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"
    assert set(body) == HEALTHZ_FIELDS
    assert body["status"] == "ok"
    assert body["service_name"] == "svc"
    assert body["env_name"] == "local"
    assert body["api_versions"] == ["v1"]
    assert body["config"]["port"] == 3000
    assert body["config"]["docs_url"] == "/docs"
    assert body["checks"] == []


def test_healthz_reports_a_down_dependency_without_leaking(client):
    async def down():
        raise RuntimeError("connection refused: postgres://u:secret@pg")

    client.app.state.checks = {"postgres": down, "redis": _up}
    res = client.get("/healthz")
    body = res.json()
    assert res.status_code == 503
    assert body["status"] == "down"
    by_name = {c["name"]: c for c in body["checks"]}
    assert by_name["postgres"]["status"] == "down"
    assert by_name["postgres"]["error"] == "unavailable"
    assert by_name["redis"]["status"] == "ok"
    assert "secret" not in res.text


async def _up():
    return None


def test_healthz_lists_every_version(client, monkeypatch):
    from service.api.routes import health

    monkeypatch.setattr(health, "API_VERSIONS", ("v1", "v2"))
    assert client.get("/healthz").json()["api_versions"] == ["v1", "v2"]


def test_healthz_is_not_versioned(client):
    assert client.get("/v1/healthz").status_code == 404
    assert client.get("/readyz").status_code == 404


def test_internal_needs_the_token(client):
    assert client.get("/internal").status_code == 401
    bad = client.get("/internal", headers={"x-internal-service-token": "no"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "unauthorized"


def test_internal_shows_health_and_the_caller(client):
    res = client.get(
        "/internal", headers={**H, "x-user-id": "u-7", "x-username": "linh"}
    )
    body = res.json()
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"
    assert set(body) == HEALTHZ_FIELDS | {"caller"}
    assert body["status"] == "ok"
    assert body["caller"] == {"user_id": "u-7", "username": "linh"}


def test_internal_caller_is_empty_without_identity_headers(client):
    assert client.get("/internal", headers=H).json()["caller"] == {
        "user_id": "",
        "username": "",
    }


def test_token_may_carry_a_bearer_prefix(client):
    for value in ("Bearer tok", "bearer tok", "  Bearer   tok "):
        res = client.get(
            "/internal", headers={"x-internal-service-token": value}
        )
        assert res.status_code == 200, value
    res = client.get(
        "/v1/items/x", headers={"x-internal-service-token": "Bearer tok"}
    )
    assert res.status_code != 401


def test_internal_reports_a_down_dependency(client):
    async def down():
        raise RuntimeError("boom postgres://u:secret@pg")

    client.app.state.checks = {"postgres": down}
    res = client.get("/internal", headers=H)
    assert res.status_code == 503
    assert res.json()["status"] == "down"
    assert "secret" not in res.text


def test_swagger_docs_cover_every_route(client):
    page = client.get("/docs")
    spec = client.get("/docs/openapi.json").json()
    assert page.status_code == 200 and "swagger" in page.text.lower()
    assert {
        "/v1/items",
        "/v1/items/{item_id}",
        "/healthz",
        "/internal",
    } <= set(spec["paths"])


def test_unhandled_error_is_generic_500(client, events):
    async def boom(*_):
        raise RuntimeError("postgres://u:secret@pg failed")

    client.app.state.use_cases.events.publish = boom
    res = TestClient(client.app, raise_server_exceptions=False).post(
        "/v1/items", json={"name": "pen"}, headers=H
    )
    assert (
        res.status_code == 500
        and res.json()["error"]["code"] == "internal_error"
    )
    assert "secret" not in res.text
