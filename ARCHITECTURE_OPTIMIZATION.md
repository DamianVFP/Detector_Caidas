# ARQUITECTURA: Optimización de Costo y Eficiencia en Firestore

**Documento:** Análisis Arquitectónico  
**Rol:** Solution Architect (Cloud)  
**Fecha:** 8 de Diciembre de 2025  
**Problema:** 5,330 registros de un video de 3 minutos (ineficiente, caro)  
**Solución:** Implementar estrategia multi-layer de batching, deduplicación y filtrado

---

## 📊 DIAGNÓSTICO DEL PROBLEMA

### Raíz Causa

```
Video: 3 minutos @ 30 fps = 5,400 frames
Lógica actual: Si ratio < 0.8 → log como caída
Resultado: 5,330 registros en Firestore

Costo en Firestore:
- Escritura: 5,330 docs × $0.06 per 100K = $3.20 USD
- Lectura de estado: 5,330 × $0.06 per 100K = $3.20 USD
- Almacenamiento: ~5330 × 1.2KB = 6.4 MB = $0.77 USD/mes
- TOTAL: ~$7 por video (x100 videos = $700)

Problema: El sistema registra CADA FRAME como evento separado.
Lo correcto: Registrar EVENTOS (caída begin/end) no frames.
```

### Impacto Económico

| Escenario | Videos/día | Registros | Costo mes | Impacto |
|-----------|-----------|----------|----------|---------|
| **Actual** (1 caída = N frames) | 10 | 53K | ~$320 | ❌ Insostenible |
| **Optimizado** (1 caída = 1 evento) | 10 | 500 | ~$30 | ✓ Viable |
| **Con batching** (agrupa eventos) | 10 | 100 | ~$10 | ✓ Óptimo |

---

## 🏗️ SOLUCIONES ARQUITECTÓNICAS

### Opción A: Event-Based Logging (Recomendada ⭐)

**Idea:** Detectar INICIO y FIN de caída, no todos los frames.

```
Frames: [OK, OK, OK, CAIDA, CAIDA, CAIDA, CAIDA, OK, OK, ...]
                    ↑                          ↑
                    Inicio                     Fin
                    = 1 evento

Evento guardado en Firestore:
{
  "event_type": "fall",
  "start_timestamp": "2025-12-08T23:07:53Z",
  "end_timestamp": "2025-12-08T23:07:56Z",
  "duration_seconds": 3,
  "frames_detected": 90,
  "photo_path_start": "fall_001.jpg",
  "photo_path_end": "fall_090.jpg",
  "severity": "critical"  # Para futuro
}
```

**Ventajas:**
- 5,330 registros → 1-2 registros
- Costo reducido 99%
- Información más útil (duración, severidad)
- Escalable

**Desventajas:**
- Requiere cambio en lógica (máquina de estados)
- Un poco más complejo

**Costo estimado:** $0.01 por video

---

### Opción B: Batching + Aggregation (Alternativa)

**Idea:** Agrupar eventos cada N segundos o cada M frames.

```
Lote 1 (frames 49-100, 50 frames):
{
  "batch_start": 49,
  "batch_end": 100,
  "count": 50,
  "timestamps": ["2025-12-08T23:07:53.585114Z", ...],
  "avg_aspect_ratio": 0.62,
  "severity": "high"
}

Lote 2 (frames 101-150, 50 frames):
{ ... }
```

**Ventajas:**
- Implementación más simple
- Reducción ~50x

**Desventajas:**
- Pierde granularidad
- Aún se crean muchos registros

**Costo estimado:** $0.15 por video

---

### Opción C: Samplng + Aggregation

**Idea:** Guardar solo frames clave (cada 5 frames) + estadísticas.

```
Guardar: frames [50, 55, 60, 65, ..., 5300]
+ Estadísticas: min/max/avg aspect_ratio, duración

Reduce registros: 5,330 → 1,000
```

**Ventajas:**
- Simple de implementar
- Buena balance

**Desventajas:**
- Pierdes algunos frames
- Aún requiere varias operaciones

**Costo estimado:** $0.30 por video

---

### Opción D: Time-Window Aggregation (Híbrida)

