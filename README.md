# VigilanteDigital IA v2.0 - Detección de Caídas con Optimización Firestore

**Una solución de IA para detección de caídas en tiempo real, optimizada para reducir costos de Firestore en 99%.**

## 🎯 Descripción Rápida

VigilanteDigital es un sistema inteligente de detección de caídas que utiliza MediaPipe Pose, OpenCV y Firebase. La versión **v2.0 introduce EventLogger**, que reduce documentos Firestore de 5,330 a 2 por video (99% de reducción).

### ¿Qué cambió en v2.0?

| Aspecto | v1.0 (Legacy) | v2.0 (Actual) | Mejora |
|--------|--------------|---------------|--------|
| Video 3 min | 5,330 docs | 2 docs | **99.96% ↓** |
| Costo/video | $7.00 USD | $0.01 USD | **700x ↓** |
| Escrituras API | 5,330 | 2 | **99.96% ↓** |

## 🚀 Inicio Rápido (5 min)

```powershell
# 1. Configurar credenciales
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\firebase-key.json"
$env:USE_EVENT_LOGGER = "true"

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar prueba
python scripts/run_test.py --video tests/test_videos/sample.mp4 --output results

# 4. Ver resultados
cat results\test_metrics.json
```

**Resultado esperado:** 2 eventos, 2 documentos Firestore ✓

## Arquitectura y Flujo de Datos
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Linux/Mac
    .\venv\Scripts\activate   # En Windows
    ```
3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configuración:**
    * Renombrar `config.example.py` a `config.py` (si aplica) y configurar las fuentes de video y credenciales API.
5.  **Ejecutar:**
    ```bash
    python main.py
    ```