#!/usr/bin/env python3
# ============================================================================
#  SISTEMA R-I-C-O v4.0 — CRECIMIENTO DE LARGO PLAZO + TÁCTICO
#
#  FILOSOFÍA:
#  - ETFs diversificados = buy-and-hold con DCA mensual fijo + rebalanceo
#  - Acciones individuales = señales tácticas de RSI/momentum/trailing stop
#  - Evidencia: Dalbar 2024 muestra que el inversor promedio pierde ~8% anual
#    intentando hacer timing. El DCA disciplinado + rebalanceo anual gana.
#
#  Ejecuta: GitHub Actions (cron semanal)
#  Datos:   Yahoo Finance (yfinance)
#  Salida:  Correo HTML + log CSV
# ============================================================================

import yfinance as yf
import numpy as np
import smtplib
import os
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

# ============================================================================
#  MÓDULO 1 — CONFIGURACIÓN
# ============================================================================

# --- Clasificación de activos (CLAVE del rediseño) ---
ETFS_CORE = ["VT", "ITOT"]
ACCIONES_TACTICAS = ["NVDA", "IBIT", "CGW", "TTWO"]
ALL_TICKERS = ETFS_CORE + ACCIONES_TACTICAS

# --- Presupuesto y asignación ---
PRESUPUESTO_MENSUAL = 50000
APORTE_ETF_MENSUAL      = 30000   # 60% al núcleo de largo plazo
APORTE_ACCIONES_MENSUAL = 17500   # 35% táctico
APORTE_CASH_MENSUAL     = 2500    # 5% reserva
ASIGNACION_ACCIONES = [12500, 5000]   # Top 1 y Top 2

# --- Asignación objetivo del portafolio acumulado ---
ASIGNACION_OBJETIVO = {"ETFS_CORE": 0.70, "ACCIONES": 0.25, "CASH": 0.05}
BANDA_REBALANCEO_PCT = 10.0

# --- Parámetros ETFs (largo plazo) ---
ETF_MOMENTUM_CORTO_MESES  = 6
ETF_MOMENTUM_LARGO_MESES  = 12
ETF_PAUSA_RSI_MENSUAL     = 80
ETF_PAUSA_DIST_MA200_PCT  = 25

# --- Parámetros acciones (táctico) ---
ACCION_RSI_MAX_COMPRA        = 60
ACCION_MOMENTUM_MIN_3M       = -10
ACCION_VOLUMEN_MIN_RATIO     = 0.6
ACCION_SURGE_PCT_SEMANAL     = 15.0
ACCION_SURGE_RSI_MIN         = 70
ACCION_TRAILING_STOP_PCT     = 15.0

ACCION_VENTA_FASES = {
    "FASE_1": {"rsi": 72, "vender_pct": 25, "etiqueta": "Reducir 25% — RSI caliente"},
    "FASE_2": {"rsi": 78, "vender_pct": 35, "etiqueta": "Reducir 35% — RSI sobrecalentado"},
    "FASE_3": {"rsi": 85, "vender_pct": 50, "etiqueta": "Reducir 50% — RSI extremo"},
}

# --- Régimen de mercado (modo cautela inteligente) ---
MERCADO_ALERTA_VT_RSI_SEMANAL  = 78
MERCADO_ALERTA_VOLATILIDAD     = 35
MERCADO_ALERTA_DIST_MA200_PCT  = 20

# --- Email ---
EMAIL_DESTINO  = os.environ.get("EMAIL_DESTINO")  or ""
EMAIL_USUARIO  = os.environ.get("EMAIL_USUARIO")  or ""
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") or ""
SMTP_SERVER    = os.environ.get("SMTP_SERVER")    or "smtp.gmail.com"
SMTP_PORT      = int(os.environ.get("SMTP_PORT")  or "587")

LOG_FILE = "historico_decisiones.csv"
USD_CLP_FALLBACK = 950.0


# ============================================================================
#  MÓDULO 2 — FUNCIONES DE ANÁLISIS TÉCNICO
# ============================================================================

