# ============================================================================
#  MÓDULO 8 — GENERADOR HTML
# ============================================================================

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any
from modules.config import load_settings

logger = logging.getLogger(__name__)

def generar_html(resultados: List[Dict], 
                decision: Dict,
                usd_clp: float,
                fecha_hora: str,
                backtest_results: Dict,
                contexto_llm: Dict) -> str:
    """Genera el HTML del reporte para el email"""
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

    # Validar decisiones
    if not decision.get("resultados"):
        decision["resultados"] = []

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
        .backtest-table {{ background: #1a1a3e; padding: 16px; border-radius: 10px; margin-top: 20px; }}
        .contexto-card {{ background: #1a1a3e; padding: 16px; border-radius: 10px; margin-top: 20px; }}
    </style></head><body><div class="container">
        <div class="header">
            <h1>R-I-C-O Bot v5.0</h1>
            <p>Largo plazo + Táctico — {fecha_hora}</p>
            <p style="color:#00d4ff; font-size:12px;">USD/CLP: ${usd_clp:,.0f} | Presupuesto: {50000:,} CLP</p>
        </div>"""

    # --- Régimen de mercado ---
    regimen = decision["regimen"]
    if regimen["estado"] == "CAUTELA":
        html += f'<div class="alerta-amarilla"><b>MODO CAUTELA</b><br>{regimen["mensaje"]}</div>'
    else:
        html += '<div class="alerta-verde"><b>RÉGIMEN NORMAL</b><br>DCA y tácticas funcionando según plan.</div>'

    # --- Backtest results ---
    if backtest_results and backtest_results["sharpe"] > 0:
        html += f"""
        <div class="backtest-table">
            <h3 style="color:#00d4ff;">Validación de Señales (Backtest)</h3>
            <table>
                <tr><th>Métrica</th><th>Valor</th></tr>
                <tr><td>Sharpe Ratio</td><td>{backtest_results['sharpe']:.2f}</td></tr>
                <tr><td>Max Drawdown</td><td>{backtest_results['max_drawdown']:.2%}</td></tr>
                <tr><td>Win Rate</td><td>{backtest_results['win_rate']:.2%}</td></tr>
                <tr><td>Profit Factor</td><td>{backtest_results['profit_factor']:.2f}</td></tr>
                <tr><td>Total Return</td><td>{backtest_results['total_return']:.2%}</td></tr>
            </table>
        </div>"""

    # --- Alertas de venta (solo acciones) ---
    if decision["alertas_venta"]:
        html += '<div class="alerta-roja"><b>ALERTAS DE VENTA</b></div>'
        for av in decision["alertas_venta"]:
            info = av["alerta_venta"]
            html += f"""<div class="alerta-roja">
                ALERTA DE VENTA: {av['simbolo']} ({info['fase']})<br>
                {info['etiqueta']}<br>
                <small>RSI: {av['rsi']} | Surge 5d: {av['surge_semanal']}%</small>
            </div>"""

    if decision["trailing_stops"]:
        html += '<div class="alerta-roja"><b>TRAILING STOPS</b></div>'
        for ts in decision["trailing_stops"]:
            html += f"""<div class="alerta-roja">
                TRAILING STOP: {ts['simbolo']}<br>
                Caída {ts['distancia_max']}% desde máximo 52s (${ts['max_52']})<br>
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

    for r in decision["resultados"]:
        if not r:
            continue
            
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
                <span class="ind">Mom 12m: {r['momentum_12m']}%</span>
                <span class="ind">MA20: {r['ma20'] or '—'}</span>
                <span class="ind">MA200: {r['ma200'] or '—'}</span>
                <span class="ind">Vol: {r['volatilidad']}%</span>
                <span class="ind">VolRatio: {r['vol_ratio']}x</span>
                <span class="ind">Tendencia: {r['tendencia']}</span>
                <span class="ind">Dist.Max: -{r['distancia_max']}%</span>
                <span class="ind">Surge5d: {r['surge_semanal']}%</span>
            </div></div>"""

    # --- Contexto cualitativo ---
    if contexto_llm and any(contexto_llm.values()):
        html += '<div class="contexto-card"><h3 style="color:#00d4ff;">Contexto Cualitativo (LLM)</h3>'
        for ticker, ctx in contexto_llm.items():
            html += f"""
            <div class="card">
                <h4 style="color:#00d4ff;">{ticker}</h4>
                <p><b>Contexto:</b> {ctx.get('contexto', 'N/A')}</p>
                <p><b>Riesgo clave:</b> {ctx.get('riesgo_clave', 'N/A')}</p>
                <p><b>Confianza:</b> {ctx.get('confianza', 'N/A')}</p>
            </div>
            """
        html += '</div>'

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
            v5.0 trata ETFs y acciones con logicas distintas. ETFs = largo plazo (momentum).
            Acciones = tactico (RSI + filtros). DCA de ETFs nunca se pausa salvo burbuja extrema.
        </p>
    </div>"""

    html += f"""<div class="footer">
            R-I-C-O Bot v5.0 — Sistema dual (largo plazo + tactico)<br>
            Datos: Yahoo Finance | GitHub Actions<br>
            Esto NO es asesoria financiera.
        </div></div></body></html>"""

    return html

def enviar_correo(html: str, fecha_hora: str, settings: Dict[str, Any]) -> bool:
    """Envía el reporte por correo"""
    if not all([settings['EMAIL_DESTINO'], settings['EMAIL_USUARIO'], settings['EMAIL_PASSWORD']]):
        logger.warning("Variables de correo no configuradas. Saltando envio.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"R-I-C-O Bot v5.0 — {fecha_hora}"
        msg["From"]    = settings['EMAIL_USUARIO']
        msg["To"]      = settings['EMAIL_DESTINO']
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings['SMTP_SERVER'], settings['SMTP_PORT']) as server:
            server.starttls()
            server.login(settings['EMAIL_USUARIO'], settings['EMAIL_PASSWORD'])
            server.sendmail(settings['EMAIL_USUARIO'], settings['EMAIL_DESTINO'], msg.as_string())
        logger.info("Correo enviado exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error enviando correo: {e}")
        return False
