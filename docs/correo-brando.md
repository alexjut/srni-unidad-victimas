# Correo para Brando — Panel web SRNI

**Para:** Brando
**De:** Javier Alexander Aguilar Castro
**Asunto:** Panel web listo — backend habilitador, credenciales y cómo pedirme endpoints

---

Hola Brando,

Te resumo lo que necesitás para trabajar en el panel web sin trabarte:

## 1. Tu rama

La rama `frontend` está siempre al día con todo el backend del proyecto. La encontrás en los dos repos:

- **Azure DevOps (repo oficial UARIV):**
  https://tfsunidad.visualstudio.com/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED-MOVIL/_git/RNI%20-%20VIVANTO%20-%20ENCUESTA%20IGED%20MOVIL%202026-04?version=GBfrontend

- **GitHub (backup):**
  https://github.com/alexjut/srni-unidad-victimas/tree/frontend

Tu zona de trabajo es `srni-frontend/`. No tocás backend ni mobile.

```bash
git fetch --all
git checkout frontend
git pull
```

## 2. Cómo arrancar el ambiente local

```bash
# Terminal 1 — backend Django
cd D:/desarrollo/unidad-victima/srni-backend
.venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8001

# Terminal 2 — panel web
cd D:/desarrollo/unidad-victima/srni-frontend
cp .env.example .env.local    # solo la primera vez
npm install                    # solo la primera vez
npm run dev
```

El panel abre en `http://localhost:5173`. El backend escucha en `http://localhost:8001`.

## 3. Credenciales de prueba

| Código | Password | Notas |
|---|---|---|
| `ALEXJUT` | `SrniTest2026!` | Todos los permisos (caracterizar, buscar RNI, reportes, admin) |
| `ADMIN01` | (pídeme si la necesitas) | Admin |

## 4. Endpoints disponibles

Todos responden 200 con tu token JWT en el header `Authorization: Bearer ...`:

**Autenticación**
- `POST /api/auth/token/` — login (devuelve access + refresh)
- `POST /api/auth/token/refresh/` — renovar access
- `GET /api/auth/perfil/` — datos del usuario logueado

**Datos**
- `GET /api/hogares/` — listar hogares (paginado)
- `GET /api/hogares/{id}/` — detalle con miembros + sesiones anidados
- `GET /api/encuestas/` — listar sesiones (paginado, filtros server-side)
- `GET /api/encuestas/{id}/` — detalle de sesión con respuestas

**Reportes**
- `GET /api/reportes/encuestador/` — dashboard del encuestador logueado
- `GET /api/reportes/encuestador/detalle/` — lista paginada de sesiones
- `GET /api/reportes/encuestador/exportar/` — CSV
- `GET /api/reportes/supervisor/` — vista agregada de todos los encuestadores
- `GET /api/reportes/dashboard/series/` — series temporales para gráficos

**Paramétricas (siempre útiles)**
- `GET /api/parametricas/departamentos/` — 33 deptos DANE
- `GET /api/parametricas/municipios/` — paginado · usar `?departamento=N` para filtrar
- `GET /api/parametricas/municipios/todos/` — los 1102 sin paginar
- `GET /api/parametricas/direcciones-territoriales/` — 21 DTs UARIV
- `GET /api/parametricas/puntos-atencion/` — usar `?direccion_territorial=N`

## 5. Cómo pedirme un endpoint nuevo

Si tu vista necesita algo que el backend NO devuelve hoy, **no toques el modelo ni el serializer** (esa parte la mantengo yo). En su lugar, mandame esto:

1. **Para qué lo necesitás** — ej. "necesito un endpoint para listar las víctimas por departamento agrupadas por género"
2. **Qué shape esperás** — un ejemplo JSON con los campos que vas a leer en el componente, ej:
   ```json
   {
     "departamento": "Antioquia",
     "total": 1500,
     "por_genero": { "M": 800, "F": 700 }
   }
   ```
3. **Filtros que vas a usar** — ej. `?fecha_desde=2026-01-01&estado=COMPLETADA`
4. **Quién puede verlo** — solo encuestador, solo supervisor, ambos
5. **Cuándo lo necesitás** — esta semana / urgente / cuando puedas

Con eso yo:
- Agrego el endpoint al backend
- Lo conecto al panel web no — eso lo hacés tú con el shape que pediste
- Te aviso por chat cuando esté arriba con su URL exacta
- Pusheo a `main` + `frontend` y vos hacés `git pull`

Tiempo típico: simple (filter o agregación) = 30 min, complejo (modelo + migración) = 2 h.

## 6. Si algo falla del lado backend

Cualquier cosa rara que veas en el panel — error HTTP, campo `undefined`, payload raro — pásame:

- La URL del endpoint
- El status code (4xx, 5xx)
- Lo que pone la consola del navegador (F12 → Console)

Y lo arreglo del lado backend sin que toques tu código.

## 7. Cambios recientes del backend que afectan al panel

Para que no te sorprendan al hacer `git pull`:

- `SesionEncuesta` ahora tiene 4 FKs opcionales: `direccion_territorial`, `departamento_atencion`, `municipio_atencion`, `punto_atencion`. Cada uno con su `*_nombre` legible.
- `RespuestaEncuesta` ahora tiene FK `miembro` opcional (null = respuesta del hogar, UUID = respuesta de un miembro específico).
- `MiembroHogarListSerializer` devuelve `nombre_completo` derivado (capturado por encuestador o derivado del RNI si es el autorizado).
- Los 8 instrumentos tienen nombres descriptivos: `Asistencia humanitaria`, `Caracterización territorial`, `Buenaventura — Sentencia T-045`, etc.

## 8. Datos disponibles para probar el panel

- 6 hogares de prueba
- 15 sesiones (algunas completadas, otras en progreso)
- ~250 respuestas
- 8 instrumentos × 1001 preguntas activas
- 21 DTs, 33 deptos, 1102 municipios, 41 puntos de atención

---

Un abrazo,
Javier