def calcular_rsi(precios, periodo=14):
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


def calcular_rsi_semanal(precios_diarios, periodo=14):
    """RSI sobre cierres semanales (cada 5 días de trading)."""
    if len(precios_diarios) < 75:
        return 50.0
    precios_semanales = precios_diarios[::-5][::-1]
    if len(precios_semanales) < periodo + 1:
        return 50.0
    return calcular_rsi(precios_semanales, periodo)


def calcular_rsi_mensual(precios_diarios, periodo=14):
    """RSI sobre cierres mensuales (cada 21 días de trading ≈ 1 mes)."""
    if len(precios_diarios) < 252:
        return 50.0
    precios_mensuales = precios_diarios[::-21][::-1]
    if len(precios_mensuales) < periodo + 1:
        return 50.0
    return calcular_rsi(precios_mensuales, periodo)


def calcular_momentum(precios, meses):
    """
    Momentum = retorno total en N meses.
    Factor con más evidencia empírica (Jegadeesh-Titman 1993, AQR).
    """
    dias = meses * 21
    if len(precios) < dias + 1:
        return 0.0
    precio_antes = precios[-dias - 1]
    precio_actual = precios[-1]
    if precio_antes <= 0:
        return 0.0
    return round(((precio_actual - precio_antes) / precio_antes) * 100, 2)


def calcular_volatilidad(precios, periodo=30):
    if len(precios) < periodo + 1:
        return 0.0
    retornos = np.diff(np.log(precios[-periodo - 1:]))
    return round(np.std(retornos) * np.sqrt(252) * 100, 2)


def calcular_ma(precios, periodo):
    if len(precios) < periodo:
        return None
    return round(np.mean(precios[-periodo:]), 2)


def calcular_volumen_ratio(volumenes, periodo=20):
    if len(volumenes) < periodo + 1:
        return 1.0
    vol_promedio = np.mean(volumenes[-periodo - 1:-1])
    vol_actual = volumenes[-1]
    if vol_promedio == 0:
        return 1.0
    return round(vol_actual / vol_promedio, 2)


def detectar_surge_semanal(precios):
    if len(precios) < 6:
        return 0.0
    precio_hace_5d = precios[-6]
    precio_actual = precios[-1]
    if precio_hace_5d == 0:
        return 0.0
    return round(((precio_actual - precio_hace_5d) / precio_hace_5d) * 100, 2)


def calcular_max_52_semanas(precios):
    if len(precios) == 0:
        return 0
    subset = precios[-252:] if len(precios) >= 252 else precios
    return round(max(subset), 2)


def calcular_distancia_max(precio_actual, max_52):
    if max_52 == 0:
        return 0
    return round(((max_52 - precio_actual) / max_52) * 100, 2)


def distancia_sobre_ma200(precio, ma200):
    """Qué tan extendido está el precio sobre su MA200 (en %)."""
    if not ma200 or ma200 == 0:
        return 0
    return round(((precio - ma200) / ma200) * 100, 2)


# ============================================================================
#  MÓDULO 3 — TIPO DE CAMBIO USD/CLP
# ============================================================================

def obtener_usd_clp():
    try:
        ticker = yf.Ticker("CLP=X")
        data = ticker.history(period="5d")
        if not data.empty:
            tasa = round(data["Close"].iloc[-1], 2)
            if tasa > 0:
                return tasa
    except Exception:
        pass
    return USD_CLP_FALLBACK


# ============================================================================
#  MÓDULO 4 — ANÁLISIS DE ETF (LARGO PLAZO)
# ============================================================================

