# ============================================================================
#  MÓDULO 2 — GESTIÓN DE ESTADO (TRANSACCIONAL)
# ============================================================================

import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .config import load_settings  # ← Import relativo (crítico para CI)

logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """Obtiene conexión a la base de datos SQLite."""
    settings = load_settings()
    db_path = settings['DB_PATH']

    # Asegurar directorio
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Directorio creado: {db_dir}")

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error conectando a SQLite: {e}")
        raise RuntimeError(f"No se pudo abrir {db_path}") from e


def init_db(conn: sqlite3.Connection) -> None:
    """Inicializa el esquema de la base de datos."""
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posiciones (
        ticker TEXT PRIMARY KEY,
        tipo TEXT NOT NULL,
        precio_compra REAL NOT NULL,
        cantidad REAL NOT NULL,
        fecha_compra TEXT NOT NULL,
        maximo_desde_compra REAL NOT NULL,
        estado TEXT CHECK(estado IN ('ACTIVA', 'CERRADA')) DEFAULT 'ACTIVA',
        ultima_actualizacion TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transacciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('COMPRA', 'VENTA')),
        cantidad REAL NOT NULL,
        precio REAL NOT NULL,
        monto REAL NOT NULL,
        comision REAL NOT NULL,
        estado TEXT CHECK(estado IN ('PENDIENTE', 'EJECUTADA')) DEFAULT 'EJECUTADA'
    )
    ''')

    conn.commit()


def load_positions(conn: sqlite3.Connection) -> Dict[str, Dict]:
    """Carga posiciones activas."""
    init_db(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticker, tipo, precio_compra, cantidad,
               fecha_compra, maximo_desde_compra, estado
        FROM posiciones
        WHERE estado = 'ACTIVA'
    """)
    return {
        row[0]: {
            'ticker': row[0],
            'tipo': row[1],
            'precio_compra': row[2],
            'cantidad': row[3],
            'fecha_compra': row[4],
            'maximo_desde_compra': row[5],
            'estado': row[6]
        }
        for row in cursor.fetchall()
    }


def get_historico_compras(posiciones: Dict[str, Dict]) -> Dict[str, float]:
    """Devuelve precios de compra por ticker."""
    return {ticker: pos['precio_compra'] for ticker, pos in posiciones.items()}


def registrar_transacciones(
    conn: sqlite3.Connection,
    decision_result: Dict,
    resultados: List[Dict],
    usd_clp: float,
    fecha_hora: str
) -> None:
    """Registra transacciones con promedio de costo."""
    cursor = conn.cursor()
    settings = load_settings()

    # ETF
    etf = decision_result.get('etf', {})
    if etf.get('simbolo'):
        ticker = etf['simbolo']
        monto = etf['monto']
        precio = next((r['precio'] for r in resultados if r['simbolo'] == ticker), 0.0)
        if precio > 0:
            cantidad = monto / precio
            comision = monto * settings['COMISION']
            cursor.execute(
                "INSERT INTO transacciones (ticker, fecha, tipo, cantidad, precio, monto, comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticker, fecha_hora, 'COMPRA', cantidad, precio, monto, comision)
            )

            # Actualizar posición (promedio ponderado)
            cursor.execute(
                "SELECT precio_compra, cantidad FROM posiciones WHERE ticker = ? AND estado = 'ACTIVA'",
                (ticker,)
            )
            row = cursor.fetchone()
            if row:
                p_old, q_old = row
                q_new = q_old + cantidad
                p_new = (p_old * q_old + precio * cantidad) / q_new
                cursor.execute(
                    "UPDATE posiciones SET precio_compra = ?, cantidad = ?, maximo_desde_compra = MAX(maximo_desde_compra, ?), ultima_actualizacion = ? WHERE ticker = ?",
                    (p_new, q_new, precio, fecha_hora, ticker)
                )
            else:
                cursor.execute(
                    "INSERT INTO posiciones (ticker, tipo, precio_compra, cantidad, fecha_compra, maximo_desde_compra, estado, ultima_actualizacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticker, 'ETF', precio, cantidad, fecha_hora, precio, 'ACTIVA', fecha_hora)
                )

    # Acciones
    for acc in decision_result.get('acciones', []):
        ticker = acc['simbolo']
        monto = acc['monto']
        precio = next((r['precio'] for r in resultados if r['simbolo'] == ticker), 0.0)
        if precio > 0:
            cantidad = monto / precio
            comision = monto * settings['COMISION']
            cursor.execute(
                "INSERT INTO transacciones (ticker, fecha, tipo, cantidad, precio, monto, comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticker, fecha_hora, 'COMPRA', cantidad, precio, monto, comision)
            )

            cursor.execute(
                "SELECT precio_compra, cantidad FROM posiciones WHERE ticker = ? AND estado = 'ACTIVA'",
                (ticker,)
            )
            row = cursor.fetchone()
            if row:
                p_old, q_old = row
                q_new = q_old + cantidad
                p_new = (p_old * q_old + precio * cantidad) / q_new
                cursor.execute(
                    "UPDATE posiciones SET precio_compra = ?, cantidad = ?, maximo_desde_compra = MAX(maximo_desde_compra, ?), ultima_actualizacion = ? WHERE ticker = ?",
                    (p_new, q_new, precio, fecha_hora, ticker)
                )
            else:
                cursor.execute(
                    "INSERT INTO posiciones (ticker, tipo, precio_compra, cantidad, fecha_compra, maximo_desde_compra, estado, ultima_actualizacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticker, 'ACCION', precio, cantidad, fecha_hora, precio, 'ACTIVA', fecha_hora)
                )

    conn.commit()
    logger.info("Transacciones registradas.")


def actualizar_maximos(conn: sqlite3.Connection, resultados: List[Dict], fecha_hora: str) -> None:
    """Actualiza maximo_desde_compra para todas las posiciones activas."""
    cursor = conn.cursor()
    for r in resultados:
        ticker = r['simbolo']
        precio_actual = r['precio']
        cursor.execute(
            "UPDATE posiciones SET maximo_desde_compra = MAX(maximo_desde_compra, ?), ultima_actualizacion = ? WHERE ticker = ? AND estado = 'ACTIVA'",
            (precio_actual, fecha_hora, ticker)
        )
    conn.commit()
