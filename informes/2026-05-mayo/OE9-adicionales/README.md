# OE9 — Actividades adicionales con supervisor

> **Obligación contractual:** *Cumplir las demás actividades relacionadas con el objeto del contrato que sean acordadas con el supervisor.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se atendieron varias actividades adicionales acordadas con el supervisor, complementarias al objeto del contrato. *(Sección a complementar por el contratista con los siguientes ítems: estado del acuerdo de confidencialidad de aplicativos —firma exigida antes del 1 de mayo—; acreditación mensual al supervisor del pago de aportes a seguridad social del mes, ARL y planilla PILA; estado real de las solicitudes formales a Oscar para obtención de accesos a los servidores SRNI —FTP UARIV, Azure IGPD, Azure Móvil y Sistema Ficha—; gestión de la API key Gemini institucional ante Google Cloud con DPA jurídica firmada y configuración en Azure Key Vault para uso en producción; verificación del snapshot semanal del repositorio en OneDrive del supervisor con permisos restringidos solo al contratista y al supervisor)*. El único acceso operativo a la fecha es el repositorio Azure DevOps oficial UARIV (rama `main` consolidada al commit `7d1a6b9`); los demás accesos siguen pendientes de aprobación formal.

## Evidencia que soporta esta actividad

- **Repositorio Azure DevOps activo:** `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04` (acceso aprobado y operativo).
- **Checklist de actividades pendientes:** sección "Checklist Mayo 2026" del README.md de esta carpeta con tabla de estado de cada acceso.
- **Anexos a aportar por el contratista:**
  - [ ] Acuerdo de confidencialidad firmado (escaneo PDF)
  - [ ] Comprobantes de aportes a seguridad social de mayo (PILA o planilla)
  - [ ] Correos de solicitud de accesos UARIV con fechas (FTP, Azure IGPD, Azure Móvil, Ficha)
  - [ ] Captura de configuración de la API key Gemini (cuando se aprueba)
  - [ ] Captura de estructura de OneDrive con permisos restringidos
  - [ ] Reporte ejecutivo a Oscar sobre estado de la API key Gemini institucional

---

## Actividades del cronograma

1. Firma acuerdo de confidencialidad aplicativos — ANTES del 1 de Mayo 2026
2. Pago seguridad social mensual — acreditación al supervisor
3. Solicitud y seguimiento accesos servidores SRNI: FTP, Azure IGPD, Azure Móvil, Ficha
4. Gestión API key Gemini institucional — Google Cloud + DPA jurídica
5. Almacenamiento en OneDrive de toda creación intelectual generada

## Checklist Mayo 2026

### Acuerdo de confidencialidad
- [ ] Firmado antes del 1 de mayo (fecha límite contractual)
- [ ] Anexar copia escaneada en OneDrive

### Seguridad social mensual
- [ ] Aporte salud (correspondiente a mayo)
- [ ] Aporte pensión
- [ ] ARL (clase de riesgo según contrato)
- [ ] Planilla PILA o comprobante
- [ ] Acreditación remitida al supervisor (correo)

### Accesos a servidores SRNI

Estado de las solicitudes formales a Oscar:

| Recurso | Solicitado | Aprobado | Activo | Notas |
|---|---|---|---|---|
| FTP UARIV | _fecha_ | ⬜ | ⬜ | Reemplazo del FTP `ftp.isegoria.co` del APK viejo |
| Azure IGPD | _fecha_ | ⬜ | ⬜ | Plataforma identificación de personas en gestión documental |
| Azure Móvil | _fecha_ | ⬜ | ⬜ | Subscription para despliegue de la app SRNI |
| Ficha (sistema SRNI) | _fecha_ | ⬜ | ⬜ | Sistema interno UARIV |
| Repositorio Azure DevOps | ✅ | ✅ | ✅ | `tfsunidad.visualstudio.com/...IGED MOVIL 2026-04` |

### API key Gemini institucional

- [ ] Solicitud formal a Google Cloud (cuenta institucional UARIV, no personal)
- [ ] DPA (Data Processing Addendum) jurídica firmada con Google
- [ ] Configuración de cuotas y alertas
- [ ] Almacenamiento de la key en Azure Key Vault (no en `.env`)
- [ ] Rotación documentada

**Estado:** durante mayo se trabajó con la key personal de desarrollo. **La key institucional sigue pendiente** — bloqueante para despliegue en producción.

### OneDrive — creación intelectual

Toda la propiedad intelectual generada se almacena en:

```
Caracterizacion-Victimas/
├── 2026/
│   ├── 04-Abril/
│   ├── 05-Mayo/      ← esta entrega
│   ├── 06-Junio/
│   └── 07-Julio/
├── Documentacion-tecnica/
├── Capturas-y-evidencias/
└── Repositorio-clon/  (snapshot semanal del repo Git)
```

- [ ] Confirmar que el snapshot semanal del repo está corriendo
- [ ] Verificar permisos: solo Javier (contratista) + Oscar (supervisor) tienen acceso
- [ ] Política de retención: indefinida durante la vigencia del contrato

## Documentos a anexar

- [ ] Acuerdo de confidencialidad firmado
- [ ] Comprobantes de aportes SS de mayo (PILA o planilla)
- [ ] Correos de solicitud de accesos (con fecha)
- [ ] Captura de configuración de la key Gemini
- [ ] Captura de estructura OneDrive

## Pendientes (a complementar Javier)

- Estado real de cada acceso (fechas de solicitud y respuesta)
- Comprobantes financieros del mes
- Reporte ejecutivo a Oscar sobre el estado de la API key Gemini institucional
