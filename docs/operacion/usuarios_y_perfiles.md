# Usuarios y perfiles en producción

**Servidor:** 30.0.1.109 · `srni_caracterizacion` · **Actualizado:** 11-ago-2026

---

## 1. Cómo se llama un usuario (la causa del 90 % de los "no me deja entrar")

El campo de acceso **no es el nombre de pila ni el correo**: es `codigo_usuario`,
y para las 1.158 encuestadoras se generó con **iniciales + apellidos**:

```
KLMUÑOZM      ← KAREN LILIANA MUÑOZ MORA
KDCARRIONT    ← KAREN DAYANA CARRION TORRES
KTSOSCUEL     ← KAREN TATIANA SOSCUE LOPEZ
```

Hay **11 usuarias llamadas Karen** y ninguna tiene `KAREN` como código. Quien
intente entrar con su nombre de pila va a fallar siempre, y el mensaje de error no
distingue "usuario que no existe" de "clave equivocada".

> **Antes de restablecer una clave, confirmar el `codigo_usuario`.** La mitad de
> los reportes se resuelven ahí.

---

## 2. Perfiles

| Código | Buscar RNI | Caracterizar | Ver reportes | Administrar | Usuarios |
|---|:---:|:---:|:---:|:---:|---:|
| `ENCUESTADOR` | ✅ | ✅ | — | — | 1.158 |
| `COORDINADOR` | ✅ | ✅ | ✅ | — | 1 |
| `SUPERVISOR` | ✅ | — | ✅ | — | 1 |
| `ADMINISTRADOR` | ✅ | ✅ | ✅ | ✅ | 1 |
| `DOCUMENTADOR` | ✅ | **❌** | ✅ | — | 1 |

### `DOCUMENTADOR` — creado el 11-ago-2026

Nació de un caso concreto: una documentadora del proyecto necesitaba entrar y no
había perfil que le correspondiera. Se creó **de solo lectura** a propósito —
puede ver el sistema para documentarlo, pero **no puede caracterizar**.

Quien documenta no necesita poder alterar la caracterización de una víctima, y
darle ese permiso "porque es más fácil" es la clase de atajo que después nadie
recuerda haber tomado.

---

## 3. 🔴 Ninguna encuestadora ha entrado nunca

Medido el 11-ago-2026: de los 1.161 usuarios, la auditoría solo registra **tres
códigos**: `ALEXJUT`, `BRANDO` y `QAPRUEBA`. Las 1.158 encuestadoras figuran
`activo=True` con perfil correcto y **`último acceso: NUNCA`**.

Las cuentas existen y están habilitadas; lo que no está verificado es que las
credenciales repartidas coincidan con lo que quedó en la base.

**Decidido el 11-ago (Javier):** las credenciales las asigna él cuando se
confirme la fecha de inicio de la operación en campo. No es un pendiente técnico
abierto — la carga masiva se hará contra una fecha conocida, no antes.

Lo que sí conviene recordar cuando llegue ese momento: probar un puñado de
cuentas reales **antes** de repartir, porque el modo de falla es que 1.158
personas reporten lo mismo el mismo día. Y que el reporte va a llegar como "no me
funciona el usuario" aunque la causa sea el `codigo_usuario` (§1).

---

## 4. Diagnosticar "no puedo entrar"

En orden, porque el primero resuelve la mayoría:

1. **¿El `codigo_usuario` es el correcto?** Buscar por nombre completo:
   ```python
   Usuario.objects.filter(nombre_completo__icontains='APELLIDO')
   ```
2. **¿Existe el usuario?** Si la búsqueda no devuelve nada, no es un problema de
   clave.
3. **¿Está activo?** `u.activo` y `u.perfil.activo` — ambos.
4. **¿La clave sirve?** `u.check_password(...)` — sin imprimirla.
5. **¿Alguna vez entró?** `u.last_login`. Un `None` en toda una población apunta
   al reparto de credenciales, no al usuario que reporta.
6. **¿Hay rastro en auditoría?** `LogAcceso` guarda `codigo_usuario` **aunque el
   usuario se borre**, así que sirve para distinguir "lo eliminaron" de "nunca
   existió". El campo de fecha es `timestamp`.

### Al diagnosticar con contraseñas

- **Pasarlas por variable de entorno**, nunca escritas en un script que quede en
  el servidor, y borrar los temporales al terminar.
- **No reutilizar una clave que circuló por chat o correo.** Si llegó por ahí,
  hay que cambiarla, funcione o no.

---

## 5. Crear un usuario

```python
from apps.autenticacion.models import Perfil, Usuario

perfil = Perfil.objects.get(codigo='DOCUMENTADOR')
Usuario.objects.create_user(
    codigo_usuario='CODIGO',        # ⚠️ este es el campo de login
    password=clave,                 # desde el entorno, no literal
    nombre_completo='Nombre Apellido',
    email='correo@dominio',
    perfil=perfil,
    activo=True,
)
```

Verificar siempre después: `check_password`, `activo`, `perfil.activo` y que los
permisos sean los que se querían — sobre todo los que NO se querían.

Las claves se guardan con **argon2**.

---

**Relacionado:** `docs/gestion/implementacion_capacitacion_despliegue.md`.
