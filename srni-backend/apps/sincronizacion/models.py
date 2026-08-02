"""
Ledger de auditoría de la escritura hacia Oracle legacy (RNIENTREVISTA).

ETAPA A del strangler-fig (ver docs/oracle-legacy/diseno_etapa_a_escritura.md):
SICAV Móvil escribe hacia Oracle INVOCANDO LOS PROCEDURES OFICIALES que usa la
app vieja (no la lógica portada a Django, que es la Etapa B). Como cada procedure
hace COMMIT interno y traga sus excepciones con WHEN OTHERS, NO existe una
transacción atómica envolvente: el flujo es una MÁQUINA DE ESTADOS REANUDABLE y
este ledger es su memoria persistente.

Cada fila = un PASO de la máquina de estados para una entidad de origen SICAV.
El (hogar, paso, origen_id) único garantiza IDEMPOTENCIA: antes de (re)ejecutar
un paso el escritor consulta este ledger y no repite lo ya VERIFICADO.

Vive en la BD de SICAV (PostgreSQL), NO en Oracle. No contiene PII en claro: los
identificadores de origen son PKs internas y el payload va redactado.
"""
from django.db import models


class PasoEscritura(models.TextChoices):
    """Pasos de la máquina de estados, en orden de dependencia."""
    HOGAR = "HOGAR", "Alta de hogar (GIC_INSERT_HOGAR1)"
    PERSONA = "PERSONA", "Alta de persona (GIC_INSERT_PERSONAS)"
    MIEMBRO = "MIEMBRO", "Vínculo miembro↔hogar (GIC_INSERT_MIEMBRO_HOGAR)"
    TERRITORIO = "TERRITORIO", "Cascada territorial (GIC_SP_*)"
    RESPUESTA = "RESPUESTA", "Respuesta de encuesta (SP_SET_RESPUESTAS_DE_ENCUESTA)"
    CAPITULO = "CAPITULO", "Capítulo finalizado (SP_FINALIZARCAPITULO)"
    # ⚠️ `SP_ACTUALIZAR_ESTADO_ENCUESTA`, NUNCA `CERRAR_ENCUESTA`: ese solo hace
    # `UPDATE ESTADO='CERRADA'` y deja el hogar marcado como cerrado con CERO
    # respuestas en la tabla definitiva. El que de verdad cierra es el otro.
    CIERRE = "CIERRE", "Cierre de encuesta (SP_ACTUALIZAR_ESTADO_ENCUESTA '4')"


class EstadoPaso(models.TextChoices):
    """
    Estados posibles de un paso. El estado crítico es EJECUTADO_SIN_VERIFICAR:
    como los procedures tragan sus errores, "llamé al procedure" NO implica "quedó
    escrito". Solo VERIFICADO (confirmado por SELECT posterior) permite avanzar.
    """
    PENDIENTE = "PENDIENTE", "Pendiente (aún no ejecutado)"
    # No es un fallo: es un dato cuyo destino en el legacy NO es esta tabla (un
    # subcampo "Otro, ¿cuál?" que viaja en el texto de su respuesta padre, la
    # identidad que va a GIC_PERSONA, un hecho que va a los validadores). Se
    # registra para que quede constancia de qué NO se escribió y por qué, en vez
    # de perder el hogar entero por ello.
    OMITIDO = "OMITIDO", "Omitido — su destino en el legacy es otro"
    DRY_RUN = "DRY_RUN", "Simulado (DRY-RUN, bloque PL/SQL registrado, sin ejecutar)"
    EJECUTADO_SIN_VERIFICAR = "EJECUTADO_SIN_VERIFICAR", "Procedure llamado, falta confirmar por consulta"
    VERIFICADO = "VERIFICADO", "Confirmado por SELECT en Oracle"
    FALLIDO = "FALLIDO", "La verificación por consulta NO encontró el resultado esperado"


