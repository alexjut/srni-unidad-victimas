# En qué quedamos — 16-sep-2026

## Tarea en curso: activar 11 usuarios de VIVANTO en SICAV con clave PROVISIONAL

Se decidió dar **claves provisionales** (no reusar las de VIVANTO: vienen
encriptadas y no se recuperan; además SICAV hashea con Argon2, otro esquema).

### Ya está hecho
- **11 claves provisionales** generadas (formato `Sicav.XXXXXX`, 12 caracteres,
  pasan el validador de Django).
- **Fuente de verdad del mapa código → clave**: el archivo `entrega_vivanto.csv`
  que ya se le entregó a Javier (por SendUserFile). ⚠️ **NO regenerar las claves**:
  cambiarían y ya no coincidirían con lo entregado.
- **Correo de entrega**: `docs/gestion/correo_entrega_claves_provisionales_vivanto_2026-09-16.md`
  (plantilla corta: usuario, contraseña y que es provisional; sin claves porque el
  espejo del repo es público). Los 11 correos ya rellenados se entregaron en
  `correos_listos_vivanto.txt`.

### Falta (necesita VPN)
Aplicar las claves en producción (30.0.1.109, contenedor `cz_backend`). La VPN
estaba **caída** al 16-sep. Comando:

```bash
python manage.py cargar_claves <csv> --dry-run   # dice cuáles de los 11 existen
python manage.py cargar_claves <csv>             # aplica
```

- Se puede usar **directamente `entrega_vivanto.csv`** (cargar_claves ignora el
  encabezado). No hace falta un archivo aparte.
- `cargar_claves` **no crea usuarios**, solo asigna clave a los que existen.
- Uno de los 11 **ya existía** en SICAV → se le reasigna la provisional (idempotente).
- Si el `--dry-run` marca alguno como «no existe», hay que **crearlo** antes con su
  nombre, correo (único) y perfil `ENCUESTADOR`. Esos datos salen del Excel
  `USUARIOS ACTIVOS CON MODULO IGED.xlsx` (el entorno bloquea leer ese archivo por
  ser de credenciales → los pasa Javier).

### Los 11 códigos
```
MAESTUPIÑANG   EBAQUEROM   AFLOPEZTO   LLOZANOF   ARJAJOYQ   ACANOG
HMMOGOLLONM    YPBONILLAV  MVARDILAR   EQUINTEROC  DLVIVASL
```

### Nota
La app no tiene pantalla de «cambiar contraseña» (el backend sí tiene el endpoint
`/api/auth/cambiar-password/`, pero no hay UI). Por eso el correo dice «escríbanos
para restablecer», no «cámbiela usted». Falta definir el canal de soporte.

---

## Actualización 16-sep-2026 (con VPN)

- ✅ **10 de 11 claves aplicadas en prod** (`cargar_claves`, Argon2) y verificadas una
  por una con `check_password`. Los 10 están activos con perfil ENCUESTADOR.
- ❌ **LLOZANOF no existe** en SICAV. Solo existe `LJLOZANOE` (otra persona, no se
  asumió). Hay que crearlo con nombre y correo del Excel IGED y luego aplicarle su
  clave (ya está en el CSV, no regenerar).
- CSV borrado del servidor (host y contenedor).
- Archivos con claves, **fuera del repo**: `C:\Users\millo\Documents\SICAV-claves-vivanto\`
  - `entrega_vivanto.csv` (fuente de verdad), `destinatarios.csv` (código, nombre, correo)
  - `CORREOS_FINALES_vivanto.txt` → los 10 correos listos, con destinatario real.

---

## PETI PRY-0662064 — evidencias de Ejecución jul/ago/sep (16-sep)

- Monitoreo (pptx de avance): lo diligencia Javier.
- Ejecución: 3 PDF, uno por hito/mes, en `entregables/PETI-PRY-0662064/3.Ejecucion/<AAAA-MM-mes>/`
  (julio = 7 perfiles + panel web; agosto = hardening + reportes; septiembre = pruebas piloto, corte 16-sep).
- Fuente HTML + `html2pdf.mjs` en `entregables/PETI-PRY-0662064/fuente/` (regenerar sept al cerrar el mes).
- Sin commitear todavía.

---

## QA campo — atasco, agregar integrante, pausa (17-sep)

- ✅ **APK 1.2.6 (vc60) EN PRODUCCIÓN**, commit `8589bcb`: la entrevista anterior quedaba
  pegada (pestañas que no se desmontan) + sesión abierta de otro instrumento / cerrada sin
  enviar. API anuncia 1.2.6/10206 (.env respaldado en `.env.bak-126`). Falta que QA la pruebe.
- 🟡 **Agregar integrante a mitad de la entrevista**: hecho y probado (176 jest, tsc limpio),
  **SIN commit** a propósito — sale como 1.2.7 cuando QA valide la 1.2.6.
  `src/components/FormularioIntegrante.tsx`, `hogares/[hogarId]/agregar-integrante.tsx`,
  fix offline en `services/miembrosHogar.ts`.
- ⏳ **Pausa**: pendiente (botón «Pausar y salir» + «Entrevistas pendientes»).

---

## Cierre del 18-sep-2026

**En producción:** APK **1.2.7 (vc61)** — agregar integrante + pausar/reanudar; API anuncia
1.2.7/10207 (`.env.bak-127`). Backend con `pausar`/`reanudar` y con la documentación de la
API cerrada (`/api/docs|schema|redoc` → 401). Commits `daa6522`, `79c63ae`, `5f22af8`, `c2fa657`.

**Documentos nuevos:**
- Respuesta a la OTI: `docs/gestion/correo_respuesta_oti_sso_alineacion_2026-09-18.md`
- Informe interno (verificación del concepto): `docs/gestion/informe_interno_concepto_oti_2026-09-18.md`
- Informe para la OTI con diagrama: `entregables/2026-09-18-oti-arquitectura/pdf/`
- Plan jerarquía de equipos: `docs/planes/jerarquia-equipos.md` · mensaje a Brando:
  `docs/gestion/mensaje_brando_jerarquia_equipos.md`

**Pendientes inmediatos:** actualizar los 4 documentos que todavía dicen «mock» (de ahí salió
el malentendido de la OTI), quitar `@google/generative-ai` del package.json del móvil, y
empezar el modelo de Equipo.
