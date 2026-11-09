# -*- coding: utf-8 -*-
"""
probar_api.py -- Autocorrección del Parcial 2: Food Store API.

Prueba la API por HTTP, sin levantar servidor y SIN tocar tu base real: cada grupo de
pruebas arma su propia base SQLite EN MEMORIA y la descarta al terminar. Se puede correr
las veces que quieras, desde la carpeta del proyecto:

    python probar_api.py                 todas las pruebas
    python probar_api.py --transaccion   demostración para el video, sobre tu base real
    python probar_api.py --ver-base      muestra lo que hay en tu base real

Cada línea dice [ OK ] o [FALLA], con el código esperado y el que llegó. Al final muestra
el total. Las pruebas son la misma lista de control para todos: que pasen todas no reemplaza
la corrección del código ni el video, pero si alguna falla, a tu entrega le falta algo.

NO modifiques este archivo.
"""

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import event, text
    from sqlalchemy.pool import StaticPool
    from sqlmodel import Session, SQLModel, create_engine
except ImportError as error:
    sys.exit(f"Falta instalar dependencias ({error}). Corré: pip install -r requirements.txt")

try:
    import database
    import models  # noqa: F401  -- registra las tablas
    from database import get_session
    from main import app
except Exception as error:  # noqa: BLE001 -- al empezar, el proyecto puede no existir todavía
    sys.exit("No se pudo cargar el proyecto. Tienen que existir main.py (con la variable app), "
             f"database.py (con get_session) y models.py.\nError: {error!r}")

# raise_server_exceptions=False: si algo explota adentro, lo vemos como un 500 y seguimos.
client = TestClient(app, raise_server_exceptions=False)
resultados: list[tuple[str, bool]] = []
ENGINES: list = []

CATEGORIAS, ETIQUETAS, PRODUCTOS, PEDIDOS = "/categorias/", "/etiquetas/", "/productos/", "/pedidos/"


# ----------------------------------------------------------------------
# Herramientas
# ----------------------------------------------------------------------
def registrar(parte: str, descripcion: str, ok: bool, detalle: str = "") -> None:
    resultados.append((parte, ok))
    marca = "[ OK ]" if ok else "[FALLA]"
    print(f"{marca} {parte} - {descripcion}" + ("" if ok else f"   -> {detalle}"))


def http(parte, descripcion, respuesta, codigo, condicion=None):
    """Compara el código HTTP y, opcionalmente, una condición sobre el JSON."""
    ok = respuesta.status_code == codigo
    detalle = f"esperaba {codigo}, llegó {respuesta.status_code}: {respuesta.text[:160]}"
    if ok and condicion is not None:
        try:
            ok = bool(condicion(respuesta.json()))
            detalle = f"el código está bien, pero el cuerpo no: {respuesta.text[:200]}"
        except Exception as error:  # noqa: BLE001
            ok, detalle = False, f"error al revisar la respuesta: {error!r}"
    registrar(parte, descripcion, ok, detalle)


def sin_cuerpo(parte, descripcion, respuesta):
    ok = respuesta.status_code == 204 and respuesta.content == b""
    registrar(parte, descripcion, ok,
              f"esperaba 204 sin cuerpo, llegó {respuesta.status_code} con {respuesta.content[:80]!r}")


def comprobar(parte, descripcion, prueba, detalle="la condición no se cumplió"):
    try:
        ok = bool(prueba())
    except Exception as error:  # noqa: BLE001
        ok, detalle = False, repr(error)
    registrar(parte, descripcion, ok, detalle)


