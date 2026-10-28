"""Ejecuta E01-E15 y muestra la bitácora (caso, estado inicial, operación, resultado, evento)."""
from decimal import Decimal
from cargar_csv import load_fixture
from app.domain import OrderItem, Money, DomainException
from app.specifications import discount_rate


def intentar(fn):
    try:
        fn()
        return "OK"
    except DomainException as e:
        return f"RECHAZO {type(e).__name__}: {e}"


def evs(o):
    return [e.name for e in o.events]


def run():
    filas = []

    def reg(caso, o, op, res):
        filas.append((caso, "DRAFT", op, res, o.status.value, evs(o)))

    O = load_fixture()
    for caso, pid in [("E01", "O001"), ("E02", "O002"), ("E04", "O005"),
                      ("E05", "O006"), ("E09", "O010"), ("E10", "O011")]:
        o = O[pid]
        reg(caso, o, "evaluar_descuento", f"{discount_rate(o) * 100:.0f}%")

    o = O["O003"]; reg("E03", o, "confirmar", intentar(o.confirm))
    o = O["O007"]; reg("E06", o, "confirmar", intentar(o.confirm))
    o = O["O008"]; reg("E07", o, "confirmar", intentar(o.confirm))
    o = O["O009"]
    reg("E08", o, "agregar SKU003 x2",
        intentar(lambda: o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))))
    o = O["O012"]
    r1 = intentar(o.confirm); r2 = intentar(lambda: o.ship(""))
    reg("E11", o, "confirmar y enviar sin guía", f"confirmar={r1} | enviar={r2}")
    o = O["O013"]
    r1 = intentar(o.confirm); r2 = intentar(o.confirm)
    reg("E12", o, "confirmar dos veces", f"1ª={r1} | 2ª={r2}")
    o = O["O014"]
    r = [intentar(o.confirm), intentar(lambda: o.ship("GUIA-1")),
         intentar(lambda: o.cancel("cliente cambió de opinión"))]
    reg("E13", o, "confirmar, enviar, cancelar", " | ".join(r))
    o = O["O015"]
    r = [intentar(o.confirm), intentar(lambda: o.ship("GUIA-2")), intentar(o.return_order)]
    reg("E14", o, "confirmar, enviar, devolver", " | ".join(r))
    o = O["O016"]
    r = [intentar(o.confirm), intentar(lambda: o.ship("GUIA-3")), intentar(o.deliver)]
    reg("E15", o, "confirmar, enviar, entregar", " | ".join(r))

    for f in sorted(filas):
        print(f"{f[0]} | {f[2]} | {f[3]} | estado final={f[4]} | eventos={f[5]}")


if __name__ == "__main__":
    run()
