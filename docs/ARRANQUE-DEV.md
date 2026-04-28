# Guía de arranque — Entorno de desarrollo SRNI

**Sistema operativo:** Windows 11  
**Shell:** PowerShell  
**Última actualización:** 2026-04-28

---

## Requisitos previos

Verifica que tienes instalado:

```powershell
python --version        # 3.12 o superior
node --version          # 18 o superior
npm --version           # 9 o superior
ngrok --version         # 3.x
```

Si falta alguno:
- Python → https://www.python.org/downloads/
- Node → https://nodejs.org/
- ngrok → https://ngrok.com/download (requiere cuenta — los dominios permanentes son de pago)

---

## PRIMERA VEZ — Configuración inicial

Haz esto **una sola vez** cuando clonas el repositorio.

### Paso 1 — Entrar a la raíz del proyecto

```powershell
cd D:\desarrollo\unidad-victima
```

### Paso 2 — Crear el entorno virtual de Python

```powershell
cd srni-backend
python -m venv .venv
```

### Paso 3 — Activar el entorno virtual e instalar dependencias

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Si PowerShell bloquea la ejecución de scripts:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Luego repite `.venv\Scripts\Activate.ps1`

### Paso 4 — Crear el archivo de variables de entorno

```powershell
# Desde srni-backend\
copy .env.example .env
```

Abre `.env` con el bloc de notas y asegúrate de que tenga al menos:

```
SECRET_KEY=dev-secret-key-local-no-importa-en-dev
DEBUG=True
```

> En desarrollo usa SQLite (no necesitas PostgreSQL ni Redis).
> El archivo `srni/settings/development.py` los reemplaza automáticamente.

### Paso 5 — Crear la base de datos y aplicar migraciones

```powershell
# Desde srni-backend\ con el venv activo
$env:DJANGO_SETTINGS_MODULE = "srni.settings.development"
python manage.py migrate
```

### Paso 6 — Cargar los instrumentos PAARI (los 6 perfiles)

```powershell
python manage.py cargar_territorial_v7
python manage.py cargar_buenaventura_v7
python manage.py cargar_san_andres_v7
python manage.py cargar_telefonico_v8
python manage.py cargar_urbano_etnico_v1
python manage.py cargar_rural_etnico_v1
```

### Paso 7 — Crear usuario de prueba para el login móvil

```powershell
python manage.py crear_usuario_prueba
```

Credenciales que quedan listas:
```
Usuario:    ENCUESTADOR001
Contraseña: SrniTest2026!
```

### Paso 8 — Instalar dependencias de la app móvil

```powershell
# Abre una nueva terminal PowerShell
cd D:\desarrollo\unidad-victima\srni-mobile
npm install
```

### Paso 9 — Crear el archivo de entorno del móvil

```powershell
# Desde srni-mobile\
New-Item -Name ".env.local" -ItemType File
Add-Content .env.local "EXPO_PUBLIC_API_URL=https://srniapk-dev.ngrok.app"
```

---

## USO DIARIO — Levantar el sistema

Necesitas **4 terminales PowerShell** abiertas al mismo tiempo.

---

### Terminal 1 — Backend Django

```powershell
cd D:\desarrollo\unidad-victima\srni-backend
.venv\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "srni.settings.development"
python manage.py runserver 0.0.0.0:8001
```

Queda corriendo en: `http://localhost:8001`  
Deja esta terminal abierta. Verás los logs de cada petición.

---

### Terminal 2 — Túnel ngrok para el backend

```powershell
cd D:\desarrollo\unidad-victima\srni-backend
.\tunnel.bat
```

El backend queda accesible desde el celular en:
`https://srniapk-dev.ngrok.app`

Deja esta terminal abierta.

---

### Terminal 3 — Expo Metro (app móvil)

```powershell
cd D:\desarrollo\unidad-victima\srni-mobile
npx expo start --port 8082
```

