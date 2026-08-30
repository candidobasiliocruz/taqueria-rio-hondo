"""Taquería Río Hondo — servidor.

Correr en local:
    uvicorn app:app --reload

Para abrirlo desde el celular en la misma red:
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

import os
import sqlite3
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "riohondo.db")
STATIC = os.path.join(BASE, "static")

app = FastAPI(title="Taquería Río Hondo")


def conectar():
    if not os.path.exists(DB):
        raise HTTPException(500, "No existe riohondo.db. Corre: python seed.py")
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    # Manejamos las transacciones a mano para poder usar BEGIN IMMEDIATE.
    con.isolation_level = None
    con.execute("PRAGMA foreign_keys = ON")
    return con


# ---------------------------------------------------------------- menú

@app.get("/api/menu")
def menu():
    """El menú que ve el cliente, agrupado por categoría.

    Solo productos activos. Los agotados sí se mandan, con disponible=false,
    para que el cliente los vea en gris y entienda que hoy no hay.
    """
    con = conectar()
    try:
        filas = con.execute(
            """
            SELECT c.id   AS cat_id,
                   c.nombre AS cat_nombre,
                   p.id, p.nombre, p.descripcion,
                   p.precio_centavos, p.imagen, p.disponible
            FROM categorias c
            JOIN productos p ON p.categoria_id = c.id
            WHERE p.activo = 1
            ORDER BY c.orden, c.id, p.orden, p.nombre
            """
        ).fetchall()
    finally:
        con.close()

    categorias = []
    indice = {}
    for f in filas:
        if f["cat_id"] not in indice:
            indice[f["cat_id"]] = len(categorias)
            categorias.append(
                {"id": f["cat_id"], "nombre": f["cat_nombre"], "productos": []}
            )
        categorias[indice[f["cat_id"]]]["productos"].append(
            {
                "id": f["id"],
                "nombre": f["nombre"],
                "descripcion": f["descripcion"],
                "precio_centavos": f["precio_centavos"],
                "imagen": f["imagen"],
                "disponible": bool(f["disponible"]),
            }
        )

    return {"categorias": categorias}


# ---------------------------------------------------------------- pedidos

class ItemIn(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0, le=50)


class PedidoIn(BaseModel):
    """El cliente manda IDs y cantidades. Nada más.

    Ni nombres ni precios: si el navegador pudiera mandar el precio,
    cualquiera con las herramientas de desarrollador pediría tacos a un peso.
    """
    mesa: str = Field(min_length=1, max_length=20)
    items: list[ItemIn] = Field(min_length=1, max_length=40)
    nota: str = Field(default="", max_length=300)


@app.post("/pedidos", status_code=201)
def crear_pedido(payload: PedidoIn):
    # Si mandan el mismo producto en dos renglones, se suman.
    cantidades = defaultdict(int)
    for i in payload.items:
        cantidades[i.producto_id] += i.cantidad

    con = conectar()
    try:
        # BEGIN IMMEDIATE es el equivalente de FOR UPDATE en SQLite: toma el
        # candado de escritura desde ya, así nadie marca "agotado" a media
        # inserción. En Postgres esto sería SELECT ... FOR UPDATE.
        con.execute("BEGIN IMMEDIATE")

        marcas = ",".join("?" * len(cantidades))
        filas = con.execute(
            f"SELECT id, nombre, precio_centavos, disponible, activo "
            f"FROM productos WHERE id IN ({marcas})",
            list(cantidades),
        ).fetchall()
        prods = {f["id"]: f for f in filas}

        desconocidos = [
            i for i in cantidades if i not in prods or not prods[i]["activo"]
        ]
        agotados = [
            {"id": i, "nombre": prods[i]["nombre"]}
            for i in cantidades
            if i in prods and prods[i]["activo"] and not prods[i]["disponible"]
        ]

        if desconocidos or agotados:
            con.execute("ROLLBACK")
            raise HTTPException(
                409,
                {
                    "codigo": "no_disponible",
                    "agotados": agotados,
                    "desconocidos": desconocidos,
                    "mensaje": "Algunos productos ya no están disponibles.",
                },
            )

        total = sum(prods[i]["precio_centavos"] * c for i, c in cantidades.items())

        cur = con.execute(
            "INSERT INTO pedidos (mesa, total_centavos, estado, nota) "
            "VALUES (?, ?, 'recibido', ?)",
            (payload.mesa.strip(), total, payload.nota.strip()),
        )
        pedido_id = cur.lastrowid

        con.executemany(
            "INSERT INTO pedido_items "
            "(pedido_id, producto_id, nombre_snapshot, cantidad, precio_unit_centavos) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (pedido_id, i, prods[i]["nombre"], c, prods[i]["precio_centavos"])
                for i, c in cantidades.items()
            ],
        )

        con.execute("COMMIT")
    except HTTPException:
        raise
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()

    return {
        "pedido_id": pedido_id,
        "mesa": payload.mesa.strip(),
        "total_centavos": total,
        "estado": "recibido",
    }


@app.get("/pedidos/activos")
def pedidos_activos():
    """Lo que verá la tableta del taquero. Por ahora, para revisar a mano."""
    con = conectar()
    try:
        pedidos = con.execute(
            "SELECT id, mesa, total_centavos, estado, pagado, nota, creado_en "
            "FROM pedidos WHERE estado != 'entregado' ORDER BY creado_en"
        ).fetchall()
        items = con.execute(
            "SELECT pedido_id, nombre_snapshot, cantidad, precio_unit_centavos "
            "FROM pedido_items ORDER BY id"
        ).fetchall()
    finally:
        con.close()

    por_pedido = defaultdict(list)
    for it in items:
        por_pedido[it["pedido_id"]].append(
            {
                "nombre": it["nombre_snapshot"],
                "cantidad": it["cantidad"],
                "precio_unit_centavos": it["precio_unit_centavos"],
            }
        )

    return {
        "pedidos": [
            {**dict(p), "pagado": bool(p["pagado"]), "items": por_pedido[p["id"]]}
            for p in pedidos
        ]
    }


# ---------------------------------------------------------------- páginas

@app.get("/")
@app.get("/m/{mesa}")
def pagina_menu(mesa: str = ""):
    """La misma página para todas las mesas. El QR de cada mesa apunta a /m/5,
    y el número se lee desde el URL en el navegador."""
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