def bd_nueva():
    """Una base vacía en memoria y get_session apuntando a ella."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    ENGINES.append(engine)
    SQLModel.metadata.create_all(engine)

    def sesion_de_prueba():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = sesion_de_prueba
    return engine


def id_de(respuesta, si_falla=999):
    """El id creado. Si el alta todavía no funciona, las pruebas siguientes dan [FALLA] sin cortarse."""
    try:
        return respuesta.json()["id"]
    except Exception:  # noqa: BLE001
        return si_falla


def categoria(nombre="Pizzas"):
    return id_de(client.post(CATEGORIAS, json={"nombre": nombre, "descripcion": "De prueba"}))


def producto(categoria_id, nombre="Pizza muzzarella", precio=1000.0, stock=10, **extra):
    datos = {"nombre": nombre, "descripcion": "Con salsa de tomate", "precio": precio,
             "stock": stock, "categoria_id": categoria_id, **extra}
    return id_de(client.post(PRODUCTOS, json=datos))


def stock_de(producto_id):
    try:
        return client.get(f"{PRODUCTOS}{producto_id}").json()["stock"]
    except Exception:  # noqa: BLE001
        return None


def pedido_body(*lineas, **extra):
    return {"cliente_nombre": "Ana Gómez", "direccion_entrega": "San Martín 1234",
            "forma_pago": "EFECTIVO",
            "detalles": [{"producto_id": p, "cantidad": c} for p, c in lineas], **extra}


class FallaSimulada(Exception):
    """Simula un corte en medio de la transacción, por ejemplo, que se caiga la conexión."""


class falla_en_segunda_linea:
    """Mientras dura el bloque, guardar la SEGUNDA línea de un pedido lanza FallaSimulada."""

    def __enter__(self):
        self.lineas = 0
        event.listen(models.DetallePedido, "before_insert", self._contar)
        return self

    def __exit__(self, *_):
        event.remove(models.DetallePedido, "before_insert", self._contar)

    def _contar(self, *_):
        self.lineas += 1
        if self.lineas == 2:
            raise FallaSimulada("Falla simulada al guardar la segunda línea del pedido")


# ----------------------------------------------------------------------
# Partes
# ----------------------------------------------------------------------
def parte_1_modelos():
    print("\n=== PARTE 1: tablas y relaciones (models.py) ===")
    P = "P1"
    tablas = SQLModel.metadata.tables
    for nombre in ("categoria", "etiqueta", "producto", "productoetiqueta", "pedido", "detallepedido"):
        comprobar(P, f"existe la tabla {nombre}", lambda n=nombre: n in tablas,
                  f"no está: revisá el nombre de la clase y table=True. Hay: {sorted(tablas)}")

    def fks(tabla):
        return {fk.target_fullname for fk in tablas[tabla].foreign_keys}

    comprobar(P, "producto tiene FK a categoria.id", lambda: "categoria.id" in fks("producto"))
    comprobar(P, "detallepedido tiene FK a pedido.id y a producto.id",
              lambda: {"pedido.id", "producto.id"} <= fks("detallepedido"))
    comprobar(P, "productoetiqueta tiene clave primaria compuesta (producto_id, etiqueta_id)",
              lambda: {c.name for c in tablas["productoetiqueta"].primary_key.columns}
              == {"producto_id", "etiqueta_id"})
    comprobar(P, "detallepedido guarda copia de nombre_producto y precio_unitario",
              lambda: {"nombre_producto", "precio_unitario", "cantidad", "subtotal"}
              <= set(tablas["detallepedido"].columns.keys()))


def parte_2_categorias():
    print("\n=== PARTE 2: categorías ===")
    P = "P2"
    bd_nueva()
    r = client.post(CATEGORIAS, json={"nombre": "Pizzas", "descripcion": "A la piedra"})
    http(P, "POST crea una categoría (201) con id y activo", r, 201,
         lambda j: j["id"] > 0 and j["nombre"] == "Pizzas" and j["activo"] is True)
    cat = id_de(r)
    http(P, "POST con nombre repetido en otras mayúsculas: 409",
         client.post(CATEGORIAS, json={"nombre": "PIZZAS"}), 409)
    http(P, "POST con nombre de 1 letra: 422", client.post(CATEGORIAS, json={"nombre": "P"}), 422)
    http(P, "GET lista las categorías", client.get(CATEGORIAS), 200,
         lambda j: isinstance(j, list) and len(j) == 1)
    http(P, "GET /{id} trae la lista productos", client.get(f"{CATEGORIAS}{cat}"), 200,
         lambda j: j["productos"] == [])
    http(P, "GET /{id} inexistente: 404", client.get(f"{CATEGORIAS}999"), 404)
    http(P, "PUT reemplaza los datos", client.put(f"{CATEGORIAS}{cat}", json={
        "nombre": "Pizzas caseras", "descripcion": "Nueva"}), 200,
        lambda j: j["nombre"] == "Pizzas caseras" and j["descripcion"] == "Nueva")
    http(P, "PUT con su propio nombre no es conflicto", client.put(f"{CATEGORIAS}{cat}", json={
        "nombre": "Pizzas caseras", "descripcion": "Otra"}), 200)
    otra = categoria("Bebidas")
    http(P, "PUT con el nombre de otra categoría: 409",
         client.put(f"{CATEGORIAS}{otra}", json={"nombre": "Pizzas caseras"}), 409)
    http(P, "PUT de un id inexistente: 404",
         client.put(f"{CATEGORIAS}999", json={"nombre": "Algo"}), 404)
    producto(cat)
    http(P, "DELETE con productos activos: 409", client.delete(f"{CATEGORIAS}{cat}"), 409)
    http(P, "DELETE hace baja lógica (200, activo false)", client.delete(f"{CATEGORIAS}{otra}"), 200,
         lambda j: j["activo"] is False)
    http(P, "la categoría dada de baja no se lista", client.get(CATEGORIAS), 200,
         lambda j: otra not in [c["id"] for c in j])
    http(P, "DELETE de una ya dada de baja: 409", client.delete(f"{CATEGORIAS}{otra}"), 409)
    http(P, "DELETE de un id inexistente: 404", client.delete(f"{CATEGORIAS}999"), 404)
    http(P, "una categoría dada de baja conserva su nombre: 409",
         client.post(CATEGORIAS, json={"nombre": "Bebidas"}), 409)


def parte_3_etiquetas():
    print("\n=== PARTE 3: etiquetas ===")
    P = "P3"
    bd_nueva()
    r = client.post(ETIQUETAS, json={"nombre": "Vegetariano"})
    http(P, "POST crea una etiqueta (201)", r, 201, lambda j: j["id"] > 0)
    et = id_de(r)
    http(P, "POST con nombre repetido: 409",
         client.post(ETIQUETAS, json={"nombre": "vegetariano"}), 409)
    http(P, "POST con nombre de 1 letra: 422", client.post(ETIQUETAS, json={"nombre": "V"}), 422)
    http(P, "GET lista las etiquetas", client.get(ETIQUETAS), 200, lambda j: len(j) == 1)
    prod = producto(categoria())
    client.post(f"{PRODUCTOS}{prod}/etiquetas/{et}")
    http(P, "DELETE de una etiqueta en uso: 409", client.delete(f"{ETIQUETAS}{et}"), 409)
    libre = id_de(client.post(ETIQUETAS, json={"nombre": "Picante"}))
    sin_cuerpo(P, "DELETE de una etiqueta libre: 204 sin cuerpo", client.delete(f"{ETIQUETAS}{libre}"))
    http(P, "DELETE de un id inexistente: 404", client.delete(f"{ETIQUETAS}999"), 404)


def parte_4_productos():
    print("\n=== PARTE 4: productos ===")
    P = "P4"
    bd_nueva()
    pizzas, bebidas = categoria("Pizzas"), categoria("Bebidas")
    base = {"nombre": "Pizza fugazza", "precio": 9000, "stock": 5, "categoria_id": pizzas,
            "descripcion": "Con cebolla", "imagen_url": "img/fugazza.jpg"}
    r = client.post(PRODUCTOS, json=base)
    http(P, "POST crea un producto (201) con su categoría y etiquetas", r, 201,
         lambda j: j["id"] > 0 and j["activo"] is True and j["categoria"]["id"] == pizzas
         and j["etiquetas"] == [] and j["imagen_url"] == "img/fugazza.jpg")
    fugazza = id_de(r)
    http(P, "imagen_url es opcional", client.post(PRODUCTOS, json={
        "nombre": "Agua mineral", "precio": 1500, "stock": 0, "categoria_id": bebidas}), 201,
        lambda j: j["imagen_url"] is None)
    http(P, "POST con nombre repetido en otras mayúsculas: 409",
         client.post(PRODUCTOS, json={**base, "nombre": "PIZZA FUGAZZA"}), 409)
    http(P, "POST con categoría inexistente: 404",
         client.post(PRODUCTOS, json={**base, "nombre": "Otra pizza", "categoria_id": 999}), 404)
    http(P, "POST con precio 0: 422",
         client.post(PRODUCTOS, json={**base, "nombre": "Otra pizza", "precio": 0}), 422)
    http(P, "POST con stock negativo: 422",
         client.post(PRODUCTOS, json={**base, "nombre": "Otra pizza", "stock": -1}), 422)
    http(P, "POST con nombre de 2 letras: 422",
         client.post(PRODUCTOS, json={**base, "nombre": "Pi"}), 422)
    inactiva = categoria("Postres")
    client.delete(f"{CATEGORIAS}{inactiva}")
    http(P, "POST en una categoría dada de baja: 404",
         client.post(PRODUCTOS, json={**base, "nombre": "Flan", "categoria_id": inactiva}), 404)

    http(P, "GET /{id} trae categoría y etiquetas", client.get(f"{PRODUCTOS}{fugazza}"), 200,
         lambda j: j["categoria"]["nombre"] == "Pizzas" and "etiquetas" in j)
    http(P, "GET /{id} inexistente: 404", client.get(f"{PRODUCTOS}999"), 404)
    http(P, "PATCH cambia solo lo enviado", client.patch(f"{PRODUCTOS}{fugazza}", json={"precio": 9500}),
         200, lambda j: j["precio"] == 9500 and j["stock"] == 5 and j["nombre"] == "Pizza fugazza")
    http(P, "PATCH a una categoría inexistente: 404",
         client.patch(f"{PRODUCTOS}{fugazza}", json={"categoria_id": 999}), 404)
    http(P, "PATCH con el nombre de otro producto: 409",
         client.patch(f"{PRODUCTOS}{fugazza}", json={"nombre": "Agua mineral"}), 409)
    http(P, "PATCH con precio negativo: 422",
         client.patch(f"{PRODUCTOS}{fugazza}", json={"precio": -5}), 422)
    http(P, "PATCH de un id inexistente: 404", client.patch(f"{PRODUCTOS}999", json={"stock": 1}), 404)

    # Listado: 12 productos en total para probar la paginación
    for numero in range(10):
        producto(pizzas, nombre=f"Pizza especial {numero:02d}", stock=numero)
    http(P, "GET devuelve total e items, 10 por defecto", client.get(PRODUCTOS), 200,
         lambda j: j["total"] == 12 and len(j["items"]) == 10)
    http(P, "cada item trae su categoría", client.get(PRODUCTOS), 200,
         lambda j: all("categoria" in x and "etiquetas" in x for x in j["items"]))
    http(P, "skip y limit paginan sin cambiar el total", client.get(PRODUCTOS, params={"skip": 10, "limit": 5}),
         200, lambda j: j["total"] == 12 and len(j["items"]) == 2)
    http(P, "limit mayor a 50: 422", client.get(PRODUCTOS, params={"limit": 51}), 422)
    http(P, "skip negativo: 422", client.get(PRODUCTOS, params={"skip": -1}), 422)
    http(P, "los items vienen ordenados por id", client.get(PRODUCTOS, params={"limit": 50}), 200,
         lambda j: [x["id"] for x in j["items"]] == sorted(x["id"] for x in j["items"]))
    http(P, "q busca en el nombre sin distinguir mayúsculas", client.get(PRODUCTOS, params={"q": "FUGAZZA"}),
         200, lambda j: j["total"] == 1)
    http(P, "q busca también en la descripción", client.get(PRODUCTOS, params={"q": "cebolla"}),
         200, lambda j: j["total"] == 1 and j["items"][0]["id"] == fugazza)
    http(P, "categoria_id filtra y el total respeta el filtro",
         client.get(PRODUCTOS, params={"categoria_id": bebidas}), 200,
         lambda j: j["total"] == 1 and j["items"][0]["nombre"] == "Agua mineral")
    http(P, "solo_con_stock deja afuera a los de stock 0",
         client.get(PRODUCTOS, params={"solo_con_stock": True, "limit": 50}), 200,
         lambda j: j["total"] == 10 and all(x["stock"] > 0 for x in j["items"]))
    http(P, "los filtros se combinan", client.get(PRODUCTOS, params={"q": "especial", "categoria_id": bebidas}),
         200, lambda j: j["total"] == 0 and j["items"] == [])
    http(P, "DELETE hace baja lógica (200, activo false)", client.delete(f"{PRODUCTOS}{fugazza}"), 200,
         lambda j: j["activo"] is False)
    http(P, "el producto dado de baja no se lista y baja el total", client.get(PRODUCTOS, params={"limit": 50}),
         200, lambda j: j["total"] == 11 and fugazza not in [x["id"] for x in j["items"]])
    http(P, "DELETE de uno ya dado de baja: 409", client.delete(f"{PRODUCTOS}{fugazza}"), 409)
    http(P, "DELETE de un id inexistente: 404", client.delete(f"{PRODUCTOS}999"), 404)
    http(P, "un producto dado de baja conserva su nombre: 409",
         client.post(PRODUCTOS, json={**base, "nombre": "Pizza fugazza"}), 409)
    http(P, "GET de la categoría trae sus productos", client.get(f"{CATEGORIAS}{bebidas}"), 200,
         lambda j: [x["nombre"] for x in j["productos"]] == ["Agua mineral"])


def parte_5_etiquetas_de_producto():
    print("\n=== PARTE 5: relación N a N entre productos y etiquetas ===")
    P = "P5"
    bd_nueva()
    cat = categoria()
    uno, dos = producto(cat, nombre="Pizza vegana"), producto(cat, nombre="Pizza de jamón")
    veg = id_de(client.post(ETIQUETAS, json={"nombre": "Vegetariano"}))
    tacc = id_de(client.post(ETIQUETAS, json={"nombre": "Sin TACC"}))
    http(P, "POST asocia una etiqueta (201) y devuelve el producto",
         client.post(f"{PRODUCTOS}{uno}/etiquetas/{veg}"), 201,
         lambda j: [e["nombre"] for e in j["etiquetas"]] == ["Vegetariano"])
    http(P, "se pueden asociar varias etiquetas", client.post(f"{PRODUCTOS}{uno}/etiquetas/{tacc}"), 201,
         lambda j: len(j["etiquetas"]) == 2)
    http(P, "asociar dos veces la misma: 409", client.post(f"{PRODUCTOS}{uno}/etiquetas/{veg}"), 409)
    http(P, "asociar a un producto inexistente: 404", client.post(f"{PRODUCTOS}999/etiquetas/{veg}"), 404)
    http(P, "asociar una etiqueta inexistente: 404", client.post(f"{PRODUCTOS}{uno}/etiquetas/999"), 404)
    client.post(f"{PRODUCTOS}{dos}/etiquetas/{tacc}")
    http(P, "etiqueta_id filtra el listado", client.get(PRODUCTOS, params={"etiqueta_id": veg}), 200,
         lambda j: j["total"] == 1 and j["items"][0]["id"] == uno)
    http(P, "una etiqueta puede estar en varios productos",
         client.get(PRODUCTOS, params={"etiqueta_id": tacc}), 200, lambda j: j["total"] == 2)
    sin_cuerpo(P, "DELETE quita la etiqueta: 204 sin cuerpo",
               client.delete(f"{PRODUCTOS}{uno}/etiquetas/{veg}"))
    http(P, "el producto ya no la tiene", client.get(f"{PRODUCTOS}{uno}"), 200,
         lambda j: [e["nombre"] for e in j["etiquetas"]] == ["Sin TACC"])
    http(P, "quitar una que no tiene: 404", client.delete(f"{PRODUCTOS}{uno}/etiquetas/{veg}"), 404)


def parte_6_pedidos():
    print("\n=== PARTE 6: crear y consultar pedidos ===")
    P = "P6"
    bd_nueva()
    cat = categoria()
    pizza = producto(cat, nombre="Pizza muzzarella", precio=1000.5, stock=10)
    empanada = producto(cat, nombre="Empanada", precio=500, stock=3)
    baja = producto(cat, nombre="Pizza vieja", stock=5)
    client.delete(f"{PRODUCTOS}{baja}")

    r = client.post(PEDIDOS, json=pedido_body((pizza, 2), (empanada, 1), notas="Sin sal"))
    http(P, "POST crea el pedido (201) en estado PENDIENTE", r, 201,
         lambda j: j["id"] > 0 and j["estado"] == "PENDIENTE" and j["notas"] == "Sin sal"
         and j["forma_pago"] == "EFECTIVO")
    pedido = r.json() if r.status_code == 201 else {"id": 999, "total": None, "detalles": []}
    comprobar(P, "el total lo calcula la API (subtotal = precio x cantidad)",
              lambda: abs(pedido["total"] - 2501.0) < 0.01, f"total recibido: {pedido.get('total')}")
    comprobar(P, "cada línea trae copia de nombre, precio, cantidad y subtotal",
              lambda: {"Pizza muzzarella", "Empanada"} == {d.get("nombre_producto") for d in pedido["detalles"]}
              and all(abs(d["subtotal"] - d["precio_unitario"] * d["cantidad"]) < 0.01
                      for d in pedido["detalles"]))
    comprobar(P, "el stock se descontó", lambda: stock_de(pizza) == 8 and stock_de(empanada) == 2)
    http(P, "el total que manda el cliente se ignora",
         client.post(PEDIDOS, json=pedido_body((pizza, 1), total=1)), 201,
         lambda j: abs(j["total"] - 1000.5) < 0.01)

    client.patch(f"{PRODUCTOS}{pizza}", json={"precio": 9999, "nombre": "Pizza renombrada"})
    http(P, "cambiar el producto no modifica los pedidos hechos", client.get(f"{PEDIDOS}{pedido['id']}"), 200,
         lambda j: any(d["nombre_producto"] == "Pizza muzzarella" and d["precio_unitario"] == 1000.5
                       for d in j["detalles"]) and abs(j["total"] - 2501.0) < 0.01)

    stock_antes = stock_de(pizza), stock_de(empanada)
    http(P, "stock insuficiente: 409",
         client.post(PEDIDOS, json=pedido_body((pizza, 1), (empanada, 99))), 409)
    comprobar(P, "TODO O NADA: tras el 409 no cambió ningún stock",
              lambda: (stock_de(pizza), stock_de(empanada)) == stock_antes,
              "se descontó una línea aunque otra falló: validá todo antes de modificar")
    pedidos_antes = client.get(PEDIDOS).json().get("total")
    with falla_en_segunda_linea():
        cortado = client.post(PEDIDOS, json=pedido_body((pizza, 1), (empanada, 1)))
    comprobar(P, "TRANSACCIÓN: con una falla en la segunda línea, el pedido no se confirma",
              lambda: cortado.status_code != 201, f"llegó {cortado.status_code}")
    comprobar(P, "TRANSACCIÓN: tras la falla no quedó ningún pedido guardado",
              lambda: client.get(PEDIDOS).json().get("total") == pedidos_antes,
              "quedó un pedido a medias: stock, pedido y líneas van en un solo commit")
    comprobar(P, "TRANSACCIÓN: tras la falla no cambió ningún stock",
              lambda: (stock_de(pizza), stock_de(empanada)) == stock_antes,
              "se confirmó parte del stock: stock, pedido y líneas van en un solo commit")
    http(P, "producto inexistente: 404", client.post(PEDIDOS, json=pedido_body((pizza, 1), (999, 1))), 404)
    comprobar(P, "TODO O NADA: tras el 404 no cambió ningún stock",
              lambda: (stock_de(pizza), stock_de(empanada)) == stock_antes)
    http(P, "producto dado de baja: 404", client.post(PEDIDOS, json=pedido_body((baja, 1))), 404)
    http(P, "producto repetido en el pedido: 409",
         client.post(PEDIDOS, json=pedido_body((pizza, 1), (pizza, 1))), 409)
    http(P, "pedido sin líneas: 422", client.post(PEDIDOS, json=pedido_body()), 422)
    http(P, "cantidad 0: 422", client.post(PEDIDOS, json=pedido_body((pizza, 0))), 422)
    http(P, "forma de pago inválida: 422",
         client.post(PEDIDOS, json=pedido_body((pizza, 1), forma_pago="TARJETA")), 422)
    http(P, "dirección de menos de 5 caracteres: 422",
         client.post(PEDIDOS, json=pedido_body((pizza, 1), direccion_entrega="Abc")), 422)
    http(P, "falta el nombre del cliente: 422", client.post(PEDIDOS, json={
        "direccion_entrega": "San Martín 1234", "forma_pago": "EFECTIVO",
        "detalles": [{"producto_id": pizza, "cantidad": 1}]}), 422)
    comprobar(P, "los pedidos rechazados no quedaron guardados",
              lambda: client.get(PEDIDOS).json()["total"] == 2,
              f"{client.get(PEDIDOS).text[:120]}")

    http(P, "GET devuelve total e items, los últimos primero", client.get(PEDIDOS), 200,
         lambda j: j["total"] == 2 and j["items"][0]["id"] > j["items"][1]["id"]
         and len(j["items"][0]["detalles"]) >= 1)
    http(P, "skip y limit paginan los pedidos", client.get(PEDIDOS, params={"skip": 1, "limit": 1}), 200,
         lambda j: j["total"] == 2 and len(j["items"]) == 1)
    http(P, "GET /{id} inexistente: 404", client.get(f"{PEDIDOS}999"), 404)


def parte_7_estados():
    print("\n=== PARTE 7: estados del pedido y resumen ===")
    P = "P7"
    bd_nueva()
    cat = categoria()
    pizza = producto(cat, precio=1000, stock=20)

    def nuevo_pedido(cantidad=2):
        return id_de(client.post(PEDIDOS, json=pedido_body((pizza, cantidad))))

    def cambiar(pedido, estado):
        return client.patch(f"{PEDIDOS}{pedido}/estado", json={"estado": estado})

    uno = nuevo_pedido()
    http(P, "PENDIENTE a EN_PREPARACION: 200", cambiar(uno, "EN_PREPARACION"), 200,
         lambda j: j["estado"] == "EN_PREPARACION")
    http(P, "no se vuelve a PENDIENTE: 409", cambiar(uno, "PENDIENTE"), 409)
    http(P, "EN_PREPARACION a ENTREGADO: 200", cambiar(uno, "ENTREGADO"), 200,
         lambda j: j["estado"] == "ENTREGADO")
    http(P, "ENTREGADO es terminal: no se cancela (409)", cambiar(uno, "CANCELADO"), 409)
    comprobar(P, "el 409 no devolvió stock", lambda: stock_de(pizza) == 18)

    dos = nuevo_pedido()
    http(P, "PENDIENTE no salta a ENTREGADO: 409", cambiar(dos, "ENTREGADO"), 409)
    comprobar(P, "antes de cancelar el stock está descontado", lambda: stock_de(pizza) == 16)
    http(P, "PENDIENTE a CANCELADO: 200", cambiar(dos, "CANCELADO"), 200,
         lambda j: j["estado"] == "CANCELADO")
    comprobar(P, "cancelar devuelve el stock", lambda: stock_de(pizza) == 18,
              f"stock actual: {stock_de(pizza)}")
    http(P, "CANCELADO es terminal: 409", cambiar(dos, "EN_PREPARACION"), 409)
    comprobar(P, "cancelar no devuelve el stock dos veces", lambda: stock_de(pizza) == 18)

    tres = nuevo_pedido(3)
    cambiar(tres, "EN_PREPARACION")
    http(P, "EN_PREPARACION también se puede cancelar", cambiar(tres, "CANCELADO"), 200)
    comprobar(P, "y devuelve el stock", lambda: stock_de(pizza) == 18)

    http(P, "estado inválido: 422", cambiar(uno, "PERDIDO"), 422)
    http(P, "cambiar el estado de un pedido inexistente: 404", cambiar(999, "CANCELADO"), 404)

    nuevo_pedido(1)
    http(P, "estado filtra el listado", client.get(PEDIDOS, params={"estado": "CANCELADO"}), 200,
         lambda j: j["total"] == 2 and all(x["estado"] == "CANCELADO" for x in j["items"]))
    http(P, "estado inválido en el filtro: 422", client.get(PEDIDOS, params={"estado": "PERDIDO"}), 422)
    http(P, "GET /pedidos/resumen cuenta por estado", client.get(f"{PEDIDOS}resumen"), 200,
         lambda j: (j["pendientes"], j["en_preparacion"], j["entregados"], j["cancelados"]) == (1, 0, 1, 2))
    http(P, "ingresos_entregados suma solo los ENTREGADO", client.get(f"{PEDIDOS}resumen"), 200,
         lambda j: abs(j["ingresos_entregados"] - 2000) < 0.01)


def parte_8_datos_y_diseno():
    print("\n=== PARTE 8: datos de ejemplo y capas ===")
    P = "P8"

    def texto(nombre):
        return (CARPETA / nombre).read_text(encoding="utf-8")

    def sin_comentarios(fuente):
        return re.sub(r"#.*", "", re.sub(r'""".*?"""', "", fuente, flags=re.S))

    def routers():
        return [sin_comentarios(r.read_text(encoding="utf-8")) for r in CARPETA.glob("router*.py")]

    comprobar(P, "hay routers (router*.py) y service.py",
              lambda: routers() and (CARPETA / "service.py").exists())
    comprobar(P, "ningún router llama a commit", lambda: not any(".commit(" in r for r in routers()))
    comprobar(P, "service.py no conoce HTTP (ni fastapi ni HTTPException)",
              lambda: not re.search(r"fastapi|HTTPException", sin_comentarios(texto("service.py"))))
    comprobar(P, "service.py usa selectinload para traer las relaciones",
              lambda: "selectinload" in texto("service.py"))
    comprobar(P, "models.py declara Relationship y link_model",
              lambda: "Relationship" in texto("models.py") and "link_model" in texto("models.py"))

    def cargar_seed():
        import service
        engine = bd_nueva()
        with Session(engine) as session:
            service.cargar_datos_de_ejemplo(session)
        with Session(engine) as session:
            service.cargar_datos_de_ejemplo(session)   # la segunda vez no tiene que duplicar

    try:
        cargar_seed()
        cargo, error = True, ""
    except Exception as e:  # noqa: BLE001
        cargo, error = False, repr(e)
    registrar(P, "service.cargar_datos_de_ejemplo(session) corre dos veces sin errores", cargo, error)
    productos = {"total": 0, "items": []}
    if cargo:
        try:
            respuesta = client.get(PRODUCTOS, params={"limit": 50}).json()
            productos = respuesta if isinstance(respuesta, dict) else productos
        except Exception:  # noqa: BLE001
            pass
    comprobar(P, "los datos de ejemplo traen al menos 12 productos",
              lambda: productos["total"] >= 12, f"hay {productos.get('total')}")
    comprobar(P, "al menos 4 categorías y 3 etiquetas",
              lambda: cargo and len(client.get(CATEGORIAS).json()) >= 4
              and len(client.get(ETIQUETAS).json()) >= 3)
    comprobar(P, "hay productos con etiquetas y alguno con stock 0",
              lambda: any(x["etiquetas"] for x in productos["items"])
              and any(x["stock"] == 0 for x in productos["items"]))
    comprobar(P, "hay productos con imagen_url",
              lambda: any(x["imagen_url"] for x in productos["items"]))


# ----------------------------------------------------------------------
# Herramientas para el video: trabajan sobre la base REAL del proyecto
# ----------------------------------------------------------------------
def foto_de_la_base() -> dict:
    """Lee directo de la base con SQL, sin pasar por la API."""
    with database.engine.connect() as conexion:
        pedidos = conexion.execute(text("SELECT COUNT(*) FROM pedido")).scalar()
        lineas = conexion.execute(text("SELECT COUNT(*) FROM detallepedido")).scalar()
        stock = conexion.execute(text("SELECT id, nombre, stock FROM producto ORDER BY id")).all()
    return {"pedidos": pedidos, "lineas": lineas, "stock": {i: (n, s) for i, n, s in stock}}


def preparar_base() -> None:
    import service
    database.crear_tablas()
    with Session(database.engine) as session:
        service.cargar_datos_de_ejemplo(session)


def nombre_de_la_base() -> str:
    url = database.engine.url
    motor = url.get_backend_name()
    return f"SQLite, archivo {url.database}" if motor == "sqlite" else f"{motor}, base {url.database}"


def ver_base() -> None:
    preparar_base()
    foto = foto_de_la_base()
    print(f"\nBase: {nombre_de_la_base()}")
    print(f"Pedidos guardados: {foto['pedidos']}   Líneas guardadas: {foto['lineas']}")
    print("\nStock de los productos:")
    for producto_id, (nombre, stock) in foto["stock"].items():
        print(f"  {producto_id:>3}  {nombre:<32} {stock}")
    with database.engine.connect() as conexion:
        ultimos = conexion.execute(text(
            "SELECT id, cliente_nombre, estado, total FROM pedido ORDER BY id DESC LIMIT 5")).all()
        print("\nÚltimos pedidos:" if ultimos else "\nTodavía no hay pedidos.")
        for pedido_id, cliente, estado, total in ultimos:
            print(f"  N.º {pedido_id}  {cliente}  {estado}  total {total}")
            lineas = conexion.execute(text(
                "SELECT nombre_producto, cantidad, precio_unitario, subtotal FROM detallepedido "
                "WHERE pedido_id = :id"), {"id": pedido_id}).all()
            for nombre, cantidad, precio, subtotal in lineas:
                print(f"       {cantidad} x {nombre} a {precio} = {subtotal}")


def demostrar_caso(titulo: str, cuerpo: dict, falla: bool) -> bool:
    print(f"\n--- {titulo} ---")
    antes = foto_de_la_base()
    print(f"Antes:   {antes['pedidos']} pedidos, {antes['lineas']} líneas")
    if falla:
        with falla_en_segunda_linea():
            respuesta = client.post(PEDIDOS, json=cuerpo)
    else:
        respuesta = client.post(PEDIDOS, json=cuerpo)
    print(f"La API respondió {respuesta.status_code}: {respuesta.text[:120]}")
    despues = foto_de_la_base()
    print(f"Después: {despues['pedidos']} pedidos, {despues['lineas']} líneas")
    igual = antes == despues and respuesta.status_code != 201
    print("[ OK ] No se guardó nada: ni pedido, ni líneas, ni cambios de stock." if igual
          else "[FALLA] Quedaron datos en la base: el pedido no es todo o nada.")
    return igual


def demostrar_transaccion() -> None:
    preparar_base()
    con_stock = [(i, s) for i, (_, s) in foto_de_la_base()["stock"].items() if s > 0]
    if len(con_stock) < 2:
        sys.exit("Hacen falta al menos dos productos con stock en la base.")
    (uno, _), (dos, stock_dos) = con_stock[:2]
    print(f"\nBase: {nombre_de_la_base()}")
    print("Se manda un pedido de dos líneas que se corta en la mitad. Nada tiene que quedar guardado.")
    casos = [
        demostrar_caso("Caso 1: falla simulada al guardar la segunda línea",
                       pedido_body((uno, 1), (dos, 1)), falla=True),
        demostrar_caso("Caso 2: la segunda línea pide más stock del que hay",
                       pedido_body((uno, 1), (dos, stock_dos + 1)), falla=False),
    ]
    print("\nComprobalo con: python probar_api.py --ver-base")
    sys.exit(0 if all(casos) else 1)


# ----------------------------------------------------------------------
def main() -> None:
    if "--ver-base" in sys.argv:
        ver_base()
        return
    if "--transaccion" in sys.argv:
        demostrar_transaccion()
        return

    partes = [parte_1_modelos, parte_2_categorias, parte_3_etiquetas, parte_4_productos,
              parte_5_etiquetas_de_producto, parte_6_pedidos, parte_7_estados,
              parte_8_datos_y_diseno]
    for parte in partes:
        try:
            parte()
        except Exception as error:  # noqa: BLE001 -- una parte rota no frena a las demás
            registrar(parte.__name__, "la parte se interrumpió", False, repr(error))

    app.dependency_overrides.clear()
    for engine in ENGINES:
        engine.dispose()

    print("\n=== RESUMEN ===")
    for clave in sorted({p for p, _ in resultados}):
        de_la_parte = [ok for p, ok in resultados if p == clave]
        print(f"  {clave}: {sum(de_la_parte)}/{len(de_la_parte)}")
    aprobadas = sum(ok for _, ok in resultados)
    print(f"\nPruebas superadas: {aprobadas}/{len(resultados)}")
    if aprobadas == len(resultados):
        print("Pasaron todas. Falta revisar que puedas explicar tu código en el video.")
    else:
        print("Todavía hay pruebas por resolver: leé el mensaje de cada [FALLA].")
    sys.exit(0 if aprobadas == len(resultados) else 1)


if __name__ == "__main__":
    main()
