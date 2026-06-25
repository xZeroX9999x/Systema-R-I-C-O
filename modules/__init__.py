# Este archivo es OBLIGATORIO para que Python reconozca 'modules' como paquete.
from .config import load_settings
from .state import get_db_connection, init_db, load_positions, registrar_transacciones, actualizar_maximos
from .technical import analizar_etf, analizar_accion, detectar_regimen_mercado, obtener_usd_clp
from .backtest import validar_senales
from .allocation import calcular_monto_vol_target
from .context import obtener_contexto_llm
from .decision import ejecutar_motor
from .html_generator import generar_html, enviar_correo

__all__ = [
    "load_settings",
    "get_db_connection", "init_db", "load_positions", "registrar_transacciones", "actualizar_maximos",
    "analizar_etf", "analizar_accion", "detectar_regimen_mercado", "obtener_usd_clp",
    "validar_senales",
    "calcular_monto_vol_target",
    "obtener_contexto_llm",
    "ejecutar_motor",
    "generar_html", "enviar_correo"
]