**Idea:** Agrupar por ventana de tiempo (cada 1 segundo) + detalles clave.

```
Ventana 1 (0-1 segundo):
{
  "window_start": "2025-12-08T23:07:53Z",
  "window_duration_sec": 1,
  "frames_in_window": 30,
  "event_count": 30,
  "aspect_ratio_min": 0.55,
  "aspect_ratio_max": 0.80,
  "aspect_ratio_mean": 0.67,
  "sample_photo": "fall_sample_at_frame_70.jpg"
}
```

**Ventajas:**
- Excelente balance costo/información
- Reduce 99% registros
- Información estadística útil

**Desventajas:**
- Requiere cálculo de percentiles

**Costo estimado:** $0.02 por video

---

## 🎯 RECOMENDACIÓN FINAL

**Implementar: OPCIÓN A (Event-Based) + OPCIÓN D (Time-Window como fallback)**

### Arquitectura Propuesta

```
Frame a frame:
  Ratio < 0.8? → Estado = CAIDA (buffer temporal)
  Ratio >= 0.8? → Estado = NORMAL

Cambio de estado (NORMAL → CAIDA o CAIDA → NORMAL):
  → Crear EVENTO con timestamps inicio/fin
  → Guardar en Firestore (1 doc por caída)
  → Agregar a agregación por ventana de tiempo

Resultado:
- Firestore: 1 documento por evento real (caída)
- Analytics: 1 documento por segundo (estadísticas)
- Eficiencia: 99% reducción de costo
- Escalabilidad: mantiene información útil
```

---

## 💻 IMPLEMENTACIÓN: Event-Based Logger

### Nueva clase: `outputs/event_logger.py`

```python
"""Event-based logger para caídas (detección de inicio/fin)."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path
import json
import threading

class EventLogger:
    """Registra eventos de caída (inicio/fin) en lugar de frames individuales."""

    def __init__(self, file_path: str = "events_log.json"):
        self.path = Path(file_path)
        self.path.parent.mkdir(exist_ok=True, parents=True)
        self._lock = threading.Lock()
        
        # Estado máquina: NORMAL o FALLING
        self.state = "NORMAL"
        self.fall_start_time: Optional[datetime] = None
        self.fall_start_frame: Optional[int] = None
        self.fall_photo_path: Optional[str] = None
        self.current_event: Dict[str, Any] = {}

    def update(self, is_falling: bool, frame_idx: int, photo_path: str = "", metadata: Dict = None) -> Optional[Dict]:
        """
        Actualiza el estado y retorna un evento si hay cambio de estado.
        
        Args:
            is_falling: Si se detecta caída en este frame
            frame_idx: Índice del frame actual
            photo_path: Ruta a foto (solo para inicio de caída)
            metadata: Datos adicionales (aspect_ratio, etc.)
        
        Returns:
            Evento completado si hay cambio de estado, None en otro caso
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            completed_event = None

            if is_falling and self.state == "NORMAL":
                # TRANSICIÓN: NORMAL → FALLING
                self.state = "FALLING"
                self.fall_start_time = now
                self.fall_start_frame = frame_idx
                self.fall_photo_path = photo_path
                print(f"[EVENT] Caída iniciada en frame {frame_idx}")

            elif not is_falling and self.state == "FALLING":
                # TRANSICIÓN: FALLING → NORMAL (caída terminó)
                fall_end_time = now
                duration = (fall_end_time - self.fall_start_time).total_seconds()
                
                completed_event = {
                    "event_type": "fall",
                    "start_time": self.fall_start_time.isoformat(),
                    "end_time": fall_end_time.isoformat(),
                    "duration_seconds": duration,
                    "start_frame": self.fall_start_frame,
                    "end_frame": frame_idx - 1,
                    "total_frames": frame_idx - self.fall_start_frame,
                    "photo_start": self.fall_photo_path,
                    "metadata": metadata or {}
                }
                
                self.state = "NORMAL"
                self.fall_start_time = None
                print(f"[EVENT] Caída finalizada. Duración: {duration:.2f}s")

            return completed_event

    def log_event(self, event: Dict[str, Any]) -> bool:
        """Guarda un evento completado en JSON."""
        try:
            with self._lock:
                history = self._read_history()
                history.append(event)
                self._write_history(history)
            return True
        except Exception:
            return False

    def _read_history(self):
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except:
            return []

    def _write_history(self, history):
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(history, fh, indent=2, ensure_ascii=False)
```

