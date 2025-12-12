"""Generador de reportes visuales en PDF para detección de caídas.

Crea un documento PDF con:
 - Imagen del frame donde se detectó la caída
 - Información: fecha, hora, cámara, sector
 - Estadísticas del evento

Uso:
    generator = ReportGenerator(camera_name="Sala Principal", sector="Planta 1")
    pdf_path = generator.generate_report(
        event=event_dict,
        frame_image=cv2_frame,
        output_dir="reports"
    )
"""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

import cv2

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

LOG = logging.getLogger(__name__)


class ReportGenerator:
    """Generador de reportes PDF para eventos de caída."""

    def __init__(
        self,
        camera_name: str = "Cámara 1",
        sector: str = "Sector Desconocido",
        facility: str = "Instalación",
    ) -> None:
        """
        Inicializa el generador de reportes.

        Args:
            camera_name: Nombre amigable de la cámara (ej: "Sala Principal")
            sector: Ubicación del sector (ej: "Planta 1", "Pasillo Oeste")
            facility: Nombre de la instalación (ej: "Centro de Cuidados")
        """
        if not HAS_REPORTLAB:
            LOG.warning(
                "reportlab no instalado. Instala con: pip install reportlab"
            )
        self.camera_name = camera_name
        self.sector = sector
        self.facility = facility

    def generate_report(
        self,
        event: Dict[str, Any],
        frame_image: Optional[Any] = None,
        output_dir: Union[str, Path] = "reports",
        return_bytes: bool = False,
    ) -> Optional[Union[str, bytes]]:
        """
        Genera un reporte PDF con la información del evento y la imagen.

        Args:
            event: Diccionario con el evento (debe tener 'start_time', 'duration_seconds', etc)
            frame_image: Frame de OpenCV (numpy array) a incluir en el reporte
            output_dir: Directorio donde guardar el PDF
            return_bytes: Si True, retorna bytes del PDF en lugar de la ruta del archivo

        Returns:
            Ruta del archivo PDF (str) o bytes del PDF si return_bytes=True,
            None si falla.
        """
        if not HAS_REPORTLAB:
            LOG.error("reportlab no está disponible. Instala con: pip install reportlab")
            return None

        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Procesar timestamp
            start_time_str = event.get("start_time", "")
            if start_time_str:
                try:
                    dt = datetime.fromisoformat(start_time_str)
                except Exception:
                    dt = datetime.now(timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            fecha = dt.strftime("%Y-%m-%d")
            hora = dt.strftime("%H:%M:%S")
            duracion = event.get("duration_seconds", 0)

            # Guardar imagen si la proporciona
            temp_image_path = None
            if frame_image is not None:
                try:
                    # Crear imagen temporal en formato PNG
                    with tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    ) as tmp:
                        temp_image_path = tmp.name
                    cv2.imwrite(temp_image_path, frame_image)
                    LOG.info("Imagen del evento guardada en: %s", temp_image_path)
                except Exception as exc:
                    LOG.warning("No se pudo guardar la imagen: %s", exc)
                    temp_image_path = None

            # Crear nombre único del PDF
            timestamp = dt.strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"reporte_caida_{timestamp}.pdf"
            pdf_path = output_path / pdf_filename

            # Generar PDF
            self._create_pdf(
                pdf_path=str(pdf_path),
                fecha=fecha,
                hora=hora,
                duracion=duracion,
                image_path=temp_image_path,
                event=event,
            )

            LOG.info("Reporte PDF generado: %s", pdf_path)

            # Limpiar imagen temporal si existe
            if temp_image_path and Path(temp_image_path).exists():
                try:
                    Path(temp_image_path).unlink()
                except Exception:
                    pass

            if return_bytes:
                with open(pdf_path, "rb") as f:
                    return f.read()
            return str(pdf_path)

        except Exception as exc:
            LOG.exception("Error generando reporte PDF: %s", exc)
            return None

    def _create_pdf(
        self,
        pdf_path: str,
        fecha: str,
        hora: str,
        duracion: float,
        image_path: Optional[str],
        event: Dict[str, Any],
    ) -> None:
        """Crea el documento PDF con contenido formateado."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas as pdf_canvas

        c = pdf_canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter

        # Encabezado
        c.setFont("Helvetica-Bold", 20)
        c.drawString(0.5 * inch, height - 0.7 * inch, "REPORTE DE CAÍDA DETECTADA")

        c.setFont("Helvetica", 10)
        c.drawString(0.5 * inch, height - 1.0 * inch, f"Instalación: {self.facility}")
        c.drawString(0.5 * inch, height - 1.2 * inch, f"Cámara: {self.camera_name}")
        c.drawString(0.5 * inch, height - 1.4 * inch, f"Sector: {self.sector}")

        # Línea separadora
        c.setLineWidth(1)
        c.line(0.5 * inch, height - 1.6 * inch, width - 0.5 * inch, height - 1.6 * inch)

        # Información del evento
        y_pos = height - 2.0 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.5 * inch, y_pos, "Información del Evento:")

        y_pos -= 0.3 * inch
        c.setFont("Helvetica", 11)
        c.drawString(0.7 * inch, y_pos, f"Fecha: {fecha}")
        y_pos -= 0.25 * inch
        c.drawString(0.7 * inch, y_pos, f"Hora: {hora}")
        y_pos -= 0.25 * inch
        c.drawString(0.7 * inch, y_pos, f"Duración de la caída: {duracion:.2f} segundos")

        y_pos -= 0.35 * inch

        # Imagen
        if image_path and Path(image_path).exists():
            try:
                c.setFont("Helvetica-Bold", 11)
                c.drawString(0.5 * inch, y_pos, "Captura de Video:")
                y_pos -= 0.25 * inch

                # Redimensionar imagen para que quepa en la página manteniendo proporción
                from reportlab.lib.utils import ImageReader

                reader = ImageReader(image_path)
                img_width, img_height = reader.getSize()

                max_width = 7 * inch
                max_height = 4 * inch

                scale = min(max_width / img_width, max_height / img_height, 1.0)
                draw_w = img_width * scale
                draw_h = img_height * scale

                x = 0.5 * inch
                y = y_pos - draw_h
                c.drawImage(reader, x, y, width=draw_w, height=draw_h)
                y_pos = y - 0.3 * inch
            except Exception as exc:
                LOG.warning("No se pudo insertar imagen en PDF: %s", exc)

        # Pie de página
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.grey)
        c.drawString(
            0.5 * inch,
            0.4 * inch,
            f"Reporte generado automáticamente - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        )

        c.save()
        LOG.info("PDF guardado en: %s", pdf_path)