# SRNI — Entorno de desarrollo con ngrok

## Dominios permanentes (cuenta pago ngrok)

| Dominio | Servicio | Puerto local |
|---------|---------|-------------|
| `srniapk-dev.ngrok.app` | Backend Django | 8001 |
| `srniapk.ngrok.app` | Expo Metro | 8082 |

---

## Levantar el entorno completo

Abre **4 terminales** en la raíz del repositorio:

### Terminal 1 — Túnel backend
```bat
cd srni-backend
tunnel.bat
```
Mantén esta terminal abierta. El backend queda expuesto en `https://srniapk-dev.ngrok.app`.

### Terminal 2 — Backend Django
```bat
cd srni-backend
python manage.py runserver 0.0.0.0:8001
```
> Si usas virtualenv: actívalo antes con `.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux/Mac).

### Terminal 3 — Túnel Expo Metro
```bat
cd srni-mobile
tunnel.bat
```
Mantén esta terminal abierta. El metro bundler queda expuesto en `https://srniapk.ngrok.app`.

### Terminal 4 — Expo Metro
```bat
cd srni-mobile
npx expo start
```
> **No uses `--tunnel`** — ngrok ya hace esa función con dominio permanente.

---

## Conectar el celular

1. Abre **Expo Go** en el celular.
2. Escanea el QR que aparece en la Terminal 4, **o** escribe manualmente la URL:
   ```
   exp+srni-mobile://expo-development-client/?url=https%3A%2F%2Fsrniapk.ngrok.app
   ```
3. La app se carga desde `https://srniapk.ngrok.app` y llama al backend en `https://srniapk-dev.ngrok.app`.

---

## Variables de entorno

`srni-mobile/.env.local` (no va al repo — gitignored):
```
EXPO_PUBLIC_API_URL=https://srniapk-dev.ngrok.app
```

---

## Migraciones pendientes

Antes de la primera ejecución (o tras un `git pull` con cambios en `migrations/`):
```bat
cd srni-backend
python manage.py migrate
```

## Crear usuario de prueba
```bat
python manage.py crear_usuario_prueba
```
Credenciales: `ENCUESTADOR001` / `SrniTest2026!`

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|---------------|---------|
| `AxiosError` en el celular | URL de ngrok incorrecta en `.env.local` | Verificar que coincida con el dominio reservado |
| `DisallowedHost` en Django | Host no reconocido | `ALLOWED_HOSTS = ['*']` ya está en `development.py` |
| `CSRF` error en POST | Origen no en `CSRF_TRUSTED_ORIGINS` | Ambos dominios ya están configurados |
| QR no carga | Metro no está corriendo | Verificar Terminal 4 |
| App carga pero no hace login | Backend no levantado | Verificar Terminal 2 |
