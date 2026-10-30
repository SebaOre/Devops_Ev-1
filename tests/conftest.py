import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Se establece antes de importar la aplicacion para no abrir la base local.
os.environ["DATABASE_URL"] = "sqlite://"

from backend.app import database
from backend.app.main import app as users_app
from estadisticas.app import services
from estadisticas.app.main import app as stats_app


@pytest.fixture
def users_client(monkeypatch):
    """Cada prueba obtiene una base SQLite independiente en memoria."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    try:
        with TestClient(users_app) as client:
            yield client
    finally:
        engine.dispose()


@pytest.fixture
def stats_client():
    with TestClient(stats_app) as client:
        yield client


@pytest.fixture(autouse=True)
def block_external_users_requests(monkeypatch):
    """Una prueba debe definir su respuesta simulada antes de consultar usuarios."""
    def unexpected_request(*args, **kwargs):
        raise AssertionError("La prueba intento consultar un servicio externo")

    monkeypatch.setattr(services, "urlopen", unexpected_request)
    monkeypatch.setattr(services, "USERS_SERVICE_URL", "http://usuarios.test:8000")