def analizar_etf(simbolo):
    """
    ETF diversificado: NO genera VENTA por RSI.
    Ranking por momentum 6m/12m. Circuit breaker solo en burbujas extremas.
    """
    try:
        ticker = yf.Ticker(simbolo)
        hist = ticker.history(period="2y")

        if hist.empty or len(hist) < 252:
            return None

        precios = hist["Close"].values
        volumenes = hist["Volume"].values
        precio_actual = round(precios[-1], 2)

        # Métricas multi-timeframe
        rsi_diario   = calcular_rsi(precios, 14)
        rsi_semanal  = calcular_rsi_semanal(precios, 14)
        rsi_mensual  = calcular_rsi_mensual(precios, 14)

        # Momentum (decide asignación de ETF)
        momentum_6m  = calcular_momentum(precios, ETF_MOMENTUM_CORTO_MESES)
        momentum_12m = calcular_momentum(precios, ETF_MOMENTUM_LARGO_MESES)

        ma20   = calcular_ma(precios, 20)
        ma50   = calcular_ma(precios, 50)
        ma200  = calcular_ma(precios, 200)

        volatilidad = calcular_volatilidad(precios, 30)
        vol_ratio   = calcular_volumen_ratio(volumenes, 20)
        max_52      = calcular_max_52_semanas(precios)
        dist_max    = calcular_distancia_max(precio_actual, max_52)
        dist_ma200  = distancia_sobre_ma200(precio_actual, ma200)

        if ma200 is None:
            tendencia = "SIN DATOS"
        elif precio_actual > ma200 * 1.02:
            tendencia = "ALCISTA"
        elif precio_actual < ma200 * 0.98:
            tendencia = "BAJISTA"
        else:
            tendencia = "NEUTRAL"

        # --- SCORE basado en momentum (no en RSI) ---
        score_momentum = 0.6 * momentum_6m + 0.4 * momentum_12m
        bonus_tendencia = 5 if tendencia == "ALCISTA" else (-5 if tendencia == "BAJISTA" else 0)
        score = round(score_momentum + bonus_tendencia, 2)

        # --- Circuit breaker: requiere AMBAS condiciones ---
        circuit_breaker = (
            rsi_mensual >= ETF_PAUSA_RSI_MENSUAL and
            dist_ma200  >= ETF_PAUSA_DIST_MA200_PCT
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
        print(f"  ERROR analizando ETF {simbolo}: {e}")
        return None


# ============================================================================
#  MÓDULO 5 — ANÁLISIS DE ACCIÓN (TÁCTICO)
# ============================================================================

def analizar_accion(simbolo):
    """
    Acción individual: SÍ aplica RSI + momentum filter + trailing stop.
    Acciones individuales pueden caer 50%+ sin recuperarse.
    """
    try:
        ticker = yf.Ticker(simbolo)
        hist = ticker.history(period="1y")

        if hist.empty or len(hist) < 50:
            return None

        precios = hist["Close"].values
        volumenes = hist["Volume"].values
        precio_actual = round(precios[-1], 2)

        rsi_diario  = calcular_rsi(precios, 14)
        rsi_semanal = calcular_rsi_semanal(precios, 14)

        momentum_3m = calcular_momentum(precios, 3)
        momentum_6m = calcular_momentum(precios, 6)

        ma20  = calcular_ma(precios, 20)
        ma200 = calcular_ma(precios, 200)

        volatilidad   = calcular_volatilidad(precios, 30)
        vol_ratio     = calcular_volumen_ratio(volumenes, 20)
        surge_semanal = detectar_surge_semanal(precios)
        max_52        = calcular_max_52_semanas(precios)
        dist_max      = calcular_distancia_max(precio_actual, max_52)

        sobre_ma200 = precio_actual > ma200 if ma200 else None

        if ma200 is None:
            tendencia = "SIN DATOS"
        elif precio_actual > ma200 * 1.02:
            tendencia = "ALCISTA"
        elif precio_actual < ma200 * 0.98:
            tendencia = "BAJISTA"
        else:
            tendencia = "NEUTRAL"

        # --- SCORE ---
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
            score -= 15   # Penalización por cuchillo cayendo
        if momentum_6m > 10:
            score += 5    # Bonus momentum positivo
        score = round(score, 2)

        # --- Detección de euforia ---
        surge_activo = (
            surge_semanal >= ACCION_SURGE_PCT_SEMANAL and
            rsi_diario    >= ACCION_SURGE_RSI_MIN
        )

        # --- Alerta de venta por fases ---
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

        # --- Trailing stop ---
        trailing_stop = dist_max >= ACCION_TRAILING_STOP_PCT

        # --- Señal final ---
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
            razon = f"Caida de {dist_max}% desde maximo 52s"

        return {
            "simbolo": simbolo,
            "tipo": "ACCION",
            "precio": precio_actual,
            "rsi": rsi_diario,
            "rsi_semanal": rsi_semanal,
            "rsi_mensual": 0,
            "momentum_6m": momentum_6m,
            "momentum_12m": 0,
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
        print(f"  ERROR analizando accion {simbolo}: {e}")
        return None


# ============================================================================
#  MÓDULO 6 — DETECTOR DE RÉGIMEN DE MERCADO
# ============================================================================

def detectar_regimen_mercado(resultado_vt):
    """
    Activa MODO CAUTELA solo con 2+ señales de euforia real.
    IMPORTANTE: el DCA de ETFs NO se pausa aquí. Solo las acciones.
    """
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


# ============================================================================
#  MÓDULO 7 — MOTOR DE DECISIÓN
# ============================================================================

def decidir_asignacion(resultados_etfs, resultados_acciones, regimen):
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
    }

    for r in resultados_acciones:
        if r["alerta_venta"]:
            decision["alertas_venta"].append(r)
        if r["trailing_stop"]:
            decision["trailing_stops"].append(r)

    # --- ETF: DCA al mejor por momentum ---
    etfs_disponibles = [e for e in resultados_etfs if not e["circuit_breaker"]]

    if etfs_disponibles:
        etfs_disponibles.sort(key=lambda x: x["score"], reverse=True)
        mejor_etf = etfs_disponibles[0]
        decision["etf"] = {
            "simbolo": mejor_etf["simbolo"],
            "monto":   APORTE_ETF_MENSUAL,
            "razon":   f"Mejor momentum (6m: {mejor_etf['momentum_6m']}%, 12m: {mejor_etf['momentum_12m']}%)",
        }
    else:
        decision["etf"] = {"simbolo": None, "monto": 0,
                           "razon": "Todos los ETFs en circuit breaker"}
        decision["reserva_cash"] += APORTE_ETF_MENSUAL

    # --- Acciones: si modo cautela, todo a reserva ---
    if regimen["pausar_acciones"]:
        decision["reserva_cash"] += APORTE_ACCIONES_MENSUAL
        decision["mensaje"] = (
            f"Acciones en pausa por régimen de cautela. "
            f"{APORTE_ACCIONES_MENSUAL:,} CLP adicionales a reserva."
        )
    else:
        comprables = [a for a in resultados_acciones if a["senal"] == "COMPRAR"]
        comprables.sort(key=lambda x: x["score"], reverse=True)

        for i, accion in enumerate(comprables[:len(ASIGNACION_ACCIONES)]):
            decision["acciones"].append({
                "simbolo": accion["simbolo"],
                "monto":   ASIGNACION_ACCIONES[i],
                "razon":   f"Score {accion['score']} | RSI {accion['rsi']} | Mom 6m {accion['momentum_6m']}%",
            })

        comprables_count = min(len(comprables), len(ASIGNACION_ACCIONES))
        if comprables_count < len(ASIGNACION_ACCIONES):
            sobrante = sum(ASIGNACION_ACCIONES[comprables_count:])
            decision["reserva_cash"] += sobrante
            decision["mensaje"] += f" {sobrante:,} CLP sin oportunidad táctica → reserva."

    decision["total_asignado"] = (
        decision["etf"]["monto"] +
        sum(a["monto"] for a in decision["acciones"]) +
        decision["reserva_cash"]
    )
    decision["sobrante"] = PRESUPUESTO_MENSUAL - decision["total_asignado"]

    return decision


# ============================================================================
#  MÓDULO 8 — GENERADOR HTML
# ============================================================================

def generar_html(resultados, decision, usd_clp, fecha):
    colores = {
        "DCA MENSUAL":   "#2ecc71",
        "PAUSAR DCA":    "#f39c12",
        "COMPRAR":       "#27ae60",
        "VENDER":        "#e74c3c",
        "ESPERAR":       "#f39c12",
        "PRECAUCION":    "#e67e22",
        "SENAL DEBIL":   "#95a5a6",
        "TRAILING STOP": "#c0392b",
    }

    html = f"""<html><head><style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0a0a1a; color: #e0e0e0; padding: 20px; }}
        .container {{ max-width: 700px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1a1a3e, #2d2d6b); padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 20px; }}
        .header h1 {{ color: #00d4ff; margin: 0; font-size: 24px; }}
        .header p {{ color: #8888aa; margin: 5px 0 0 0; font-size: 13px; }}
        .alerta-roja {{ background: #c0392b; color: white; padding: 18px; border-radius: 10px; margin: 12px 0; text-align: center; font-weight: bold; border: 2px solid #e74c3c; }}
        .alerta-amarilla {{ background: #7d6608; color: #fff3cd; padding: 14px; border-radius: 10px; margin: 12px 0; text-align: center; border: 2px solid #f1c40f; }}
        .alerta-verde {{ background: #1e4d2b; color: #d4edda; padding: 14px; border-radius: 10px; margin: 12px 0; text-align: center; border: 2px solid #27ae60; }}
        .card {{ background: #12122a; border: 1px solid #2a2a4a; border-radius: 10px; padding: 16px; margin: 10px 0; }}
        .card-etf {{ border-left: 4px solid #00d4ff; }}
        .card-compra {{ border-left: 4px solid #27ae60; }}
        .card-venta {{ border-left: 4px solid #e74c3c; }}
        .card-esperar {{ border-left: 4px solid #f39c12; }}
        .card-neutro {{ border-left: 4px solid #555; }}
        .ticker {{ font-size: 20px; font-weight: bold; color: #00d4ff; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; }}
        .indicadores {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
        .ind {{ background: #1a1a3e; padding: 4px 10px; border-radius: 6px; font-size: 12px; color: #aaa; }}
        .asignacion {{ font-size: 18px; font-weight: bold; color: #2ecc71; float: right; margin-top: -30px; }}
        .resumen {{ background: #1a1a3e; padding: 16px; border-radius: 10px; margin-top: 20px; }}
        .resumen h3 {{ color: #00d4ff; margin-top: 0; }}
        .footer {{ text-align: center; color: #555; font-size: 11px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #222; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th {{ background: #1a1a3e; color: #00d4ff; padding: 8px; text-align: left; font-size: 12px; }}
        td {{ padding: 8px; border-bottom: 1px solid #1a1a3a; font-size: 12px; }}
    </style></head><body><div class="container">
        <div class="header">
            <h1>R-I-C-O Bot v4.0</h1>
            <p>Largo plazo + Táctico — {fecha}</p>
            <p style="color:#00d4ff; font-size:12px;">USD/CLP: ${usd_clp:,.0f} | Presupuesto: {PRESUPUESTO_MENSUAL:,} CLP</p>
        </div>"""

    # --- Régimen de mercado ---
    regimen = decision["regimen"]
    if regimen["estado"] == "CAUTELA":
        html += f'<div class="alerta-amarilla"><b>MODO CAUTELA</b><br>{regimen["mensaje"]}</div>'
    else:
        html += '<div class="alerta-verde"><b>RÉGIMEN NORMAL</b><br>DCA y tácticas funcionando según plan.</div>'

    # --- Alertas de venta (solo acciones) ---
    for av in decision["alertas_venta"]:
        info = av["alerta_venta"]
        html += f"""<div class="alerta-roja">
            ALERTA DE VENTA: {av['simbolo']} ({info['fase']})<br>
            {info['etiqueta']}<br>
            <small>RSI: {av['rsi']} | Surge 5d: {av['surge_semanal']}%</small>
        </div>"""

    for ts in decision["trailing_stops"]:
        html += f"""<div class="alerta-roja">
            TRAILING STOP: {ts['simbolo']}<br>
            Caida {ts['distancia_max']}% desde maximo 52s (${ts['max_52']})<br>
            <small>Precio: ${ts['precio']} | RSI: {ts['rsi']}</small>
        </div>"""

    # --- Asignación del mes ---
    html += '<div class="resumen"><h3>Asignación del Mes</h3><table>'
    html += '<tr><th>Destino</th><th>Tipo</th><th>Monto CLP</th></tr>'

    if decision["etf"]["simbolo"]:
        html += f'<tr><td style="color:#00d4ff;"><b>{decision["etf"]["simbolo"]}</b></td><td>ETF (DCA)</td><td style="color:#2ecc71;"><b>{decision["etf"]["monto"]:,}</b></td></tr>'

    for acc in decision["acciones"]:
        html += f'<tr><td style="color:#00d4ff;"><b>{acc["simbolo"]}</b></td><td>Acción</td><td style="color:#2ecc71;"><b>{acc["monto"]:,}</b></td></tr>'

    if decision["reserva_cash"] > 0:
        html += f'<tr><td style="color:#3498db;"><b>RESERVA</b></td><td>Cash</td><td style="color:#3498db;"><b>{decision["reserva_cash"]:,}</b></td></tr>'

    html += f'<tr style="border-top:2px solid #00d4ff;"><td colspan="2"><b>TOTAL</b></td><td><b>{decision["total_asignado"]:,} CLP</b></td></tr>'
    html += '</table></div>'

    # --- Detalle por activo ---
    html += '<h2 style="color:#00d4ff; margin-top:25px;">Detalle por Activo</h2>'

    for r in resultados:
        senal = r["senal"]
        color = colores.get(senal, "#555")

        if r["tipo"] == "ETF":
            clase_card = "card-etf"
        elif senal == "COMPRAR":
            clase_card = "card-compra"
        elif senal in ("VENDER", "TRAILING STOP"):
            clase_card = "card-venta"
        elif senal in ("ESPERAR", "PRECAUCION", "SENAL DEBIL", "PAUSAR DCA"):
            clase_card = "card-esperar"
        else:
            clase_card = "card-neutro"

        monto_asignado = 0
        if decision["etf"]["simbolo"] == r["simbolo"]:
            monto_asignado = decision["etf"]["monto"]
        for acc in decision["acciones"]:
            if acc["simbolo"] == r["simbolo"]:
                monto_asignado = acc["monto"]

        html += f'<div class="card {clase_card}">'
        html += f'<span class="ticker">{r["simbolo"]}</span>'
        html += f'<span class="badge" style="background:{color}; margin-left:10px;">{senal}</span>'
        html += f'<span style="color:#888; margin-left:8px; font-size:12px;">({r["tipo"]})</span>'

        if monto_asignado > 0:
            acciones_usd = monto_asignado / usd_clp
            html += f'<div class="asignacion">{monto_asignado:,} CLP<br><span style="font-size:12px;color:#888;">≈ ${acciones_usd:.1f} USD</span></div>'

        if r["razon"]:
            html += f'<div style="color:#e67e22; font-size:12px; margin-top:4px;">{r["razon"]}</div>'

        if r["tipo"] == "ETF":
            html += f"""<div class="indicadores">
                <span class="ind">Precio: ${r['precio']}</span>
                <span class="ind">RSI diario: {r['rsi']}</span>
                <span class="ind">RSI semanal: {r['rsi_semanal']}</span>
                <span class="ind">RSI mensual: {r['rsi_mensual']}</span>
                <span class="ind">Mom 6m: {r['momentum_6m']}%</span>
                <span class="ind">Mom 12m: {r['momentum_12m']}%</span>
                <span class="ind">MA200: {r['ma200'] or '—'}</span>
                <span class="ind">Tendencia: {r['tendencia']}</span>
                <span class="ind">vs MA200: +{r['distancia_ma200']}%</span>
            </div></div>"""
        else:
            html += f"""<div class="indicadores">
                <span class="ind">Precio: ${r['precio']}</span>
                <span class="ind">RSI: {r['rsi']}</span>
                <span class="ind">Mom 6m: {r['momentum_6m']}%</span>
                <span class="ind">MA20: {r['ma20'] or '—'}</span>
                <span class="ind">MA200: {r['ma200'] or '—'}</span>
                <span class="ind">Vol: {r['volatilidad']}%</span>
                <span class="ind">VolRatio: {r['vol_ratio']}x</span>
                <span class="ind">Tendencia: {r['tendencia']}</span>
                <span class="ind">Dist.Max: -{r['distancia_max']}%</span>
                <span class="ind">Surge5d: {r['surge_semanal']}%</span>
            </div></div>"""

    # --- Leyenda ---
    html += """<div class="resumen" style="margin-top:20px;">
        <h3>Como Leer Este Reporte</h3>
        <p style="font-size:12px; line-height:1.6;">
            <b style="color:#2ecc71;">DCA MENSUAL (ETF)</b>: Compra automatica mes a mes. El tiempo en mercado vence al timing.<br>
            <b style="color:#f39c12;">PAUSAR DCA</b>: Solo si RSI mensual >80 + precio >25% sobre MA200 (burbuja clara).<br>
            <b style="color:#27ae60;">COMPRAR (accion)</b>: RSI sano + momentum positivo + sobre MA200.<br>
            <b style="color:#e67e22;">PRECAUCION</b>: RSI atractivo pero bajo MA200 o con momentum negativo.<br>
            <b style="color:#f39c12;">ESPERAR</b>: RSI alto, sin descuento.<br>
            <b style="color:#e74c3c;">VENDER</b>: Solo acciones. Fases 72 / 78 / 85 de RSI.<br>
            <b style="color:#c0392b;">TRAILING STOP</b>: Solo acciones. Caida >15% desde maximo.
        </p>
        <p style="font-size:11px; color:#666;">
            v4.0 trata ETFs y acciones con logicas distintas. ETFs = largo plazo (momentum).
            Acciones = tactico (RSI + filtros). DCA de ETFs nunca se pausa salvo burbuja extrema.
        </p>
    </div>"""

    html += f"""<div class="footer">
            R-I-C-O Bot v4.0 — Sistema dual (largo plazo + tactico)<br>
            Datos: Yahoo Finance | GitHub Actions<br>
            Esto NO es asesoria financiera.
        </div></div></body></html>"""

    return html


# ============================================================================
#  MÓDULO 9 — EMAIL + LOG + MAIN
# ============================================================================

def enviar_correo(html, fecha):
    if not all([EMAIL_DESTINO, EMAIL_USUARIO, EMAIL_PASSWORD]):
        print("  Variables de correo no configuradas. Saltando envio.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"R-I-C-O Bot v4.0 — {fecha}"
    msg["From"]    = EMAIL_USUARIO
    msg["To"]      = EMAIL_DESTINO
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USUARIO, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USUARIO, EMAIL_DESTINO, msg.as_string())
        print("  Correo enviado.")
        return True
    except Exception as e:
        print(f"  Error enviando correo: {e}")
        return False


def guardar_log(resultados, decision, usd_clp, fecha):
    archivo = Path(LOG_FILE)
    escribir_header = not archivo.exists()

    try:
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if escribir_header:
                writer.writerow([
                    "fecha", "ticker", "tipo", "precio_usd", "rsi_diario",
                    "rsi_semanal", "rsi_mensual", "momentum_6m", "momentum_12m",
                    "ma20", "ma200", "volatilidad", "vol_ratio", "tendencia",
                    "score", "senal", "monto_clp", "usd_clp", "regimen",
                ])
            for r in resultados:
                monto = 0
                if decision["etf"]["simbolo"] == r["simbolo"]:
                    monto = decision["etf"]["monto"]
                for acc in decision["acciones"]:
                    if acc["simbolo"] == r["simbolo"]:
                        monto = acc["monto"]
                writer.writerow([
                    fecha, r["simbolo"], r["tipo"], r["precio"],
                    r["rsi"], r["rsi_semanal"], r["rsi_mensual"],
                    r["momentum_6m"], r["momentum_12m"],
                    r["ma20"], r["ma200"], r["volatilidad"], r["vol_ratio"],
                    r["tendencia"], r["score"], r["senal"], monto, usd_clp,
                    decision["regimen"]["estado"],
                ])
        print(f"  Log guardado en {LOG_FILE}")
    except Exception as e:
        print(f"  Error guardando log: {e}")


def main():
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print(f"  R-I-C-O Bot v4.0 — {fecha}")
    print("=" * 60)

    usd_clp = obtener_usd_clp()
    print(f"\n  USD/CLP: ${usd_clp:,.0f}")
    print(f"  Analizando {len(ALL_TICKERS)} activos...\n")

    resultados_etfs = []
    resultados_acciones = []
    resultados_todos = []

    for simbolo in ETFS_CORE:
        print(f"    ETF {simbolo}...", end=" ")
        r = analizar_etf(simbolo)
        if r:
            resultados_etfs.append(r)
            resultados_todos.append(r)
            print(f"Mom 6m:{r['momentum_6m']}% | Score:{r['score']} | {r['senal']}")
        else:
            print("ERROR")

    for simbolo in ACCIONES_TACTICAS:
        print(f"    ACC {simbolo}...", end=" ")
        r = analizar_accion(simbolo)
        if r:
            resultados_acciones.append(r)
            resultados_todos.append(r)
            print(f"RSI:{r['rsi']} | Score:{r['score']} | {r['senal']}")
        else:
            print("ERROR")

    if not resultados_todos:
        print("\n  No se pudo analizar ningun activo. Abortando.")
        return

    vt_resultado = next((r for r in resultados_etfs if r["simbolo"] == "VT"), None)
    regimen = detectar_regimen_mercado(vt_resultado)
    print(f"\n  Régimen de mercado: {regimen['estado']}")
    if regimen["mensaje"]:
        print(f"    {regimen['mensaje']}")

    print("\n  Ejecutando motor de decisión...")
    decision = decidir_asignacion(resultados_etfs, resultados_acciones, regimen)

    print("\n  DECISIÓN DEL MES:")
    if decision["etf"]["simbolo"]:
        print(f"    ETF DCA:    {decision['etf']['simbolo']} = {decision['etf']['monto']:,} CLP")
    for acc in decision["acciones"]:
        print(f"    ACCION:     {acc['simbolo']} = {acc['monto']:,} CLP")
    print(f"    RESERVA:    {decision['reserva_cash']:,} CLP")
    print(f"    TOTAL:      {decision['total_asignado']:,} CLP")

    if decision["alertas_venta"]:
        print("\n  ALERTAS DE VENTA:")
        for av in decision["alertas_venta"]:
            print(f"    {av['simbolo']}: {av['alerta_venta']['etiqueta']}")
    if decision["trailing_stops"]:
        print("\n  TRAILING STOPS:")
        for ts in decision["trailing_stops"]:
            print(f"    {ts['simbolo']}: caida {ts['distancia_max']}%")

    resultados_etfs.sort(key=lambda x: x["score"], reverse=True)
    resultados_acciones.sort(key=lambda x: x["score"], reverse=True)
    resultados_ordenados = resultados_etfs + resultados_acciones

    print("\n  Generando correo...")
    html = generar_html(resultados_ordenados, decision, usd_clp, fecha)
    enviar_correo(html, fecha)
    guardar_log(resultados_ordenados, decision, usd_clp, fecha)

    print("\n" + "=" * 60)
    print("  Ejecucion completada.")
    print("=" * 60)


if __name__ == "__main__":
    main()
