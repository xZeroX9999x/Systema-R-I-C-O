# ============================================================================
#  MÓDULO 5 — ASIGNACIÓN POR VOLATILIDAD (RISK BUDGETING)
# ============================================================================

import numpy as np
import logging
from modules.config import APORTE_ACCIONES_MENSUAL

logger = logging.getLogger(__name__)

def calcular_monto_vol_target(precio: float, vol_anual_pct: float, 
                           riesgo_objetivo: float = 0.02, 
                           capital: float = 50000) -> float:
    """
    Calcula el monto óptimo para una posición basado en volatilidad.
    
    Args:
        precio: Precio actual del activo
        vol_anual_pct: Volatilidad anualizada en porcentaje
        riesgo_objetivo: Riesgo máximo deseado (ej: 0.02 = 2%)
        capital: Capital total disponible
        
    Returns:
        Monto óptimo para la posición
    """
    # Validación de inputs
    if precio <= 0:
        logger.warning(f"Precio inválido ({precio}), usando valor por defecto de 100.0")
        precio = 100.0
    
    if vol_anual_pct < 0.1 or vol_anual_pct > 100:
        logger.warning(f"Volatilidad inválida ({vol_anual_pct}%), usando valor por defecto de 30.0")
        vol_anual_pct = 30.0
    
    # Convertir volatilidad a decimal
    vol_anual = vol_anual_pct / 100
    
    # Calcular volatilidad diaria
    vol_diaria = vol_anual / np.sqrt(252)
    
    # Calcular el monto que corresponde al riesgo objetivo
    monto_riesgo = capital * riesgo_objetivo
    
    # Calcular la cantidad de activos (en USD)
    try:
        cantidad_usd = monto_riesgo / (vol_diaria * precio)
    except ZeroDivisionError:
        logger.error("División por cero en cálculo de cantidad. Usando monto mínimo.")
        cantidad_usd = 50.0
    
    # Convertir a CLP
    monto_clp = cantidad_usd * precio
    
    # Ajustar a límites operativos
    monto_clp = max(5000, min(monto_clp, 15000))
    
    return monto_clp
