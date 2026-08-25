"""
Recalcula `porcentaje_completado` de las sesiones YA guardadas.

Por qué existe (APK-005). El arreglo de la skip-logic en `recalcular_porcentaje`
solo aplica hacia adelante: el porcentaje se reescribe al responder, al guardar
en bloque y al finalizar, y los tres cortan si la sesión ya está COMPLETADA. Las
sesiones que QA fotografió en 0 % se quedan en 0 % para siempre a menos que se
las recalcule a mano. Este comando hace exactamente eso, sobre todas las
sesiones (COMPLETADA incluida).

Diseño para producción:
  · Por lotes (--batch), no todo en memoria: hay muchas sesiones.
  · Idempotente: recalcula el valor real; correrlo dos veces da lo mismo.
  · Solo escribe lo que cambió, y solo el campo `porcentaje_completado`.
  · --dry-run para medir el impacto antes de tocar nada (imprime cuántas
    cambiarían y algunos ejemplos), que es lo que hay que hacer ANTES de que
    salga un reporte de avance a la UARIV: el promedio del panel va a moverse.

Uso en el servidor (VPN inestable → del lado del servidor, no por SSH directo):
    setsid nohup python manage.py backfill_porcentaje \\
        > /tmp/backfill_pct.log 2>&1 &
    tail -f /tmp/backfill_pct.log

Medir primero, sin escribir:
    python manage.py backfill_porcentaje --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.encuestas.models import SesionEncuesta


class Command(BaseCommand):
    help = 'Recalcula porcentaje_completado de las sesiones existentes (APK-005).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch', type=int, default=500,
            help='Tamaño del lote (por defecto 500).')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='No escribe: solo informa cuántas cambiarían y ejemplos.')
        parser.add_argument(
            '--estado', default='',
            help='Limitar a un estado (INICIADA, EN_PROGRESO, COMPLETADA, '
                 'SUSPENDIDA). Vacío = todas.')

    def handle(self, *args, **opts):
        batch = opts['batch']
        dry = opts['dry_run']
        estado = (opts['estado'] or '').strip().upper()

        qs = SesionEncuesta.objects.all()
        if estado:
            qs = qs.filter(estado=estado)
        # select_related del hogar: recalcular_porcentaje lo usa para los
        # miembros; sin esto sería una consulta extra por sesión.
        qs = qs.select_related('hogar', 'instrumento').order_by('id')

        total = qs.count()
        self.stdout.write(
            f'Sesiones a revisar: {total}'
            + (f' (estado={estado})' if estado else '')
            + (' [DRY-RUN, no escribe]' if dry else ''))

        revisadas = 0
        cambiadas = 0
        ejemplos = []

        # Iteración por lotes por rango de id: estable aunque se escriba en medio.
        ultimo_id = 0
        while True:
            lote = list(qs.filter(id__gt=ultimo_id)[:batch])
            if not lote:
                break
            ultimo_id = lote[-1].id

            porcambiar = []
            for sesion in lote:
                revisadas += 1
                try:
                    nuevo = sesion.recalcular_porcentaje()
                except Exception as exc:  # noqa: BLE001 — no abortar todo por una
                    self.stderr.write(
                        f'  ! sesión {sesion.id}: error al recalcular: {exc}')
                    continue
                if nuevo != sesion.porcentaje_completado:
                    if len(ejemplos) < 10:
                        ejemplos.append(
                            (sesion.id, sesion.estado,
                             sesion.porcentaje_completado, nuevo))
                    sesion.porcentaje_completado = nuevo
                    porcambiar.append(sesion)

            cambiadas += len(porcambiar)
            if porcambiar and not dry:
                with transaction.atomic():
                    SesionEncuesta.objects.bulk_update(
                        porcambiar, ['porcentaje_completado'])

            self.stdout.write(
                f'  ... {revisadas}/{total} revisadas, '
                f'{cambiadas} {"cambiarían" if dry else "actualizadas"}')

        self.stdout.write('')
        if ejemplos:
            self.stdout.write('Ejemplos (id · estado · antes% → después%):')
            for sid, est, antes, desp in ejemplos:
                self.stdout.write(f'  · {sid} · {est} · {antes}% → {desp}%')
        verbo = 'cambiarían' if dry else 'actualizadas'
        self.stdout.write(self.style.SUCCESS(
            f'Listo. {cambiadas} de {revisadas} sesiones {verbo}.'))
        if dry and cambiadas:
            self.stdout.write(
                'Para aplicarlo, corré el comando sin --dry-run.')