---

## 🗑️ LIMPIAR FIRESTORE

### Script: `scripts/cleanup_firestore.py`

```python
"""Elimina todos los documentos de una colección en Firestore."""
import os
from google.cloud import firestore

def delete_collection(db, collection_name: str, batch_size: int = 100):
    """Elimina todos los documentos de una colección."""
    docs = db.collection(collection_name).stream()
    
    batch = db.batch()
    count = 0
    
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        
        if count % batch_size == 0:
            batch.commit()
            batch = db.batch()
            print(f"Eliminados {count} documentos...")
    
    # Commit final
    batch.commit()
    print(f"✓ Total eliminados: {count}")

if __name__ == "__main__":
    os.environ.setdefault("FIRESTORE_COLLECTION", "Prueba_Alertas")
    
    db = firestore.client()
    collection = os.getenv("FIRESTORE_COLLECTION")
    
    print(f"Eliminando colección: {collection}")
    response = input("¿Estás seguro? (si/no): ")
    
    if response.lower() in ["si", "yes"]:
        delete_collection(db, collection)
    else:
        print("Cancelado")
```

---

## 📋 RESUMEN DE CAMBIOS PARA v2.0

### Archivos Modificados

1. **`config.py`** → Añadir parámetros de deduplicación
   - `EVENT_DEDUP_WINDOW_SEC = 2` (agrupa caídas < 2s)
   - `MIN_FALL_DURATION_SEC = 1` (ignora caídas muy cortas)

2. **`outputs/firebase_connector.py`** → Filtrar eventos antes de subir
   - Solo subir eventos de duración > MIN_FALL_DURATION_SEC
   - Deduplicar por ventana temporal

3. **`main.py`** → Reemplazar lógica simple con máquina de estados
   - Usar `EventLogger` en lugar de registrar cada frame

4. **`scripts/run_test.py`** → Actualizar para usar `EventLogger`

5. **`requirements.txt`** → Añadir google-cloud-firestore si falta

### Impacto Estimado

| Métrica | Antes | Después | Ahorro |
|---------|-------|---------|--------|
| Registros/video (3 min) | 5,330 | 1-2 | 99% |
| Costo/video | $7 | $0.01 | 99% |
| Tamaño almacenado | 6.4 MB | 0.012 MB | 99% |
| Información retenida | Todos los frames | Eventos + estadísticas | ✓ Mejor |

---

## 🚀 ROADMAP

```
HOY (8 Dic):
├─ [x] Identificar raíz causa (5,330 registros/video)
├─ [x] Proponer soluciones (A, B, C, D)
├─ [ ] Implementar Opción A (EventLogger)
└─ [ ] Limpiar Firestore (backup primero)

Mañana (9 Dic):
├─ [ ] Integrar EventLogger en main.py
├─ [ ] Prueba con nuevo video
├─ [ ] Validar que solo crea 1-2 registros
└─ [ ] Push v2.0 a GitHub

Semana siguiente:
├─ [ ] Agregar Opción D (time-window aggregation)
├─ [ ] Dashboard para monitoreo de eventos
└─ [ ] Alertas automáticas en SMS/Email
```

---

## 🎓 LECCIONES APRENDIDAS

1. **Logging a nivel de frame es ineficiente** para eventos duradores (caídas)
2. **Event-based es la arquitectura correcta** para detección de anomalías
3. **Firestore cobra por operación, no por GB** → minimizar writes es crítico
4. **Máquina de estados es esencial** para detectar inicio/fin de eventos
5. **Deduplicación temporal previene falsos positivos** persistentes

---

## 📞 PRÓXIMOS PASOS

1. Implementar `EventLogger` en `outputs/event_logger.py`
2. Actualizar `main.py` para usar `EventLogger`
3. Script de limpieza: `scripts/cleanup_firestore.py`
4. Validación y v2.0 release
