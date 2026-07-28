"""
Management command: cargar_puntos_atencion_oracle

Reemplaza el catálogo PLACEHOLDER de puntos de atención por el **catálogo real de
Oracle** (pendiente 3a.11). Fuente: `apps/sincronizacion/oracle/catalogos_oracle.json`
→ `dt_puntos`, volcado de `GIC_N_DT_PUNTOS_ATENCION` en producción: **1.370 filas,
266 puntos**.

Por qué importa
--------------
`cargar_puntos_atencion` (el viejo) inventa 2 puntos por DT con nombres que Oracle NO
conoce ('Centro Regional Medellín', 'ATENCIÓN TELEFÓNICA'). El cruce a Oracle es **por
nombre** (`mapeo.resolver_territorio`), así que un hogar atendido en uno de esos puntos
NO resuelve su territorio: la cascada deja `GIC_N_RELACION_DT_PUNTO` incompleto y los
reportes territoriales de Vivanto pierden ese hogar — el bug histórico del proyecto.

Estructura del catálogo (medida, no supuesta)
---------------------------------------------
- 266 puntos, cada uno en **exactamente una DT y un departamento** (0 excepciones).
- 21 DT en Oracle = 21 en SICAV, **cruzan 21/21** por nombre normalizado.
- 227 de los 266 puntos atienden **un solo municipio** → ese es su sede física.
- Los 39 restantes son itinerantes ('JORNADAS DE ATENCIÓN Y/O FERIAS DE SERVICIO',
  hasta 123 municipios) → **no tienen sede**; se les asigna la capital de su
  departamento como sede indicativa.

La sede NO participa en el cruce a Oracle: `resolver_territorio` usa
`sesion.municipio_atencion`, no `punto.municipio` (verificado en mapeo.py). O sea que
una sede aproximada afecta a la UI, nunca al dato que se escribe.

Qué hace con el placeholder
---------------------------
Los puntos que Oracle no conoce se **desactivan** (`activo=False`), no se borran: la FK
es PROTECT y puede haber sesiones que los referencien. Así dejan de ofrecerse al
encuestador sin romper el histórico.

Uso:
    python manage.py cargar_puntos_atencion_oracle --dry-run   # ver qué haría
    python manage.py cargar_puntos_atencion_oracle

Idempotente: `update_or_create` por código `ORACLE_PA_<idpuntoatencion>`.
"""
import collections

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.parametricas.models import (
    DireccionTerritorial, Departamento, Municipio, PuntoAtencion,
)
from apps.sincronizacion.oracle import catalogos

PREFIJO = "ORACLE_PA_"


def _norm_depto(nombre):
    """
    Nombre de departamento comparable entre SICAV y Oracle.

    Se normaliza aparte porque la única divergencia real entre los 33 departamentos de
    ambos lados es una COMA: SICAV dice 'Archipiélago de San Andrés, Providencia y
    Santa Catalina' y Oracle 'ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA'.
    Sin esto se caían los 2 puntos de San Andrés — y ese es un perfil activo del
    proyecto (instrumento SAN_ANDRES).

    NO se arregla tocando `catalogos.normalizar_nombre`: ese normalizador es la
    autoridad del cruce de OPCIONES de respuesta, donde la coma sí es semántica
    ('Otro, ¿cuál?'). Aquí el plegado extra es local y solo aplica a departamentos.
    """
    return " ".join(catalogos.normalizar_nombre(nombre).replace(",", " ").split())


