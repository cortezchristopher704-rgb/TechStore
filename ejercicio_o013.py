"""Ejercicio de la guía: confirmar O013 dos veces."""
from cargar_csv import load_fixture

orders = load_fixture()
order = orders["O013"]
print("Antes:   ", order.status.value, order.units, order.total.amount)

order.confirm()
print("1a vez:  ", order.status.value, [e.name for e in order.events])

try:
    order.confirm()
except Exception as e:
    print("2a vez:   RECHAZO", type(e).__name__, "-", e)
print("Despues: ", order.status.value, [e.name for e in order.events])
