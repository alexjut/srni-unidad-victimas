# Carpeta de distribución de la APK

Coloca aquí el archivo **`app.apk`** (firmado, generado por EAS) para que quede
servido en `https://<dominio>/movil/app.apk` y disponible en la página de descarga
(`/descargar/`).

```bash
# Desde la máquina de desarrollo, tras el build EAS:
scp -i $KEY app.apk admin_rni@30.0.1.109:/home/admin_rni/caracterizacion/infra/deploy/movil/app.apk
```

El `.apk` no se versiona en git (excluido por `.gitignore`).

> ⚠️ La APK que se distribuye al campo debe construirse con la **URL permanente de la OTI**
> (no la de ngrok, que es solo para pruebas).