class Command(BaseCommand):
    help = ("Carga los 266 puntos de atención REALES de Oracle (3a.11) y desactiva "
            "los placeholder que Oracle no conoce.")

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Informa sin escribir nada en la base.")

    @transaction.atomic
    def handle(self, *args, **opts):
        seco = opts["dry_run"]
        filas = self._filas_oracle()
        dts = self._indice_dt()
        municipios = self._indice_municipios()

        puntos = collections.defaultdict(list)
        for fila in filas:
            puntos[fila["idpuntoatencion"]].append(fila)

        creados = actualizados = 0
        sin_dt, sin_sede, itinerantes = [], [], 0
        vigentes = set()

        for id_punto, grupo in sorted(puntos.items(), key=lambda kv: int(kv[0])):
            cabeza = grupo[0]
            dt = dts.get(catalogos.normalizar_nombre(cabeza["dt"]))
            if dt is None:
                sin_dt.append((id_punto, cabeza["dt"]))
                continue

            sede, itinerante = self._sede(grupo, municipios)
            if sede is None:
                sin_sede.append((id_punto, cabeza["punto"], cabeza["departamento"]))
                continue
            itinerantes += int(itinerante)

            codigo = f"{PREFIJO}{id_punto}"
            vigentes.add(codigo)
            if seco:
                continue
            _, creado = PuntoAtencion.objects.update_or_create(
                codigo=codigo,
                defaults={
                    # El nombre debe ser el de Oracle LITERAL: es la clave del cruce.
                    "nombre": cabeza["punto"],
                    "direccion_territorial": dt,
                    "municipio": sede,
                    "direccion_fisica": "",
                    "activo": True,
                },
            )
            creados += int(creado)
            actualizados += int(not creado)

        obsoletos = PuntoAtencion.objects.exclude(codigo__startswith=PREFIJO).filter(activo=True)
        n_obsoletos = obsoletos.count()
        if not seco:
            obsoletos.update(activo=False)

        # ── informe ──────────────────────────────────────────────────────────
        marca = "[DRY-RUN] " if seco else ""
        self.stdout.write(self.style.SUCCESS(
            f"{marca}Puntos de atención de Oracle: {len(vigentes)} vigentes "
            f"({creados} creados, {actualizados} actualizados)."
        ))
        self.stdout.write(
            f"  {len(vigentes) - itinerantes} con sede propia · {itinerantes} itinerantes "
            f"(sede = capital del departamento)"
        )
        self.stdout.write(self.style.WARNING(
            f"  {n_obsoletos} punto(s) placeholder desactivado(s) — Oracle no los conoce, "
            f"y un hogar atendido ahí no resolvería su territorio."
        ))
        for etiqueta, lista in (("sin DT en SICAV", sin_dt), ("sin municipio sede", sin_sede)):
            if lista:
                self.stdout.write(self.style.ERROR(
                    f"  ⚠ {len(lista)} punto(s) {etiqueta} — NO cargados: {lista[:5]}"
                ))
        if seco:
            self.stdout.write(self.style.NOTICE("  (dry-run: no se escribió nada)"))

    # ── piezas ───────────────────────────────────────────────────────────────
    def _filas_oracle(self):
        filas = catalogos.cargar_dt_puntos()
        if not filas:
            raise CommandError(
                "El crosswalk de puntos (catalogos_oracle.json → dt_puntos) está vacío."
            )
        return filas

    def _indice_dt(self):
        dts = {catalogos.normalizar_nombre(d.nombre): d
               for d in DireccionTerritorial.objects.all()}
        if not dts:
            raise CommandError(
                "No hay Direcciones Territoriales cargadas. Corre primero:\n"
                "    python manage.py cargar_direcciones_territoriales"
            )
        return dts

    def _indice_municipios(self):
        """
        {(depto_norm, muni_norm): Municipio} + {depto_norm: capital}.

        Se indexa por PAR departamento+municipio a propósito: hay nombres de municipio
        repetidos entre departamentos (La Unión, Albania…), y cruzar solo por nombre
        asignaría sedes de otro departamento.
        """
        if not Municipio.objects.exists():
            raise CommandError(
                "No hay municipios cargados. Corre primero:\n"
                "    python manage.py cargar_departamentos_municipios --csv=data/municipios_dane.csv"
            )
        por_par, capitales = {}, {}
        for m in Municipio.objects.select_related("departamento"):
            depto = _norm_depto(m.departamento.nombre)
            por_par[(depto, catalogos.normalizar_nombre(m.nombre))] = m
            # Capital DANE = código del departamento + '001'.
            if m.codigo_dane == f"{m.departamento.codigo_dane}001":
                capitales[depto] = m
        return {"pares": por_par, "capitales": capitales}

    def _sede(self, grupo, municipios):
        """(Municipio, es_itinerante). El punto de un solo municipio tiene sede propia."""
        depto = _norm_depto(grupo[0]["departamento"])
        if len(grupo) == 1:
            sede = municipios["pares"].get(
                (depto, catalogos.normalizar_nombre(grupo[0]["municipio"])))
            if sede is not None:
                return sede, False
            # El municipio de Oracle no existe en la DIVIPOLA de SICAV (localidades de
            # Bogotá, corregimientos departamentales…): cae a la capital, como itinerante.
        return municipios["capitales"].get(depto), True
