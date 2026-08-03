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
    # De GIC_N_VALIDADORESXPERSONA salen el ESTADO_RUV y los
    # HECHO_VICTIMIZANTE_1..14 de los reportes y de la constancia. Sin estos tres
    # pasos el hogar llega al legacy con esas columnas VACÍAS.
    #
    # Van ANTES de RESPUESTA y no es un detalle de estilo: cada respuesta dispara
    # `SP_INS_ETNIA_ARES`, que deriva los marcadores étnicos del hogar (5007-5012)
    # y el de desplazamiento (506) leyendo los validadores que YA estén escritos —
    # y no hace nada si el hogar todavía no tiene un 5001/5002/5003.
    VALIDADOR = "VALIDADOR", "Validadores de la persona (GIC_INSERT_VALIDADOR_HOGAR + _PARENT)"
    HECHO = "HECHO", "Hecho victimizante (GIC_INSERT_VALIDADOR_HECHO_AUX)"
    ENCUESTADO = "ENCUESTADO", "Marca de encuestado (GIC_ACTUALIZA_ENCUESTADO)"
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


class UsuarioLegacy(models.Model):
    """
    Un encuestador del legacy (`GIC_USUARIO`), traído a SICAV.

    ─── Para qué, más allá de "tener el nombre" ──────────────────────────────
    Tres cosas, y la tercera es la que obliga:

    1. **Atribución.** `GIC_HOGAR.USU_USUARIOCREACION` es una cadena suelta. Sin
       este catálogo, un hogar del legacy dice "lo capturó JGUARINH" y no hay
       forma de saber quién es, ni a quién enrutarle una novedad del territorio.

    2. **Diagnóstico.** "Mis encuestas" se arma con un `INNER JOIN GIC_USUARIO`
       (`SP_REPORTE_MIEMBROSXCODIGO`, `src_GIC_N_CARACTERIZACION.sql:2451`). Un
       hogar cuyo creador no tiene fila ahí **desaparece del listado** aunque esté
       cerrado y archivado. Teniendo el catálogo de este lado, esa causa se
       detecta sin abrir Oracle.

    3. **Un `USU_IDUSUARIO` por encuestador, en vez del usuario de servicio
       compartido.** Es la razón fuerte. `GIC_INSERT_HOGAR1` solo crea un hogar si
       el usuario **no tiene ninguno en ACTIVA**; si lo tiene, no crea nada y
       devuelve el código del viejo. Con un único usuario de servicio para todo
       SICAV, basta que **un** hogar quede abierto para que el siguiente —de otro
       encuestador, de otro municipio— se le meta adentro. No es un riesgo
       teórico: es el mismo mecanismo que ya produce fusiones en el legacy.

    ─── Lo que este catálogo NO puede arreglar ───────────────────────────────
    La autoría del histórico ya está rota y traerla no la repara: medido en
    producción, **1.077.712 hogares (97,7 %)** tienen un `USU_USUARIOCREACION`
    que no existe en `GIC_USUARIO` —9.424 cadenas distintas contra ~8.100
    usuarios— y el `USU_IDUSUARIO` no cruza en el 99,7 %. Este modelo permite
    *medir* ese hueco y no ampliarlo; cerrarlo hacia atrás es otra discusión.

    ─── Datos personales ─────────────────────────────────────────────────────
    Son funcionarios, no víctimas, y aquí no se aplica el cifrado del padrón
    —igual que `autenticacion.Usuario`, que guarda nombre y correo en claro—.
    Aun así se trae **lo mínimo que sirve**: se dejan fuera `USU_CONTRASENA` y
    `USU_TOKEN` (credenciales, que no tenemos por qué replicar) y los campos de
    bloqueo. El documento sí se trae: cuando el login del legacy y el de SICAV no
    coinciden, es lo único que permite reconocer a la misma persona.
    """
    #: `USU_IDUSUARIO`. Es la PK acá también: es el valor que viaja en
    #: `GIC_HOGAR.USU_IDUSUARIO` y el que hay que poder resolver.
    usu_idusuario = models.BigIntegerField(primary_key=True)
    #: `USU_USUARIO` — el login ('JGUARINH'). Es lo que compara el INNER JOIN de
    #: "mis encuestas", así que es la llave real para el diagnóstico.
    usu_usuario = models.CharField(max_length=100, db_index=True)

    nombre_completo = models.CharField(max_length=200, blank=True)
    documento = models.CharField(max_length=30, blank=True, db_index=True)
    correo = models.EmailField(blank=True)

    ent_identidad = models.BigIntegerField(
        null=True, blank=True, help_text="ENT_IDENTIDAD — entidad a la que pertenece.")
    est_idestado = models.BigIntegerField(
        null=True, blank=True, help_text="EST_IDESTADO — estado en el legacy.")
    codigo = models.CharField(max_length=50, blank=True, help_text="USU_CODIGO.")
    dado_de_baja = models.BooleanField(
        default=False,
        help_text="USU_DADODEBAJA — un usuario de baja sigue siendo el autor de "
                  "sus hogares, así que se conserva.")
    #: `ID_USUARIOVIVANTO` — el puente con las identidades de Vivanto. Es el
    #: campo que permitiría cruzar sin depender de que el login coincida.
    id_usuario_vivanto = models.BigIntegerField(null=True, blank=True, db_index=True)
    creado_en_legacy = models.DateTimeField(null=True, blank=True)

    #: Enlace con el usuario de SICAV, cuando se pudo reconocer a la misma
    #: persona. Nullable a propósito: la mayoría de los 8.000 del legacy no tiene
    #: cuenta en SICAV, y forzar el enlace inventaría correspondencias.
    usuario_sicav = models.OneToOneField(
        "autenticacion.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="usuario_legacy",
    )

    importado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usuario del legacy"
        verbose_name_plural = "Usuarios del legacy"
        ordering = ["usu_usuario"]

    def __str__(self):
        return f"{self.usu_usuario} ({self.usu_idusuario})"


