"""
Bloques 2 y 3 — Alta de miembro del hogar (persona + vínculo).

En Oracle son dos procedures de GIC_CATEGORIZACION:

  GIC_INSERT_PERSONAS (package body líneas 32-95):
    - Guard anti-duplicado (NR 25/06/2024): rechaza si el mismo NDOCU ya es
      miembro de un hogar 'ACTIVA' creado en las últimas 24h:
          SELECT COUNT(1) ... FROM gic_hogar
           WHERE hog_codigo IN (SELECT b.hog_codigo
                                  FROM gic_persona a, gic_miembros_hogar b
                                 WHERE a.per_idpersona = b.per_idpersona
                                   AND per_numerodoc = NDOCU
                                   AND a.usu_fechacreacion > SYSDATE - 1)
                             AND estado = 'ACTIVA';
          IF v_t_miembro > 0 THEN RAISE v_duplicado; END IF;
    - Normaliza nombres a UPPERCASE: INSERT ... VALUES(0, UPPER(PNOMBRE), ...).

  GIC_INSERT_MIEMBRO_HOGAR: vincula persona↔hogar (no debe duplicar el vínculo).

En el modelo Django, "persona" y "vínculo" están FUSIONADOS en MiembroHogar
(la persona NO-RNI vive cifrada en el propio MiembroHogar; la persona RNI se
referencia por FK a Victima). Por eso aquí es UN solo servicio: `agregar_miembro`.

DIVERGENCIAS CONSCIENTES (ver reporte de paridad):
- Oracle guarda `per_numerodoc` en claro y lo consulta con `=`. En Django el
  documento va CIFRADO (EncryptedField, sin hash en MiembroHogar), así que el
  guard compara por HASH dentro de la ventana de 24h (conjunto pequeño):
  usa `Victima.numero_documento_hash` para miembros RNI y descifra+hashea el
  documento cifrado para miembros NO-RNI. Mismo criterio, adaptado al cifrado.
- El hash usa `sha256_hash(numero.strip().upper())`, idéntico al de Victima.save,
  para que un miembro RNI y uno NO-RNI con el mismo documento casen igual.
- Oracle traga el duplicado con `WHEN OTHERS` (lo loguea y NO inserta). Aquí
  levantamos `MiembroDuplicadoError` (mismo resultado —no inserta— pero SIN
  pérdida silenciosa: es una MEJORA consciente).
- Oracle 'ACTIVA' ≡ Django 'BORRADOR' (ver alta_hogar.ESTADO_ABIERTO).
"""
from datetime import timedelta

from django.utils import timezone

from apps.victimas.fields import sha256_hash
from .alta_hogar import ESTADO_ABIERTO

# Oracle: usu_fechacreacion > SYSDATE - 1  (un día)
VENTANA_DUPLICADO = timedelta(hours=24)


class MiembroDuplicadoError(Exception):
    """El documento ya es miembro de un hogar abierto creado en las últimas 24h."""

    def __init__(self, numero_documento: str):
        self.numero_documento = numero_documento
        super().__init__(
            f"Documento duplicado en hogar activo (<24h): {numero_documento}"
        )


def _hash_numero(numero: str) -> str:
    """Hash canónico del número de documento — idéntico a Victima.save."""
    return sha256_hash(str(numero).strip().upper())


def documento_ya_en_hogar_activo_reciente(numero_documento: str, *, ahora=None) -> bool:
    """
    Port del guard de GIC_INSERT_PERSONAS: ¿el documento ya es miembro de un
    hogar ABIERTO creado en las últimas 24h?
    """
    from apps.hogares.models import MiembroHogar

    if not numero_documento:
        return False
    ahora = ahora or timezone.now()
    limite = ahora - VENTANA_DUPLICADO
    objetivo = _hash_numero(numero_documento)

    candidatos = MiembroHogar.objects.filter(
        hogar__estado=ESTADO_ABIERTO,
        hogar__created_at__gt=limite,
    ).select_related("victima")

    for m in candidatos:
        if m.victima_id and m.victima.numero_documento_hash == objetivo:
            return True
        if m.numero_documento and _hash_numero(m.numero_documento) == objetivo:
            return True
    return False


