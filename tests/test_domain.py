import pytest
from decimal import Decimal

from app.domain import (
    Money, OrderItem, Order, Customer, OrderStatus,
    InvalidOrderData, InvalidOrderTransition, OrderItemLimitExceeded,
)
from app.specifications import (
    ten_percent, five_percent, discount_rate, MinimumAmountSpec,
    VIPCustomerSpec, ActivePromotionSpec,
)
from cargar_csv import load_fixture


def item(qty=1, price="100.00", sku="SKU001"):
    return OrderItem(sku, qty, Money(Decimal(price)))


def nuevo_pedido(vip=False, active=True, promo=False):
    return Order(Customer("C", vip, active), "T1", has_promotion=promo)


# ---------- Value Objects ----------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


def test_money_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1"), "MXN").add(Money(Decimal("1"), "USD"))


def test_money_add_no_modifica_operandos():
    a, b = Money(Decimal("100")), Money(Decimal("50"))
    assert a.add(b).amount == Decimal("150")
    assert a.amount == Decimal("100")


def test_orderitem_cantidad_cero():
    with pytest.raises(InvalidOrderData):
        item(qty=0)


# ---------- Carga ----------
def test_o001_inicia_draft():
    o = load_fixture()["O001"]
    assert o.status == OrderStatus.DRAFT
    assert o.units == 4
    assert o.total.amount == Decimal("2100.00")


def test_se_cargan_16_pedidos():
    assert len(load_fixture()) == 16


# ---------- Límite de unidades ----------
def test_20_unidades_exactas_permitidas():
    o = nuevo_pedido()
    o.add_item(item(qty=20))
    assert o.units == 20


def test_21_unidades_rechazadas_y_no_modifica():
    o = nuevo_pedido()
    o.add_item(item(qty=19))
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(item(qty=2))
    assert o.units == 19


# ---------- Confirmación ----------
def test_pedido_vacio_no_se_confirma():
    o = nuevo_pedido()
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_cliente_inactivo_no_confirma():
    o = nuevo_pedido(active=False)
    o.add_item(item())
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.events == []


def test_confirmar_dos_veces():
    o = nuevo_pedido()
    o.add_item(item())
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert len(o.events) == 1


# ---------- Envío, cancelación, entrega, devolución ----------
def confirmado():
    o = nuevo_pedido()
    o.add_item(item())
    o.confirm()
    return o


def test_enviar_sin_guia():
    o = confirmado()
    with pytest.raises(InvalidOrderData):
        o.ship("  ")
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_cancelar_sin_motivo():
    o = confirmado()
    with pytest.raises(InvalidOrderData):
        o.cancel("")
    assert o.status == OrderStatus.CONFIRMED


def test_cancelar_desde_shipped_falla():
    o = confirmado()
    o.ship("G1")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("tarde")
    assert o.status == OrderStatus.SHIPPED


def test_flujo_completo_entrega():
    o = confirmado()
    o.ship("G1")
    o.deliver()
    assert o.status == OrderStatus.DELIVERED
    assert [e.name for e in o.events] == [
        "OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_flujo_devolucion():
    o = confirmado()
    o.ship("G1")
    o.return_order()
    assert o.status == OrderStatus.RETURNED


def test_cancelacion_valida():
    o = confirmado()
    o.cancel("ya no lo quiero")
    assert o.status == OrderStatus.CANCELLED
    assert o.events[-1].name == "OrderCancelled"


# ---------- Specifications ----------
def test_descuento_vip_10():
    assert discount_rate(load_fixture()["O001"]) == Decimal("0.10")


def test_no_vip_0():
    assert discount_rate(load_fixture()["O002"]) == Decimal("0")


def test_promocion_activa_bloquea():
    assert discount_rate(load_fixture()["O005"]) == Decimal("0")


def test_total_mayor_5000_da_5():
    assert discount_rate(load_fixture()["O006"]) == Decimal("0.05")


def test_umbral_estricto_500():
    o = load_fixture()["O010"]
    assert o.total.amount == Decimal("500.00")
    assert not MinimumAmountSpec(500).is_satisfied_by(o)
    assert discount_rate(o) == Decimal("0")


def test_vip_con_3_unidades_no_califica():
    assert discount_rate(load_fixture()["O011"]) == Decimal("0")


def test_prioridad_10_sobre_5():
    o = nuevo_pedido(vip=True)
    o.add_item(item(qty=1, price="6000.00"))
    o.add_item(item(qty=3, price="10.00", sku="SKU002"))
    assert ten_percent.is_satisfied_by(o) and five_percent.is_satisfied_by(o)
    assert discount_rate(o) == Decimal("0.10")


def test_composicion_not_y_or():
    o = nuevo_pedido(vip=True, promo=True)
    assert (VIPCustomerSpec() & ActivePromotionSpec()).is_satisfied_by(o)
    assert not (VIPCustomerSpec() & ~ActivePromotionSpec()).is_satisfied_by(o)
    assert (~VIPCustomerSpec() | ActivePromotionSpec()).is_satisfied_by(o)


def test_specification_no_modifica_pedido():
    o = load_fixture()["O001"]
    antes = (o.status, o.units, len(o.events))
    discount_rate(o)
    assert (o.status, o.units, len(o.events)) == antes
