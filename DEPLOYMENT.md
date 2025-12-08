# GUÍA DE DESPLIEGUE: Vigilante Digital IA con Firebase

## Resumen Rápido

El proyecto usa credenciales de Firebase almacenadas en una variable de entorno `GOOGLE_APPLICATION_CREDENTIALS`. **NUNCA van en el repositorio.**

---

## Para tu máquina (desarrollo local)

### 1. Descarga las credenciales desde Firebase

- Ve a **Firebase Console** → **Configuración del Proyecto** → **Cuentas de Servicio**
- Haz click en **Generar nueva clave privada**
- Se descarga un archivo JSON: `alertas1-b2c10-firebase-adminsdk-fbsvc-bd62392ef5.json`

### 2. Guarda el JSON FUERA del repositorio

```
C:\secrets\alertas1-b2c10-firebase-adminsdk-fbsvc-bd62392ef5.json
```

**IMPORTANTE:** No dentro de `C:\...\VigilanteDigital_1.0\`. Créalo en otra ruta.

### 3. Configura la variable de entorno (PowerShell)

**Para la sesión actual:**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\secrets\alertas1-b2c10-firebase-adminsdk-fbsvc-bd62392ef5.json"
```

**Para siempre (reinicia la shell después):**
```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "C:\secrets\alertas1-b2c10-firebase-adminsdk-fbsvc-bd62392ef5.json"
```

### 4. Verifica que funciona

```powershell
python -c "import os; print(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))"
```

Debe mostrar: `C:\secrets\alertas1-b2c10-firebase-adminsdk-fbsvc-bd62392ef5.json`

### 5. Ejecuta la app

```powershell
python main.py
```

---

## Para la máquina del cliente (Producción)

### Escenario A: Cliente con Windows (servidor o PC)

1. **Copia el JSON a una ruta segura en la máquina del cliente:**
   ```
   C:\AppData\Local\AlertasIA\alertas1-service-key.json
   ```

2. **En PowerShell del cliente (como Admin):**
   ```powershell
   setx GOOGLE_APPLICATION_CREDENTIALS "C:\AppData\Local\AlertasIA\alertas1-service-key.json"
   ```
   Reinicia la sesión de PowerShell.

3. **Verifica permisos del archivo:**
   - Click derecho en el JSON → **Propiedades** → **Seguridad**
   - Solo el usuario que ejecuta la app debe leer el archivo

4. **Ejecuta la app:**
   ```powershell
   cd C:\path\to\VigilanteDigital_1.0
   python main.py
   ```

### Escenario B: Cliente con Linux (servidor)

1. **Copia el JSON a una ruta segura:**
   ```bash
   sudo cp alertas1-service-key.json /etc/alertas1-service-key.json
   sudo chmod 600 /etc/alertas1-service-key.json
   sudo chown root:root /etc/alertas1-service-key.json
   ```

2. **Añade la variable de entorno al usuario que ejecuta la app:**
   - Edit `~/.bashrc` o `/etc/environment`
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/etc/alertas1-service-key.json"
   ```

3. **Aplica los cambios:**
   ```bash
   source ~/.bashrc
   ```

4. **Ejecuta la app:**
   ```bash
   cd /path/to/VigilanteDigital_1.0
   python main.py
   ```

### Escenario C: Cliente con Docker (contenedor)

1. **El JSON NO va en la imagen.** Monta como volumen:

   ```bash
   docker run \
     -e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/alertas1-key.json \
     -v /host/path/alertas1-service-key.json:/run/secrets/alertas1-key.json:ro \
     -v /host/path/videos:/app/videos \
     vigilante-ia:latest
   ```

2. **Si usas docker-compose:**
   ```yaml
   version: '3.8'
   services:
     vigilante:
       image: vigilante-ia:latest
       environment:
         - GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/alertas1-key.json
       volumes:
         - /host/path/alertas1-service-key.json:/run/secrets/alertas1-key.json:ro
         - /host/path/videos:/app/videos
       secrets:
         - alertas1-key
   secrets:
     alertas1-key:
       file: /path/to/alertas1-service-key.json
   ```

---

## Cómo funciona en el código

### Flujo de autenticación

```
main.py
  ↓
imports outputs.firebase_connector
  ↓
FirebaseConnector.__init__()
  ↓
_init_firebase()
  ↓
firebase_admin.initialize_app()  ← Lee $GOOGLE_APPLICATION_CREDENTIALS
  ↓
Se conecta a Firestore usando la clave privada
  ↓
Sube eventos a la colección "Prueba_Alertas"
```

### El código NO cambió

Tu `main.py` y `outputs/firebase_connector.py` funcionan igual en:
- Tu PC local
- Máquina del cliente (Windows/Linux)
- Docker
- Servidor en la nube

**Solo la ubicación del JSON y cómo se proporciona cambia.**

---

## Preguntas Frecuentes

### ¿Y si pierdo el JSON?

Descárgalo de nuevo desde Firebase Console. Genera una nueva clave privada.

### ¿Qué pasa si alguien ve el JSON en la máquina del cliente?

Es un riesgo. Soluciones:
- Usa permisos de archivo restringidos (solo el usuario necesario).
- Si es un servidor, usa Secret Manager de GCP o Vault de HashiCorp.

### ¿Cómo monitoreo si los eventos se suben a Firestore?

1. Ve a **Firebase Console** → **Firestore Database** → **Colección `Prueba_Alertas`**
2. Verás los documentos con campos: `timestamp`, `photo_path`, `event_type`, `uploaded_at`.

### ¿Puedo cambiar la colección?

Sí, en `config.py` o con la variable de entorno:
```powershell
$env:FIRESTORE_COLLECTION = "Mi_Coleccion_Custom"
```

---

## Checklist de Seguridad

- [ ] El JSON está en `C:\secrets\` o `/etc/` (FUERA del repo)
- [ ] `.gitignore` incluye `*.json` y `secrets/`
- [ ] Variable `GOOGLE_APPLICATION_CREDENTIALS` está configurada
- [ ] Permisos del archivo JSON: solo lectura para el usuario necesario
- [ ] El JSON coincide con el proyecto `alertas1-b2c10` (revisar `project_id` en el JSON)
- [ ] Hizo push a Git SIN subir el JSON (revisa `git log` para confirmar)

---

## Soporte

Si hay problemas en la máquina del cliente:

1. Verifica: `$env:GOOGLE_APPLICATION_CREDENTIALS`
2. Revisa logs: `python main.py` mostrará errores de autenticación
3. Confirma que Firestore tiene la colección `Prueba_Alertas`
4. Si está en Docker, verifica volúmenes: `docker inspect <container>`
