# Arrancar el entorno SRNI

Abre **4 ventanas de PowerShell** y ejecuta una en cada una.

---

## Terminal 1 — Backend Django

```powershell
cd D:\desarrollo\unidad-victima\srni-backend
.venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8001
```

Espera hasta ver:
```
Starting development server at http://0.0.0.0:8001/
```

---

## Terminal 2 — Túnel backend (ngrok)

```powershell
cd D:\desarrollo\unidad-victima\srni-backend
.\tunnel.bat
```

Espera hasta ver:
```
Forwarding   https://srniapk-dev.ngrok.app -> http://localhost:8001
```

---

## Terminal 3 — App móvil (Expo)

```powershell
cd D:\desarrollo\unidad-victima\srni-mobile
npx expo start --port 8082
```

Espera hasta que aparezca el **código QR** en pantalla.

---

## Terminal 4 — Túnel app (ngrok)

```powershell
cd D:\desarrollo\unidad-victima\srni-mobile
.\tunnel.bat
```

Espera hasta ver:
```
Forwarding   https://srniapk.ngrok.app -> http://localhost:8082
```

---

## Celular

1. Abre **Expo Go**
2. Escanea el QR de la Terminal 3
3. Inicia sesión con:
   - Usuario: `ENCUESTADOR001`
   - Contraseña: `SrniTest2026!`

---

## Orden de arranque

```
Terminal 1  →  Terminal 2  →  Terminal 3  →  Terminal 4  →  Celular
```

No cierres ninguna terminal mientras estés probando.
