# ============================================================================
#  MÓDULO 2 — GESTIÓN DE ESTADO TRANSACTIONAL (CORREGIDO)
# ============================================================================

import sqlite3
import os
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .config import load_settings

logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    settings = load_settings()
    db_path = settings['DB_PATH']
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
    init_db(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticker, tipo, precio_compra, cantidad, fecha_compra, maximo_desde_compra, estado
        FROM posiciones WHERE estado = 'ACTIVA'
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
    return {ticker: pos['precio_compra'] for ticker, pos in posiciones.items()}


def registrar_transacciones(
    conn: sqlite3.Connection,
    decision_result: Dict,
    resultados: List[Dict],
    usd_clp: float,
    fecha_hora: str
) -> None:
    cursor = conn.cursor()
    settings = load_settings()

    # 1. PROCESAR ETF CORE
    etf = decision_result.get('etf', {})
    if etf.get('simbolo'):
        ticker = etf['simbolo']
        monto = etf['monto']
        precio = next((r['precio'] for r in resultados if r['simbolo'] == ticker), 0.0)
        if precio > 0:
            # CORRECCIÓN: Conversión correcta usando tipo de cambio (CLP / (USD * TASA))
            cantidad = monto / (precio * usd_clp)
            comision = monto * settings['COMISION']
            
            cursor.execute(
                "INSERT INTO transacciones (ticker, fecha, tipo, cantidad, precio, monto, comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticker, fecha_hora, 'COMPRA', cantidad, precio, monto, comision)
            )
            cursor.execute(
                "SELECT precio_compra, cantidad FROM posiciones WHERE ticker = ? AND estado = 'ACTIVA'", (ticker,)
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

    # 2. PROCESAR ACCIONES TÁCTICAS
    for acc in decision_result.get('acciones', []):
        ticker = acc['simbolo']
        monto = acc['monto']
        precio = next((r['precio'] for r in resultados if r['simbolo'] == ticker), 0.0)
        if precio > 0:
            # CORRECCIÓN: Conversión de divisa integrada
            cantidad = monto / (precio * usd_clp)
            comision = monto * settings['COMISION']
            
            cursor.execute(
                "INSERT INTO transacciones (ticker, fecha, tipo, cantidad, precio, monto, comision) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticker, fecha_hora, 'COMPRA', cantidad, precio, monto, comision)
            )
            cursor.execute(
                "SELECT precio_compra, cantidad FROM posiciones WHERE ticker = ? AND estado = 'ACTIVA'", (ticker,)
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
    logger.info("Transacciones registradas en SQLite de forma balanceada.")

    # 3. ACTUALIZAR HISTÓRICO CSV PARA GITHUB ACTIONS (CORRECCIÓN)
    csv_path = "historico_decisiones.csv"
    if os.path.exists(csv_path):
        try:
            regimen_estado = decision_result.get('regimen', {}).get('estado', 'NORMAL')
            with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for r in resultados:
                    if not r:
                        continue
                    
                    # Calcular el monto adjudicado a este ticker específico
                    monto_asignado = 0
                    if decision_result.get('etf', {}).get('simbolo') == r['simbolo']:
                        monto_asignado = decision_result['etf']['monto']
                    for a in decision_result.get('acciones', []):
                        if a['simbolo'] == r['simbolo']:
                            monto_asignado = a['monto']
                    
                    # Mapeo idéntico de cabeceras estructurales
                    writer.writerow([
                        fecha_hora,
                        r.get('simbolo'),
                        r.get('tipo'),
                        r.get('precio'),
                        r.get('rsi'),
                        r.get('rsi_semanal'),
                        r.get('rsi_mensual'),
                        r.get('momentum_6m'),
                        r.get('momentum_12m'),
                        r.get('ma20'),
                        r.get('ma200'),
                        r.get('volatilidad'),
                        r.get('vol_ratio'),
                        r.get('tendencia'),
                        r.get('score'),
                        r.get('senal'),
                        monto_asignado,
                        usd_clp,
                        regimen_estado
                    ])
            logger.info("Archivo log histórico CSV sincronizado correctamente.")
        except Exception as csv_err:
            logger.error(f"Fallo al registrar líneas en histórico CSV: {csv_err}")


def actualizar_maximos(conn: sqlite3.Connection, resultados: List[Dict], fecha_hora: str) -> None:
    cursor = conn.cursor()
    for r in resultados:
        if not r:
            continue
        ticker = r['simbolo']
        precio_actual = r['precio']
        cursor.execute(
            "UPDATE posiciones SET maximo_desde_compra = MAX(maximo_desde_compra, ?), ultima_actualizacion = ? WHERE ticker = ? AND estado = 'ACTIVA'",
            (precio_actual, fecha_hora, ticker)
        )
    conn.commit()
