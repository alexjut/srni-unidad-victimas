"""
Management command: purgar_padron

Borra las personas que entraron por una **carga masiva** del Oracle legacy, para
poder recargar el padrón desde cero. Es lo que hay que correr antes de
`cargar_padron_oracle --carga-inicial` cuando cambia el criterio de la carga.

Qué NO borra
------------
Todo lo que **no vino de una carga masiva** se preserva, por diseño y no por
cuidado del operador:

* **altas manuales** (`creado_por` no nulo) — alguien las creó en campo porque no
  estaban en el padrón, y es justamente el caso de la cuarta parte de víctimas
  incluidas que la .9 no tiene;
* **personas con membresía de hogar** — están enlazadas a una caracterización real;
* **autorizados de un hogar** — son el titular de la entrevista; borrarlos rompe
  el hogar entero;
* **personas con hechos victimizantes** cargados.

Borrar una de esas no es "recargar el padrón": es perder trabajo de campo. Por eso
la protección va aquí adentro y no en la línea de comandos.

Por qué existe este comando y no un DELETE a mano
--------------------------------------------------
Un `DELETE` suelto por SSH no deja rastro, no protege nada y no se puede probar.
Este deja registro en `CargaPadron`, tiene DRY-RUN y tiene tests.

Uso
---
    python manage.py purgar_padron                 # DRY-RUN: dice qué haría
    python manage.py purgar_padron --confirmar     # borra de verdad
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone


class Command(BaseCommand):
    help = ("Borra las personas cargadas masivamente del padrón, preservando altas "
            "manuales y personas con caracterización. DRY-RUN por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Borra de verdad. Sin él, solo informa.")

    def handle(self, *args, **opts):
        from apps.victimas.models import CargaPadron, Victima

        confirmar = opts["confirmar"]
        total = Victima.objects.count()
        if not total:
            self.stdout.write("El padrón ya está vacío. No hay nada que purgar.")
            return

        protegidas = self._protegidas(Victima)
        a_borrar = total - len(protegidas)

        self.stdout.write(self.style.WARNING(
            f"\n{'BORRADO REAL' if confirmar else 'DRY-RUN (no borra)'}\n"
            f"  en el padrón hoy : {total:,}\n"
            f"  se preservan     : {len(protegidas):,}\n"
            f"  se borrarían     : {a_borrar:,}\n"))

        for victima in Victima.objects.filter(id__in=protegidas)[:20]:
            razon = ("alta manual" if victima.creado_por_id
                     else "enlazada a caracterización")
            self.stdout.write(
                f"    preservada · {victima.numero_documento} "
                f"{victima.primer_nombre} {victima.primer_apellido} ({razon})")
        if len(protegidas) > 20:
            self.stdout.write(f"    … y {len(protegidas) - 20:,} más")

        if not confirmar:
            self.stdout.write(self.style.NOTICE(
                "\n  DRY-RUN: no se borró nada. Agregá --confirmar para ejecutarlo."))
            return

        inicio = time.monotonic()
        registro = CargaPadron.objects.create(
            origen="purga previa a recarga", estado="EN_CURSO")
        try:
            borradas = self._borrar(protegidas)
        except Exception as exc:                                   # noqa: BLE001
            registro.estado = "FALLIDA"
            registro.detalle = f"{type(exc).__name__}: {exc}"[:1900]
            registro.terminada_en = timezone.now()
            registro.save()
            raise CommandError(f"La purga falló: {exc}")

        registro.estado = "COMPLETADA"
        registro.descartadas = borradas
        registro.detalle = (f"Purga: {borradas:,} borradas, "
                            f"{len(protegidas):,} preservadas")
        registro.terminada_en = timezone.now()
        registro.save()

        self.stdout.write(self.style.SUCCESS(
            f"\nBorradas {borradas:,} personas en {time.monotonic() - inicio:.0f}s"))
        self.stdout.write(f"  quedan {Victima.objects.count():,} (las preservadas)")
        self.stdout.write(self.style.NOTICE(
            "  SIGUIENTE PASO: `cargar_padron_oracle --carga-inicial --confirmar`"))

    # ── piezas ───────────────────────────────────────────────────────────────
    @staticmethod
    def _protegidas(Victima):
        """
        Ids que NO se borran: los de alta manual y los que tengan **cualquier**
        relación entrante desde otra tabla.

        Las relaciones se recorren con `_meta.related_objects` en vez de listarlas a
        mano, así que una tabla nueva que apunte a `Victima` queda protegida sola. Es
        lo contrario de una lista que hay que acordarse de actualizar.

        Se pregunta **desde la tabla hija**, no desde `Victima`: un
        `Victima.objects.exclude(membresias_hogar=None)` se traduce a un `NOT IN`
        sobre los 3,5 M del padrón y no termina nunca —medido: >10 min sin responder—
        mientras que preguntarle a la tabla hija, que tiene unas pocas filas, es
        instantáneo.
        """
        protegidas = set(
            Victima.objects.exclude(creado_por=None).values_list("id", flat=True))
        for rel in Victima._meta.related_objects:
            campo = rel.field.name
            protegidas |= set(
                rel.related_model.objects.exclude(**{campo: None})
                .values_list(campo, flat=True))
        protegidas.discard(None)
        return protegidas

    @staticmethod
    def _borrar(protegidas):
        """`_raw_delete` en vez de `.delete()`: este último trae los millones de
        objetos a memoria para poder disparar señales y resolver cascadas. Aquí no
        hay señales que disparar —y las cascadas están cubiertas, porque lo que
        tiene relaciones es justamente lo que se protege— así que se borra en la
        base de un solo DELETE.

        Tampoco se arma el SQL a mano: la llave es un UUID y cada motor lo bindea
        distinto (SQLite lo rechaza, Postgres pide cast). Django lo resuelve."""
        from apps.victimas.models import ColisionDocumento, Victima

        with transaction.atomic():
            # `ColisionDocumento` apunta a `Victima` con `related_name='+'`, que la
            # vuelve invisible para `_protegidas` (Django excluye las relaciones
            # ocultas de `related_objects`), y `_raw_delete` no ejecuta el
            # `on_delete=SET_NULL`. Sin esto, la purga aborta por violación de
            # llave foránea.
            #
            # Se vacía en vez de protegerse a propósito: proteger las ~700 mil
            # filas preferidas dejaría media base en pie y anularía la purga. Es un
            # derivado recalculable —se reconstruye con `clasificar_colisiones`—,
            # así que no se pierde nada que no se pueda volver a producir.
            ColisionDocumento.objects.all().delete()
            objetivo = Victima.objects.exclude(id__in=protegidas)
            return objetivo._raw_delete(objetivo.db)
