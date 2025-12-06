import cv2
import time
# Importamos NUESTRO módulo modular
from core.pose_detector import PoseDetector

# --- CONFIGURACIÓN RÁPIDA PARA PRUEBAS ---
# Reemplaza esto con el nombre del video que descargaste
VIDEO_PATH = "tu_video_de_caida.mp4" 
# -----------------------------------------

def main():
    # 1. Inicializar Entrada de Video
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Error: No se pudo abrir el video: {VIDEO_PATH}")
        return

    # 2. Inicializar el Cerebro (Detector de Pose)
    # Usamos complexity=1 para buen balance velocidad/precisión
    detector = PoseDetector(complexity=1)

    p_time = 0

    print("Iniciando Sistema Modular Vigilante IA...")
    print("Presiona 'q' para salir.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Fin del video.")
            break

        # --- BUCLE PRINCIPAL DEL SISTEMA ---

        # A. Usar el módulo para encontrar la pose y dibujarla
        frame = detector.find_pose(frame, draw=True)
        
        # B. Extraer datos de posición (para futura lógica de caída)
        lm_list, bbox = detector.find_position(frame, draw=True)

        # C. Lógica de detección de caída (PRELIMINAR)
        if bbox:
            # Heurística simple 1: Relación de aspecto
            aspect_ratio = bbox["height"] / bbox["width"]
            # Si es más ancho que alto (ratio < 1), podría estar caído
            if aspect_ratio < 0.8: 
                cv2.putText(frame, "POSIBLE CAIDA (Ratio)", (bbox["xmin"], bbox["ymin"] - 20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                # Dibujar caja roja
                cv2.rectangle(frame, (bbox["xmin"], bbox["ymin"]), (bbox["xmax"], bbox["ymax"]), (0, 0, 255), 3)
            else:
                 cv2.putText(frame, "Persona Detectada", (bbox["xmin"], bbox["ymin"] - 20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # D. Cálculo de FPS (Para monitorear rendimiento)
        c_time = time.time()
        fps = 1 / (c_time - p_time)
        p_time = c_time
        cv2.putText(frame, f'FPS: {int(fps)}', (20, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 0), 3)

        # E. Mostrar resultado
        # Reducir un poco si el video es 4K para verlo bien en pantalla
        frame_show = cv2.resize(frame, (1280, 720)) 
        cv2.imshow("Vigilante IA - Modular Test", frame_show)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()