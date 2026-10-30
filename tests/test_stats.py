import io
import json
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from estadisticas.app import services


@pytest.mark.parametrize("emails, expected", [
    ([], {"total_users": 0, "unique_domains": 0, "users_by_domain": {}}),
    (
        ["ana@EXAMPLE.com", "luis@example.com", "eva@example.org"],
        {"total_users": 3, "unique_domains": 2,
         "users_by_domain": {"example.com": 2, "example.org": 1}},
    ),
])
def test_summary_counts_users_and_normalizes_domains(emails, expected):
    assert services.summarize_users(emails) == expected


@pytest.mark.parametrize("total", [0, 2, 100, 105, 200])
def test_fetch_reads_all_pages(monkeypatch, total):
    records = [{"email": f"usuario{i}@example.com"} for i in range(total)]
    offsets = []

    def fake_urlopen(request, timeout):
        url = urlsplit(request.full_url)
        assert url.netloc == "usuarios.test:8000"
        assert url.path == "/users/"
        assert 0 < timeout <= 5
        params = parse_qs(url.query)
        skip, limit = int(params["skip"][0]), int(params["limit"][0])
        offsets.append(skip)
        return io.BytesIO(json.dumps(records[skip:skip + limit]).encode())

    monkeypatch.setattr(services, "urlopen", fake_urlopen)
    assert services.fetch_user_emails() == [record["email"] for record in records]
    assert offsets == list(range(0, total + 1, 100))


@pytest.mark.parametrize("route", ["/health", "/info"])
def test_stats_metadata_does_not_require_users(stats_client, route):
    response = stats_client.get(route)
    assert response.status_code == 200
    assert response.json()["service"] == "Microservicio de Estadisticas"


def test_stats_endpoint_returns_aggregates_only(stats_client, monkeypatch):
    users = [
        {"name": "Ana", "email": "ana@example.com"},
        {"name": "Luis", "email": "luis@example.org"},
    ]
    monkeypatch.setattr(
        services, "urlopen",
        lambda *args, **kwargs: io.BytesIO(json.dumps(users).encode()),
    )
    response = stats_client.get("/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total_users": 2, "unique_domains": 2,
        "users_by_domain": {"example.com": 1, "example.org": 1},
    }
    assert "ana@example.com" not in response.text


def test_stats_endpoint_with_no_users(stats_client, monkeypatch):
    monkeypatch.setattr(
        services, "urlopen",
        lambda *args, **kwargs: io.BytesIO(b"[]"),
    )
    assert stats_client.get("/stats").json() == {
        "total_users": 0, "unique_domains": 0, "users_by_domain": {},
    }


@pytest.mark.parametrize("payload", [
    {}, None, [None], [{"name": "Sin correo"}], [{"email": None}],
    [{"email": 123}], [{"email": "invalido"}], [{"email": "a@@example.com"}],
    [{"email": "@example.com"}], [{"email": "ana@"}],
    [{"email": "ana@example.com"}] * 101,
])
def test_invalid_upstream_payload_returns_503(stats_client, monkeypatch, payload):
    monkeypatch.setattr(
        services, "urlopen",
        lambda *args, **kwargs: io.BytesIO(json.dumps(payload).encode()),
    )
    assert stats_client.get("/stats").status_code == 503


@pytest.mark.parametrize("body", [b"not json", b"\xff"])
def test_malformed_upstream_json_returns_503(stats_client, monkeypatch, body):
    monkeypatch.setattr(
        services, "urlopen", lambda *args, **kwargs: io.BytesIO(body),
    )
    assert stats_client.get("/stats").status_code == 503


@pytest.mark.parametrize("error", [
    URLError("sin conexion"), TimeoutError("tiempo agotado"),
    HTTPError("http://usuarios.test/users/", 500, "error interno", {}, None),
])
def test_upstream_failure_returns_503(stats_client, monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(services, "urlopen", fail)
    response = stats_client.get("/stats")
    assert response.status_code == 503
    assert response.json() == {
        "detail": "No se pudieron consultar los datos del servicio de usuarios",
    }
    assert stats_client.get("/health").status_code == 200


def test_later_page_failure_does_not_return_partial_totals(stats_client, monkeypatch):
    calls = []

    def fail_on_second_page(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            return io.BytesIO(json.dumps([{"email": "ana@example.com"}] * 100).encode())
        raise URLError("segunda pagina no disponible")

    monkeypatch.setattr(services, "urlopen", fail_on_second_page)
    response = stats_client.get("/stats")
    assert len(calls) == 2
    assert response.status_code == 503
    assert "total_users" not in response.json()
