import pytest
from fastapi.testclient import TestClient

from app.api import app, reset_orders


@pytest.fixture()
def client():
    reset_orders()
    return TestClient(app)


def test_get_pedido(client):
    r = client.get("/orders/O001")
    assert r.status_code == 200
    assert r.json()["units"] == 4


def test_pedido_inexistente_404(client):
    assert client.post("/orders/NOEXISTE/confirm").status_code == 404


def test_confirmar_ok(client):
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMED"


def test_confirmar_dos_veces_409(client):
    client.post("/orders/O013/confirm")
    assert client.post("/orders/O013/confirm").status_code == 409


def test_confirmar_vacio_422(client):
    assert client.post("/orders/O007/confirm").status_code == 422


def test_enviar_sin_guia_422(client):
    client.post("/orders/O012/confirm")
    r = client.post("/orders/O012/ship", json={"tracking_number": ""})
    assert r.status_code == 422


def test_cancelar_desde_shipped_409(client):
    client.post("/orders/O014/confirm")
    client.post("/orders/O014/ship", json={"tracking_number": "G1"})
    r = client.post("/orders/O014/cancel", json={"reason": "tarde"})
    assert r.status_code == 409
