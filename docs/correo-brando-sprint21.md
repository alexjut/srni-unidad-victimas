# Correo para Brando — Cierre de jornada Sprint 20 + 21

**Para:** Brando (Frontend Web SRNI)
**De:** Javier Alexander Aguilar Castro
**Asunto:** Backend al día — Sprint 20 + 21 cerrados, listo para tu trabajo en panel web

---

Hola Brando,

Cierre del día. Hoy avanzamos bastante. Te resumo lo que necesitás saber para mañana.

## 1. La rama `frontend` está al día en azure y origin

Pusheado a los dos remotes en commit `eab3075`. Para tomarla:

```bash
git fetch --all
git checkout frontend
git pull
```

- **Azure DevOps (oficial UARIV):**
  https://tfsunidad.visualstudio.com/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED-MOVIL/_git/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED%20MOVIL%202026-04?version=GBfrontend

- **GitHub (backup):**
  https://github.com/alexjut/srni-unidad-victimas/tree/frontend

## 2. Backend listo para tu panel — endpoints habilitados

Smoke test ALEXJUT / `SrniTest2026!` (todos 200):

| Endpoint | Estado |
|---|---|
| `POST /api/auth/token/` | ✅ |
| `POST /api/auth/token/refresh/` | ✅ |
| `GET /api/auth/perfil/` | ✅ |
| `GET /api/hogares/` | ✅ |
| `GET /api/encuestas/` | ✅ |
| `GET /api/reportes/encuestador/` | ✅ con aliases del shape (sesiones_finalizadas, hogares_total, etc.) |
| `GET /api/reportes/encuestador/detalle/` | ✅ |
| `GET /api/reportes/encuestador/exportar/` | ✅ |
| `GET /api/reportes/supervisor/` | ✅ |
| `GET /api/reportes/dashboard/series/` | ✅ |

## 3. Cambios del modelo que tu panel verá (importantes)

### a) `SesionEncuesta` ahora tiene ubicación de atención

4 campos nuevos opcionales que vienen del nuevo flujo móvil:
- `direccion_territorial` (FK · `DT_ATLANTICO`, etc. — 21 DTs UARIV cargadas)
- `departamento_atencion` (FK · 33 deptos DANE)
- `municipio_atencion` (FK · 1102 municipios DANE)
- `punto_atencion` (FK · 41 puntos placeholder; UARIV nos pasa el oficial)

El serializer expone los IDs + sus nombres legibles (`_nombre`) y un alias top-level `direccion_territorial_nombre` para que filtres/agrupes fácil en el dashboard.

### b) `RespuestaEncuesta` ahora puede ser por miembro

Campo nuevo `miembro` (FK a `MiembroHogar`, nullable):
- `miembro = NULL` → respuesta de pregunta nivel HOGAR (única para la sesión)
- `miembro = <uuid>` → respuesta de pregunta nivel PERSONA (una por miembro)

UniqueConstraint `(sesion, pregunta, miembro)` garantiza no duplicados.

**En el panel web** esto significa: si querés mostrar respuestas detalladas de una sesión, agrupar por `miembro` cuando aparezca. Si `miembro` es null es un dato del hogar; si tiene UUID es del miembro indicado.

### c) Nombres descriptivos de los 8 instrumentos

| código | nombre |
|---|---|
| ASISTENCIA | Asistencia humanitaria |
| TERRITORIAL | Caracterización territorial |
| BUENAVENTURA | Buenaventura — Sentencia T-045 |
| SAN_ANDRES | San Andrés, Providencia y Santa Catalina |
| TELEFONICO | Entrevista telefónica |
| URBANO_ETNICO | Urbano étnico |
| RURAL_ETNICO | Rural étnico |
| VICTIMAS_EXTERIOR | Víctimas en el exterior |

### d) `MiembroHogarListSerializer` ahora expone `nombre_completo`

El endpoint `/api/hogares/{id}/` ya devuelve el nombre del miembro (derivado: nombre propio capturado por encuestador o, en su defecto, nombre del RNI si el miembro es el autorizado). Sirve para mostrar quién es cada persona en tablas y vistas.

## 4. Cómo arrancar tu lado

```bash
# Terminal 1 — backend
cd D:/desarrollo/unidad-victima/srni-backend
.venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8001

# Terminal 2 — panel web
cd D:/desarrollo/unidad-victima/srni-frontend
cp .env.example .env.local    # solo la primera vez
npm install                    # solo la primera vez
npm run dev
```

Te abre el panel en `http://localhost:5173`.

## 5. Credenciales

| Código | Password | Notas |
|---|---|---|
| `ALEXJUT` | `SrniTest2026!` | Todos los permisos |
| `ADMIN01` | (pídeme si la necesitas) | Admin |

## 6. Datos disponibles para que el panel no esté vacío

- 6 hogares de prueba
- 15 sesiones (8 completadas, 7 en progreso)
- ~250 respuestas
- 8 instrumentos × 1001 preguntas activas × 2239 opciones
- 21 DTs, 33 deptos, 1102 municipios, 41 puntos

## 7. Pendientes del backend (no te bloquean)

- Pedirle a Oscar el dataset oficial de centros regionales UARIV
- QA E2E final del flujo mobile con todas las mejoras del día (preguntas por miembro, calendario, wizard)

## 8. Lo que mejoramos hoy del lado mobile (informativo)

Si te aparecen estos cambios en el modelo, ahora sabes por qué:

- Preguntas tipo PERSONA se preguntan UNA por cada miembro del hogar (wizard mobile con botones Anterior/Siguiente)
- Calendario nativo en preguntas FECHA, agregar miembro y búsqueda RNI
- Capítulo "Información general" (DT/Depto/Mun/Punto de atención) movido a metadata de la sesión — ya no es una pregunta del formulario
- Render de COMBO_DINAMICO con selector de municipio (search bar sobre 1102 muns)

## 9. Cualquier duda

Si algo no compila, falta un campo o ves un `undefined` en el panel: F12 → Console → pásame el error y lo arreglo del lado backend para que no tengas que tocar tu código.

Un abrazo,
Javier
