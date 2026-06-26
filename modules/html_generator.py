# ============================================================================
#  MÓDULO 8 — GENERADOR HTML + ENVÍO DE CORREO
# ============================================================================

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Any

from .config import load_settings

logger = logging.getLogger(__name__)


def generar_html(resultados: List[Dict],
                 decision: Dict,
                 usd_clp: float,
                 fecha_hora: str,
                 backtest_results: Dict,
                 contexto_llm: Dict) -> str:
    """Genera el HTML del reporte para el email."""
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
    if backtest_results and backtest_results.get("sharpe", 0) > 0:
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

    # --- Alertas de venta ---
    if decision.get("alertas_venta"):
        for av in decision["alertas_venta"]:
            info = av.get("alerta_venta", {})
            html += f"""<div class="alerta-roja">
                ALERTA DE VENTA: {av['simbolo']} ({info.get('fase', '')})<br>
                {info.get('etiqueta', '')}<br>
                <small>RSI: {av.get('rsi', '')} | Surge 5d: {av.get('surge_semanal', '')}%</small>
            </div>"""

    if decision.get("trailing_stops"):
        for ts in decision["trailing_stops"]:
            html += f"""<div class="alerta-roja">
                TRAILING STOP: {ts['simbolo']}<br>
                Caída {ts.get('distancia_max', 0)}% desde máximo 52s (${ts.get('max_52', 0)})<br>
                <small>Precio: ${ts.get('precio', 0)} | RSI: {ts.get('rsi', '')}</small>
            </div>"""

    # --- Asignación del mes ---
    html += '<div class="resumen"><h3>Asignación del Mes</h3><table>'
    html += '<tr><th>Destino</th><th>Tipo</th><th>Monto CLP</th></tr>'

    if decision["etf"].get("simbolo"):
        html += f'<tr><td style="color:#00d4ff;"><b>{decision["etf"]["simbolo"]}</b></td><td>ETF (DCA)</td><td style="color:#2ecc71;"><b>{decision["etf"]["monto"]:,}</b></td></tr>'

    for acc in decision.get("acciones", []):
        html += f'<tr><td style="color:#00d4ff;"><b>{acc["simbolo"]}</b></td><td>Acción</td><td style="color:#2ecc71;"><b>{acc["monto"]:,}</b></td></tr>'

    if decision.get("reserva_cash", 0) > 0:
        html += f'<tr><td style="color:#3498db;"><b>RESERVA</b></td><td>Cash</td><td style="color:#3498db;"><b>{decision["reserva_cash"]:,}</b></td></tr>'

    html += f'<tr style="border-top:2px solid #00d4ff;"><td colspan="2"><b>TOTAL</b></td><td><b>{decision.get("total_asignado", 0):,} CLP</b></td></tr>'
    html += '</table></div>'

    # --- Detalle por activo ---
    html += '<h2 style="color:#00d4ff; margin-top:25px;">Detalle por Activo</h2>'

    for r in decision.get("resultados", []):
        if not r:
            continue

        senal = r.get("senal", "")
        color = colores.get(senal, "#555")

        if r.get("tipo") == "ETF":
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
        if decision["etf"].get("simbolo") == r.get("simbolo"):
            monto_asignado = decision["etf"].get("monto", 0)
        for acc in decision.get("acciones", []):
            if acc.get("simbolo") == r.get("simbolo"):
                monto_asignado = acc.get("monto", 0)

        html += f'<div class="card {clase_card}">'
        html += f'<span class="ticker">{r.get("simbolo", "")}</span>'
        html += f'<span class="badge" style="background:{color}; margin-left:10px;">{senal}</span>'
        html += f'<span style="color:#888; margin-left:8px; font-size:12px;">({r.get("tipo", "")})</span>'

        if monto_asignado > 0:
            acciones_usd = monto_asignado / usd_clp if usd_clp > 0 else 0
            html += f'<div class="asignacion">{monto_asignado:,} CLP<br><span style="font-size:12px;color:#888;">≈ ${acciones_usd:.1f} USD</span></div>'

        if r.get("razon"):
            html += f'<div style="color:#e67e22; font-size:12px; margin-top:4px;">{r["razon"]}</div>'

        if r.get("tipo") == "ETF":
            html += f"""<div class="indicadores">
                <span class="ind">Precio: ${r.get('precio', 0)}</span>
                <span class="ind">RSI diario: {r.get('rsi', '')}</span>
                <span class="ind">RSI semanal: {r.get('rsi_semanal', '')}</span>
                <span class="ind">RSI mensual: {r.get('rsi_mensual', '')}</span>
                <span class="ind">Mom 6m: {r.get('momentum_6m', 0)}%</span>
                <span class="ind">Mom 12m: {r.get('momentum_12m', 0)}%</span>
                <span class="ind">MA200: {r.get('ma200') or '—'}</span>
                <span class="ind">Tendencia: {r.get('tendencia', '')}</span>
                <span class="ind">vs MA200: +{r.get('distancia_ma200', 0)}%</span>
            </div></div>"""
        else:
            html += f"""<div class="indicadores">
                <span class="ind">Precio: ${r.get('precio', 0)}</span>
                <span class="ind">RSI: {r.get('rsi', '')}</span>
                <span class="ind">Mom 6m: {r.get('momentum_6m', 0)}%</span>
                <span class="ind">Mom 12m: {r.get('momentum_12m', 0)}%</span>
                <span class="ind">MA20: {r.get('ma20') or '—'}</span>
                <span class="ind">MA200: {r.get('ma200') or '—'}</span>
                <span class="ind">Vol: {r.get('volatilidad', 0)}%</span>
                <span class="ind">VolRatio: {r.get('vol_ratio', 0)}x</span>
                <span class="ind">Tendencia: {r.get('tendencia', '')}</span>
                <span class="ind">Dist.Max: -{r.get('distancia_max', 0)}%</span>
                <span class="ind">Surge5d: {r.get('surge_semanal', 0)}%</span>
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
            </div>"""
        html += '</div>'

    # --- Leyenda ---
    html += """<div class="resumen" style="margin-top:20px;">
        <h3>Como Leer Este Reporte</h3>
        <p style="font-size:12px; line-height:1.6;">
            <b style="color:#2ecc71;">DCA MENSUAL (ETF)</b>: Compra automática mes a mes.<br>
            <b style="color:#f39c12;">PAUSAR DCA</b>: Solo si RSI mensual >80 + precio >25% sobre MA200.<br>
            <b style="color:#27ae60;">COMPRAR (acción)</b>: RSI sano + momentum positivo + sobre MA200.<br>
            <b style="color:#e67e22;">PRECAUCION</b>: RSI atractivo pero bajo MA200 o momentum negativo.<br>
            <b style="color:#f39c12;">ESPERAR</b>: RSI alto, sin descuento.<br>
            <b style="color:#e74c3c;">VENDER</b>: Solo acciones. Fases 72 / 78 / 85 de RSI.<br>
            <b style="color:#c0392b;">TRAILING STOP</b>: Solo acciones. Caída >15% desde máximo.
        </p>
    </div>"""

    html += f"""<div class="footer">
            R-I-C-O Bot v5.0 — Sistema dual (largo plazo + táctico)<br>
            Datos: Yahoo Finance | GitHub Actions<br>
            Esto NO es asesoría financiera.
        </div></div></body></html>"""

    return html


