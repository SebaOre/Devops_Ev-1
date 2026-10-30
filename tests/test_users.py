import pytest


def create_user(client, name="Ana", email="ana@example.com"):
    response = client.post("/users/", json={"name": name, "email": email})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("route", ["/health", "/info"])
def test_service_metadata(users_client, route):
    response = users_client.get(route)
    assert response.status_code == 200
    assert response.json()["service"] == "Microservicio de Usuarios"
    assert response.json()["status"] in ("ok", "running")


@pytest.mark.parametrize("route", ["/", "/static/index.html"])
def test_frontend_is_served(users_client, route):
    response = users_client.get(route)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Microservicio de Usuarios" in response.text


def test_user_lifecycle(users_client):
    assert users_client.get("/users/").json() == []
    user = create_user(users_client)
    route = f"/users/{user['id']}"
    assert user["created_at"]
    assert user["updated_at"]
    assert users_client.get(route).json() == user
    assert users_client.get("/users/").json() == [user]

    response = users_client.put(route, json={"name": "Ana Maria"})
    assert response.status_code == 200
    assert response.json()["name"] == "Ana Maria"
    assert response.json()["email"] == "ana@example.com"

    response = users_client.put(route, json={"email": "ana.nueva@example.org"})
    assert response.status_code == 200
    assert response.json()["email"] == "ana.nueva@example.org"
    assert response.json()["name"] == "Ana Maria"

    response = users_client.delete(route)
    assert response.status_code == 204
    assert response.content == b""
    assert users_client.get(route).status_code == 404
    assert users_client.get("/users/").json() == []


def test_user_pagination(users_client):
    users = [
        create_user(users_client, f"Usuario {i}", f"usuario{i}@example.com")
        for i in range(3)
    ]
    response = users_client.get("/users/", params={"skip": 1, "limit": 1})
    assert response.status_code == 200
    assert response.json() == [users[1]]
    assert users_client.get("/users/", params={"skip": 3}).json() == []


def test_duplicate_email_on_creation(users_client):
    original = create_user(users_client)
    response = users_client.post(
        "/users/", json={"name": "Otra persona", "email": original["email"]}
    )
    assert response.status_code == 400
    assert users_client.get("/users/").json() == [original]


def test_duplicate_email_on_update_does_not_modify_users(users_client):
    first = create_user(users_client)
    second = create_user(users_client, "Luis", "luis@example.org")
    response = users_client.put(
        f"/users/{second['id']}",
        json={"name": "Cambio rechazado", "email": first["email"]},
    )
    assert response.status_code == 400
    assert users_client.get(f"/users/{first['id']}").json() == first
    assert users_client.get(f"/users/{second['id']}").json() == second


def test_updating_with_own_email_is_allowed(users_client):
    user = create_user(users_client)
    response = users_client.put(f"/users/{user['id']}", json={"email": user["email"]})
    assert response.status_code == 200
    assert response.json()["email"] == user["email"]


def test_empty_update_preserves_user(users_client):
    user = create_user(users_client)
    response = users_client.put(f"/users/{user['id']}", json={})
    assert response.status_code == 200
    assert response.json()["name"] == user["name"]
    assert response.json()["email"] == user["email"]


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_user(users_client, method):
    kwargs = {"json": {"name": "Inexistente"}} if method == "put" else {}
    response = getattr(users_client, method)("/users/9999", **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado"


@pytest.mark.parametrize("payload", [
    {}, {"name": "Ana"}, {"email": "ana@example.com"},
    {"name": "Ana", "email": "correo-invalido"},
])
def test_invalid_creation_is_rejected(users_client, payload):
    assert users_client.post("/users/", json=payload).status_code == 422
    assert users_client.get("/users/").json() == []


def test_non_numeric_id_is_rejected(users_client):
    assert users_client.get("/users/no-es-un-id").status_code == 422


def test_invalid_email_update_preserves_original(users_client):
    user = create_user(users_client)
    route = f"/users/{user['id']}"
    assert users_client.put(route, json={"email": "invalido"}).status_code == 422
    assert users_client.get(route).json() == user


@pytest.mark.parametrize("field", ["name", "email"])
def test_null_update_is_rejected_without_modifying_user(users_client, field):
    user = create_user(users_client)
    route = f"/users/{user['id']}"
    assert users_client.put(route, json={field: None}).status_code == 422
    assert users_client.get(route).json() == user
