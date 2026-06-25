# ============================================================================
#  MÓDULO 1 — CONFIGURACIÓN COMPLETA
# ============================================================================

import os
import logging
from typing import Dict, Any

# Configuración de logging
def setup_logging():
    """Configura el sistema de logging para el proyecto"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("rico_bot.log", encoding='utf-8')
        ]
    )
    logging.getLogger('yfinance').setLevel(logging.WARNING)


def load_settings() -> Dict[str, Any]:
    """Carga configuración con manejo robusto de variables vacías."""
    
    def _get_int(key: str, default: int) -> int:
        val = os.environ.get(key, "").strip()
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            logging.getLogger(__name__).warning(
                f"Valor inválido para {key}='{val}', usando default={default}"
            )
            return default

    def _get_float(key: str, default: float) -> float:
        val = os.environ.get(key, "").strip()
        if not val:
            return default
        try:
            return float(val)
        except ValueError:
            logging.getLogger(__name__).warning(
                f"Valor inválido para {key}='{val}', usando default={default}"
            )
            return default

    return {
        'EMAIL_DESTINO':    os.environ.get("EMAIL_DESTINO", "").strip(),
        'EMAIL_USUARIO':    os.environ.get("EMAIL_USUARIO", "").strip(),
        'EMAIL_PASSWORD':   os.environ.get("EMAIL_PASSWORD", ""),
        'SMTP_SERVER':      os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip(),
        'SMTP_PORT':        _get_int("SMTP_PORT", 587),
        'USD_CLP_FALLBACK': _get_float("USD_CLP_FALLBACK", 950.0),
        'LLM_API_KEY':      os.environ.get("LLM_API_KEY", "").strip(),
        'LLM_MODEL':        os.environ.get("LLM_MODEL", "Qwen3.7-Max").strip(),
        'COMISION':         _get_float("COMISION", 0.0015),
        'RISK_TARGET':      _get_float("RISK_TARGET", 0.02),
        'DB_PATH':          os.environ.get("DB_PATH", "db/posiciones.db").strip(),
    }


# ============================================================================
#  CONSTANTES DE CONFIGURACIÓN DEL BOT
# ============================================================================

# Clasificación de activos
ETFS_CORE = ["VT", "ITOT"]
ACCIONES_TACTICAS = ["NVDA", "IBIT", "CGW", "TTWO", "BBAI"]
ALL_TICKERS = ETFS_CORE + ACCIONES_TACTICAS

# Presupuesto y asignación
PRESUPUESTO_MENSUAL = 50000
APORTE_ETF_MENSUAL = 30000
APORTE_ACCIONES_MENSUAL = 17500
APORTE_CASH_MENSUAL = 2500
ASIGNACION_ACCIONES = [12500, 5000]

# Parámetros ETFs (largo plazo)
ETF_MOMENTUM_CORTO_MESES = 6
ETF_MOMENTUM_LARGO_MESES = 12
ETF_PAUSA_RSI_MENSUAL = 80
ETF_PAUSA_DIST_MA200_PCT = 25

# Parámetros acciones (táctico)
ACCION_RSI_MAX_COMPRA = 60
ACCION_MOMENTUM_MIN_3M = -10
ACCION_VOLUMEN_MIN_RATIO = 0.6
ACCION_SURGE_PCT_SEMANAL = 15.0
ACCION_SURGE_RSI_MIN = 70
ACCION_TRAILING_STOP_PCT = 15.0

ACCION_VENTA_FASES = {
    "FASE_1": {"rsi": 72, "vender_pct": 25, "etiqueta": "Reducir 25% — RSI caliente"},
    "FASE_2": {"rsi": 78, "vender_pct": 35, "etiqueta": "Reducir 35% — RSI sobrecalentado"},
    "FASE_3": {"rsi": 85, "vender_pct": 50, "etiqueta": "Reducir 50% — RSI extremo"},
}

# Régimen de mercado
MERCADO_ALERTA_VT_RSI_SEMANAL = 78
MERCADO_ALERTA_VOLATILIDAD = 35
MERCADO_ALERTA_DIST_MA200_PCT = 20
