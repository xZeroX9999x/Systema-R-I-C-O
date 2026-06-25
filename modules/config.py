import os
import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')

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
