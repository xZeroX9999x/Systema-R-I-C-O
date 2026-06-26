# ============================================================================
#  MÓDULO 4 — BACKTESTING VECTORIZADO (ESTABILIZADO)
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
    """Valida las señales de estrategia dual usando backtesting vectorizado real"""
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
    
    tickers = [r['simbolo'] for r in resultados_etfs + resultados_acciones if r]
    precios = {}
    
    # Descargar información histórica de control
    for ticker in tickers:
        try:
            data = vbt.YFData.download(ticker, period='5y').get('Close')
            if data is None or data.empty:
                logger.warning(f"No se pudieron obtener datos históricos para {ticker}")
                continue
            precios[ticker] = data
        except Exception as e:
            logger.warning(f"Error de red al descargar histórico de {ticker}: {e}")
            continue
    
    if not precios:
        logger.warning("Matriz de precios vacía. Saltando simulación vectorizada.")
        return {
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "detailed": {}
        }
    
    senal_compra = {}
    senal_venta = {}
    results = {}
    
    for ticker in tickers:
        if ticker not in precios:
            continue
            
        close = precios[ticker]
        rsi = vbt.RSI.run(close, 14).rsi
        macd = vbt.MACD.run(close)
        momentum = macd.hist
        
        # CORRECCIÓN: Se aplica la lógica dual unificada real (Condición + Histograma)
        senal_compra[ticker] = (rsi < 30) & (momentum > 0)
        senal_venta[ticker] = (rsi > 70) & (momentum < 0)
        
        buy_signals = senal_compra[ticker].reindex(close.index, fill_value=False)
        sell_signals = senal_venta[ticker].reindex(close.index, fill_value=False)
        
        if not buy_signals.any() or not sell_signals.any():
            continue
            
        try:
            pf = vbt.Portfolio.from_signals(
                close=close,
                entries=buy_signals,
                exits=sell_signals,
                fees=comision,
                slippage=0.001,
                init_cash=50000
            )
            
            results[ticker] = {
                "sharpe": float(np.nan_to_num(pf.sharpe_ratio())),
                "max_drawdown": float(np.nan_to_num(pf.max_drawdown())),
                "win_rate": float(np.nan_to_num(pf.win_rate())),
                "profit_factor": float(np.nan_to_num(pf.profit_factor())),
                "total_return": float(np.nan_to_num(pf.total_return()))
            }
        except Exception as e:
            logger.error(f"Inconsistencia matemática en portfolio de {ticker}: {e}")
            continue
            
    if not results:
        return {
            "sharpe": 0.0, "max_drawdown": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "total_return": 0.0, "detailed": {}
        }
    
    # Consolidación geométrica promediada
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
