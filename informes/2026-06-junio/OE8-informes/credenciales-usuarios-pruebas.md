# Credenciales y roles — Ambiente de validación SRNI

> **Ambiente:** https://prod-caracterizacion.ngrok.app (panel web) · APK de pruebas
> **Importante:** credenciales de **PRUEBA** sobre datos ficticios. Cambiar antes de producción.
> El login normaliza el código a mayúsculas (podés escribir `alexjut` o `ALEXJUT`).

## Usuarios creados

| Código | Contraseña | Nombre | Rol / Perfil | Usa |
|--------|-----------|--------|--------------|-----|
| **alexjut** | `alexjut1030` | Javier Alexander Aguilar Castro | **Administrador** | Panel web (todo + administración) + APK |
| **brando** | `Brando2026*` | Brando — Líder Frontend | **Coordinador / Líder** | Panel web + APK |
| **supervisor** | `Supervisor2026*` | Oscar A. Manosalva (Supervisor) | **Supervisor** | Panel web (ve todo / reportes) |
| **ENC001** | `SrniTest2026!` | Encuestador de Prueba 1 | Encuestador | APK |
| **ENC002** | `SrniTest2026!` | Encuestador de Prueba 2 | Encuestador | APK |
| **ENC003** | `SrniTest2026!` | Encuestador de Prueba 3 | Encuestador | APK |
| **ENC004** | `SrniTest2026!` | Encuestador de Prueba 4 | Encuestador | APK |
| **ENC005** | `SrniTest2026!` | Encuestador de Prueba 5 | Encuestador | APK |

## Qué puede hacer cada rol

| Permiso | Administrador | Coordinador/Líder | Supervisor | Encuestador |
|---------|:---:|:---:|:---:|:---:|
| Buscar en el RNI | ✅ | ✅ | ✅ | ✅ |
| Caracterizar (diligenciar) | ✅ | ✅ | ❌ | ✅ |
| Ver reportes | ✅ | ✅ | ✅ | ❌ |
| **Administrar usuarios** | ✅ | ❌ | ❌ | ❌ |
| Acceso a `/admin/` de Django | ✅ | ❌ | ❌ | ❌ |

- **Administrador (alexjut):** control total. Único que ve el módulo de **Administración de usuarios** en el panel.
- **Coordinador/Líder (brando):** usa APK y panel; caracteriza y ve reportes. Sin administración.
- **Supervisor:** ve todo el panel (dashboards, reportes, supervisión, auditoría); no caracteriza.
- **Encuestadores (ENC001–005):** trabajan en campo con la APK.

## Cómo se gestionan de aquí en adelante
- El **administrador** crea/edita/desactiva usuarios desde el panel web
  (módulo *Administración de usuarios* — lo construye Brando sobre el API `/api/usuarios/`).
- Reproducible por comando: `python manage.py crear_usuarios_demo` (idempotente).
- Todas las contraseñas se pueden cambiar; estas son iniciales de prueba.
