# Taquería Río Hondo — v1

Menú digital. Esta primera versión es **solo lectura**: el cliente ve el menú
desde su celular, todavía no pide. El carrito es el siguiente paso.

## Correr

```bash
pip install fastapi "uvicorn[standard]"
python seed.py
uvicorn app:app --reload
```

Abre http://localhost:8000

Para verlo desde tu celular en la misma red WiFi:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Y entras desde el celular a `http://<ip-de-tu-compu>:8000`

## Archivos

| Archivo | Qué hace |
|---|---|
| `schema.sql` | Tablas. Incluye ya las de pedidos, para no migrar después |
| `seed.py` | Crea la base y carga el menú. `--reset` la rehace desde cero |
| `app.py` | Servidor. `GET /api/menu` y las rutas de la página |
| `static/index.html` | La página del cliente |

## Rutas

- `GET /` — el menú
- `GET /m/5` — el menú con "Mesa 5" en el encabezado. Aquí apunta el QR
- `GET /api/menu` — el JSON

## Antes de enseñárselo a alguien

**Los precios son de arranque, los puse para que veas la página funcionando.**
Ajústalos con los reales:

```bash
python -c "
import sqlite3
c = sqlite3.connect('riohondo.db')
c.execute('UPDATE productos SET precio_centavos=? WHERE nombre=?', (3500, 'Taco de barbacoa'))
c.commit()"
```

Cuando llegue el panel de admin esto se hace desde la pantalla.

## Dos cosas del código que vale la pena que no se pierdan

**El dinero va en centavos, en enteros.** `precio_centavos = 3000` son $30.00.
Con `float`, `0.1 + 0.2` no da `0.3` y los cortes de caja acaban con diferencias
de centavos que nadie sabe de dónde salieron.

**`disponible` y `activo` son distintos.** `disponible` es "se acabó hoy", lo
mueve el taquero y se resetea cada mañana. `activo` es "ya no lo vendemos", lo
mueves tú y es permanente. Si los juntas en un solo campo, el reset de la mañana
te va a resucitar productos que quitaste hace un mes.

## Probar el estado de agotado

```bash
python -c "
import sqlite3
c = sqlite3.connect('riohondo.db')
c.execute(\"UPDATE productos SET disponible=0 WHERE nombre='Taco de pata'\")
c.commit()"
```

Recarga la página: el producto aparece en gris con "Hoy no hay". Se queda
visible a propósito, para que el cliente entienda que existe pero hoy no lo hay,
en lugar de preguntarse si lo quitaron.

## Pendiente

- Las tipografías cargan desde Google Fonts. Cuando esto salga a producción con
  el hotspot, descárgalas y sírvelas desde `/static` — son dos peticiones menos
  y una dependencia externa menos.
- Sin fotos todavía. Cuando las agregues: WebP, 600px máximo, carga diferida.

## Siguiente

Carrito → `POST /pedidos` con la validación de disponibilidad → vista del
taquero → panel de agotados → admin → pagos.
