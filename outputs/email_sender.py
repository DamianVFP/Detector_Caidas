"""Módulo para enviar reportes por correo electrónico usando Gmail.

Configuración requerida:
1. Habilitar 2FA en tu cuenta Google (https://myaccount.google.com/security)
2. Crear una App Password (https://myaccount.google.com/apppasswords)
   - Selecciona "Mail" y "Windows Computer"
   - Google te generará una contraseña de 16 caracteres
3. Guardar la contraseña en variable de entorno o pasarla al módulo

Uso:
    sender = EmailSender(sender_email="tu@gmail.com", app_password="xxxx xxxx xxxx xxxx")
    sender.send_report(
        recipient_email="destinatario@example.com",
        pdf_path="reportes/reporte_caida_20251211_143000.pdf",
        subject="Alerta: Caída Detectada"
    )

Alternativa con variables de entorno:
    export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
    export GMAIL_SENDER_EMAIL="tu@gmail.com"
    
    sender = EmailSender()  # Lee del entorno automáticamente
    sender.send_report(recipient_email="...")
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

LOG = logging.getLogger(__name__)


class EmailSender:
    """Envía reportes por correo electrónico usando Gmail SMTP."""

    def __init__(
        self,
        sender_email: Optional[str] = None,
        app_password: Optional[str] = None,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ) -> None:
        """
        Inicializa el configurador de correo.

        Args:
            sender_email: Email de origen (ej: tu@gmail.com).
                          Si es None, lee de env var GMAIL_SENDER_EMAIL.
            app_password: Contraseña de aplicación de Google (16 caracteres con espacios).
                          Si es None, lee de env var GMAIL_APP_PASSWORD.
            smtp_server: Servidor SMTP de Gmail (por defecto smtp.gmail.com).
            smtp_port: Puerto SMTP (por defecto 587 para TLS).
        """
        self.sender_email = sender_email or os.getenv("GMAIL_SENDER_EMAIL", "")
        self.app_password = app_password or os.getenv("GMAIL_APP_PASSWORD", "")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

        if not self.sender_email or not self.app_password:
            LOG.warning(
                "EmailSender inicializado sin credenciales. "
                "Proporciona sender_email y app_password, o configura variables de entorno: "
                "GMAIL_SENDER_EMAIL y GMAIL_APP_PASSWORD"
            )

    def send_report(
        self,
        recipient_email: str,
        pdf_path: str,
        subject: str = "Reporte de Detección de Caída",
        body: Optional[str] = None,
    ) -> bool:
        """
        Envía un reporte PDF por correo.

        Args:
            recipient_email: Dirección de correo del destinatario.
            pdf_path: Ruta al archivo PDF del reporte.
            subject: Asunto del correo.
            body: Cuerpo del mensaje (opcional; usa texto por defecto si no se proporciona).

        Returns:
            True si el envío fue exitoso, False en caso de error.
        """
        if not self.sender_email or not self.app_password:
            LOG.error(
                "No se han configurado credenciales de correo. "
                "Establece GMAIL_SENDER_EMAIL y GMAIL_APP_PASSWORD."
            )
            return False

        if not Path(pdf_path).exists():
            LOG.error("El archivo PDF no existe: %s", pdf_path)
            return False

        try:
            # Crear mensaje
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient_email
            message["Subject"] = subject

            # Cuerpo del mensaje
            if body is None:
                body = (
                    "Se ha detectado una caída.\n\n"
                    "Por favor, consulte el reporte adjunto para más detalles.\n\n"
                    "Sistema de Vigilancia Digital IA"
                )
            message.attach(MIMEText(body, "plain"))

            # Adjuntar PDF
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            from email import encoders

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {Path(pdf_path).name}",
            )
            message.attach(part)

            # Conectar y enviar
            LOG.info("Conectando a servidor SMTP: %s:%d", self.smtp_server, self.smtp_port)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.send_message(message)

            LOG.info("✓ Correo enviado exitosamente a: %s", recipient_email)
            return True

        except smtplib.SMTPAuthenticationError:
            LOG.error(
                "Error de autenticación. Verifica que la App Password sea correcta. "
                "Obtén una nueva en: https://myaccount.google.com/apppasswords"
            )
            return False
        except smtplib.SMTPException as exc:
            LOG.error("Error SMTP al enviar correo: %s", exc)
            return False
        except Exception as exc:
            LOG.exception("Error inesperado al enviar correo: %s", exc)
            return False

    @staticmethod
    def prompt_recipient() -> Optional[str]:
        """Pide al usuario que ingrese la dirección de correo destino por consola.

        Returns:
            Dirección de correo válida o None si el usuario cancela.
        """
        while True:
            email = input("\nIngresa la dirección de correo para enviar el reporte: ").strip()
            if not email:
                print("Operación cancelada.")
                return None
            if "@" in email and "." in email.split("@")[1]:
                return email
            print("Dirección de correo inválida. Intenta nuevamente.")

    @staticmethod
    def get_credentials_from_env() -> tuple[Optional[str], Optional[str]]:
        """Lee las credenciales de Gmail desde variables de entorno.

        Returns:
            Tupla (sender_email, app_password) o (None, None) si no están configuradas.
        """
        sender = os.getenv("GMAIL_SENDER_EMAIL")
        password = os.getenv("GMAIL_APP_PASSWORD")
        return sender, password
