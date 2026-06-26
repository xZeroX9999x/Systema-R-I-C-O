# ============================================================================
#  MÓDULO 3 — ANÁLISIS TÉCNICO (CORREGIDO)
# ============================================================================

import yfinance as yf
import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional, Any

from .config import (
    ETF_MOMENTUM_CORTO_MESES, ETF_MOMENTUM_LARGO_MESES,
    ETF_PAUSA_RSI_MENSUAL, ETF_PAUSA_DIST_MA200_PCT,
    ACCION_RSI_MAX_COMPRA, ACCION_MOMENTUM_MIN_3M,
    ACCION_VOLUMEN_MIN_RATIO, ACCION_SURGE_PCT_SEMANAL,
    ACCION_SURGE_RSI_MIN, ACCION_TRAILING_STOP_PCT,
    ACCION_VENTA_FASES, MERCADO_ALERTA_VT_RSI_SEMANAL,
    MERCADO_ALERTA_VOLATILIDAD, MERCADO_ALERTA_DIST_MA200_PCT
)

logger = logging.getLogger(__name__)


def calcular_rsi(precios: np.ndarray, periodo: int = 14) -> float:
    """RSI con suavizado Wilder clásico."""
    if len(precios) < periodo + 1:
        return 50.0
    deltas = np.diff(precios)
    ganancia = np.where(deltas > 0, deltas, 0)
    perdida = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(ganancia[:periodo])
    avg_loss = np.mean(perdida[:periodo])
    for i in range(periodo, len(deltas)):
        avg_gain = (avg_gain * (periodo - 1) + ganancia[i]) / periodo
        avg_loss = (avg_loss * (periodo - 1) + perdida[i]) / periodo
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calcular_rsi_semanal(precios_diarios: np.ndarray, periodo: int = 14) -> float:
    """RSI sobre cierres semanales usando resampleo correcto."""
    if len(precios_diarios) < 75:
        return 50.0
    try:
        df = pd.DataFrame({'close': precios_diarios})
        df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='B')
        weekly = df['close'].resample('W-FRI').last().dropna()
        if len(weekly) < periodo + 1:
            return 50.0
        return calcular_rsi(weekly.values, periodo)
    except Exception as e:
        logger.warning(f"Error calculando RSI semanal: {e}")
        return 50.0


def calcular_rsi_mensual(precios_diarios: np.ndarray, periodo: int = 14) -> float:
    """RSI sobre cierres mensuales usando resampleo correcto."""
    if len(precios_diarios) < 252:
        return 50.0
    try:
        df = pd.DataFrame({'close': precios_diarios})
        df.index = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='B')
        monthly = df['close'].resample('ME').last().dropna()
        if len(monthly) < periodo + 1:
            return 50.0
        return calcular_rsi(monthly.values, periodo)
    except Exception as e:
        logger.warning(f"Error calculando RSI mensual: {e}")
        return 50.0


def calcular_momentum(precios: np.ndarray, meses: int) -> float:
    """Momentum = retorno total en N meses."""
    dias = int(meses * 21)
    if len(precios) <= dias:
        return 0.0
    precio_antes = precios[-dias - 1]
    precio_actual = precios[-1]
    if precio_antes <= 0 or np.isnan(precio_antes) or np.isnan(precio_actual):
        return 0.0
    return round(((precio_actual - precio_antes) / precio_antes) * 100, 2)


def calcular_volatilidad(precios: np.ndarray, periodo: int = 30) -> float:
    """Volatilidad anualizada usando desviación estándar muestral (ddof=1)."""
    if len(precios) < periodo + 1:
        return 0.0
    retornos = np.diff(np.log(precios[-periodo - 1:]))
    return round(float(np.std(retornos, ddof=1) * np.sqrt(252) * 100), 2)


def calcular_ma(precios: np.ndarray, periodo: int) -> Optional[float]:
    if len(precios) < periodo:
        return None
    return round(float(np.mean(precios[-periodo:])), 2)


def calcular_volumen_ratio(volumenes: np.ndarray, periodo: int = 20) -> float:
    if len(volumenes) < periodo + 1:
        return 1.0
    vol_promedio = np.mean(volumenes[-periodo - 1:-1])
    vol_actual = volumenes[-1]
    if vol_promedio == 0 or np.isnan(vol_promedio):
        return 1.0
    return round(float(vol_actual / vol_promedio), 2)


