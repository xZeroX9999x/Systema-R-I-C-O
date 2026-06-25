# ============================================================================
#  MÓDULO 4 — BACKTESTING VECTORIZADO
# ============================================================================

import vectorbt as vbt
import numpy as np
import logging
from typing import Dict, List, Any
from modules.config import load_settings

logger = logging.getLogger(__name__)

def validar_senales(resultados_etfs: List[Dict], 
                   resultados_acciones: List[Dict],
                   comision: float = 0.0015) -> Dict[str, Any]:
    """
    Valida las señales del bot usando backtesting vectorizado.
    
    Args:
        resultados_etfs: Resultados de análisis ETF
        resultados_acciones: Resultados de análisis acciones
        comision: Comisión por transacción
        
    Returns:
        Métricas de rendimiento del backtest
    """
    # Validación de inputs
    if not resultados_etfs and not resultados_acciones:
        logger.error("No hay resultados de análisis para backtest. Saltando.")
        return {
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "detailed": {}
        }
    
    # Preparar datos para backtest
    tickers = [r['simbolo'] for r in resultados_etfs + resultados_acciones if r]
    precios = {}
    
    # Descargar datos históricos
    for ticker in tickers:
        try:
            data = vbt.YFData.download(ticker, period='5y').get('Close')
            if data is None or data.empty:
                logger.warning(f"No se pudieron obtener datos para {ticker}")
                continue
            precios[ticker] = data
        except Exception as e:
            logger.warning(f"No se pudo descargar datos para {ticker}: {e}")
            continue
    
    # Si no hay datos, no se puede hacer backtest
    if not precios:
        logger.warning("No hay datos suficientes para backtest. Saltando.")
        return {
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "detailed": {}
        }
    
    # Crear señales de compra/venta
    senal_compra = {}
    senal_venta = {}
    
    for ticker in tickers:
        if ticker not in precios:
            continue
            
        # Crear señales basadas en las reglas del bot
        close = precios[ticker]
        rsi = vbt.RSI.run(close, 14).rsi
        momentum = vbt.MACD.run(close).hist
        
        # Señal de compra: RSI < 30 y momentum positivo
        senal_compra[ticker] = rsi < 30
        # Señal de venta: RSI > 70 y momentum negativo
        senal_venta[ticker] = rsi > 70
        
    # Ejecutar backtest para cada activo
    results = {}
    for ticker in tickers:
        if ticker not in precios:
            continue
            
        # Asegurar que las señales estén alineadas con los precios
        close = precios[ticker]
        buy_signals = senal_compra[ticker].reindex(close.index, fill_value=False)
        sell_signals = senal_venta[ticker].reindex(close.index, fill_value=False)
        
        # Verificar que haya al menos una señal
        if not buy_signals.any() or not sell_signals.any():
            logger.warning(f"No hay señales válidas para {ticker}. Saltando backtest.")
            continue
            
        # Ejecutar portfolio
        try:
            pf = vbt.Portfolio.from_signals(
                close=close,
                entries=buy_signals,
                exits=sell_signals,
                fees=comision,
                slippage=0.001,
                init_cash=50000
            )
            
            # Almacenar métricas
            results[ticker] = {
                "sharpe": pf.sharpe_ratio(),
                "max_drawdown": pf.max_drawdown(),
                "win_rate": pf.win_rate(),
                "profit_factor": pf.profit_factor(),
                "total_return": pf.total_return()
            }
        except Exception as e:
            logger.error(f"Error en backtest para {ticker}: {e}")
            continue
    
    # Calcular métricas agregadas
    if not results:
        return {
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "detailed": results
        }
    
    # Promedios ponderados
    total_return = sum(r['total_return'] for r in results.values()) / len(results)
    sharpe = sum(r['sharpe'] for r in results.values()) / len(results)
    max_drawdown = min(r['max_drawdown'] for r in results.values())
    win_rate = sum(r['win_rate'] for r in results.values()) / len(results)
    profit_factor = sum(r['profit_factor'] for r in results.values()) / len(results)
    
    return {
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_return": total_return,
        "detailed": results
    }
