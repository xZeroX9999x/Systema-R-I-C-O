# ============================================================================
#  NUEVO MÓDULO R-I-C-O — MOTOR VALOR INTRÍNSECO (FILOSOFÍA WARREN BUFFETT)
# ============================================================================

import yfinance as yf
import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def analizar_filosofia_buffett(simbolo: str) -> Optional[Dict[str, Any]]:
    """
    Escanea un activo bajo los criterios cuantitativos rigurosos de Warren Buffett.
    Evita la lectura directa de la SEC usando los estados financieros consolidados de yfinance.
    """
    try:
        ticker = yf.Ticker(simbolo)
        
        # 1. Cargar Estados Financieros Históricos (Últimos 3-4 años)
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        if financials.empty or balance_sheet.empty or cashflow.empty:
            logger.warning(f"Filtro Buffett: {simbolo} no tiene estados financieros suficientes.")
            return None
            
        # Extraer variables clave del último año con manejo robusto de nombres de filas
        try:
            # Soporte para variaciones de nombres en el índice de yfinance
            revenue = financials.loc['Total Revenue'].iloc[0]
            net_income = financials.loc['Net Income'].iloc[0]
            operating_income = financials.loc['Operating Income'].iloc[0]
            gross_profit = financials.loc['Gross Profit'].iloc[0]
            
            equity = balance_sheet.loc['Stockholders Equity'].iloc[0]
            # Manejar si la deuda total no está consolidada explícitamente
            total_debt = 0.0
            for debt_key in ['Total Debt', 'Long Term Debt', 'Commercial Paper']:
                if debt_key in balance_sheet.index:
                    total_debt += balance_sheet.loc[debt_key].iloc[0]
                    
            free_cash_flow = cashflow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cashflow.index else None
            if free_cash_flow is None:
                # Proxy alternativo de Owner Earnings si no viene la fila explícita
                operating_cash = cashflow.loc['Operating Cash Flow'].iloc[0]
                capex = abs(cashflow.loc['Capital Expenditure'].iloc[0]) if 'Capital Expenditure' in cashflow.index else 0.0
                free_cash_flow = operating_cash - capex
                
        except KeyError as ke:
            logger.warning(f"Filtro Buffett: {simbolo} carece de la métrica contable esencial {ke}. Saltando.")
            return None

        # 2. CALCULAR LOS RATIOS FINANCIEROS DE BUFFETT
        # Margen Bruto (Ventaja de manufactura/precios)
        margen_bruto = round((gross_profit / revenue) * 100, 2)
        # Margen Operativo (Eficiencia interna y Moat comercial)
        margen_operativo = round((operating_income / revenue) * 100, 2)
        # Retorno sobre Capital Propio (ROE)
        roe = round((net_income / equity) * 100, 2) if equity > 0 else 0.0
        # Años necesarios para pagar la deuda con la utilidad neta actual
        anos_pago_deuda = round(total_debt / net_income, 2) if net_income > 0 else 999.0

        # Historial de estabilidad: Verificar que las ganancias netas no sean erráticas
        historico_net_income = financials.loc['Net Income'].values
        ganancias_estables = all(x > 0 for x in historico_net_income if not np.isnan(x))

        # 3. EVALUACIÓN PASA/NO PASA (Puntuación Cuantitativa de Moat)
        puntos_score = 0
        if margen_bruto >= 40.0: puntos_score += 25
        if margen_operativo >= 15.0: puntos_score += 25
        if roe >= 15.0: puntos_score += 25
        if anos_pago_deuda <= 3.5: puntos_score += 25
        if not ganancias_estables: puntos_score -= 30  # Castigo por pérdidas recientes

        # 4. VALORACIÓN: CÁLCULO DEL VALOR INTRÍNSECO (Flujo de Caja Capitalizado Conservador)
        # Usamos un modelo de crecimiento de cupones modificado de Buffett (tasa de descuento del 10%)
        precio_actual = ticker.history(period="1d")["Close"].iloc[-1]
        info = ticker.info
        shares_outstanding = info.get('sharesOutstanding')
        
        if not shares_outstanding or free_cash_flow <= 0:
            return None
            
        # Proyección conservadora: crecimiento del 5% anualizado por 10 años, descontado al 10%
        tasa_crecimiento = 0.05
        tasa_descuento = 0.10
        valor_presente_fcf = 0.0
        fcf_proyectado = free_cash_flow
        
        for _ in range(10):
            fcf_proyectado *= (1 + tasa_crecimiento)
            valor_presente_fcf += fcf_proyectado / ((1 + tasa_descuento) ** (_ + 1))
            
        valor_intrinseco_empresa = valor_presente_fcf
        valor_intrinseco_accion = round(valor_intrinseco_empresa / shares_outstanding, 2)
        
        # Calcular Margen de Seguridad Real (%)
        if valor_intrinseco_accion > 0:
            margen_seguridad = round(((valor_intrinseco_accion - precio_actual) / valor_intrinseco_accion) * 100, 2)
        else:
            margen_seguridad = -999.0

        # Determinación de Oportunidad Exitosa
        # Puntuación cuantitativa excelente (>75) y cotizando con al menos 20% de descuento
        es_oportunidad_buffett = puntos_score >= 75 and margen_seguridad >= 20.0
        
        if es_oportunidad_buffett:
            senal = "COMPRAR OPORTUNIDAD"
            razon = f"Moat Score {puntos_score}/100 | Descuento del {margen_seguridad}% vs Valor Intrínseco."
        elif puntos_score >= 75:
            senal = "VALOR EXCELENTE / PRECIO ALTO"
            razon = f"Empresa magnífica, pero cara. Margen de seguridad insuficiente ({margen_seguridad}%)."
        else:
            senal = "DESCARTADO"
            razon = f"No cumple criterios de negocio Buffett (Score: {puntos_score}/100)."

        return {
            "simbolo": simbolo,
            "tipo": "ACCION_POTENCIAL",
            "precio_actual": round(precio_actual, 2),
            "valor_intrinseco": valor_intrinseco_accion,
            "margen_bruto": margen_bruto,
            "margen_operativo": margen_operativo,
            "roe": roe,
            "anos_deuda": anos_pago_deuda,
            "score_buffett": puntos_score,
            "margen_seguridad": margen_seguridad,
            "senal": senal,
            "razon": razon
        }
        
    except Exception as e:
        logger.error(f"Error procesando análisis Buffett para {simbolo}: {e}")
        return None
