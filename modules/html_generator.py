def enviar_correo(html: str, fecha_hora: str, settings: Dict[str, Any]) -> bool:
    """Envía el reporte por correo con soporte SSL (465) y STARTTLS (587)."""
    if not all([settings['EMAIL_DESTINO'], settings['EMAIL_USUARIO'], settings['EMAIL_PASSWORD']]):
        logger.warning("Variables de correo no configuradas. Saltando envio.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"R-I-C-O Bot v5.0 — {fecha_hora}"
        msg["From"]    = settings['EMAIL_USUARIO']
        msg["To"]      = settings['EMAIL_DESTINO']
        msg.attach(MIMEText(html, "html"))

        port = settings['SMTP_PORT']
        server_host = settings['SMTP_SERVER']

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