class RegistroEscrituraOracle(models.Model):
    """
    Un paso de escritura hacia Oracle para una entidad SICAV. Auditable y reanudable.
    """
    # ── Origen (SICAV) ────────────────────────────────────────────────────────
    hogar = models.ForeignKey(
        "hogares.Hogar",
        on_delete=models.PROTECT,
        related_name="registros_escritura_oracle",
        help_text="Hogar SICAV que ancla toda la máquina de estados de esta caracterización.",
    )
    paso = models.CharField(max_length=20, choices=PasoEscritura.choices)
    # PK interna de la entidad de origen del paso (MiembroHogar.id para PERSONA/
    # MIEMBRO, RespuestaEncuesta.id para RESPUESTA, SesionEncuesta.id para
    # TERRITORIO/CIERRE, y el propio Hogar.id para HOGAR). Cadena para no atarlo a
    # un tipo de PK. Es el eje de la idempotencia junto con (hogar, paso).
    origen_id = models.CharField(
        max_length=64,
        help_text="PK interna SICAV de la entidad de este paso (no PII).",
    )

    # ── Destino (Oracle) ──────────────────────────────────────────────────────
    destino_hog_codigo = models.CharField(
        max_length=200, blank=True,
        help_text="HOG_CODIGO devuelto/confirmado en Oracle (no es PII).",
    )
    destino_per_idpersona = models.BigIntegerField(
        null=True, blank=True,
        help_text="PER_IDPERSONA (VALSECUENCIA) devuelto por GIC_INSERT_PERSONAS.",
    )

    # ── Estado de la máquina ──────────────────────────────────────────────────
    estado = models.CharField(
        max_length=24, choices=EstadoPaso.choices, default=EstadoPaso.PENDIENTE,
    )
    intento = models.PositiveIntegerField(default=0)

    # ── Evidencia / auditoría ─────────────────────────────────────────────────
    # Bloque PL/SQL EXACTO que se ejecutó (o se ejecutaría en DRY-RUN), con los
    # binds por NOMBRE. Los valores PII van redactados (ver oracle/procedimientos).
    bloque_plsql = models.TextField(blank=True)
    # Payload enviado, con PII redactada (nombres/documentos → hash o máscara).
    payload = models.JSONField(default=dict, blank=True)
    # Resultado de la verificación por consulta (qué SELECT se corrió y qué devolvió).
    resultado = models.JSONField(default=dict, blank=True)
    # Entorno destino real de la ejecución ('local' | 'produccion' | '' en DRY-RUN).
    destino_entorno = models.CharField(max_length=16, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de escritura a Oracle"
        verbose_name_plural = "Registros de escritura a Oracle"
        constraints = [
            # Idempotencia: un registro vigente por (hogar, paso, entidad origen)
            # Y POR DESTINO.
            #
            # `destino_entorno` entra en la clave a propósito (2026-07-28, antes del
            # primer piloto en producción). Sin él, escribir el mismo hogar en la
            # réplica local y luego en producción era imposible de representar: el
            # `update_or_create` del escritor pisaba el registro de local con el de
            # prod. Consecuencias: se perdía la traza de lo escrito en local y, al
            # re-correr contra local, el ledger ya no lo reconocía y volvía a
            # escribir — duplicando.
            #
            # Cada base lleva su propia contabilidad. Es lo que permite ensayar en
            # local y después migrar de verdad sin que una corrida contamine a la otra.
            models.UniqueConstraint(
                fields=["hogar", "paso", "origen_id", "destino_entorno"],
                name="uniq_registro_escritura_oracle_paso_origen_destino",
            ),
        ]
        indexes = [
            models.Index(fields=["hogar", "paso"]),
            models.Index(fields=["estado"]),
        ]
        ordering = ["hogar", "creado_en"]

    def __str__(self):
        return f"{self.hogar_id}/{self.paso}/{self.origen_id} → {self.estado}"

    @property
    def completado(self) -> bool:
        """Solo VERIFICADO cuenta como completado para avanzar la máquina."""
        return self.estado == EstadoPaso.VERIFICADO
