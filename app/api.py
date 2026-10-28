"""API REST TechStore. Los controladores NO tienen reglas de negocio:
buscan el pedido, llaman a Order y traducen las excepciones a códigos HTTP."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cargar_csv import load_fixture
from app.domain import (
    InvalidOrderTransition, InvalidOrderData, OrderItemLimitExceeded, Order,
)
from app.specifications import discount_rate

app = FastAPI(title="TechStore U4")
orders = load_fixture()


def reset_orders():
    """Vuelve a cargar los pedidos desde los CSV (útil para pruebas)."""
    orders.clear()
    orders.update(load_fixture())


class ShipRequest(BaseModel):
    tracking_number: str


class CancelRequest(BaseModel):
    reason: str


def _get(order_id: str) -> Order:
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="No existe")
    return order


def _view(order: Order):
    return {
        "id": order.id,
        "status": order.status.value,
        "units": order.units,
        "total": str(order.total.amount),
        "discount_rate": str(discount_rate(order)),
        "events": [e.name for e in order.events],
    }


def _run(action):
    """Ejecuta una operación del dominio y traduce errores a HTTP."""
    try:
        action()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except OrderItemLimitExceeded as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    return _view(_get(order_id))


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = _get(order_id)
    _run(order.confirm)
    return _view(order)


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipRequest):
    order = _get(order_id)
    _run(lambda: order.ship(body.tracking_number))
    return _view(order)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelRequest):
    order = _get(order_id)
    _run(lambda: order.cancel(body.reason))
    return _view(order)