def _vinculo_ya_existe(hogar, *, victima, numero_documento) -> bool:
    """
    Port de la no-duplicación de GIC_INSERT_MIEMBRO_HOGAR: ¿ya existe este
    integrante en el hogar? Para RNI se llavea por (hogar, victima); para NO-RNI,
    por (hogar, documento) — el análogo de la clave (HOG_CODIGO, PER_IDPERSONA).
    """
    from apps.hogares.models import MiembroHogar

    if victima is not None:
        return MiembroHogar.objects.filter(hogar=hogar, victima=victima).exists()
    if numero_documento:
        objetivo = _hash_numero(numero_documento)
        for m in MiembroHogar.objects.filter(hogar=hogar, victima__isnull=True):
            if m.numero_documento and _hash_numero(m.numero_documento) == objetivo:
                return True
    return False


def agregar_miembro(
    *,
    hogar,
    user=None,
    victima=None,
    nombre_completo: str = "",
    tipo_documento=None,
    numero_documento: str = "",
    parentesco: str = "",
    genero: str = "",
    fecha_nacimiento=None,
    rol: str = "MIEMBRO",
    es_autorizado: bool = False,
    estado_inclusion: str = "NO_INCLUIDO",
    validar_duplicado: bool = True,
    ahora=None,
):
    """
    Crea un MiembroHogar aplicando los guards de los tres procedures Oracle.

    - Guard duplicado 24h (bloque 2): levanta MiembroDuplicadoError.
    - No duplicar vínculo (bloque 3): si ya existe, devuelve el miembro existente
      (idempotente) sin crear otro.
    - Nombres en UPPERCASE (bloque 2).

    Devuelve el MiembroHogar (nuevo o existente).
    """
    from apps.hogares.models import MiembroHogar

    # Documento efectivo: RNI ⇒ el de la víctima; NO-RNI ⇒ el provisto.
    numero_efectivo = (
        (victima.numero_documento if victima is not None else numero_documento) or ""
    )

    # Bloque 3 — idempotencia del vínculo PRIMERO: re-vincular al MISMO hogar no es
    # un "duplicado" (en Oracle son procedures distintos; GIC_INSERT_MIEMBRO_HOGAR
    # no aplica el guard de GIC_INSERT_PERSONAS). Devuelve el miembro existente.
    if _vinculo_ya_existe(hogar, victima=victima, numero_documento=numero_documento):
        if victima is not None:
            return MiembroHogar.objects.get(hogar=hogar, victima=victima)
        objetivo = _hash_numero(numero_documento)
        for m in MiembroHogar.objects.filter(hogar=hogar, victima__isnull=True):
            if m.numero_documento and _hash_numero(m.numero_documento) == objetivo:
                return m

    # Bloque 2 — guard anti-duplicado (mismo doc en OTRO hogar abierto reciente).
    if validar_duplicado and numero_efectivo and documento_ya_en_hogar_activo_reciente(
        numero_efectivo, ahora=ahora
    ):
        raise MiembroDuplicadoError(numero_efectivo)

    return MiembroHogar.objects.create(
        hogar=hogar,
        victima=victima,
        # Bloque 2 — UPPERCASE de nombres/documento (UPPER(PNOMBRE), UPPER(NDOCU)).
        nombre_completo=(nombre_completo or "").strip().upper(),
        tipo_documento=tipo_documento,
        numero_documento=(numero_documento or "").strip().upper(),
        parentesco=parentesco,
        genero=genero,
        fecha_nacimiento=fecha_nacimiento,
        rol=rol,
        es_autorizado=es_autorizado,
        estado_inclusion=estado_inclusion,
        creado_por=user,
    )