def detectar_surge_semanal(precios: np.ndarray) -> float:
    """Detecta surge (subida rápida) en los últimos 5 días."""
    if len(precios) < 6:
        return 0.0
    precio_hace_5d = precios[-6]
    precio_actual = precios[-1]
    if precio_hace_5d == 0 or np.isnan(precio_hace_5d):
        return 0.0
    return round(((precio_actual - precio_hace_5d) / precio_hace_5d) * 100, 2)


def calcular_max_52_semanas(precios: np.ndarray) -> float:
    if len(precios) == 0:
        return 0.0
    subset = precios[-252:] if len(precios) >= 252 else precios
    return round(float(np.max(subset)), 2)


def calcular_distancia_max(precio_actual: float, max_52: float) -> float:
    if max_52 == 0 or np.isnan(max_52):
        return 0.0
    return round(((max_52 - precio_actual) / max_52) * 100, 2)


def distancia_sobre_ma200(precio: float, ma200: Optional[float]) -> float:
    """Qué tan extendido está el precio sobre su MA200 (en %)."""
    if not ma200 or ma200 == 0 or np.isnan(ma200):
        return 0.0
    return round(((precio - ma200) / ma200) * 100, 2)


def obtener_usd_clp() -> float:
    try:
        ticker = yf.Ticker("CLP=X")
        data = ticker.history(period="5d")
        if not data.empty:
            tasa = round(float(data["Close"].iloc[-1]), 2)
            if tasa > 0 and not np.isnan(tasa):
                return tasa
    except Exception as e:
        logger.warning(f"Error obteniendo USD/CLP: {e}")
    return 950.0


def analizar_etf(simbolo: str) -> Optional[Dict[str, Any]]:
    """ETF diversificado: NO genera VENTA por RSI."""
    try:
        ticker = yf.Ticker(simbolo)
        hist = ticker.history(period="2y")

        if hist.empty or len(hist) < 252:
            logger.warning(f"ETF {simbolo}: datos insuficientes")
            return None

        # CORRECCIÓN: 'Close' ya viene ajustado. Se eliminan NaNs para mercado en vivo.
        hist = hist.dropna(subset=["Close"])
        precios = hist["Close"].values
        volumenes = hist["Volume"].values
        precio_actual = round(float(precios[-1]), 2)

        if np.isnan(precio_actual):
            logger.warning(f"ETF {simbolo}: precio actual es NaN")
            return None

        rsi_diario = calcular_rsi(precios, 14)
        rsi_semanal = calcular_rsi_semanal(precios, 14)
        rsi_mensual = calcular_rsi_mensual(precios, 14)

        momentum_6m = calcular_momentum(precios, ETF_MOMENTUM_CORTO_MESES)
        momentum_12m = calcular_momentum(precios, ETF_MOMENTUM_LARGO_MESES)

        ma20 = calcular_ma(precios, 20)
        ma50 = calcular_ma(precios, 50)
        ma200 = calcular_ma(precios, 200)

        volatilidad = calcular_volatilidad(precios, 30)
        vol_ratio = calcular_volumen_ratio(volumenes, 20)
        max_52 = calcular_max_52_semanas(precios)
        dist_max = calcular_distancia_max(precio_actual, max_52)
        dist_ma200 = distancia_sobre_ma200(precio_actual, ma200)

        if ma200 is None:
            tendencia = "SIN DATOS"
        elif precio_actual > ma200 * 1.02:
            tendencia = "ALCISTA"
        elif precio_actual < ma200 * 0.98:
            tendencia = "BAJISTA"
        else:
            tendencia = "NEUTRAL"

        score_momentum = 0.6 * momentum_6m + 0.4 * momentum_12m
        bonus_tendencia = 5 if tendencia == "ALCISTA" else (-5 if tendencia == "BAJISTA" else 0)
        score = round(score_momentum + bonus_tendencia, 2)

        circuit_breaker = (
            rsi_mensual >= ETF_PAUSA_RSI_MENSUAL and
            dist_ma200 >= ETF_PAUSA_DIST_MA200_PCT
        )

        if circuit_breaker:
            senal = "PAUSAR DCA"
            razon = f"Burbuja: RSI mensual {rsi_mensual} + {dist_ma200}% sobre MA200"
        else:
            senal = "DCA MENSUAL"
            razon = f"Mom 6m: {momentum_6m}% | Mom 12m: {momentum_12m}% | {tendencia}"

        return {
            "simbolo": simbolo,
            "tipo": "ETF",
            "precio": precio_actual,
            "rsi": rsi_diario,
            "rsi_semanal": rsi_semanal,
            "rsi_mensual": rsi_mensual,
            "momentum_6m": momentum_6m,
            "momentum_12m": momentum_12m,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "volatilidad": volatilidad,
            "vol_ratio": vol_ratio,
            "tendencia": tendencia,
            "max_52": max_52,
            "distancia_max": dist_max,
            "distancia_ma200": dist_ma200,
            "surge_semanal": detectar_surge_semanal(precios),
            "score": score,
            "senal": senal,
            "razon": razon,
            "circuit_breaker": circuit_breaker,
            "alerta_venta": None,
            "trailing_stop": False,
        }
    except Exception as e:
        logger.error(f"ERROR analizando ETF {simbolo}: {e}")
        return None


