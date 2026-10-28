# TechStore U4: núcleo de negocio con FastAPI

Actividad 4 de **Componentes de Lógica de Negocio** (Unidad 4: Desarrollo de Componentes de Negocio), FIME · UANL.

**Equipo 11:**

- Christopher Cortez Garcia
- Oscar Elias Vera Moreno
- Christofer Aaron Torres Puga

## ¿De qué trata?

TechStore es una tienda ficticia. Este proyecto implementa el **núcleo de negocio** de sus pedidos:

- Entidades y Value Objects que protegen sus reglas desde el constructor.
- Reglas de descuento con **Specification Pattern** (AND, OR, NOT).
- Una **máquina de estados** para el ciclo de vida del pedido, con **Domain Events**.
- Una **API REST** con FastAPI que solo traduce peticiones HTTP a operaciones del dominio.
- Pruebas automáticas con **pytest**.

Todo funciona **en memoria**: no hay base de datos y los cambios no persisten entre ejecuciones.

## Requisitos

- Python 3.11 o superior
- Librerías: `fastapi`, `uvicorn`, `pytest`, `httpx` (están en `requirements.txt`)

## Instalación

Desde la carpeta del proyecto (la que contiene `app/`, `datos/` y `tests/`):

```bash
python -m venv .venv
```

Activar el entorno virtual:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Mac / Linux
source .venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

## Cómo ejecutarlo

| Qué quieres hacer | Comando |
|---|---|
| Cargar los 16 pedidos desde los CSV | `python cargar_csv.py` |
| Ejecutar los 15 escenarios (E01 a E15) | `python correr_escenarios.py` |
| Ejercicio de confirmar O013 dos veces | `python ejercicio_o013.py` |
| Correr todas las pruebas | `python -m pytest -q` |
| Levantar la API | `uvicorn app.api:app --reload` |

Con la API encendida, la documentación interactiva (Swagger / OpenAPI) está en:

```
http://127.0.0.1:8000/docs
```

> Como los pedidos viven en memoria, para repetir una prueba en Swagger hay que detener el servidor (`Ctrl+C`) y volver a ejecutar `uvicorn`.

## Estructura del proyecto

```
techstore-u4/
├── app/
│   ├── __init__.py
│   ├── domain.py            # Money, OrderItem, Customer, Order, eventos y excepciones
│   ├── specifications.py    # Specifications y reglas de descuento
│   └── api.py               # API REST (FastAPI)
├── tests/
│   ├── test_domain.py       # Pruebas del dominio y de las Specifications
│   └── test_api.py          # Pruebas de la API
├── datos/                   # clientes, productos, pedidos, detalle_pedidos y escenarios (CSV)
├── cargar_csv.py            # Convierte los CSV en objetos del dominio
├── correr_escenarios.py     # Ejecuta E01 a E15 y muestra la bitácora
├── ejercicio_o013.py        # Ejercicio de la doble confirmación
├── requirements.txt
└── README.md
```

## Reglas de negocio

### Dinero y pedidos

- `Money` es inmutable, usa `Decimal` (nunca `float`) y **no admite montos negativos**.
- Un pedido admite **máximo 20 unidades** (se suman las cantidades, no los renglones).
- Solo se pueden agregar artículos mientras el pedido está en `DRAFT`.

### Descuentos (Specification Pattern)

| Descuento | Condiciones |
|---|---|
| **10 %** | Cliente VIP **Y** total mayor a 500 MXN **Y** 4 o más unidades **Y** sin promoción activa |
| **5 %** | Total mayor a 5,000 MXN **Y** sin promoción activa |

Si se cumplen ambas reglas, gana el **10 %**. El umbral de monto es estricto (`>`): un pedido de exactamente 500 MXN no califica.

Operadores de composición: `&` (AND), `|` (OR) y `~` (NOT).

### Máquina de estados

```
DRAFT --confirm--> CONFIRMED --ship--> SHIPPED --deliver--> DELIVERED
                       |                  |
                    cancel              return
                       |                  |
                   CANCELLED           RETURNED
```

| Método | Evento | Se permite desde | Condición extra |
|---|---|---|---|
| `confirm()` | `OrderConfirmed` | `DRAFT` | Tener artículos y cliente activo |
| `ship(guía)` | `OrderShipped` | `CONFIRMED` | Número de guía no vacío |
| `cancel(motivo)` | `OrderCancelled` | `CONFIRMED` | Motivo no vacío |
| `deliver()` | `OrderDelivered` | `SHIPPED` | Ninguna |
| `return_order()` | `OrderReturned` | `SHIPPED` | Ninguna |

En cada transición el orden es: **1) validar, 2) cambiar el estado, 3) registrar el evento**. Si la validación falla, no cambia nada y no se registra ningún evento.

### Excepciones de dominio

| Excepción | Cuándo se lanza |
|---|---|
| `InvalidOrderData` | Datos inválidos: pedido vacío, cliente inactivo, guía o motivo vacío, monto negativo |
| `InvalidOrderTransition` | Transición no permitida desde el estado actual |
| `OrderItemLimitExceeded` | Se intenta pasar de 20 unidades |

Todas heredan de `DomainException`.

## API REST

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/orders/{id}` | Consulta un pedido (estado, unidades, total, descuento y eventos) |
| `POST` | `/orders/{id}/confirm` | Confirma el pedido |
| `POST` | `/orders/{id}/ship` | Envía el pedido. Cuerpo: `{"tracking_number": "GUIA-1"}` |
| `POST` | `/orders/{id}/cancel` | Cancela el pedido. Cuerpo: `{"reason": "motivo"}` |

### Códigos HTTP

| Código | Significado | Cuándo |
|---|---|---|
| `200` | Éxito | La transición fue válida |
| `404` | No encontrado | El pedido no existe |
| `409` | Conflicto | Transición no permitida o límite de 20 unidades excedido |
| `422` | Datos inválidos | Pedido vacío, cliente inactivo, guía o motivo vacío |

### Ejemplo

```
POST /orders/O013/confirm
```

Respuesta `200`:

```json
{
  "id": "O013",
  "status": "CONFIRMED",
  "units": 1,
  "total": "600.00",
  "discount_rate": "0",
  "events": ["OrderConfirmed"]
}
```

Si se repite la misma petición, la respuesta es `409` porque el pedido ya no está en `DRAFT`.

La API **no contiene reglas de negocio**: busca el pedido, llama al método correspondiente de `Order` y traduce las excepciones del dominio a códigos HTTP.

## Pruebas

```bash
python -m pytest -q
```

Las pruebas cubren:

- Value Objects (`Money`, `OrderItem`) y sus invariantes.
- Límite de 20 unidades y confirmación de pedidos.
- Todas las transiciones válidas e inválidas, y los eventos generados.
- Cada Specification, su composición y la prioridad del descuento del 10 %.
- Respuestas de la API: 200, 404, 409 y 422.

## Notas

- El campo `existencia` de `productos.csv` es solo información de catálogo; no se implementa control de inventario.
- Los repositorios son en memoria: al reiniciar la aplicación se recargan los datos originales de los CSV.
- No se modificaron los archivos CSV para que ningún caso pase.
