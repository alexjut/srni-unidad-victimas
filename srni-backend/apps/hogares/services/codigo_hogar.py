"""
Bloque 1a — Generación de HOG_CODIGO con reintento anti-colisión.

PORT de GIC_CATEGORIZACION.GIC_INSERT_HOGAR1 (RNIENTREVISTA), package body líneas 183-191:

    CODIGOENCUESTA := GIC_N_CARACTERIZACION.FN_GET_CODIGOENCUESTA;
    CODIGOENCUESTA := ID_USUARIO || '-' || CODIGOENCUESTA;
    SELECT COUNT(*) INTO TOTALHOGAR FROM GIC_HOGAR H WHERE H.HOG_CODIGO = CODIGOENCUESTA;
    WHILE TOTALHOGAR > 0 LOOP  -- regenerar hasta que no exista
        CODIGOENCUESTA := ID_USUARIO || '-' || GIC_N_CARACTERIZACION.FN_GET_CODIGOENCUESTA;
        ...
    END LOOP;

Formato observado en producción (patrón HOG_CODIGO, ej. `228206-6I0D6`):
    {codigo_usuario}-{5 caracteres alfanuméricos}

DIVERGENCIA CONSCIENTE (ver reporte de paridad):
- `FN_GET_CODIGOENCUESTA` es opaca (su cuerpo no se leyó). Aquí generamos 5
  caracteres con `secrets` (CSPRNG) sobre un alfabeto sin caracteres ambiguos
  (0/O/1/I) en vez de replicar su RNG interno. El *formato externo* es idéntico.
- Se añade `max_intentos` como salvaguarda: el `WHILE` de Oracle es infinito.
"""
import secrets

# Base32 tipo Crockford sin 0/O/1/I para evitar ambigüedad al leer códigos.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _codigo_aleatorio(longitud: int = 5) -> str:
    return "".join(secrets.choice(_ALFABETO) for _ in range(longitud))


def generar_codigo_hogar(user, *, longitud: int = 5, max_intentos: int = 100) -> str:
    """
    Genera un `codigo_hogar` único con formato `{id_usuario}-{aleatorio}`.

    `user` puede ser una instancia de Usuario o directamente el identificador.

    PREFIJO: se usa `user.codigo_usuario` (el código numérico del encuestador,
    ej. `228206`) porque es el análogo directo del `USU_IDUSUARIO`/`ID_USUARIO`
    de Oracle que forma el HOG_CODIGO `228206-6I0D6`. El PK de `Usuario` en Django
    es un UUID y NO sirve como prefijo. Cae a `user.pk` solo si no hay codigo_usuario.

    Lanza RuntimeError si no logra un código único tras `max_intentos`.
    """
    # Import diferido: evita ciclos al cargar la app.
    from apps.hogares.models import Hogar

    id_usuario = str(getattr(user, "codigo_usuario", None) or getattr(user, "pk", user))
    for _ in range(max_intentos):
        codigo = f"{id_usuario}-{_codigo_aleatorio(longitud)}"
        if not Hogar.objects.filter(codigo_hogar=codigo).exists():
            return codigo
    raise RuntimeError(
        f"No se pudo generar un HOG_CODIGO único tras {max_intentos} intentos."
    )
