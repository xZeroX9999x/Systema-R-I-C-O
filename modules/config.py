import os
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger('yfinance').setLevel(logging.WARNING)

def load_settings():
    return {
        'EMAIL_DESTINO': os.environ.get("EMAIL_DESTINO", ""),
        'EMAIL_USUARIO': os.environ.get("EMAIL_USUARIO", ""),
        'EMAIL_PASSWORD': os.environ.get("EMAIL_PASSWORD", ""),
        'SMTP_SERVER': os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        'SMTP_PORT': int(os.environ.get("SMTP_PORT", "587")),
        'USD_CLP_FALLBACK': float(os.environ.get("USD_CLP_FALLBACK", "950.0")),
        'LLM_API_KEY': os.environ.get("LLM_API_KEY", ""),
        'LLM_MODEL': os.environ.get("LLM_MODEL", "Qwen3.7-Max"),
        'COMISION': float(os.environ.get("COMISION", "0.0015")),
        'RISK_TARGET': float(os.environ.get("RISK_TARGET", "0.02")),
        'DB_PATH': os.environ.get("DB_PATH", "db/posiciones.db")
    }

ETFS_CORE = ["VT", "ITOT"]
ACCIONES_TACTICAS = ["NVDA", "IBIT", "CGW", "TTWO", "BBAI"]
ALL_TICKERS = ETFS_CORE + ACCIONES_TACTICAS
PRESUPUESTO_MENSUAL = 50000
APORTE_ETF_MENSUAL = 30000
APORTE_ACCIONES_MENSUAL = 17500
APORTE_CASH_MENSUAL = 2500
ASIGNACION_ACCIONES = [12500, 5000]
ETF_MOMENTUM_CORTO_MESES = 6
ETF_MOMENTUM_LARGO_MESES = 12
ETF_PAUSA_RSI_MENSUAL = 80
ETF_PAUSA_DIST_MA200_PCT = 25
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
MERCADO_ALERTA_VT_RSI_SEMANAL = 78
MERCADO_ALERTA_VOLATILIDAD = 35
MERCADO_ALERTA_DIST_MA200_PCT = 20
