import cv2
import mediapipe as mp
import math

class PoseDetector:
    def __init__(self, mode=False, complexity=1, smooth=True, detection_con=0.5, track_con=0.5):
        """
        Inicializa el modelo de MediaPipe Pose.
        complexity: 0 (rápido), 1 (balanceado), 2 (preciso pero lento).
        """
        self.mode = mode
        self.complexity = complexity
        self.smooth = smooth
        self.detection_con = detection_con
        self.track_con = track_con

        self.mp_draw = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        
        # Inicializamos el objeto Pose de MediaPipe
        self.pose = self.mp_pose.Pose(
            static_image_mode=self.mode,
            model_complexity=self.complexity,
            smooth_landmarks=self.smooth,
            min_detection_confidence=self.detection_con,
            min_tracking_confidence=self.track_con
        )
        self.results = None

    def find_pose(self, img, draw=True):
        """
        Recibe un frame, detecta la pose y dibuja el esqueleto si se solicita.
        Retorna la imagen procesada.
        """
        # MediaPipe usa RGB, OpenCV usa BGR. Hay que convertir.
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # PROCESAMIENTO PRINCIPAL: Aquí ocurre la magia de la IA
        self.results = self.pose.process(img_rgb)

        if self.results.pose_landmarks:
            if draw:
                # Dibuja las conexiones y puntos del cuerpo sobre la imagen original
                self.mp_draw.draw_landmarks(
                    img, 
                    self.results.pose_landmarks, 
                    self.mp_pose.POSE_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), # Puntos
                    self.mp_draw.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)  # Líneas
                )
        return img

    def find_position(self, img, draw=True):
        """
        Extrae las coordenadas (x, y) de los puntos clave.
        Retorna una lista con los landmarks y la caja delimitadora (bounding box).
        """
        lm_list = []
        bbox_info = {}
        if self.results.pose_landmarks:
            h, w, c = img.shape
            x_list = []
            y_list = []
            
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                # Convertir coordenadas normalizadas (0.0-1.0) a píxeles
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])
                x_list.append(cx)
                y_list.append(cy)

            # Calcular Bounding Box (Caja que encierra al humano)
            xmin, xmax = min(x_list), max(x_list)
            ymin, ymax = min(y_list), max(y_list)
            bbox_info = {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "width": xmax-xmin, "height": ymax-ymin}

            if draw:
                # Dibujar rectángulo alrededor de la persona
                cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        
        return lm_list, bbox_info