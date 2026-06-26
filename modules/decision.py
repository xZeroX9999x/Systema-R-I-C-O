# ============================================================================
#  MÓDULO 7 — MOTOR DE DECISIÓN (CORREGIDO)
# ============================================================================

import logging
from typing import Dict, List, Any
from modules import allocation, technical
from modules.config import (
    APORTE_ETF_MENSUAL,
    APORTE_ACCIONES_MENSUAL,
    APORTE_CASH_MENSUAL,
    ASIGNACION_ACCIONES
)

logger = logging.getLogger(__name__)

def ejecutar_motor(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta el motor de decisión con asignación por volatilidad y priorización"""
    resultados_etfs = input_data['resultados_etfs']
    resultados_acciones = input_data['resultados_acciones']
    historico_compras = input_data['historico_compras']
    usd_clp = input_data['usd_clp']
    settings = input_data['settings']
    
    # 1. Validar datos de entrada
    if not resultados_etfs and not resultados_acciones:
        logger.error("No hay resultados de análisis. Abortando.")
        return {
            "etf": {"simbolo": None, "monto": 0, "razon": "Error: Datos faltantes"},
            "acciones": [],
            "reserva_cash": APORTE_CASH_MENSUAL,
            "total_asignado": 0,
            "sobrante": 0,
            "alertas_venta": [],
            "trailing_stops": [],
            "regimen": {"estado": "ERROR", "pausar_acciones": True, "mensaje": "Sin datos de análisis"},
            "mensaje": "Error: No se pudieron analizar los activos",
            "resultados": []
        }
    
    # 2. Detectar régimen de mercado
    vt_resultado = next((r for r in resultados_etfs if r["simbolo"] == "VT"), None)
    regimen = technical.detectar_regimen_mercado(vt_resultado)
    
    # 3. Inicializar estructura de decisión
    decision = {
        "etf":            {"simbolo": None, "monto": 0, "razon": ""},
        "acciones":       [],
        "reserva_cash":   APORTE_CASH_MENSUAL,
        "total_asignado": 0,
        "sobrante":       0,
        "alertas_venta":  [],
        "trailing_stops": [],
        "regimen":        regimen,
        "mensaje":        "",
        "resultados":     resultados_etfs + resultados_acciones,
        "backtest":       None,
        "contexto_llm":   None
    }

    for r in resultados_acciones:
        if r and r.get("alerta_venta"):
            decision["alertas_venta"].append(r)
        if r and r.get("trailing_stop"):
            decision["trailing_stops"].append(r)
    
    # --- ETF: DCA al mejor por momentum ---
    etfs_disponibles = [e for e in resultados_etfs if e and not e.get("circuit_breaker")]
    
    if etfs_disponibles:
        etfs_disponibles.sort(key=lambda x: x["score"], reverse=True)
        mejor_etf = etfs_disponibles[0]
        decision["etf"] = {
            "simbolo": mejor_etf["simbolo"],
            "monto":   APORTE_ETF_MENSUAL,
            "razon":   f"Mejor momentum (6m: {mejor_etf['momentum_6m']}%, 12m: {mejor_etf['momentum_12m']}%)",
        }
    else:
        decision["etf"] = {"simbolo": None, "monto": 0, "razon": "Todos los ETFs en circuit breaker"}
        decision["reserva_cash"] += APORTE_ETF_MENSUAL

    # --- Acciones: si modo cautela, todo a reserva ---
    if regimen["pausar_acciones"]:
        decision["reserva_cash"] += APORTE_ACCIONES_MENSUAL
        decision["mensaje"] = (
            f"Acciones en pausa por régimen de cautela. "
            f"{APORTE_ACCIONES_MENSUAL:,} CLP adicionales a reserva."
        )
    else:
        # 4. Filtrar y ORDENAR acciones comprables por score de forma descendente
        comprables = [a for a in resultados_acciones if a and a.get("senal") == "COMPRAR"]
        comprables.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        monto_disponible = APORTE_ACCIONES_MENSUAL
        
        # Ajustar montos según volatilidad targeting
        for i, accion in enumerate(comprables[:len(ASIGNACION_ACCIONES)]):
            monto = allocation.calcular_monto_vol_target(
                precio=accion["precio"],
                vol_anual_pct=accion["volatilidad"],
                riesgo_objetivo=settings['RISK_TARGET'],
                capital=monto_disponible
            )
            
            # Limitar según matriz operativa de presupuesto
            monto = max(5000, min(monto, ASIGNACION_ACCIONES[i]))
            
            # CORRECCIÓN: Se inyectan las llaves rsi y senal solicitadas por el módulo context.py
            decision["acciones"].append({
                "simbolo": accion["simbolo"],
                "monto":   monto,
                "rsi":     accion["rsi"],
                "senal":   accion["senal"],
                "razon":   f"Score {accion['score']} | RSI {accion['rsi']} | Vol {accion['volatilidad']}%",
            })
            monto_disponible -= monto
        
        # 5. Manejar remanente presupuestario
        if monto_disponible > 0:
            decision["reserva_cash"] += monto_disponible
            decision["mensaje"] += f" {monto_disponible:,.0f} CLP sin oportunidad táctica → reserva."

    # 6. Calcular métricas finales de control monetario
    decision["total_asignado"] = (
        decision["etf"]["monto"] +
        sum(a["monto"] for a in decision["acciones"]) +
        decision["reserva_cash"]
    )
    decision["sobrante"] = (APORTE_ETF_MENSUAL + APORTE_ACCIONES_MENSUAL + APORTE_CASH_MENSUAL) - decision["total_asignado"]
    
    return decision
