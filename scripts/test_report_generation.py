"""Script de prueba para generar reportes PDF.

Simula un evento de caída y genera un reporte PDF con imagen.
Útil para verificar que los reportes se generan correctamente
antes de implementar el envío por email.

Uso:
  python scripts/test_report_generation.py --video tests/test_videos/fall_sample_01.mp4 --output reports
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
from core.pose_detector import PoseDetector
from outputs.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("test_report_generation")


def main(video_path: str, output_dir: str):
    """Procesa un video, detecta una caída y genera un reporte PDF."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Abrir video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        LOG.error("No se pudo abrir el video: %s", video_path)
        return 1

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    LOG.info("Video abierto: %d frames", total_frames)

    # Inicializar detector
    detector = PoseDetector(complexity=1)
    generator = ReportGenerator(
        camera_name="Cámara Sala Principal",
        sector="Planta 1 - Pasillo Este",
        facility="Centro de Cuidados del Adulto Mayor",
    )

    frame_idx = 0
    fall_detected = False
    captured_frame = None

    # Procesar video hasta encontrar una caída
    while cap.isOpened() and not fall_detected:
        success, frame = cap.read()
        if not success:
            break

        frame_idx += 1

        # Detectar pose
        proc_frame, results = detector.find_pose(frame, draw=True)
        lm_list, bbox = detector.find_position(proc_frame, results, draw=True)

        # Lógica de detección de caída
        if bbox:
            aspect_ratio = bbox["height"] / max(1, bbox["width"])
            is_falling = aspect_ratio < 0.8

            if is_falling:
                LOG.info(
                    "✓ Caída detectada en frame %d (aspect_ratio=%.2f)",
                    frame_idx,
                    aspect_ratio,
                )
                fall_detected = True
                captured_frame = proc_frame.copy()

        # Mostrar progreso cada 100 frames
        if frame_idx % 100 == 0:
            LOG.info(
                "Procesados %d/%d frames (%.1f%%)",
                frame_idx,
                total_frames,
                100 * frame_idx / total_frames,
            )

    cap.release()

    if not fall_detected or captured_frame is None:
        LOG.warning(
            "No se detectó caída en el video. Usando frame 50 como ejemplo."
        )
        cap = cv2.VideoCapture(video_path)
        for _ in range(50):
            success, frame = cap.read()
            if success:
                captured_frame = frame
        cap.release()

    # Crear evento simulado
    event = {
        "event_type": "caída",
        "start_time": "2025-12-11T14:30:00+00:00",
        "duration_seconds": 12.5,
        "start_frame": 50,
        "metadata": {
            "aspect_ratio": 0.75,
            "frames_count": 300,
        },
    }

    LOG.info("Generando reporte PDF...")
    pdf_path = generator.generate_report(
        event=event,
        frame_image=captured_frame,
        output_dir=output_dir,
    )

    if pdf_path:
        LOG.info("✓ Reporte generado exitosamente: %s", pdf_path)
        print(f"\nReporte guardado en: {pdf_path}")
        return 0
    else:
        LOG.error("✗ Fallo al generar reporte")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera un reporte PDF de prueba con detección de caída"
    )
    parser.add_argument(
        "--video",
        default="tests/test_videos/fall_sample_01.mp4",
        help="Ruta al video MP4",
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Directorio donde guardar el PDF",
    )
    args = parser.parse_args()

    sys.exit(main(video_path=args.video, output_dir=args.output))
