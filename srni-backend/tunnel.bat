@echo off
REM Arranca un túnel ngrok hacia el backend Django en puerto 8001.
REM Prerrequisito: ngrok instalado (npm install -g ngrok o https://ngrok.com/download)
REM
REM Uso:
REM   1. Ejecuta este archivo (doble clic o desde cmd)
REM   2. Copia la URL HTTPS que aparece (ej: https://abc123.ngrok-free.app)
REM   3. Pega esa URL en srni-mobile/.env.local como EXPO_PUBLIC_API_URL
REM   4. Recarga Expo con "r" en la terminal del metro bundler

echo [SRNI] Iniciando tunel ngrok para el backend Django (puerto 8001)...
echo [SRNI] Copia la URL https://....ngrok-free.app y ponla en .env.local
echo.
ngrok http 8001
