"""Script de prueba para envío de reportes por correo.

Demuestra cómo configurar Gmail y enviar un reporte en PDF.

Pasos previos (IMPORTANTE):
1. Habilitar 2FA en tu cuenta Google:
   https://myaccount.google.com/security
   
2. Crear una App Password:
   https://myaccount.google.com/apppasswords
   - Selecciona "Mail" y "Windows Computer"
   - Google te dará una contraseña de 16 caracteres con espacios (ej: "xxxx xxxx xxxx xxxx")
   
3. Opción A (Recomendado): Guardar credenciales en variables de entorno:
   PowerShell:
     $env:GMAIL_SENDER_EMAIL = "tu@gmail.com"
     $env:GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   
   Luego ejecutar: python .\scripts\test_email_send.py
   
4. Opción B (Solo para prueba): Pasar directamente en línea de comandos:
   python .\scripts\test_email_send.py --sender tu@gmail.com --password "xxxx xxxx xxxx xxxx" --recipient destinatario@example.com

Uso:
  python .\scripts\test_email_send.py [--sender EMAIL] [--password PASS] [--recipient EMAIL] [--pdf RUTA]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import logging
from outputs.email_sender import EmailSender
from outputs.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("test_email_send")


def main(
    sender_email: str = None,
    app_password: str = None,
    recipient_email: str = None,
    pdf_path: str = None,
):
    """Prueba el envío de correo con un reporte."""
    
    LOG.info("=== Prueba de Envío de Reporte por Correo ===\n")
    
    # Paso 1: Obtener credenciales
    if not sender_email or not app_password:
        sender_email, app_password = EmailSender.get_credentials_from_env()
        if not sender_email or not app_password:
            LOG.error(
                "Credenciales no configuradas.\n"
                "Configura GMAIL_SENDER_EMAIL y GMAIL_APP_PASSWORD en el entorno:\n"
                "  $env:GMAIL_SENDER_EMAIL = 'tu@gmail.com'\n"
                "  $env:GMAIL_APP_PASSWORD = 'xxxx xxxx xxxx xxxx'"
            )
            return 1
    
    LOG.info(f"✓ Correo de origen: {sender_email}")
    
    # Paso 2: Obtener dirección de destino
    if not recipient_email:
        recipient_email = EmailSender.prompt_recipient()
        if not recipient_email:
            return 1
    
    LOG.info(f"✓ Correo destino: {recipient_email}")
    
    # Paso 3: Generar o buscar PDF
    if not pdf_path or not Path(pdf_path).exists():
        LOG.info("Generando reporte de prueba...")
        gen = ReportGenerator(
            camera_name="Cámara Prueba",
            sector="Laboratorio",
            facility="Centro de Pruebas"
        )
        
        # Evento simulado
        event = {
            "event_type": "caída",
            "start_time": "2025-12-11T14:30:00+00:00",
            "duration_seconds": 8.5,
            "start_frame": 50,
            "end_frame": 350,
        }
        
        pdf_path = gen.generate_report(
            event=event,
            frame_image=None,
            output_dir="reports"
        )
        
        if not pdf_path:
            LOG.error("Fallo al generar reporte PDF")
            return 1
    
    LOG.info(f"✓ PDF a enviar: {pdf_path}")
    
    # Paso 4: Enviar
    LOG.info("Enviando correo...")
    sender = EmailSender(sender_email=sender_email, app_password=app_password)
    success = sender.send_report(
        recipient_email=recipient_email,
        pdf_path=pdf_path,
        subject="[Demo] Reporte de Detección de Caída",
        body=(
            "Se ha detectado una caída en el sistema de vigilancia.\n"
            "Por favor, revise el reporte adjunto para más detalles.\n\n"
            "Información del evento:\n"
            "- Tipo: Caída detectada\n"
            "- Duración: 8.5 segundos\n"
            "- Cámara: Cámara Prueba\n"
            "- Sector: Laboratorio\n\n"
            "Sistema de Vigilancia Digital IA"
        )
    )
    
    if success:
        LOG.info("✓ Reporte enviado exitosamente")
        print(f"\n✓ El reporte ha sido enviado a: {recipient_email}")
        return 0
    else:
        LOG.error("✗ Fallo al enviar el reporte")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prueba envío de reportes PDF por correo Gmail"
    )
    parser.add_argument("--sender", help="Email de origen (ó usa GMAIL_SENDER_EMAIL env var)")
    parser.add_argument("--password", help="App Password de Gmail (ó usa GMAIL_APP_PASSWORD env var)")
    parser.add_argument("--recipient", help="Email destinatario (será solicitado si no se proporciona)")
    parser.add_argument("--pdf", help="Ruta al PDF (se genera uno de prueba si no existe)")
    
    args = parser.parse_args()
    
    sys.exit(main(
        sender_email=args.sender,
        app_password=args.password,
        recipient_email=args.recipient,
        pdf_path=args.pdf,
    ))
