# Correo para Brando — Backend habilitador panel web (Sprint 20)

**Para:** Brando (Frontend Web SRNI)
**De:** Javier Alexander Aguilar Castro
**Asunto:** Panel web listo para conectar — backend habilitador completo

---

Hola Brando,

Te cuento dos cosas:

## 1. La rama `frontend` ya está al día en azure y origin

Hoy actualicé la rama `frontend` con todo lo que tenía pendiente del backend (Sprints 18, 19 y 20). Está pusheada en los dos repos:

- **Azure DevOps (oficial UARIV):**
  https://tfsunidad.visualstudio.com/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED-MOVIL/_git/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED%20MOVIL%202026-04?version=GBfrontend

- **GitHub (backup):**
  https://github.com/alexjut/srni-unidad-victimas/tree/frontend

Para que la tomes:

```bash
git fetch --all
git checkout frontend
git pull
```

La rama `frontend` ahora tiene el backend listo, el mobile actualizado y `srni-frontend/` sin tocar (sigue siendo tu zona).

## 2. El backend ya habla con tu panel sin que toques código

Cuando intenté arrancar `srni-frontend/` me di cuenta que llamaba endpoints que el backend no exponía. Lo arreglé del lado backend (sin tocar tu código). Estos son los endpoints que ya responden 200:

| Endpoint que tu front llama | Estado |
|---|---|
| `POST /api/auth/token/` | ✅ |
| `POST /api/auth/token/refresh/` | ✅ |
| `GET /api/auth/perfil/` | ✅ |
| `GET /api/hogares/` | ✅ |
| `GET /api/encuestas/` | ✅ |
| `GET /api/reportes/encuestador/` | ✅ |
| `GET /api/reportes/encuestador/detalle/` | ✅ |
| `GET /api/reportes/encuestador/exportar/` | ✅ |
| `GET /api/reportes/supervisor/` | ✅ |
| `GET /api/reportes/dashboard/series/` | ✅ |

Además el JSON del dashboard ya trae los campos exactos que lees en `Dashboard.tsx` y `Reportes.tsx`:
`sesiones_finalizadas`, `sesiones_en_proceso`, `hogares_total`, `victimas_caracterizadas`, `periodo_inicio`, `periodo_fin`.

## 3. Cómo arrancar tu lado

Backend Django y panel web Vite, ambos locales:

```bash
# Terminal 1 — backend
cd D:/desarrollo/unidad-victima/srni-backend
.venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8001

# Terminal 2 — panel web
cd D:/desarrollo/unidad-victima/srni-frontend
cp .env.example .env.local      # solo la primera vez
# Edita .env.local si tu backend NO está en localhost:
#   VITE_API_URL=http://localhost:8001
npm install                      # solo la primera vez
npm run dev
```

Te abre el panel en `http://localhost:5173`.

## 4. Credenciales de prueba

| Código | Password | Rol |
|---|---|---|
| `ALEXJUT` | `SrniTest2026!` | Encuestador con todos los permisos |
| `ADMIN01` | (la que ya tenías) | Admin |

Si la contraseña de `ADMIN01` no la recuerdas, dime y la reseteo.

## 5. Datos disponibles en BD para que el panel no se vea vacío

- 6 hogares
- 13 sesiones de caracterización (8 completadas, 5 en progreso)
- 61 respuestas
- 8 instrumentos cargados con todas sus preguntas y opciones
- 33 departamentos, 1102 municipios, 21 direcciones territoriales UARIV, 41 puntos de atención

Con eso el dashboard, hogares, encuestas y reportes deben mostrar contenido real.

## 6. Lo que ya está y lo que sigue

**Listo del lado backend:**
- Login + perfil + refresh JWT (con aliases que tu front ya usa)
- Hogares, encuestas, reportes (encuestador + supervisor + dashboard)
- Validación cascada Dirección Territorial → Depto → Municipio → Punto
- 21 DTs UARIV cargadas con su mapeo a departamentos DANE
- Mapa de estado completo del proyecto: `docs/estado-actual.md` (mismo repo)

**Pendiente del lado backend (no te frena):**
- Pedirle a Oscar el dataset oficial de centros regionales UARIV (hoy uso 2 placeholders por DT)
- QA end-to-end del flujo móvil nuevo de ubicación de atención

**Cualquier cosa rara que veas** (HTTP 4xx/5xx, campo `undefined` en una vista, error en consola): pásame F12 → Console y lo arreglo del lado backend. La idea es que tú trabajes solo en la UI, sin pelearte con contratos.

Un abrazo,
Javier
