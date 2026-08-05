"""
Carga el UNIVERSO de víctimas desde `FUENTES.TEMP_UNIV_VICT_PER_MI<DDMMAA>ALL`.

─── Por qué existe ──────────────────────────────────────────────────────────
El padrón se armaba desde `GIC_PERSONA ⨝ M_CARACT_TABLA_RA_PER`, o sea desde el
**registro de quién ya fue caracterizado**. Preguntarle a eso "¿existe esta
víctima?" es preguntarle al libro de visitas quién vive en la ciudad: una persona
que nunca pasó por una entrevista era invisible para SICAV.

Caso real que lo destapó — `28548486`: no está en `GIC_PERSONA` (0 filas), sí
está en el universo (`CONS_PERSONA` 23988216, 3 hechos). En Vivanto la dejaban
caracterizar y en SICAV "no existía".

─── 🔴 El id del universo NO es `cons_persona` ──────────────────────────────
Medido el 5-ago-2026 sobre **243.610 pares con el mismo documento: CERO
coincidencias** entre `CONS_PERSONA` (universo) y `PER_IDPERSONA` (legacy).

    1115724047 → universo    CONS_PERSONA  = 23664117
    1115724047 → GIC_PERSONA PER_IDPERSONA = 958858 / 6566478 / 9184606

`Victima.cons_persona` es lo que `oracle/mapeo.py` escribe al legacy. Este
comando **nunca lo toca**: el id del universo va a `cons_persona_universo`, y el
enlace con `Victima` se resuelve **por hash de documento**.

─── Dos fases, y no una ─────────────────────────────────────────────────────
1. **Cargar** las ~12,5 M filas del corte, sin deduplicar.
2. **Resolver** los documentos repetidos con una consulta sobre la base ya
   cargada, marcando `es_preferida` y registrando por qué perdieron las otras.

Deduplicar durante la carga obligaría a mantener 12 M de hashes en memoria (~800
MB) o a pedirle `ORDER BY documento` a Oracle, que sobre una tabla de este tamaño
ya está medido en 12 h. Las dos fases cuestan minutos y **no pierden ninguna
fila**: las no preferidas se conservan, marcadas.
"""

import datetime
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.victimas import homologacion as H
from apps.victimas.repository.base import doc_hash, normalizar_doc, num_hash

#: Días de antigüedad tolerados antes de gritar. El antecedente es
#: `GIC_REPORTE_HOGAR`, congelado desde 2021 sin que nadie lo notara.
DIAS_ALERTA_CORTE = 45

#: Cuántos cortes hacia atrás se buscan si el del mes en curso no existe.
MESES_FALLBACK = 6

PLANTILLA = "TEMP_UNIV_VICT_PER_MI{ddmmaa}ALL"
_RE_CORTE = re.compile(r"TEMP_UNIV_VICT_PER_MI(\d{2})(\d{2})(\d{2})ALL$")

CONSULTA = """
    SELECT CONS_PERSONA, TIPO_DOC, DOCUMENTO,
           NOMBRE1, NOMBRE2, APELLIDO1, APELLIDO2,
           GENERO_HOM, PERT_ETNICA, DISCAP, TIPO_DISCAP, CICLO_VITAL,
           NUM_HECHOS
      FROM FUENTES.{tabla}@CONSULTAFUENTES
"""

#: Reglas de desempate cuando varias filas del corte comparten documento.
#: Todas terminan en `cons_persona_universo` para que el resultado sea
#: DETERMINISTA: sin ese último criterio, dos corridas podrían elegir filas
#: distintas y el padrón cambiaría solo.
DESEMPATES = {
    "completitud": "-_completitud, -num_hechos, cons_persona_universo",
    "hechos":      "-num_hechos, -_completitud, cons_persona_universo",
    "menor-id":    "cons_persona_universo",
}


def fecha_de_corte(nombre: str):
    """`TEMP_UNIV_VICT_PER_MI010726ALL` → date(2026, 7, 1). None si no matchea."""
    m = _RE_CORTE.search(nombre or "")
    if not m:
        return None
    dia, mes, anio = (int(g) for g in m.groups())
    try:
        return datetime.date(2000 + anio, mes, dia)
    except ValueError:
        return None


def nombre_de_corte(fecha: datetime.date) -> str:
    return PLANTILLA.format(ddmmaa=f"01{fecha.month:02d}{fecha.year % 100:02d}")


def _mes_anterior(fecha: datetime.date) -> datetime.date:
    return (fecha.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)


