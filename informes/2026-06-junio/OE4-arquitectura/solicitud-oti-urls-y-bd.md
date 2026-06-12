# Solicitud a la OTI — Publicación de URL y conectividad a BD externa
## Sistema de Caracterización de Víctimas — SRNI

**Contrato:** 2226-2026
**Contratista:** Javier Alexander Aguilar Castro
**Servidor asignado:** `30.0.1.109` (Ubuntu, infraestructura UARIV)
**Fecha:** junio 2026

---

## 0. Estado actual (lo ya hecho)

La solución **ya está desplegada y operativa** en el servidor `30.0.1.109`, en una
carpeta aislada (`/home/admin_rni/caracterizacion/`), **sin afectar** los servicios
existentes (`nginx-proxy-manager` y `uariv-auth-service`).

Corre como un stack Docker independiente y **publica en el puerto `8090` (HTTP)**:

| Componente | Detalle |
|---|---|
| Panel web + API | Servidos en el **mismo origen**: `http://30.0.1.109:8090/` |
| Backend Django (API) | `http://30.0.1.109:8090/api/` |
| Admin Django | `http://30.0.1.109:8090/admin/` |
| Descarga APK | `http://30.0.1.109:8090/movil/` |

Verificado funcionando: login con JWT, consulta de paramétricas, control de permisos.

---

## 1. Lo que solicitamos — Asignación de URL + TLS

Necesitamos que la OTI **publique la aplicación bajo una URL institucional con HTTPS**.
El servidor ya tiene el **Nginx Proxy Manager** (NPM), que es justamente la herramienta
para esto: basta crear un **Proxy Host** que enrute el dominio hacia nuestro puerto.

### Datos que entregamos para que la OTI configure el proxy

| Parámetro | Valor |
|---|---|
| **IP / destino interno** | `30.0.1.109` |
| **Puerto de la aplicación** | `8090` (HTTP) |
| **Esquema interno** | HTTP (el TLS lo termina el NPM) |
| **Rutas** | Todo bajo `/` (SPA + `/api` + `/admin` + `/static` + `/movil`) |
| **Websockets** | No requeridos |

### Lo que pedimos a la OTI que defina/entregue

1. **El nombre de dominio / subdominio** que usaremos (sugerencias, a criterio de la OTI):
   - `caracterizacion.unidadvictimas.gov.co`, o
   - `srni-caracterizacion.unidadvictimas.gov.co`
2. **Certificado TLS** para ese dominio (el NPM puede emitirlo automáticamente vía
   Let's Encrypt, o la OTI provee el certificado institucional).
3. **Creación del Proxy Host** en el NPM:
   `https://<dominio> → http://30.0.1.109:8090`

> **Importante:** una vez la OTI nos confirme el dominio definitivo, hacemos un ajuste
> de 1 minuto en la configuración de la app (`ALLOWED_HOSTS` y `CORS`) para aceptar ese
> dominio. Por eso necesitamos **que la OTI nos diga primero la URL**.

### Alternativa temporal (mientras se define el dominio)

Si se quiere probar **ya mismo por IP**, basta con **abrir el puerto `8090/TCP`** en el
firewall hacia el segmento de los desarrolladores/validadores. Quedaría accesible en
`http://30.0.1.109:8090/`. (Hoy lo probamos por túnel SSH; para acceso directo se
requiere esa regla.)

---

## 2. Conectividad a Base de Datos externa (Oracle RNI) — preparación

La aplicación hoy opera con su **propia base PostgreSQL local** y, para la búsqueda de
víctimas, usa un **repositorio de datos de prueba (mock)**. Está **diseñada para
conectarse a la BD Oracle institucional** del RNI cuando la Subdirección lo autorice
(la selección es por configuración: `VICTIMA_REPOSITORY = MOCK | ORACLE`).

Para habilitar esa integración necesitaremos de la OTI / DBA:

### 2.1 Datos de conexión Oracle
| Dato | Necesario |
|---|---|
| Host / IP del servidor Oracle | ✔ |
| Puerto | ✔ (típicamente `1521`) |
| **Service name** o **SID** | ✔ |
| Usuario de solo lectura (consulta) | ✔ |
| Contraseña (por canal seguro) | ✔ |
| Nombre del esquema / vistas a consultar | ✔ (ej. `INH_REPORTE_GAVE` y relacionadas) |

### 2.2 Acceso de red (firewall)
- Habilitar salida desde **`30.0.1.109`** hacia **`<host_oracle>:1521/TCP`**.
- Confirmar si requiere estar dentro de una VLAN/segmento específico.

### 2.3 Definición funcional
- **Vistas/consultas** autorizadas para: verificar inclusión en RUV, habilitación para
  caracterización y conformación del grupo familiar por documento.
- Confirmar que el usuario entregado es **solo lectura** (la app nunca escribe en Oracle).

> Esta integración es un **trámite independiente** y posterior; se solicita ahora solo
> para que la OTI/DBA vaya preparando credenciales y la regla de red. Mientras tanto la
> app funciona de forma autónoma con datos de prueba.

---

## 3. Resumen de lo que pedimos a la OTI

1. **Definir la URL** (subdominio) de la aplicación y **emitir su certificado TLS**.
2. **Crear el Proxy Host** en el NPM: `https://<dominio> → http://30.0.1.109:8090`.
3. *(Opcional, para probar ya por IP)* **Abrir el puerto `8090/TCP`** a los validadores.
4. *(Preparación)* Reunir **credenciales Oracle de solo lectura** + **regla de firewall**
   de `30.0.1.109` hacia `Oracle:1521` para la futura integración con el RNI.

Apenas la OTI confirme la URL, dejamos la aplicación publicada y lista para validación
funcional con el equipo de caracterización.

Cordialmente,

**Javier Alexander Aguilar Castro**
Contratista — Sistema de Caracterización de Víctimas SRNI
Contrato 2226-2026
