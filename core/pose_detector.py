import logging
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
import math

class PoseDetector:
    """Wrapper ligero sobre MediaPipe Pose optimizado para uso en streaming.

    Mejoras aplicadas:
    - `model_complexity` por defecto a 0 (más rápido) y configurable.
    - `frame_scale` permite procesar una versión reducida del frame (más rápido).
    - Manejo de errores en `process` para evitar caídas del contenedor.
    - `close()` y context manager para liberar recursos explícitamente.
    - Type hints y docstrings para facilitar mantenimiento.
    """

    def __init__(
        self,
        mode: bool = False,
        complexity: int = 0,
        smooth: bool = True,
        detection_con: float = 0.5,
        track_con: float = 0.5,
        frame_scale: float = 1.0,
    ) -> None:
        """Inicializa MediaPipe Pose.

        Args:
            mode: si True, fuerza procesamiento por imagen (sin tracking entre frames).
            complexity: 0 (rápido), 1 (balanceado), 2 (preciso pero lento).
            smooth: suaviza landmarks entre frames.
            detection_con: umbral mínimo para la detección inicial.
            track_con: umbral mínimo para el tracking entre frames.
            frame_scale: escala a la que se procesa el frame (0.5 = mitad de resolución).
        """
        self.logger = logging.getLogger(__name__)
        self.mode = mode
        self.complexity = complexity
        self.smooth = smooth
        self.detection_con = detection_con
        self.track_con = track_con
        self.frame_scale = float(frame_scale)

        self.mp_draw = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose

        # Crear una instancia persistente de Pose y reutilizarla (más eficiente que crearla por frame)
        self.pose = self.mp_pose.Pose(
            static_image_mode=self.mode,
            model_complexity=self.complexity,
            smooth_landmarks=self.smooth,
            enable_segmentation=False,
            min_detection_confidence=self.detection_con,
            min_tracking_confidence=self.track_con,
        )
        self.results: Optional[object] = None

    def find_pose(self, img: 'np.ndarray', draw: bool = True) -> Tuple['np.ndarray', Optional[object]]:
        """Procesa un frame y (opcionalmente) dibuja los landmarks sobre la imagen original.

        Para mejorar rendimiento se puede reducir la resolución mediante `frame_scale`.

        Args:
            img: imagen BGR tal como la devuelve OpenCV.
            draw: si True dibuja landmarks sobre la imagen original.

        Returns:
            Tupla (imagen_con_dibujo, results) donde `results` es el objeto retornado por MediaPipe.
        """
        orig_img = img

        # Aplicar reescalado si se configuró (usar valores <1.0 acelera el procesamiento)
        proc_img = img
        if self.frame_scale > 0 and self.frame_scale != 1.0:
            try:
                proc_img = cv2.resize(
                    img, (0, 0), fx=self.frame_scale, fy=self.frame_scale, interpolation=cv2.INTER_LINEAR
                )
            except Exception as e:
                self.logger.exception("Error al reescalar imagen: %s", e)
                proc_img = img

        # MediaPipe necesita RGB
        img_rgb = cv2.cvtColor(proc_img, cv2.COLOR_BGR2RGB)

        try:
            # Procesamiento central (puede lanzar excepciones en casos raros)
            self.results = self.pose.process(img_rgb)
        except Exception:
            self.logger.exception("MediaPipe processing error; retornando imagen original")
            return orig_img, None

        if self.results and getattr(self.results, 'pose_landmarks', None):
            if draw:
                # Dibujar sobre la imagen original usando landmarks normalizados (se ajustan a tamaño automáticamente)
                try:
                    self.mp_draw.draw_landmarks(
                        orig_img,
                        self.results.pose_landmarks,
                        self.mp_pose.POSE_CONNECTIONS,
                        self.mp_draw.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                        self.mp_draw.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2),
                    )
                except Exception:
                    self.logger.exception("Error dibujando landmarks")

        return orig_img, self.results

    def find_position(self, img: 'np.ndarray', results: Optional[object] = None, draw: bool = True) -> Tuple[List[List[int]], Dict[str, int]]:
        """Extrae coordenadas de landmarks y bounding box.

        Args:
            img: imagen BGR original (se usa para convertir coordenadas normalizadas a píxeles).
            results: objeto retornado por `find_pose` o por `pose.process`.
            draw: si True dibuja la bounding box sobre la imagen.

        Returns:
            (lm_list, bbox_info)
        """
        lm_list: List[List[int]] = []
        bbox_info: Dict[str, int] = {}

        if results is None:
            results = self.results

        if not results or not getattr(results, 'pose_landmarks', None):
            return lm_list, bbox_info

        h, w, c = img.shape
        x_list: List[int] = []
        y_list: List[int] = []

        for idx, lm in enumerate(results.pose_landmarks.landmark):
            cx, cy = int(lm.x * w), int(lm.y * h)
            lm_list.append([idx, cx, cy])
            x_list.append(cx)
            y_list.append(cy)

        if x_list and y_list:
            xmin, xmax = min(x_list), max(x_list)
            ymin, ymax = min(y_list), max(y_list)
            bbox_info = {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "width": xmax - xmin, "height": ymax - ymin}

            if draw:
                try:
                    cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                except Exception:
                    self.logger.exception("Error dibujando bounding box")

        return lm_list, bbox_info

    def close(self) -> None:
        """Cierra/Libera los recursos asociados a MediaPipe Pose."""
        try:
            self.pose.close()
        except Exception:
            self.logger.exception("Error cerrando MediaPipe Pose")

    def __enter__(self) -> 'PoseDetector':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()