def analizar_accion(simbolo: str, historico_compras: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
    """Acción individual: SÍ aplica RSI + momentum filter + trailing stop."""
    try:
        ticker = yf.Ticker(simbolo)
        hist = ticker.history(period="1y")

        if hist.empty or len(hist) < 50:
            logger.warning(f"Acción {simbolo}: datos insuficientes")
            return None

        # CORRECCIÓN: 'Close' ya viene ajustado. Se eliminan NaNs para mercado en vivo.
        hist = hist.dropna(subset=["Close"])
        precios = hist["Close"].values
        volumenes = hist["Volume"].values
        precio_actual = round(float(precios[-1]), 2)

        if np.isnan(precio_actual):
            logger.warning(f"Acción {simbolo}: precio actual es NaN")
            return None

        rsi_diario = calcular_rsi(precios, 14)
        rsi_semanal = calcular_rsi_semanal(precios, 14)

        momentum_3m = calcular_momentum(precios, 3)
        momentum_6m = calcular_momentum(precios, 6)
        momentum_12m = calcular_momentum(precios, 12)

        ma20 = calcular_ma(precios, 20)
        ma200 = calcular_ma(precios, 200)

        volatilidad = calcular_volatilidad(precios, 30)
        vol_ratio = calcular_volumen_ratio(volumenes, 20)
        surge_semanal = detectar_surge_semanal(precios)
        max_52 = calcular_max_52_semanas(precios)
        dist_max = calcular_distancia_max(precio_actual, max_52)

        sobre_ma200 = precio_actual > ma200 if ma200 else None

        if ma200 is None:
            tendencia = "SIN DATOS"
        elif precio_actual > ma200 * 1.02:
            tendencia = "ALCISTA"
        elif precio_actual < ma200 * 0.98:
            tendencia = "BAJISTA"
        else:
            tendencia = "NEUTRAL"

        score = 100 - rsi_diario
        if sobre_ma200:
            score += 10
        elif sobre_ma200 is False:
            score -= 15
        if vol_ratio >= 1.2:
            score += 5
        elif vol_ratio < ACCION_VOLUMEN_MIN_RATIO:
            score -= 10
        if volatilidad > 50:
            score -= 8
        if momentum_3m < ACCION_MOMENTUM_MIN_3M:
            score -= 15
        if momentum_6m > 10:
            score += 5
        score = round(score, 2)

        surge_activo = (
            surge_semanal >= ACCION_SURGE_PCT_SEMANAL and
            rsi_diario >= ACCION_SURGE_RSI_MIN
        )

        alerta_venta = None
        if surge_activo or rsi_diario >= ACCION_VENTA_FASES["FASE_1"]["rsi"]:
            for fase_key in ["FASE_3", "FASE_2", "FASE_1"]:
                fase = ACCION_VENTA_FASES[fase_key]
                if rsi_diario >= fase["rsi"]:
                    alerta_venta = {
                        "fase": fase_key,
                        "pct_vender": fase["vender_pct"],
                        "etiqueta": fase["etiqueta"],
                        "rsi": rsi_diario,
                    }
                    break

        # Trailing stop usando historico de compras de DB
        trailing_stop = False
        if historico_compras and simbolo in historico_compras:
            precio_compra = historico_compras[simbolo]
            dias_desde_compra = min(126, len(precios))
            precios_desde_compra = precios[-dias_desde_compra:]
            max_desde_compra = float(np.max(precios_desde_compra))
            caida_desde_max_compra = ((max_desde_compra - precio_actual) / max_desde_compra) * 100
            trailing_stop = caida_desde_max_compra >= ACCION_TRAILING_STOP_PCT
        else:
            trailing_stop = dist_max >= ACCION_TRAILING_STOP_PCT

        senal = "COMPRAR"
        razon = ""

        if rsi_diario > ACCION_RSI_MAX_COMPRA:
            senal = "ESPERAR"
            razon = f"RSI alto ({rsi_diario})"
        elif momentum_3m < ACCION_MOMENTUM_MIN_3M:
            senal = "PRECAUCION"
            razon = f"Momentum 3m negativo ({momentum_3m}%) — no atrapar cuchillo"
        elif sobre_ma200 is False:
            senal = "PRECAUCION"
            razon = "Bajo MA200 — tendencia bajista"
        elif vol_ratio < ACCION_VOLUMEN_MIN_RATIO:
            senal = "SENAL DEBIL"
            razon = f"Volumen seco (ratio {vol_ratio})"

        if alerta_venta:
            senal = "VENDER"
            razon = alerta_venta["etiqueta"]

        if trailing_stop:
            senal = "TRAILING STOP"
            razon = f"Caída de {dist_max}% desde máximo 52s"

        return {
            "simbolo": simbolo,
            "tipo": "ACCION",
            "precio": precio_actual,
            "rsi": rsi_diario,
            "rsi_semanal": rsi_semanal,
            "rsi_mensual": 0,
            "momentum_6m": momentum_6m,
            "momentum_12m": momentum_12m,
            "ma20": ma20,
            "ma50": None,
            "ma200": ma200,
            "volatilidad": volatilidad,
            "vol_ratio": vol_ratio,
            "tendencia": tendencia,
            "max_52": max_52,
            "distancia_max": dist_max,
            "distancia_ma200": distancia_sobre_ma200(precio_actual, ma200),
            "surge_semanal": surge_semanal,
            "score": score,
            "senal": senal,
            "razon": razon,
            "circuit_breaker": False,
            "alerta_venta": alerta_venta,
            "trailing_stop": trailing_stop,
        }
    except Exception as e:
        logger.error(f"ERROR analizando acción {simbolo}: {e}")
        return None


def detectar_regimen_mercado(resultado_vt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Activa MODO CAUTELA solo con 2+ señales de euforia real."""
    if resultado_vt is None:
        return {"estado": "NORMAL", "pausar_acciones": False, "mensaje": "VT no disponible"}

    señales_alerta = 0
    razones = []

    if resultado_vt["rsi_semanal"] >= MERCADO_ALERTA_VT_RSI_SEMANAL:
        señales_alerta += 1
        razones.append(f"VT RSI semanal {resultado_vt['rsi_semanal']}")
    if resultado_vt["volatilidad"] >= MERCADO_ALERTA_VOLATILIDAD:
        señales_alerta += 1
        razones.append(f"Volatilidad {resultado_vt['volatilidad']}%")
    if resultado_vt["distancia_ma200"] >= MERCADO_ALERTA_DIST_MA200_PCT:
        señales_alerta += 1
        razones.append(f"VT {resultado_vt['distancia_ma200']}% sobre MA200")

    if señales_alerta >= 2:
        return {
            "estado": "CAUTELA",
            "pausar_acciones": True,
            "mensaje": (
                f"Mercado sobrecalentado ({señales_alerta}/3 señales): "
                f"{' | '.join(razones)}. "
                f"DCA de ETFs continúa. Compras tácticas de acciones en pausa."
            )
        }

    return {"estado": "NORMAL", "pausar_acciones": False, "mensaje": ""}
