"""
Management command: cargar_puntos_atencion

Carga un conjunto MÍNIMO de Puntos de Atención por Dirección Territorial UARIV,
suficiente para que la UI cascada del mobile funcione end-to-end mientras UARIV
nos entrega el catálogo oficial completo.

Puntos cargados por DT:
  1. "JORNADAS DE ATENCIÓN Y/O FERIAS DE SERVICIO"  (presente en todas las DT)
  2. "CENTRO REGIONAL <nombre depto principal>"     (1 por DT con depto principal)

Para Esquema No Presencial:
  - "ATENCIÓN TELEFÓNICA"

Uso:
    python manage.py cargar_puntos_atencion

Idempotente: usa update_or_create por código de Punto.

IMPORTANTE: cuando UARIV entregue el dataset oficial de centros regionales por
DT (con direcciones físicas reales), reemplazar el contenido de este comando
o agregar un comando `cargar_puntos_atencion_oficiales.py` que lea desde CSV/Excel.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.parametricas.models import DireccionTerritorial, PuntoAtencion, Municipio


# Municipio capital donde se ubica el Centro Regional por DT
# (códigos DANE de las capitales departamentales correspondientes)
CENTRO_REGIONAL_POR_DT = {
    'DT_ANTIOQUIA':          ('05001', 'Centro Regional Medellín'),
    'DT_ATLANTICO':          ('08001', 'Centro Regional Barranquilla'),
    'DT_BOLIVAR':            ('13001', 'Centro Regional Cartagena'),
    'DT_CAQUETA_HUILA':      ('18001', 'Centro Regional Florencia'),
    'DT_CAUCA':              ('19001', 'Centro Regional Popayán'),
    'DT_CENTRAL':            ('11001', 'Centro Regional Bogotá'),
    'DT_CESAR_GUAJIRA':      ('20001', 'Centro Regional Valledupar'),
    'DT_CHOCO':              ('27001', 'Centro Regional Quibdó'),
    'DT_CORDOBA':            ('23001', 'Centro Regional Montería'),
    'DT_EJE_CAFETERO':       ('66001', 'Centro Regional Pereira'),
    'DT_MAGDALENA':          ('47001', 'Centro Regional Santa Marta'),
    'DT_MAGDALENA_MEDIO':    ('68081', 'Centro Regional Barrancabermeja'),
    'DT_META_LLANOS':        ('50001', 'Centro Regional Villavicencio'),
    'DT_NARINO':             ('52001', 'Centro Regional Pasto'),
    'DT_NORTE_SANT_ARAUCA':  ('54001', 'Centro Regional Cúcuta'),
    'DT_PUTUMAYO':           ('86001', 'Centro Regional Mocoa'),
    'DT_SANTANDER':          ('68001', 'Centro Regional Bucaramanga'),
    'DT_SUCRE':              ('70001', 'Centro Regional Sincelejo'),
    'DT_URABA':              ('05045', 'Centro Regional Apartadó'),
    'DT_VALLE':              ('76001', 'Centro Regional Cali'),
}


class Command(BaseCommand):
    help = 'Carga puntos de atención mínimos por DT (placeholder hasta dataset oficial UARIV).'

    @transaction.atomic
    def handle(self, *args, **options):
        creados = actualizados = 0
        municipios_faltantes = set()

        for dt in DireccionTerritorial.objects.all():
            # Resolver municipio donde colocar los puntos de esta DT
            cr_data = CENTRO_REGIONAL_POR_DT.get(dt.codigo)

            if cr_data is None:
                # Esquema No Presencial — usar Bogotá como sede administrativa
                municipio = Municipio.objects.filter(codigo_dane='11001').first()
                if municipio:
                    _, c = PuntoAtencion.objects.update_or_create(
                        codigo=f'{dt.codigo}__TELEFONICA',
                        defaults={
                            'nombre': 'ATENCIÓN TELEFÓNICA',
                            'direccion_territorial': dt,
                            'municipio': municipio,
                            'direccion_fisica': '',
                            'activo': True,
                        },
                    )
                    creados += int(c)
                    actualizados += int(not c)
                continue

            codigo_mun, nombre_cr = cr_data
            try:
                municipio = Municipio.objects.get(codigo_dane=codigo_mun)
            except Municipio.DoesNotExist:
                municipios_faltantes.add(codigo_mun)
                continue

            # 1) Punto "Jornadas / Ferias de servicio"
            _, c1 = PuntoAtencion.objects.update_or_create(
                codigo=f'{dt.codigo}__JORNADAS',
                defaults={
                    'nombre': 'JORNADAS DE ATENCIÓN Y/O FERIAS DE SERVICIO',
                    'direccion_territorial': dt,
                    'municipio': municipio,
                    'direccion_fisica': '',
                    'activo': True,
                },
            )
            creados += int(c1)
            actualizados += int(not c1)

            # 2) Centro Regional
            _, c2 = PuntoAtencion.objects.update_or_create(
                codigo=f'{dt.codigo}__CR',
                defaults={
                    'nombre': nombre_cr.upper(),
                    'direccion_territorial': dt,
                    'municipio': municipio,
                    'direccion_fisica': '',
                    'activo': True,
                },
            )
            creados += int(c2)
            actualizados += int(not c2)

        self.stdout.write(
            self.style.SUCCESS(f'Puntos de Atención: {creados} creados, {actualizados} actualizados.')
        )
        if municipios_faltantes:
            self.stdout.write(
                self.style.WARNING(
                    f'Municipios no encontrados (corre cargar_departamentos_municipios primero): '
                    f'{sorted(municipios_faltantes)}'
                )
            )
        self.stdout.write(
            self.style.WARNING(
                'PLACEHOLDER: este es un catálogo mínimo (2 puntos por DT). '
                'Reemplazar con dataset oficial UARIV cuando esté disponible.'
            )
        )
