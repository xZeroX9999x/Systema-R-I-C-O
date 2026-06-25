# ============================================================================
#  MÓDULO 6 — CONTEXTO CUALITATIVO (LLM)
# ============================================================================

import os
import logging
import requests
from typing import Dict, List, Any
from modules.config import load_settings

logger = logging.getLogger(__name__)

def obtener_contexto_llm(acciones: List[Dict], 
                        api_key: str, 
                        model: str = "Qwen3.7-Max") -> Dict[str, Any]:
    """
    Obtiene contexto cualitativo para las acciones usando un LLM.
    
    Args:
        acciones: Lista de acciones con señales
        api_key: API key para el LLM
        model: Modelo a usar
        
    Returns:
        Contexto cualitativo para cada acción
    """
    if not api_key:
        logger.warning("LLM_API_KEY no configurado. Saltando contexto cualitativo.")
        return {}
    
    contexto = {}
    settings = load_settings()
    
    for acc in acciones:
        ticker = acc['simbolo']
        senal = acc['senal']
        rsi = acc['rsi']
        
        # Obtener noticias reales (en la práctica, se usaría una API real)
        try:
            noticias = obtener_noticias_reales(ticker)
        except Exception as e:
            logger.error(f"Error obteniendo noticias para {ticker}: {e}")
            noticias = [
                f"{ticker} announces new product launch",
                f"{ticker} reports strong quarterly earnings",
                f"Market analyst upgrades {ticker} to 'Buy'"
            ]
        
        # Generar contexto usando LLM
        try:
            contexto[ticker] = generar_contexto_llm(ticker, senal, rsi, noticias, api_key, model)
        except Exception as e:
            logger.error(f"Error generando contexto para {ticker}: {e}")
            contexto[ticker] = {
                "contexto": "No se pudo obtener contexto del LLM",
                "riesgo_clave": "N/A",
                "confianza": "BAJA"
            }
    
    return contexto

def obtener_noticias_reales(ticker: str) -> List[str]:
    """Obtiene noticias reales para un ticker (simulación)"""
    # En producción, esto se reemplazaría por una llamada a una API real de noticias
    return [
        f"{ticker} announces new product launch",
        f"{ticker} reports strong quarterly earnings",
        f"Market analyst upgrades {ticker} to 'Buy'"
    ]

def generar_contexto_llm(ticker: str, senal: str, rsi: float, noticias: list[str], 
                        api_key: str, model: str) -> Dict[str, Any]:
    """
    Genera contexto cualitativo usando un LLM.
    
    Args:
        ticker: Ticker del activo
        senal: Señal técnica
        rsi: Valor del RSI
        noticias: Noticias recientes
        api_key: API key para el LLM
        model: Modelo a usar
        
    Returns:
        Contexto cualitativo estructurado
    """
    # En producción, esto se reemplazaría por una llamada a la API del LLM
    prompt = f"""
    Activo: {ticker}. Señal técnica: {senal}. RSI: {rsi}.
    Noticias recientes: {'; '.join(noticias[:3])}
    Responde EXACTAMENTE en este formato:
    CONTEXTO: [1 línea]
    RIESGO_CLAVE: [1 línea]
    CONFIANZA: [ALTA/MEDIA/BAJA]
    No inventes datos. Si no hay información relevante, responde CONTEXTO: Sin catalizadores recientes.
    """
    
    try:
        # Simulación de llamada a API
        # En producción, se usaría requests.post para llamar a la API real
        return {
            "contexto": "El contexto es positivo con noticias de crecimiento",
            "riesgo_clave": "Riesgo de sobrevaloración",
            "confianza": "MEDIA"
        }
    except Exception as e:
        logger.error(f"Error en llamada a LLM para {ticker}: {e}")
        return {
            "contexto": "No se pudo obtener contexto del LLM",
            "riesgo_clave": "N/A",
            "confianza": "BAJA"
        }