def enviar_correo(html: str, fecha_hora: str, settings: Dict[str, Any]) -> bool:
    """Envía el reporte por correo con soporte SSL (465) y STARTTLS (587)."""
    if not all([settings.get('EMAIL_DESTINO'), settings.get('EMAIL_USUARIO'), settings.get('EMAIL_PASSWORD')]):
        logger.warning("Variables de correo no configuradas. Saltando envío.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"R-I-C-O Bot v5.0 — {fecha_hora}"
        msg["From"]    = settings['EMAIL_USUARIO']
        msg["To"]      = settings['EMAIL_DESTINO']
        msg.attach(MIMEText(html, "html"))

        port = settings.get('SMTP_PORT', 587)
        server_host = settings.get('SMTP_SERVER', 'smtp.gmail.com')

        # Puerto 465 = SSL directo; Puerto 587 = STARTTLS
        if port == 465:
            logger.info(f"Conectando vía SSL directo a {server_host}:{port}")
            server = smtplib.SMTP_SSL(server_host, port, timeout=30)
        else:
            logger.info(f"Conectando vía STARTTLS a {server_host}:{port}")
            server = smtplib.SMTP(server_host, port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(settings['EMAIL_USUARIO'], settings['EMAIL_PASSWORD'])
        server.sendmail(settings['EMAIL_USUARIO'], settings['EMAIL_DESTINO'], msg.as_string())
        server.quit()
        logger.info("Correo enviado exitosamente.")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Error de autenticación SMTP: {e}. Verifica EMAIL_USUARIO y EMAIL_PASSWORD.")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"Error de conexión SMTP: {e}. Verifica SMTP_SERVER y SMTP_PORT.")
        return False
    except Exception as e:
        logger.error(f"Error inesperado enviando correo: {type(e).__name__}: {e}")
        return False