class Command(BaseCommand):
    help = ("Carga el universo de víctimas del corte mensual. DRY-RUN por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Escribe de verdad. Sin él, solo informa.")
        parser.add_argument("--corte", default="",
                            help="Nombre exacto de la tabla. Sin esto se resuelve "
                                 "por fecha, con fallback a meses anteriores.")
        parser.add_argument("--limite", type=int, default=0,
                            help="Procesa solo N filas (para probar).")
        parser.add_argument("--lote", type=int, default=5000,
                            help="Filas por fetch y por bulk_create (default 5000).")
        parser.add_argument("--desempate", default="completitud",
                            choices=sorted(DESEMPATES),
                            help="Regla para elegir la fila preferida cuando varias "
                                 "comparten documento (default: completitud).")
        parser.add_argument("--sin-documento", action="store_true",
                            help="Carga también las filas sin documento usable. Por "
                                 "defecto se descartan: son 487.473 y sin una vía de "
                                 "búsqueda alterna son volumen sin función.")
        parser.add_argument("--solo-resolver", action="store_true",
                            help="Salta la carga y solo resuelve duplicados de un "
                                 "corte ya cargado.")

    # ── entrada ──────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        confirmar = opts["confirmar"]
        conexion = self._abrir()
        try:
            corte = (opts["corte"] or "").strip() or self._resolver_corte(conexion)
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\nUniverso de víctimas — corte {corte}"))
            self.stdout.write(f"  origen : {conexion['dsn']}")
            self._avisar_antiguedad(corte)

            if not opts["solo_resolver"]:
                self._cargar(conexion, corte, opts, confirmar)
        finally:
            conexion["con"].close()

        self._resolver_duplicados(corte, opts["desempate"], confirmar)
        self._enlazar_con_padron(corte, confirmar)

        if not confirmar:
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN: no se escribió nada. Repetí con --confirmar."))

    # ── resolución del corte ────────────────────────────────────────────────
    def _resolver_corte(self, conexion) -> str:
        """
        El nombre NO se embebe en el código: se arma por fecha y se verifica que
        exista. Si el corte del mes todavía no está, se cae al anterior y **se
        dice** — medido el 5-ago-2026, el corte de agosto no existía y el más
        reciente era el de julio.
        """
        cur = conexion["con"].cursor()
        fecha = datetime.date.today().replace(day=1)
        for intento in range(MESES_FALLBACK):
            nombre = nombre_de_corte(fecha)
            cur.execute(
                "select count(*) from all_tables@CONSULTAFUENTES "
                "where owner='FUENTES' and table_name = :t", {"t": nombre})
            if cur.fetchone()[0]:
                if intento:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠ el corte del mes en curso no existe; se usa {nombre} "
                        f"({intento} mes(es) atrás)"))
                return nombre
            fecha = _mes_anterior(fecha)
        raise CommandError(
            f"No se encontró ningún corte en los últimos {MESES_FALLBACK} meses. "
            f"¿Cambió el nombre de la tabla, o dejaron de generarla?")

    def _avisar_antiguedad(self, corte: str) -> None:
        fecha = fecha_de_corte(corte)
        if fecha is None:
            self.stdout.write(self.style.WARNING(
                f"  ⚠ no se pudo deducir la fecha de {corte!r}: no se puede "
                f"controlar su antigüedad"))
            return
        dias = (datetime.date.today() - fecha).days
        self.stdout.write(f"  corte  : {fecha:%Y-%m-%d} ({dias} días)")
        if dias > DIAS_ALERTA_CORTE:
            self.stdout.write(self.style.ERROR(
                f"  🔴 el corte tiene {dias} días (umbral {DIAS_ALERTA_CORTE}). "
                f"La generación es mensual: si se atrasó, alguien tiene que saberlo."))

    # ── fase 1: cargar ──────────────────────────────────────────────────────
    def _cargar(self, conexion, corte, opts, confirmar) -> None:
        from apps.victimas.models import DescarteUniverso, PersonaUniverso

        fecha_corte = fecha_de_corte(corte)
        lote, limite = opts["lote"], opts["limite"]
        con_sin_doc = opts["sin_documento"]

        if confirmar and PersonaUniverso.objects.filter(corte=corte).exists():
            raise CommandError(
                f"El corte {corte} ya está cargado. Para rehacerlo, borrá primero "
                f"sus filas; así dos cortes pueden convivir sin pisarse.")

        cur = conexion["con"].cursor()
        cur.arraysize = lote
        cur.execute(CONSULTA.format(tabla=corte))

        cont = {"leidas": 0, "cargadas": 0, "sin_documento": 0, "sin_id": 0}
        acumulador, descartes = [], []
        # Vocabularios que la fuente trae y SICAV no reconoce. Se juntan para
        # avisarlos al final: `homologar_genero` devuelve ND ante lo desconocido
        # —correcto, nunca inventa— pero si el RUV agrega un valor mañana, sin
        # esto se lo traga en silencio.
        generos_nuevos = set()

        while True:
            filas = cur.fetchmany(lote)
            if not filas:
                break
            for fila in filas:
                cont["leidas"] += 1
                if not H.genero_es_conocido(fila[7]):
                    generos_nuevos.add(str(fila[7]))
                registro = self._a_registro(fila, corte, fecha_corte)
                if registro is None:
                    cont["sin_id"] += 1
                    descartes.append(DescarteUniverso(
                        corte=corte, motivo="SIN_CONS_PERSONA"))
                    continue
                if not registro.numero_documento_hash_sin_tipo and not con_sin_doc:
                    cont["sin_documento"] += 1
                    descartes.append(DescarteUniverso(
                        corte=corte,
                        cons_persona_universo=registro.cons_persona_universo,
                        motivo="SIN_DOCUMENTO",
                        detalle="DOCUMENTO ausente o de menos de 5 caracteres"))
                    continue
                acumulador.append(registro)
                cont["cargadas"] += 1

            # El vaciado va SIEMPRE, también en DRY-RUN. Si solo se vaciara al
            # escribir, un ensayo sin `--limite` acumularía los 12,5 M de objetos
            # en memoria y moriría por OOM — justo la corrida que se hace para
            # NO arriesgar nada.
            if len(acumulador) >= lote:
                self._volcar(PersonaUniverso, acumulador, confirmar)
            if len(descartes) >= lote:
                self._volcar(DescarteUniverso, descartes, confirmar)
            if cont["leidas"] % (lote * 20) == 0:
                self.stdout.write(f"  {cont['leidas']:>10,} leídas · "
                                  f"{cont['cargadas']:>10,} cargadas")
            if limite and cont["leidas"] >= limite:
                break

        self._volcar(PersonaUniverso, acumulador, confirmar)
        self._volcar(DescarteUniverso, descartes, confirmar)

        # `ignore_conflicts` hace que un choque contra la unicidad por corte se
        # pierda SIN excepción, así que el contador de arriba puede estar
        # mintiendo. Se compara contra la base y se avisa: un descarte silencioso
        # es indistinguible de una fuente incompleta.
        if confirmar:
            reales = PersonaUniverso.objects.filter(corte=corte).count()
            if reales != cont["cargadas"]:
                self.stdout.write(self.style.ERROR(
                    f"  🔴 se contaron {cont['cargadas']:,} cargadas pero la base "
                    f"tiene {reales:,}: {cont['cargadas'] - reales:,} chocaron "
                    f"contra la unicidad por corte y se perdieron sin aviso. "
                    f"Revisar si CONS_PERSONA se repite en el origen."))

        self.stdout.write(self.style.SUCCESS(
            f"\n  leídas          : {cont['leidas']:,}\n"
            f"  cargadas        : {cont['cargadas']:,}\n"
            f"  sin documento   : {cont['sin_documento']:,}"
            f"{'  (cargadas igual)' if con_sin_doc else '  (descartadas)'}\n"
            f"  sin id de fuente: {cont['sin_id']:,}"))

        if generos_nuevos:
            self.stdout.write(self.style.ERROR(
                f"  🔴 GENERO_HOM con valores que SICAV no reconoce: "
                f"{', '.join(sorted(generos_nuevos))}\n"
                f"     Se guardan crudos y homologan a ND. Hay que decidir su "
                f"equivalencia en apps/victimas/homologacion.py antes de que el "
                f"universo alimente altas de víctimas."))

    def _a_registro(self, fila, corte, fecha_corte):
        from apps.victimas.models import PersonaUniverso

        (cons, tipo_doc, documento, n1, n2, a1, a2,
         genero, etnia, discap, tipo_discap, ciclo, num_hechos) = fila
        if cons is None:
            return None

        documento = (documento or "").strip()
        tipo_doc = (tipo_doc or "").strip().upper()
        # El umbral se mide sobre el documento YA NORMALIZADO, que es lo que se
        # hashea. Medirlo sobre el crudo dejaba pasar '1.2.3' —cinco caracteres
        # con separadores— que al normalizar queda en '123' y no identifica a
        # nadie: exactamente lo que el umbral quiere evitar.
        usable = len(normalizar_doc("", documento).split("|", 1)[-1]) >= 5

        return PersonaUniverso(
            cons_persona_universo=int(cons),
            tipo_documento=tipo_doc,
            numero_documento=documento,
            numero_documento_hash=doc_hash(tipo_doc, documento) if (usable and tipo_doc) else "",
            numero_documento_hash_sin_tipo=num_hash(documento) if usable else "",
            primer_nombre=(n1 or "").strip(),
            segundo_nombre=(n2 or "").strip(),
            primer_apellido=(a1 or "").strip(),
            segundo_apellido=(a2 or "").strip(),
            genero=(genero or "").strip()[:20],
            pertenencia_etnica=(etnia or "").strip()[:60],
            # La canónica, no `bool()`: es type-agnostic y trata NULL como
            # 'no consta'. Tener dos homologaciones de lo mismo en el repo es
            # el defecto que ya costó una tarde con los hechos victimizantes.
            discapacidad=H.homologar_discapacidad(discap),
            tipo_discapacidad=str(tipo_discap or "").strip()[:20],
            ciclo_vital=(ciclo or "").strip()[:20],
            num_hechos=int(num_hechos) if num_hechos is not None else None,
            corte=corte,
            fecha_corte=fecha_corte,
        )

    @staticmethod
    def _volcar(modelo, acumulador, confirmar):
        """Vacía el acumulador SIEMPRE; escribe solo si `confirmar`."""
        if acumulador and confirmar:
            modelo.objects.bulk_create(acumulador, batch_size=1000,
                                       ignore_conflicts=True)
        acumulador.clear()

    # ── fase 2: resolver documentos repetidos ───────────────────────────────
    def _resolver_duplicados(self, corte, regla, confirmar) -> None:
        """
        Marca una fila preferida por documento y deja el resto en `False`, con su
        motivo en `DescarteUniverso`.

        **No borra nada.** Una fila que pierde el desempate sigue siendo un dato
        real de la fuente; borrarla haría imposible responder después por qué esa
        persona no aparece.
        """
        from django.db.models import Count

        from apps.victimas.models import DescarteUniverso, PersonaUniverso

        base = (PersonaUniverso.objects
                .filter(corte=corte)
                .exclude(numero_documento_hash_sin_tipo=""))
        repetidos = (base.values("numero_documento_hash_sin_tipo")
                         .annotate(n=Count("id")).filter(n__gt=1))

        total_grupos = repetidos.count()
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nDocumentos compartidos por más de una fila: {total_grupos:,}"))
        if not total_grupos:
            return

        orden = self._orden_de(regla)
        perdedoras, descartes = [], []
        for grupo in repetidos.iterator(chunk_size=1000):
            filas = list(base.filter(
                numero_documento_hash_sin_tipo=grupo["numero_documento_hash_sin_tipo"]))
            filas.sort(key=orden)
            for fila in filas[1:]:
                perdedoras.append(fila.pk)
                descartes.append(DescarteUniverso(
                    corte=corte,
                    cons_persona_universo=fila.cons_persona_universo,
                    numero_documento_hash_sin_tipo=fila.numero_documento_hash_sin_tipo,
                    motivo="DOCUMENTO_REPETIDO",
                    detalle=f"ganó {filas[0].cons_persona_universo} por «{regla}»"))

        self.stdout.write(f"  filas que no quedan como preferidas: {len(perdedoras):,}")
        if confirmar and perdedoras:
            with transaction.atomic():
                # 1) Reset a True antes de marcar. La fase es TOTAL, no
                #    incremental: sin esto, volver a resolver con otra regla
                #    acumula los `False` de la corrida anterior y un grupo puede
                #    quedar SIN NINGUNA preferida — esa persona desaparecería del
                #    enlace y de toda derivación posterior, que es exactamente el
                #    caso que este módulo vino a arreglar.
                PersonaUniverso.objects.filter(corte=corte).update(es_preferida=True)
                PersonaUniverso.objects.filter(pk__in=perdedoras).update(es_preferida=False)
                # 2) Y los descartes de esta fase se reemplazan, no se suman:
                #    la tabla existe para responder "cuántas personas faltan", y
                #    después de dos corridas respondía el doble.
                DescarteUniverso.objects.filter(
                    corte=corte, motivo="DOCUMENTO_REPETIDO").delete()
                DescarteUniverso.objects.bulk_create(descartes, batch_size=1000)
            self.stdout.write(self.style.SUCCESS("  marcadas y registradas."))

    @staticmethod
    def _orden_de(regla):
        """Clave de orden. La preferida es la PRIMERA tras ordenar."""
        def completitud(p):
            return sum(1 for c in (p.primer_nombre, p.segundo_nombre, p.primer_apellido,
                                   p.segundo_apellido, p.genero, p.pertenencia_etnica,
                                   p.ciclo_vital, p.tipo_documento) if c)

        if regla == "menor-id":
            return lambda p: (p.cons_persona_universo,)
        if regla == "hechos":
            return lambda p: (-(p.num_hechos or 0), -completitud(p),
                              p.cons_persona_universo)
        return lambda p: (-completitud(p), -(p.num_hechos or 0),
                          p.cons_persona_universo)

    # ── enlace con el padrón operativo ──────────────────────────────────────
    def _enlazar_con_padron(self, corte, confirmar) -> None:
        """
        Une cada fila del universo con su `Victima`, **por hash de documento**.

        Por id sería inútil: `CONS_PERSONA` y `cons_persona` son numeraciones
        distintas (0 coincidencias en 243.610 pares medidos).
        """
        from apps.victimas.models import PersonaUniverso, Victima

        pendientes = (PersonaUniverso.objects
                      .filter(corte=corte, es_preferida=True, victima__isnull=True)
                      .exclude(numero_documento_hash_sin_tipo=""))
        total = pendientes.count()
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nEnlazando con el padrón operativo ({total:,} sin enlazar)"))
        if not total:
            return

        from apps.victimas.models import DescarteUniverso

        enlazadas = ambiguas = 0
        for chunk in self._por_lotes(pendientes, 2000):
            hashes = {p.numero_documento_hash_sin_tipo for p in chunk}

            # Un hash puede resolver a VARIAS víctimas: el campo está indexado
            # pero no es único, y en el padrón hay documentos compartidos por
            # cientos de filas (medido: hasta 505 de la misma persona). Sin
            # orden, gana "la última que devuelva Postgres" — no determinista, y
            # en los grupos que son personas DISTINTAS enlazaría con otra.
            candidatas = {}
            for v in (Victima.objects
                      .filter(numero_documento_hash_sin_tipo__in=hashes)
                      .only("id", "numero_documento_hash_sin_tipo")
                      .order_by("numero_documento_hash_sin_tipo", "id")):
                candidatas.setdefault(v.numero_documento_hash_sin_tipo, []).append(v)

            actualizar, descartes = [], []
            for p in chunk:
                opciones = candidatas.get(p.numero_documento_hash_sin_tipo, [])
                if len(opciones) == 1:
                    p.victima = opciones[0]
                    actualizar.append(p)
                elif len(opciones) > 1:
                    # Más de una candidata: NO se elige. Inventar una
                    # correspondencia es peor que no tenerla — el mismo criterio
                    # que ya aplica `ColisionDocumento.victima_preferida=NULL`
                    # para los documentos ambiguos.
                    ambiguas += 1
                    descartes.append(DescarteUniverso(
                        corte=corte,
                        cons_persona_universo=p.cons_persona_universo,
                        numero_documento_hash_sin_tipo=p.numero_documento_hash_sin_tipo,
                        motivo="ENLACE_AMBIGUO",
                        detalle=f"{len(opciones)} víctimas comparten ese documento"))
            if confirmar and actualizar:
                PersonaUniverso.objects.bulk_update(actualizar, ["victima"],
                                                    batch_size=1000)
            if confirmar and descartes:
                DescarteUniverso.objects.bulk_create(descartes, batch_size=1000)
            enlazadas += len(actualizar)

        self.stdout.write(
            f"  enlazadas          : {enlazadas:,}\n"
            f"  ambiguas (sin enlazar): {ambiguas:,}  "
            f"(el documento resuelve a más de una víctima: no se elige)\n"
            f"  solo en el universo: {total - enlazadas - ambiguas:,}  "
            f"(personas que SICAV no tenía — el hueco que esto viene a cubrir)")

    @staticmethod
    def _por_lotes(qs, tam):
        buffer = []
        for obj in qs.iterator(chunk_size=tam):
            buffer.append(obj)
            if len(buffer) >= tam:
                yield buffer
                buffer = []
        if buffer:
            yield buffer

    # ── conexión ────────────────────────────────────────────────────────────
    def _abrir(self):
        from apps.sincronizacion.oracle import conexion as cx
        try:
            cfg = cx.resolver_config(cx.DESTINO_PRODUCCION)
        except cx.DestinoNoConfigurado as exc:
            raise CommandError(
                f"{exc}\nExportá ORACLE_PROD_HOST/SERVICE/USER/PASSWORD antes de correr.")
        return {"con": cx.abrir_conexion(cx.DESTINO_PRODUCCION),
                "dsn": f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['service']}"}
