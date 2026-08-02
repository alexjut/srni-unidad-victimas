# Guion de pruebas funcionales — identidad y documentos repetidos

**Para la sesión del 3-ago-2026.** Cubre lo que cambió el 2-ago: el manejo de
documentos compartidos por varias personas, en los cuatro caminos donde se usa.

Cada caso dice **qué se hace**, **qué debe pasar** y **qué sería un fallo**. La
columna de fallo importa: varios de estos defectos no se ven —el sistema responde
algo perfectamente creíble— y por eso hay que mirar el dato concreto.

---

## 0. Antes de empezar

| Qué | Dónde |
|---|---|
| Backend | `https://caracterizacion.unidadvictimas.gov.co` — debe dar 200 en `/api/` |
| APK | descarga desde el servidor (`/movil/app.apk`) — **debe ser la del 2-ago o posterior** |
| Usuarios | los de siempre (`ENC001`…`ENC005`, `SUPERVISOR`) |
| Padrón | 5.926.004 víctimas reales. **No son datos de prueba: es PII real.** |

⚠️ **La APK vieja no sirve para estas pruebas.** El cambio incluye migración del
almacén local (v11); una APK anterior no tiene la columna `clase_colision` y se
comporta como antes.

### Documentos para las pruebas

Los documentos reales que sirven para cada caso salen de la base, no se inventan.
Para obtenerlos (en el servidor, solo lectura):

```bash
docker exec -w /app cz_backend python manage.py shell <<'PY'
from apps.victimas.models import ColisionDocumento, Victima
for clase in ('AMBIGUO', 'DUPLICADO_FUENTE', 'NO_IDENTIFICANTE'):
    c = ColisionDocumento.objects.filter(clase=clase).first()
    if not c: continue
    v = Victima.objects.filter(numero_documento_hash=c.doc_hash).first()
    print(clase, '→', v.tipo_documento.codigo if v.tipo_documento_id else '(sin tipo)',
          v.numero_documento, f'({c.filas} filas → {c.personas} personas)')
PY
```

---

## 1. Búsqueda web — documento de una sola persona

1. Entrar al panel web y buscar un documento normal.
2. **Debe:** mostrar la ficha de la persona, sin avisos.
3. **Sería un fallo:** un 500, o un aviso de "confirme cuál corresponde" cuando
   solo hay una persona.

## 2. Búsqueda web — documento repetido que es LA MISMA persona

Usar el documento `DUPLICADO_FUENTE` del script (son el 92 % de los repetidos).

1. Buscarlo.
2. **Debe:** responder normal, con **una** ficha. El encuestador no debe notar
   nada raro: son 505 filas de la misma señora en la fuente, no una decisión.
3. **Sería un fallo:** que pregunte cuál es. Preguntar cuando no hay nada que
   decidir es lo que enseña a ignorar el aviso de la prueba 3.

## 3. Búsqueda web — documento de PERSONAS DISTINTAS  ⭐ el caso central

Usar el documento `AMBIGUO`.

1. Buscarlo.
2. **Debe:** NO mostrar una ficha. Debe salir el aviso *"Hay N registros con este
   documento. CONFIRME cuál corresponde antes de caracterizar."* y **una tarjeta
   por candidato**, cada una con su municipio y estado RUV, y un botón
   "Ver detalle y confirmar".
3. Abrir el detalle de uno y volver.
4. **Sería un fallo grave:** que muestre a una sola persona como si fuera la
   única. Ahí el encuestador caracterizaría a alguien con los datos de otro.

## 4. Búsqueda web — documento de relleno

Usar el documento `NO_IDENTIFICANTE` (o probar directamente con `99` o `0`).

1. Buscarlo.
2. **Debe:** decir que el número **no identifica a una persona** y mandar a
   verificar el documento o al alta manual. **Sin mostrar el nombre de nadie.**
3. **Sería un fallo grave:** que devuelva a alguien. `99` lo comparten 3.780
   personas distintas: cualquiera que muestre es un desconocido.

## 5. Búsqueda web — persona cargada sin tipo de documento

El 14,5 % del padrón está cargado sin tipo. Tomar una y buscarla con **CC**.

1. **Debe:** encontrarla, con el aviso de que el tipo registrado no es «CC» y
   que verifique la identidad.
2. **Sería un fallo:** "no se encontró ninguna víctima con ese documento" —es
   falso, y empuja a dar de alta a alguien que ya está—.

---

## 6. APK con red — los mismos cuatro casos

Repetir 1 a 4 desde la app, con conexión.

- El caso ambiguo **debe** mostrar la lista de personas con **nombre y fecha de
  nacimiento** (con red hay más datos que sin ella) y esperar la elección.
- **Sería un fallo:** que con red muestre directamente a una persona y sin red
  pregunte. Eso era exactamente el defecto: la pregunta aparecía sin señal y
  desaparecía con señal.

## 7. APK sin red — el caso que importa en campo  ⭐

1. Iniciar sesión **con** red (la precarga baja el padrón del día).
2. Activar modo avión.
3. Buscar el documento `AMBIGUO`.
4. **Debe:** listar las personas y pedir confirmación. Al elegir una, seguir el
   flujo con **los datos de esa** persona.
5. Buscar el documento de relleno → debe explicar que no identifica y ofrecer
   alta manual.
6. **Sería un fallo grave:** que muestre una sola persona sin avisar. Sin señal
   el encuestador no tiene cómo verificarlo.

### 7-bis. Que la elección no se pise

Tras elegir un candidato en el paso 4, comprobar que el nombre que queda en
pantalla y el que viaja al hogar son **los de la persona elegida**.

**Sería un fallo:** que aparezca el nombre del otro candidato. Es un defecto que
existió: la jornada tenía una fila por documento y pisaba la elección.

## 8. APK — actualizar la app sin perder el padrón

1. Con la app vieja instalada y sesión abierta, instalar la nueva encima.
2. Abrir **sin red**.
3. **Debe:** el padrón sigue estando; la búsqueda offline funciona.
4. **Sería un fallo:** "la persona no está en los datos offline" para alguien que
   sí estaba. La migración anterior borraba la tabla dando por hecho que la
   precarga la repuebla, y la precarga solo corre al iniciar sesión.

---

## 9. Alta manual

1. Buscar un documento que no exista.
2. Darla de alta a mano.
3. **Debe:** quedar con estado **`NO_VERIFICADO`** ("no está en el padrón
   descargado"), no `NO_INCLUIDO`.
4. **Sería un fallo:** que diga "No incluido" — eso afirma algo sobre el RUV que
   nadie verificó, y 1,88 M de víctimas incluidas están fuera del padrón.

---

## Qué mirar si algo falla

| Síntoma | Dónde mirar |
|---|---|
| 502 en todo `/api/` | `docker restart cz_nginx` (al recrear el backend cambia su IP) |
| La búsqueda pregunta siempre | ¿corrió `clasificar_colisiones`? Sin veredicto, el sistema pregunta a propósito |
| La búsqueda nunca pregunta | ¿la APK es la nueva? ¿el padrón se regeneró después de clasificar? |
| Un documento repetido da 500 | es el defecto original: la versión desplegada es anterior al 2-ago |

Contexto completo de por qué el sistema se comporta así:
[`../oracle-legacy-padron/decision_documentos_duplicados.md`](../oracle-legacy-padron/decision_documentos_duplicados.md).
