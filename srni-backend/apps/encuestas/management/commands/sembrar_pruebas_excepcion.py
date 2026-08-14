"""
Deja listo el escenario para probar las DOS rutas de caracterización.

    python manage.py sembrar_pruebas_excepcion

Nace de una pregunta concreta del 14-ago-2026: «¿tenemos los usuarios de prueba
para hacer las dos validaciones — ruta normal y ruta de edición?». La respuesta
tenía que ser reproducible en cualquier entorno y no un puñado de filas creadas a
mano en una base, que es lo que después nadie sabe si sigue ahí.

Deja montado:

    RUTA NORMAL          9990000003 · CARLOS PRUEBA
                         Sin caracterización previa. Se caracteriza de una,
                         sin autorizar nada.

    RUTA DE EDICIÓN      9990000001 · ANA PRUEBA   (autorizada del hogar)
                         9990000002 · MARIA PRUEBA (miembro del mismo hogar)
                         Hogar conformado y encuesta COMPLETADA, con ficha
                         vigente hasta 2028. Bloqueadas hasta que coordinación
                         autorice la excepción desde /autorizaciones/.

    USUARIOS             QACOORD  · autoriza excepciones (no caracteriza en campo)
                         QAENC    · encuestador, es quien usa la APK
                         clave de ambos: SrniTest2026!

Es **idempotente**: correrlo dos veces no duplica nada ni pisa lo que ya existe
en la base. No toca ningún dato real — todos los documentos empiezan por 999,
que es la convención de datos de prueba del proyecto.

⚠️ NO crea la excepción autorizada: eso es justamente lo que se va a probar a
mano desde la pantalla. Si ya existe una vigente de una corrida anterior, se
informa para que no sorprenda ver a la persona habilitada de entrada.
"""
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

CLAVE = 'SrniTest2026!'
FICHA_VIGENTE = datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc)
FECHA_NACIMIENTO = '1990-05-20'


