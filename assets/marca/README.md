# Marca — Unidad para las Víctimas

Fuente única (master) de los logos institucionales del proyecto SRNI. Aquí viven
los SVG originales entregados por la diseñadora. Cada aplicación mantiene su copia
de trabajo en el formato que necesita; este folder es la referencia.

## Variantes

| Archivo | Orientación | Uso recomendado |
|---|---|---|
| `logo-unidad-vertical-color.svg` | Vertical, a color | Fondos claros (escudo + texto oscuro) |
| `logo-unidad-vertical-color-negativo.svg` | Vertical, color sobre negativo | Fondos oscuros (login de la APK) |
| `logo-unidad-vertical-bn-negativo.svg` | Vertical, blanco | Fondos oscuros, una sola tinta |
| `logo-unidad-horizontal-color.svg` | Horizontal, a color | Encabezados sobre fondo claro (admin modo claro) |
| `logo-unidad-horizontal-negativo.svg` | Horizontal, blanco | Encabezados sobre fondo oscuro (admin modo oscuro, barra azul) |

## Dónde se usan (copias de trabajo por app)

- **APK (mobile):** `srni-mobile/assets/logos/*.png` — PNG generados desde estos SVG
  (login vertical negativo; header horizontal negativo).
- **Panel web (frontend):** `srni-frontend/src/assets/LogoHorizontal*.svg` — importados por Vite.
- **Admin (backend):** `srni-backend/static/marca/*.svg` — usados por django-unfold
  (`SITE_LOGO`/`SITE_ICON`).

> Si la diseñadora entrega nuevas versiones, actualizar primero aquí y luego
> propagar a las copias de cada app.
