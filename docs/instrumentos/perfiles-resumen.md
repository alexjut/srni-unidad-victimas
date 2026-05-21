# Perfiles de Caracterización UARIV — Resumen

**Fuente:** Diccionarios de datos oficiales UARIV  
**Última actualización:** 2026-04-28

---

## Los 6 Perfiles

| # | Código | Nombre | Versión | Capítulos | Loader | Estado |
|---|--------|--------|---------|-----------|--------|--------|
| 1 | TERRITORIAL | Perfil Territorial | V7 | 14 | `cargar_territorial_v7.py` | ✅ Listo |
| 2 | BUENAVENTURA | Perfil Buenaventura | V7 | 17 | `cargar_buenaventura_v7.py` | ✅ Listo |
| 3 | SAN_ANDRES | Perfil San Andrés / SAI | V7 | 14 | `cargar_san_andres_v7.py` | ✅ Listo |
| 4 | TELEFONICO | Perfil Telefónico SAAH | V8 | 7 | `cargar_telefonico_v8.py` | ✅ Listo |
| 5 | URBANO_ETNICO | Perfil Urbano Étnico | V1 | 12 | `cargar_urbano_etnico_v1.py` | ✅ Listo |
| 6 | RURAL_ETNICO | Perfil Rural Étnico | V1 | 14 | `cargar_rural_etnico_v1.py` | ✅ Listo |

---

## Detalle por Perfil

### 1. Territorial V7
- **Población:** Víctimas en todo el territorio nacional
- **Capítulos HOGAR:** A, C, D, E, JA, M, T
- **Capítulos PERSONA:** B, F, G, H, JF, K, L
- **Preguntas:** ~248
- **Fuente documental:** `Diccionario_de_datos__Entrevista de Caracterización_V7_Perfil Territorial.xlsx`

### 2. Buenaventura V7
- **Población:** Víctimas en Buenaventura (Afro-colombianas)
- **Capítulos HOGAR:** A, C, D, FA, JA, M, NA, O, T
- **Capítulos PERSONA:** B, F, G, H, JF, K, L, NP
- **Capítulos exclusivos:** NA (Info Adicional Hogar), NP (Info Adicional Persona), O (Seguridad Jurídica Territorio)
- **Preguntas:** ~300
- **Fuente documental:** `Diccionario_de_datos__Entrevista de Caracterización_V7_perfilBuenaventura.xlsx`

### 3. San Andrés / SAI V7
- **Población:** Víctimas en el archipiélago SAIPSCA (pueblo RAIZAL)
- **Capítulos HOGAR:** A, C, D, E, JA, M, T
- **Capítulos PERSONA:** B, F, G, H, JF, K, L
- **Adaptaciones SAI:**
  - Cap. A: sin vereda, usa "sector/barrio" (las islas no tienen veredas)
  - Cap. B: identidad RAIZAL + idioma Creole English
  - Cap. M: territorio insular y pesca artesanal
- **Preguntas:** ~290
- **Fuente documental:** `Diccionario_de_datos__Entrevista de Caracterización_V7_Perfil San Andrés.xlsx`

### 4. Telefónico SAAH V8
- **Población:** Atención asistida remota (SAAH — Sistema de Atención y Asistencia al Hogar)
- **Modalidad:** Entrevista telefónica — sin desplazamiento presencial
- **Versión:** V8 (más reciente)
- **Cargador:** JSON fixture + `cargar_diccionario_v8.py` (genérico)
- **Estado:** En desarrollo

### 5. Urbano Étnico V1
- **Población:** Comunidades étnicas en contexto urbano
- **Nota:** Versión inicial, menor cantidad de preguntas que Territorial
- **Estado:** Pendiente de loader

### 6. Rural Étnico V1
- **Población:** Comunidades étnicas en territorios rurales y colectivos
- **Modalidad:** Solo offline (app móvil sin conectividad)
- **Estado:** Pendiente de loader

---

## PKs de Instrumentos (fixture `perfiles_iniciales.json`)

```
Territorial V7   → InstrumentoVersion PK: 22222222-0001-0001-0001-000000000001
Buenaventura V7  → InstrumentoVersion PK: 22222222-0002-0002-0002-000000000002
San Andrés V7    → InstrumentoVersion PK: 22222222-0003-0003-0003-000000000003
Telefónico V8    → InstrumentoVersion PK: 22222222-0004-0004-0004-000000000004
Urbano Étnico V1 → InstrumentoVersion PK: 22222222-0005-0005-0005-000000000005
Rural Étnico V1  → InstrumentoVersion PK: 22222222-0006-0006-0006-000000000006
```

---

## Cómo cargar todos los perfiles disponibles

```bash
cd srni-backend
python manage.py loaddata perfiles_iniciales   # prerequisito
python manage.py cargar_territorial_v7
python manage.py cargar_buenaventura_v7
python manage.py cargar_san_andres_v7
python manage.py cargar_diccionario_v8         # Asistencia V8
```