class Command(BaseCommand):
    help = 'Siembra el escenario de prueba de las rutas normal y de excepción.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clave', default=CLAVE,
            help='Contraseña de los usuarios de prueba (default: la del script).')

    @transaction.atomic
    def handle(self, *args, **opciones):
        from apps.autenticacion.models import Perfil, Usuario
        from apps.encuestas.models import ExcepcionVigencia, SesionEncuesta
        from apps.formulario.models import Instrumento
        from apps.hogares.models import Hogar, MiembroHogar
        from apps.parametricas.models import Departamento, Municipio, TipoDocumento
        from apps.victimas.models import Victima
        from apps.victimas.repository.base import doc_hash

        clave = opciones['clave']

        tipo, _ = TipoDocumento.objects.get_or_create(
            codigo='CC', defaults={'nombre': 'Cédula de ciudadanía'})
        depto, _ = Departamento.objects.get_or_create(
            codigo_dane='11', defaults={'nombre': 'Bogotá D.C.'})
        muni, _ = Municipio.objects.get_or_create(
            codigo_dane='11001',
            defaults={'nombre': 'Bogotá D.C.', 'departamento': depto})

        # ── Usuarios ────────────────────────────────────────────────────────
        #
        # Dos perfiles y no uno: el sentido del cambio del 14-ago es que quien
        # autoriza no sea quien ejecuta. Probarlo con un solo usuario que pueda
        # todo no probaría nada.
        perfil_coord, _ = Perfil.objects.get_or_create(
            codigo='QA_COORDINACION',
            defaults={'nombre': 'QA — Coordinación'})
        perfil_coord.puede_buscar_rni = True
        perfil_coord.puede_caracterizar = False
        perfil_coord.puede_ver_reportes = True
        perfil_coord.puede_autorizar_excepciones = True
        perfil_coord.activo = True
        perfil_coord.save()

        perfil_enc, _ = Perfil.objects.get_or_create(
            codigo='QA_ENCUESTADOR',
            defaults={'nombre': 'QA — Encuestador de campo'})
        perfil_enc.puede_buscar_rni = True
        perfil_enc.puede_caracterizar = True
        perfil_enc.puede_ver_reportes = False
        perfil_enc.puede_autorizar_excepciones = False
        perfil_enc.activo = True
        perfil_enc.save()

        coord = self._usuario('QACOORD', 'Coordinación de pruebas',
                              perfil_coord, clave, Usuario)
        enc = self._usuario('QAENC', 'Encuestadora de pruebas',
                            perfil_enc, clave, Usuario)

        # ── Personas ────────────────────────────────────────────────────────
        def victima(doc, nombre, apellido, *, con_ficha):
            obj, _ = Victima.objects.update_or_create(
                numero_documento_hash=doc_hash('CC', doc),
                defaults=dict(
                    tipo_documento=tipo, numero_documento=doc,
                    primer_nombre=nombre, primer_apellido=apellido,
                    # Texto: la fecha de nacimiento es un campo cifrado y el
                    # cifrado trabaja sobre la cadena, no sobre un `date`.
                    fecha_nacimiento=FECHA_NACIMIENTO,
                    genero='F', estado_ruv='INCLUIDO',
                    pertenencia_etnica='NINGUNA', discapacidad=False,
                    municipio_residencia=muni,
                    # La vigencia es lo único que separa los dos casos: con
                    # fecha reciente queda bloqueada; sin fecha, habilitada.
                    fecha_ult_caracterizacion=FICHA_VIGENTE if con_ficha else None,
                    habilitado_para_caracterizacion=not con_ficha,
                ))
            return obj

        ana = victima('9990000001', 'ANA', 'PRUEBA', con_ficha=True)
        maria = victima('9990000002', 'MARIA', 'PRUEBA', con_ficha=True)
        carlos = victima('9990000003', 'CARLOS', 'PRUEBA', con_ficha=False)

        # ── El hogar ya caracterizado (caso de edición) ──────────────────────
        hogar = Hogar.objects.filter(autorizado=ana).first()
        if hogar is None:
            hogar = Hogar.objects.create(
                autorizado=ana, municipio=muni, creado_por=enc,
                numero_personas=2)

        for v, parentesco, es_aut in [(ana, '', True), (maria, 'HIJO', False)]:
            # Solo el vínculo y el rol: los datos personales del miembro salen
            # de la FK a `victima`, no se copian acá.
            MiembroHogar.objects.get_or_create(
                hogar=hogar, victima=v,
                defaults=dict(
                    tipo_documento=tipo, parentesco=parentesco,
                    genero=v.genero, es_autorizado=es_aut,
                    rol='MIEMBRO'))

        instrumento = (Instrumento.objects.filter(activo=True).first()
                       or Instrumento.objects.first())
        sesion = None
        if instrumento is not None:
            sesion = SesionEncuesta.objects.filter(hogar=hogar).first()
            if sesion is None:
                sesion = SesionEncuesta.objects.create(
                    hogar=hogar, instrumento=instrumento, encuestador=enc,
                    ruta_entrevista='GENERAL', estado='COMPLETADA',
                    fecha_fin=timezone.now(), porcentaje_completado=100)

        vigentes = ExcepcionVigencia.objects.filter(
            victima__in=[ana, maria], estado=ExcepcionVigencia.VIGENTE).count()

        # ── Resumen ─────────────────────────────────────────────────────────
        w = self.stdout.write
        ok = self.style.SUCCESS
        w('')
        w(ok('Escenario de prueba listo.'))
        w('')
        w('  USUARIOS (clave: %s)' % clave)
        w('    QACOORD   autoriza excepciones · NO caracteriza · %s' % coord.codigo_usuario)
        w('    QAENC     encuestador de campo (APK)            · %s' % enc.codigo_usuario)
        w('')
        w('  RUTA NORMAL — se caracteriza sin autorizar nada')
        w('    CC 9990000003  CARLOS PRUEBA   sin ficha previa, habilitado')
        w('')
        w('  RUTA DE EDICIÓN — bloqueadas hasta autorizar la excepción')
        w('    CC 9990000001  ANA PRUEBA      autorizada del hogar')
        w('    CC 9990000002  MARIA PRUEBA    miembro del hogar')
        w('    hogar %s · encuesta %s' % (
            hogar.id,
            'COMPLETADA' if sesion else 'SIN SESIÓN (no hay instrumento cargado)'))
        w('    ficha vigente hasta 14/03/2028')
        w('')
        if vigentes:
            w(self.style.WARNING(
                '  ⚠ Ya hay %d excepción(es) VIGENTE(s) de una corrida anterior: '
                'esas personas van a aparecer habilitadas de entrada. Anúlelas '
                'desde la pantalla si quiere probar el bloqueo desde cero.'
                % vigentes))
            w('')
        if instrumento is None:
            w(self.style.WARNING(
                '  ⚠ No hay instrumentos cargados: el hogar quedó sin encuesta '
                'completada. Cargue uno con `cargar_perfil` y vuelva a correr esto.'))
            w('')
        w('  Autorizar en:  /autorizaciones/   (o /api/autorizaciones/)')
        w('')

    @staticmethod
    def _usuario(codigo, nombre, perfil, clave, Usuario):
        """Crea o actualiza sin pisar a un usuario real que se llame igual."""
        u = Usuario.objects.filter(codigo_usuario=codigo).first()
        if u is None:
            return Usuario.objects.create_user(
                codigo_usuario=codigo, password=clave, nombre_completo=nombre,
                email=f'{codigo.lower()}@srni.dev', perfil=perfil, activo=True)
        u.perfil = perfil
        u.activo = True
        u.set_password(clave)
        u.save()
        return u
