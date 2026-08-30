PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categorias (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT    NOT NULL UNIQUE,
    orden   INTEGER NOT NULL DEFAULT 0
);

-- precio_centavos: el dinero SIEMPRE en enteros. 30.00 MXN = 3000.
-- Con float, 0.1 + 0.2 != 0.3 y los cortes de caja no cuadran.
CREATE TABLE IF NOT EXISTS productos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id    INTEGER NOT NULL REFERENCES categorias(id),
    nombre          TEXT    NOT NULL,
    descripcion     TEXT    NOT NULL DEFAULT '',
    precio_centavos INTEGER NOT NULL,
    imagen          TEXT,
    -- disponible: se acabó hoy. Lo mueve el taquero, se resetea cada mañana.
    disponible      INTEGER NOT NULL DEFAULT 1,
    -- activo: ya no lo vendemos. Lo mueves tú, es permanente.
    activo          INTEGER NOT NULL DEFAULT 1,
    orden           INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria_id);

CREATE TABLE IF NOT EXISTS pedidos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mesa            TEXT    NOT NULL,
    total_centavos  INTEGER NOT NULL,
    -- pendiente_pago -> recibido -> preparando -> listo -> entregado
    estado          TEXT    NOT NULL DEFAULT 'pendiente_pago',
    pagado          INTEGER NOT NULL DEFAULT 0,
    metodo_pago     TEXT,
    nota            TEXT    NOT NULL DEFAULT '',
    creado_en       TEXT    NOT NULL DEFAULT (datetime('now')),
    actualizado_en  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos(estado);

-- precio_unit_centavos se congela aquí. Si mañana sube el taco,
-- los pedidos de hoy conservan su precio y los reportes cuadran.
CREATE TABLE IF NOT EXISTS pedido_items (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id            INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    producto_id          INTEGER NOT NULL REFERENCES productos(id),
    nombre_snapshot      TEXT    NOT NULL,
    cantidad             INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unit_centavos INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_pedido ON pedido_items(pedido_id);

CREATE TABLE IF NOT EXISTS precio_historial (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id              INTEGER NOT NULL REFERENCES productos(id),
    precio_anterior_centavos INTEGER NOT NULL,
    precio_nuevo_centavos    INTEGER NOT NULL,
    cambiado_en              TEXT    NOT NULL DEFAULT (datetime('now'))
);
