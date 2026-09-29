"""
helpers/mailer.py
Envío de correos de verificación de email vía Postfix local.
Usa smtplib (stdlib) conectándose a localhost:25, sin autenticación SMTP externa.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import MAIL_FROM, MAIL_SMTP_HOST, MAIL_SMTP_PORT, BASE_URL


def send_verification_email(to_email, token, nombre):
    """
    Envía un correo de verificación al usuario recién registrado.

    Args:
        to_email: dirección de correo del destinatario.
        token: token de verificación único.
        nombre: nombre del usuario para personalizar el saludo.
    """
    verification_url = f"{BASE_URL}/verify-email?token={token}"

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #2c3e50;">¡Bienvenido a Librería en Línea!</h2>
    <p>Hola <strong>{nombre}</strong>,</p>
    <p>Gracias por registrarte. Para activar tu cuenta, haz clic en el siguiente enlace:</p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{verification_url}"
           style="background-color: #3498db; color: white; padding: 12px 30px;
                  text-decoration: none; border-radius: 5px; font-size: 16px;">
            Verificar mi cuenta
        </a>
    </p>
    <p>O copia y pega esta URL en tu navegador:</p>
    <p style="word-break: break-all; color: #7f8c8d;">{verification_url}</p>
    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
    <p style="color: #95a5a6; font-size: 12px;">
        Este enlace expira en 24 horas. Si no solicitaste esta cuenta, ignora este correo.
    </p>
</body>
</html>"""

    text_body = (
        f"Hola {nombre},\n\n"
        f"Gracias por registrarte en Librería en Línea.\n"
        f"Para verificar tu cuenta, visita:\n{verification_url}\n\n"
        f"Este enlace expira en 24 horas.\n"
    )

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Verifica tu cuenta — Librería en Línea'
    msg['From'] = MAIL_FROM
    msg['To'] = to_email

    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP(MAIL_SMTP_HOST, MAIL_SMTP_PORT, timeout=3.0) as server:
        server.send_message(msg)

