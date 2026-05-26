"""
Management command: cargar_direcciones_territoriales

Carga las 21 Direcciones Territoriales UARIV + su mapeo M2M a Departamentos DANE.

Fuente: estructura organizacional pública UARIV
(https://www.unidadvictimas.gov.co/es/territoriales).

Uso:
    python manage.py cargar_direcciones_territoriales

Idempotente: usa update_or_create por código de DT.

Notas:
    - "Magdalena Medio" y "Urabá" son sub-regiones territoriales — no cubren
      un departamento completo, sino municipios específicos. Aquí se mapean
      a los departamentos que tocan. La asignación municipal fina se hace
      a nivel de PuntoAtencion (cuando se cargue ese catálogo oficial).
    - "Central" cubre Cundinamarca, Bogotá y Tolima.
    - "Esquema No Presencial" es una opción especial para sesiones remotas
      (sin punto físico). Se carga sin departamentos asociados.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.parametricas.models import DireccionTerritorial, Departamento


# (codigo, nombre, [códigos_dane_departamento])
DIRECCIONES_TERRITORIALES = [
    ('DT_ANTIOQUIA',          'DIRECCION TERRITORIAL ANTIOQUIA',          ['05']),
    ('DT_ATLANTICO',          'DIRECCION TERRITORIAL ATLANTICO',          ['08']),
    ('DT_BOLIVAR',            'DIRECCION TERRITORIAL BOLIVAR',            ['13']),
    ('DT_CAQUETA_HUILA',      'DIRECCION TERRITORIAL CAQUETA Y HUILA',    ['18', '41']),
    ('DT_CAUCA',              'DIRECCION TERRITORIAL CAUCA',              ['19']),
    ('DT_CENTRAL',            'DIRECCION TERRITORIAL CENTRAL',            ['11', '25', '73']),
    ('DT_CESAR_GUAJIRA',      'DIRECCION TERRITORIAL CESAR Y GUAJIRA',    ['20', '44']),
    ('DT_CHOCO',              'DIRECCION TERRITORIAL CHOCO',              ['27']),
    ('DT_CORDOBA',            'DIRECCION TERRITORIAL CORDOBA',            ['23']),
    ('DT_EJE_CAFETERO',       'DIRECCION TERRITORIAL EJE CAFETERO',       ['17', '63', '66']),
    ('DT_MAGDALENA',          'DIRECCION TERRITORIAL MAGDALENA',          ['47']),
    ('DT_MAGDALENA_MEDIO',    'DIRECCION TERRITORIAL MAGDALENA MEDIO',    ['05', '15', '68']),
    ('DT_META_LLANOS',        'DIRECCION TERRITORIAL META Y LLANOS ORIENTALES',
                                                                          ['50', '85', '94', '95', '99']),
    ('DT_NARINO',             'DIRECCION TERRITORIAL NARIÑO',             ['52']),
    ('DT_NORTE_SANT_ARAUCA',  'DIRECCION TERRITORIAL NORTE DE SANTANDER Y ARAUCA',
                                                                          ['54', '81']),
    ('DT_PUTUMAYO',           'DIRECCION TERRITORIAL PUTUMAYO',           ['86', '91']),
    ('DT_SANTANDER',          'DIRECCION TERRITORIAL SANTANDER',          ['68']),
    ('DT_SUCRE',              'DIRECCION TERRITORIAL SUCRE',              ['70']),
    ('DT_URABA',              'DIRECCION TERRITORIAL URABA',              ['05', '27']),
    ('DT_VALLE',              'DIRECCION TERRITORIAL VALLE',              ['76']),
    ('DT_NO_PRESENCIAL',      'ESQUEMA NO PRESENCIAL',                    []),
]


class Command(BaseCommand):
    help = 'Carga las 21 Direcciones Territoriales UARIV + mapeo a Departamentos DANE.'

    @transaction.atomic
    def handle(self, *args, **options):
        creadas = actualizadas = 0
        deptos_faltantes = set()

        for codigo, nombre, codigos_depto in DIRECCIONES_TERRITORIALES:
            dt, created = DireccionTerritorial.objects.update_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'activo': True},
            )
            if created:
                creadas += 1
            else:
                actualizadas += 1

            deptos = []
            for cod in codigos_depto:
                try:
                    deptos.append(Departamento.objects.get(codigo_dane=cod))
                except Departamento.DoesNotExist:
                    deptos_faltantes.add(cod)
            dt.departamentos.set(deptos)

        self.stdout.write(
            self.style.SUCCESS(
                f'Direcciones Territoriales: {creadas} creadas, {actualizadas} actualizadas.'
            )
        )
        if deptos_faltantes:
            self.stdout.write(
                self.style.WARNING(
                    f'Departamentos no encontrados (corre cargar_departamentos_municipios primero): '
                    f'{sorted(deptos_faltantes)}'
                )
            )
