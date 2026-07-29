# app/services/email_service.py
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send_smtp_email(to_email: str, subject: str, body: str) -> bool:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("EMAIL_USER")
    smtp_password = os.getenv("EMAIL_PASS")

    if not smtp_user or not smtp_password:
        print("Configuración SMTP no encontrada")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando email: {str(e)}")
        return False


def send_password_change_notification(email: str, nombre: str) -> bool:
    """Envía notificación por email cuando se cambia la contraseña desde la web"""
    fecha_cambio = datetime.now().strftime("%d/%m/%Y a las %H:%M")
    body = f"""
Hola {nombre},

Te informamos que tu contraseña ha sido cambiada exitosamente el {fecha_cambio}.

DETALLES DEL CAMBIO:
• Cambio realizado desde: Aplicación Web (usuario logueado)
• Fecha y hora: {fecha_cambio}
• IP: [Sistema interno]

Si no realizaste este cambio, contacta inmediatamente con el administrador del sistema.

RECORDATORIOS DE SEGURIDAD:
• Nunca compartas tu contraseña con otras personas
• Usa contraseñas únicas y seguras
• Si sospechas actividad no autorizada, cambia tu contraseña inmediatamente

Saludos,
Administración Polo 52
    """
    sent = _send_smtp_email(email, "Contraseña Cambiada - Polo 52", body)
    if sent:
        print(f"Notificación de cambio de contraseña enviada a {email}")
    return sent


def send_password_change_failure_notification(email: str, nombre: str, reason: str) -> bool:
    """Avisa que un intento de cambio de contraseña falló (flujo logueado)."""
    body = f"""
Hola {nombre},

Se intentó actualizar tu contraseña pero ocurrió un problema:
- Detalle: {reason}

Por favor, intentá nuevamente. Si el problema persiste, contactá soporte.

Saludos,
Administración Polo 52
    """
    return _send_smtp_email(email, "Polo 52 - No pudimos actualizar tu contraseña", body)


def send_password_reset_email(email: str, nombre: str, reset_link: str) -> bool:
    """Envía el link para restablecer contraseña (flujo 'olvidé mi contraseña')."""
    body = f"""
Hola {nombre},

Has solicitado restablecer tu contraseña en el sistema del Parque Industrial Polo 52.

Para proceder con el cambio, haz clic en el siguiente enlace:
{reset_link}

INSTRUCCIONES IMPORTANTES:
• Deberás ingresar una nueva contraseña dos veces para confirmar
• No podrás usar contraseñas que hayas utilizado anteriormente
• Este enlace expirará en 1 hora por seguridad
• Solo se puede usar una vez

REQUISITOS PARA LA NUEVA CONTRASEÑA:
• Mínimo 8 caracteres
• Al menos una letra mayúscula
• Al menos una letra minúscula
• Al menos un número

Si no solicitaste este cambio, puedes ignorar este email de forma segura.

Saludos,
Administración Polo 52
    """
    return _send_smtp_email(email, "Recuperar Contraseña - Polo 52", body)


def send_admin_password_change_request_email(email: str, nombre: str, reset_link: str) -> bool:
    """Envía el link de cambio de contraseña solicitado por un admin_polo logueado."""
    body = f"""
Hola {nombre},

Has solicitado cambiar tu contraseña como administrador del polo.

Para proceder con el cambio, haz clic en el siguiente enlace:
{reset_link}

RECUERDA:
• Necesitarás tu contraseña actual
• Deberás confirmar la nueva contraseña dos veces
• No podrás reutilizar contraseñas anteriores
• Este enlace expira en 1 hora

Si no solicitaste este cambio, ignora este email.

Saludos,
Sistema Polo 52
    """
    return _send_smtp_email(email, "Cambio de Contraseña Admin Polo - Polo 52", body)


def send_welcome_email(email: str, nombre: str, username: str, password: str) -> bool:
    """Envía email de bienvenida con credenciales"""
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200").rstrip("/")
    body = f"""
Hola {nombre},

Se le ha creado una nueva cuenta en "Parque Industrial Polo 52".

Sus credenciales de acceso son:

Nombre de usuario: {username}
Contraseña temporal: {password}

Se le recomienda solicitar el cambio de contraseña cuando acceda por primera vez.

Para comenzar a usar el sistema, ingrese en:
{frontend_url}/login

Si necesita ayuda, puede contactar con el administrador del sitio.

Saludos,
Administración Polo 52
    """
    sent = _send_smtp_email(email, "Bienvenido al Parque Industrial Polo 52", body)
    if sent:
        print(f"Email enviado exitosamente a {email}")
    return sent