class CaracterizacionLegacy(models.Model):
    """
    Una caracterización hecha en el legacy, traída para que su autor la vea.

    ─── El objetivo, en una frase ────────────────────────────────────────────
    Que un encuestador entre a SICAV y vea **lo que ya hizo**, aunque lo haya
    hecho en la aplicación vieja. Hoy su trabajo vive en una base a la que no
    tiene acceso y en un listado que —como se comprobó— puede no mostrárselo.

    ─── La decisión de diseño que importa ────────────────────────────────────
    El vínculo con el autor es la **cadena** `USU_USUARIOCREACION`, NO el
    catálogo `GIC_USUARIO`.

    Parece un detalle y es lo contrario. Medido en producción: **1.077.712
    hogares (97,7 %)** tienen un `USU_USUARIOCREACION` que no existe en
    `GIC_USUARIO`, y el `USU_IDUSUARIO` no cruza en el 99,7 %. `JGUARINH` —el
    del caso de Pandi— es uno de ellos: 18 caracterizaciones y ninguna fila de
    usuario. Cruzar por el catálogo, que es lo que hace el legacy con su INNER
    JOIN, perdería el 97 % del trabajo hecho. Justo lo contrario de lo que se
    busca acá.

    Por eso `usuario_creador` es una cadena y no una FK, y `usuario_legacy` —que
    sí apunta al catálogo— es opcional y solo enriquece (nombre, correo, id de
    Vivanto) cuando por casualidad la fila existe.

    ─── Qué NO es ────────────────────────────────────────────────────────────
    No es una copia de la caracterización: no trae respuestas ni personas, y por
    lo tanto **no trae PII**. Es el recibo — qué se capturó, cuándo, en qué
    estado quedó y si los reportes lo ven. Para el detalle está el legacy.
    """
    hog_codigo = models.CharField(max_length=200, primary_key=True)

    #: El autor, tal como quedó escrito en `GIC_HOGAR.USU_USUARIOCREACION`. Es la
    #: llave real: se compara con `Usuario.codigo_usuario` de SICAV.
    usuario_creador = models.CharField(max_length=100, db_index=True)
    usu_idusuario = models.BigIntegerField(null=True, blank=True, db_index=True)
    #: Enriquecimiento opcional. Nulo en el 97,7 % de los casos, y no pasa nada.
    usuario_legacy = models.ForeignKey(
        UsuarioLegacy, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="caracterizaciones",
    )

    estado = models.CharField(max_length=40, db_index=True)
    creado_en_legacy = models.DateTimeField(null=True, blank=True, db_index=True)
    fecha_estado = models.DateTimeField(null=True, blank=True)

    miembros = models.PositiveIntegerField(default=0)
    respuestas_definitivas = models.PositiveIntegerField(default=0)
    respuestas_trabajo = models.PositiveIntegerField(default=0)
    capitulos = models.PositiveIntegerField(default=0)

    #: El veredicto de `oracle.diagnostico.dictaminar`. Se guarda calculado para
    #: que la pantalla del encuestador no tenga que abrir Oracle para pintarse.
    veredicto = models.CharField(max_length=32, blank=True, db_index=True)
    #: Si los reportes de la UARIV ven esta caracterización. Es lo que convierte
    #: el listado en algo accionable: no basta con decir "la hiciste", hay que
    #: poder decir "y no está contando".
    visible_en_reportes = models.BooleanField(default=False, db_index=True)

    sincronizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Caracterización del legacy"
        verbose_name_plural = "Caracterizaciones del legacy"
        ordering = ["-creado_en_legacy"]
        indexes = [models.Index(fields=["usuario_creador", "-creado_en_legacy"])]

    def __str__(self):
        return f"{self.hog_codigo} ({self.estado})"
