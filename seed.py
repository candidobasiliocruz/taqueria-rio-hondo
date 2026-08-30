"""Crea riohondo.db y carga el menú inicial.

    python seed.py          crea la base si no existe
    python seed.py --reset  la borra y la vuelve a crear

OJO: los precios son de arranque, puestos para que veas la página funcionando.
Cámbialos por los reales antes de enseñárselo a alguien.
"""

import argparse
import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), "riohondo.db")
SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")

# (categoría, [(nombre, descripción, precio en pesos), ...])
MENU = [
    ("Tacos", [
        ("Taco de barbacoa", "", 35),
        ("Taco de cabeza", "", 30),
        ("Taco de pancita", "", 30),
        ("Taco de pata", "", 30),
    ]),
    ("Mixiotes", [
        ("Mixiote de pollo", "", 75),
        ("Mixiote de puerco", "", 75),
    ]),
    ("Consomé", [
        ("Consomé chico", "", 25),
        ("Consomé grande", "", 45),
    ]),
    ("Para acompañar", [
        ("Pan", "", 15),
    ]),
    ("Refrescos", [
        ("Coca Cola", "", 25),
        ("Boing", "", 22),
    ]),
    ("Café y té", [
        ("Café", "", 20),
        ("Té", "", 20),
    ]),
    ("Cervezas", [
        ("Cerveza", "", 40),
    ]),
]


def crear(reset=False):
    if reset and os.path.exists(DB):
        os.remove(DB)
        print("Base anterior borrada.")

    nueva = not os.path.exists(DB)
    con = sqlite3.connect(DB)
    con.executescript(open(SCHEMA, encoding="utf-8").read())

    if not nueva:
        con.close()
        print("La base ya existía, no se tocó el menú. Usa --reset para rehacerla.")
        return

    for orden_cat, (categoria, productos) in enumerate(MENU):
        cur = con.execute(
            "INSERT INTO categorias (nombre, orden) VALUES (?, ?)",
            (categoria, orden_cat),
        )
        cat_id = cur.lastrowid
        for orden_prod, (nombre, desc, pesos) in enumerate(productos):
            con.execute(
                "INSERT INTO productos "
                "(categoria_id, nombre, descripcion, precio_centavos, orden) "
                "VALUES (?, ?, ?, ?, ?)",
                (cat_id, nombre, desc, int(round(pesos * 100)), orden_prod),
            )

    con.commit()
    total = con.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    con.close()
    print(f"Listo: {total} productos en {len(MENU)} categorías.")
    print("Recuerda ajustar los precios reales.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true", help="borra la base y la rehace")
    crear(reset=p.parse_args().reset)
