def load_settings():
    """Carga configuración con manejo robusto de variables vacías."""
    
    def _get_int(key: str, default: int) -> int:
        val = os.environ.get(key, "").strip()
        return int(val) if val else default

    def _get_float(key: str, default: float) -> float:
        val = os.environ.get(key, "").strip()
        try:
            return float(val) if val else default
        except ValueError:
            return default

    return {
        'EMAIL_DESTINO':    os.environ.get("EMAIL_DESTINO", "").strip(),
        'EMAIL_USUARIO':    os.environ.get("EMAIL_USUARIO", "").strip(),
        'EMAIL_PASSWORD':   os.environ.get("EMAIL_PASSWORD", ""),
        'SMTP_SERVER':      os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip(),
        'SMTP_PORT':        _get_int("SMTP_PORT", 587),          # ← Fix crítico
        'USD_CLP_FALLBACK': _get_float("USD_CLP_FALLBACK", 950.0),
        'LLM_API_KEY':      os.environ.get("LLM_API_KEY", "").strip(),
        'LLM_MODEL':        os.environ.get("LLM_MODEL", "Qwen3.7-Max").strip(),
        'COMISION':         _get_float("COMISION", 0.0015),
        'RISK_TARGET':      _get_float("RISK_TARGET", 0.02),
        'DB_PATH':          os.environ.get("DB_PATH", "db/posiciones.db").strip(),
    }
