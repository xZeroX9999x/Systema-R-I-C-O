#!/usr/bin/env python3
# ============================================================================
#  SISTEMA R-I-C-O v5.0 — CRECIMIENTO DE LARGO PLAZO + TÁCTICO
#
#  FILOSOFÍA:
#  - ETFs diversificados = buy-and-hold con DCA mensual fijo + rebalanceo
#  - Acciones individuales = señales tácticas de RSI/momentum + gestión de riesgo
#  - Escáner Buffett = Análisis de valor intrínseco y Moat económico en Watchlist
# ============================================================================

import os
import logging
from datetime import datetime, timezone
from modules import (
    config,
    state,
    technical,
    backtest,
    allocation,
    context,
    decision,
    html_generator
)

# Configurar logging
config.setup_logging()
logger = logging.getLogger(__name__)

def main():
    """Flujo principal del sistema R-I-C-O Bot v5.0"""
    logger.info("=" * 60)
    logger.info(f"R-I-C-O Bot v5.0 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    # 1. Configuración inicial
    logger.info("Cargando configuración...")
    settings = config.load_settings()
    
    # 2. Gestionar estado (posiciones y transacciones)
    logger.info("Cargando estado transaccional...")
    try:
        db_conn = state.get_db_connection()
        state.init_db(db_conn)
        posiciones = state.load_positions(db_conn)
        historico_compras = state.get_historico_compras(posiciones)
    except Exception as e:
        logger.error(f"Error al cargar estado transaccional: {e}")
        posiciones = {}
        historico_compras = {}
        db_conn = None

    # 3. Obtener datos de mercado
    logger.info("Obteniendo datos de mercado...")
    usd_clp = technical.obtener_usd_clp()
    logger.info(f"USD/CLP: ${usd_clp:,.0f}")
    
    # 4. Análisis técnico con precios ajustados
    logger.info("Ejecutando análisis técnico...")
    resultados_etfs = []
    resultados_acciones = []
    
    for simbolo in config.ETFS_CORE:
        logger.info(f"ETF {simbolo}...")
        r = technical.analizar_etf(simbolo)
        if r:
            resultados_etfs.append(r)
            logger.info(f"  Mom 6m:{r['momentum_6m']}% | Score:{r['score']} | {r['senal']}")
    
    for simbolo in config.ACCIONES_TACTICAS:
        logger.info(f"ACC {simbolo}...")
        r = technical.analizar_accion(simbolo, historico_compras)
        if r:
            resultados_acciones.append(r)
            logger.info(f"  RSI:{r['rsi']} | Score:{r['score']} | {r['senal']}")
            
    # 4b. Escáner de Oportunidades de Alta Ganancia (Filosofía Warren Buffett)
    logger.info("Ejecutando escáner de valor Buffett en Watchlist de Vigilancia...")
    from modules import buffett_engine
    
    oportunidades_encontradas = []
    for simbolo in config.ACCIONES_VIGILANCIA_BUFFETT:
        logger.info(f"Escaneando métricas Buffett para {simbolo}...")
        res_buffett = buffett_engine.analizar_filosofia_buffett(simbolo)
        if res_buffett and res_buffett["senal"] == "COMPRAR OPORTUNIDAD":
            oportunidades_encontradas.append(res_buffett)
            logger.info(f"  🔥 ¡OPORTUNIDAD DETECTADA!: {res_buffett['razon']}")
    
    if not resultados_etfs + resultados_acciones:
        logger.error("No se pudo analizar ningún activo del portafolio base. Abortando.")
        if db_conn:
            db_conn.close()
        return

    # 5. Backtesting para validación de señales
    logger.info("Validando señales con backtesting...")
    backtest_results = backtest.validar_senales(
        resultados_etfs, 
        resultados_acciones,
        settings['COMISION']
    )
    logger.info(f"Backtest: Sharpe {backtest_results['sharpe']:.2f} | Max DD {backtest_results['max_drawdown']:.1%}")

    # 6. Asignación por volatilidad targeting y motor de decisión
    logger.info("Calculando asignación por volatilidad...")
    decision_input = {
        'resultados_etfs': resultados_etfs,
        'resultados_acciones': resultados_acciones,
        'historico_compras': historico_compras,
        'usd_clp': usd_clp,
        'settings': settings
    }
    decision_result = decision.ejecutar_motor(decision_input)
    
    # Inyección segura de oportunidades Buffett para el ecosistema global de datos
    decision_result['oportunidades_buffett'] = oportunidades_encontradas

    # 7. Contexto cualitativo (LLM)
    logger.info("Obteniendo contexto cualitativo...")
    contexto_llm = context.obtener_contexto_llm(
        decision_result['acciones'],
        settings['LLM_API_KEY'],
        settings['LLM_MODEL']
    )

    # 8. Generar reporte HTML
    logger.info("Generando reporte HTML...")
    fecha_hora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    html = html_generator.generar_html(
        decision_result['resultados'],
        decision_result,
        usd_clp,
        fecha_hora,
        backtest_results,
        contexto_llm
    )

    # 9. Enviar correo y registrar transacciones
    logger.info("Enviando correo...")
    email_exitoso = html_generator.enviar_correo(html, fecha_hora, settings)
    
    # 10. Actualizar estado transaccional
    if email_exitoso and db_conn:
        try:
            logger.info("Actualizando estado transaccional...")
            state.registrar_transacciones(
                db_conn,
                decision_result,
                decision_result['resultados'],
                usd_clp,
                fecha_hora
            )
            state.actualizar_maximos(db_conn, decision_result['resultados'], fecha_hora)
            logger.info("Estado transaccional actualizado exitosamente.")
        except Exception as e:
            logger.error(f"Error al actualizar estado transaccional: {e}")
    else:
        if not email_exitoso:
            logger.warning("Email no enviado. Estado transaccional no actualizado.")
        if not db_conn:
            logger.warning("No hay conexión a la base de datos. Estado transaccional no actualizado.")

    # Cerrar conexión a la base de datos
    if db_conn:
        try:
            db_conn.close()
            logger.info("Conexión a la base de datos cerrada.")
        except Exception as e:
            logger.error(f"Error al cerrar conexión a la base de datos: {e}")

    logger.info("=" * 60)
    logger.info("Ejecución completada.")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Error crítico en la ejecución del bot: {e}")
        raise