Verás el QR en esta terminal. Deja esta terminal abierta.

---

### Terminal 4 — Túnel ngrok para Expo

```powershell
cd D:\desarrollo\unidad-victima\srni-mobile
.\tunnel.bat
```

El metro bundler queda accesible en:
`https://srniapk.ngrok.app`

Deja esta terminal abierta.

---

### Conectar el celular

1. Instala **Expo Go** desde Play Store o App Store.
2. Abre Expo Go y escanea el QR que aparece en la **Terminal 3**, **o** escribe manualmente:
   ```
   exp+srni-mobile://expo-development-client/?url=https%3A%2F%2Fsrniapk.ngrok.app
   ```
3. La app carga desde el túnel y llama al backend en `https://srniapk-dev.ngrok.app`.

---

## ORDEN CORRECTO DE ARRANQUE

```
1. Terminal 1  →  Django backend    (esperar a que diga "Starting development server")
2. Terminal 2  →  ngrok backend     (esperar a que muestre el dominio activo)
3. Terminal 3  →  Expo Metro        (esperar a que muestre el QR)
4. Terminal 4  →  ngrok Expo        (esperar a que muestre el dominio activo)
5. Celular     →  Expo Go + QR
```

---

## Comandos útiles

### Ver la base de datos desde Django

```powershell
# Con el venv activo, desde srni-backend\
python manage.py shell
```

```python
from apps.autenticacion.models import Usuario
Usuario.objects.all().values('codigo_usuario', 'activo')
```

### Crear las migraciones después de cambiar modelos

```powershell
python manage.py makemigrations
python manage.py migrate
```

### Recargar un instrumento (idempotente — no duplica datos)

```powershell
python manage.py cargar_territorial_v7
```

### Ver todas las rutas disponibles del API

```powershell
python manage.py show_urls
```

### Correr los tests del backend

```powershell
pytest
```

### Correr los tests del móvil

```powershell
# Desde srni-mobile\
npm test
```

---

## Solución de problemas frecuentes

| Síntoma | Causa | Solución |
|---------|-------|---------|
| `AxiosError: Network Error` en el celular | ngrok no está corriendo | Revisar Terminal 2 y 4 |
| `DisallowedHost` en Django | Host no reconocido | Ya resuelto en `development.py` (`ALLOWED_HOSTS = ['*']`) |
| `ModuleNotFoundError` al arrancar Django | Venv no activo | Ejecutar `.venv\Scripts\Activate.ps1` antes de `runserver` |
| QR no carga en Expo Go | Metro en puerto incorrecto | Usar `--port 8082` en el comando expo start |
| App carga pero login falla | Backend no está corriendo | Verificar Terminal 1 |
| `No such table` en SQLite | Migraciones no aplicadas | Ejecutar `python manage.py migrate` |
| PowerShell bloquea `.ps1` | Política de ejecución | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `CSRF` error en POST | Origen no reconocido | Los dominios ngrok ya están en `CSRF_TRUSTED_ORIGINS` |

---

## Estructura de terminales de un vistazo

```
PS D:\desarrollo\unidad-victima\srni-backend>   ← Terminal 1 (Django)
PS D:\desarrollo\unidad-victima\srni-backend>   ← Terminal 2 (ngrok backend)
PS D:\desarrollo\unidad-victima\srni-mobile>    ← Terminal 3 (Expo)
PS D:\desarrollo\unidad-victima\srni-mobile>    ← Terminal 4 (ngrok Expo)
```

---

## Notas de seguridad

- El archivo `.env` **nunca** va al repositorio (está en `.gitignore`).
- El archivo `srni-mobile/.env.local` **nunca** va al repositorio.
- Las credenciales `ENCUESTADOR001 / SrniTest2026!` son **solo para desarrollo local** — nunca las uses en un servidor real.
- En desarrollo se usa SQLite local. En producción va PostgreSQL + Docker.
