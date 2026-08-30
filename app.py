"""Taquería Río Hondo — servidor.

Correr en local:
    uvicorn app:app --reload

Para abrirlo desde el celular en la misma red:
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

import os
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "riohondo.db")
STATIC = os.path.join(BASE, "static")

app = FastAPI(title="Taquería Río Hondo")


def conectar():
    if not os.path.exists(DB):
        raise HTTPException(500, "No existe riohondo.db. Corre: python seed.py")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


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


@app.get("/")
@app.get("/m/{mesa}")
def pagina_menu(mesa: str = ""):
    """La misma página para todas las mesas. El QR de cada mesa apunta a /m/5,
    y el número se lee desde el URL en el navegador."""
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
