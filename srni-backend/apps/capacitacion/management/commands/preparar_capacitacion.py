"""
Management command: preparar_capacitacion

Deja listas las **cuentas** y los **datos de práctica** de las tres jornadas de
capacitación de SICAV (15, 24 y 29 de septiembre de 2026).

──────────────────────────────────────────────────────────────────────────────
POR QUÉ ES UN COMANDO Y NO UN PUÑADO DE FILAS CREADAS A MANO
──────────────────────────────────────────────────────────────────────────────
Son 37 personas en tres fechas distintas, y entre una jornada y la siguiente
alguien va a pedir «vuélvanlo a dejar como estaba». Un escenario creado a mano
en la base no se puede volver a dejar como estaba: nadie sabe qué había. Este
comando es **idempotente** —correrlo dos veces deja lo mismo— y es la única
definición de qué cuentas existen para la capacitación y sobre qué personas se
practica.

Es la misma lección de `sembrar_pruebas_excepcion`, del que hereda la
convención: **todo documento de práctica empieza por 999**. Lo que empieza por
999 no es una víctima real y se puede borrar sin pensarlo.

──────────────────────────────────────────────────────────────────────────────
QUÉ CREA
──────────────────────────────────────────────────────────────────────────────
**Cuentas.** Una por participante, con perfil `COORDINADOR`. Es el único perfil
que cubre la jornada entera: caracteriza en la aplicación (Bloque A, los tres
casos) y ve supervisión, reportes, auditoría y **recaracterizaciones** (Bloque B).
Con `ENCUESTADOR` el Bloque B se les ve a medias.

Desde el 11-sep-2026 la razón cambió pero la conclusión no: antes hacía falta
`autorizar_excepciones` para el Caso 2 y ahora hace falta `ver_reportes` para
llegar al punto de control, que es donde el Caso 2 termina. `COORDINADOR` tiene
los dos.

El `codigo_usuario` sigue la convención del sistema —iniciales de los nombres +
primer apellido + inicial del segundo—, la misma con la que se generaron las
1.158 encuestadoras (`KLMUÑOZM` ← Karen Liliana Muñoz Mora). No se inventa un
esquema paralelo tipo `CAP01`: el participante debe entrar el 15 con el mismo
código con el que va a entrar en campo.

**Personas de práctica.** Cinco por participante, numeradas con su índice, de
modo que dos participantes nunca se pisen el hogar:

    999NN00001  ficha vigente  → CASO 2, la que se recaracteriza sin permiso
    999NN00002  ficha vigente  → CASO 2, el integrante que se RETIRA del hogar
    999NN00003  sin ficha      → CASO 1, la señora que recibe
    999NN00004  sin ficha      → CASO 1, hijo de 14 años
    999NN00005  sin ficha      → CASO 1, madre de 71 años
    999NN00009  NO SE CREA     → CASO 3, el señor que no aparece

El `999NN00009` **no existe a propósito**: el caso 3 es justamente la persona
que no aparece en la búsqueda y hay que dar de alta. Crearlo arruinaría el caso.

**El hogar ya caracterizado.** Para que el caso 2 sea real, la persona `…0001`
tiene que tener de verdad una caracterización vigente y una familia ya
registrada, no un letrero que lo diga. Se le crea hogar, dos miembros y una
sesión COMPLETADA, y se le fecha la última caracterización **ocho meses atrás**,
que es el enunciado literal del caso.

Ese escenario sirve igual antes y después del 11-sep-2026, y por eso no se tocó:
lo que cambió es qué se hace con él. Antes se autorizaba una excepción; ahora se
continúa sin pedir permiso, se comprueba que la familia aparezca sin recapturarla,
y se retira al integrante `…0002` con la fecha del hecho.

──────────────────────────────────────────────────────────────────────────────
LO QUE NO HACE
──────────────────────────────────────────────────────────────────────────────
**No crea excepciones de vigencia, y con el control retirado ya no se pueden
crear**: el servidor rechaza el POST porque otorgar un permiso que no habilita
nada es peor que no tener la pantalla. Si quedó alguna VIGENTE de una corrida
anterior lo sigue avisando, pero ya no estorba al caso: hoy la persona aparece
habilitada de todos modos.

**No deja a nadie retirado del hogar.** El retiro se practica a mano, y el banco
de pruebas (`scripts/qa/probar_casos_uso_capacitacion.py`) reincorpora al
terminar. Si al preparar una jornada `…0002` aparece retirado de la anterior,
hay que reincorporarlo o el participante no tendrá a quién retirar.

**No toca ninguna víctima real.** Todo lo que escribe empieza por 999.

Uso:
    python manage.py preparar_capacitacion                    # DRY-RUN
    python manage.py preparar_capacitacion --confirmar
    python manage.py preparar_capacitacion --confirmar --sesion 1
    python manage.py preparar_capacitacion --confirmar --conservar-claves
    python manage.py preparar_capacitacion --confirmar --salida /tmp/cred.csv
"""
from __future__ import annotations

import csv
import secrets
import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

#: Perfil de los participantes. Ver el encabezado: es el único que cubre los dos
#: bloques del temario y el caso 2 completo.
PERFIL = 'COORDINADOR'

#: Alfabeto de las claves. Sin `l`, `I`, `O`, `0` ni `1`: la clave se dicta en
#: voz alta en una sala y se teclea en un celular, y esos cinco caracteres son
#: los que se confunden. Perder 5 símbolos de 62 no cambia nada frente a un
#: ataque; que 37 personas puedan entrar a la primera, sí.
ALFABETO_CLAVE = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'

#: Ocho meses atrás, que es el enunciado literal del Caso 2 del Anexo C. La
#: vigencia es de dos años, así que ocho meses la deja bloqueada con holgura:
#: no queda a merced de la fecha en que se corra esto.
MESES_FICHA_VIGENTE = 8

#: (sesión, dirección territorial, nombre completo, ciudad, correo)
#: Tomado del Plan de Capacitación, secciones 6, 7 y 8, actualizado el 8-sep-2026.
ROSTER = [
    # ── Sesión 1 · martes 15 de septiembre · Equipo SRNI (híbrida) ──────────
    (1, 'Red Nacional de Información', 'Alexandra María López Sevillano', 'Bogotá', 'alexandram.lopez@unidadvictimas.gov.co'),
    (1, 'Red Nacional de Información', 'Javier Alexander Aguilar Castro', 'Bogotá', 'javier.aguilarc@unidadvictimas.gov.co'),
    (1, 'Red Nacional de Información', 'Brandon Esteven Niño Quiroga', 'Bogotá', 'brandon.nino@unidadvictimas.gov.co'),
    (1, 'Red Nacional de Información', 'Jorge Cardona Gregory', 'Bogotá', 'jorge.cardona@unidadvictimas.gov.co'),
    (1, 'Red Nacional de Información', 'Karen Liseth Serna González', 'Bogotá', 'karen.serna@unidadvictimas.gov.co'),
    (1, 'Red Nacional de Información', 'Nixon Alonso Duarte Acosta', 'Bogotá', 'nixon.duarte@unidadvictimas.gov.co'),
    (1, 'Red Nacional de Información', 'María Elena Silva Fandiño', 'Bogotá', 'mariaele.silva@unidadvictimas.gov.co'),

    # ── Sesión 2 · jueves 24 de septiembre · Grupo A (virtual) ──────────────
    (2, 'Antioquia', 'Eliana María Ocampo Atehortúa', 'Medellín', 'eliana.ocampo@unidadvictimas.gov.co'),
    (2, 'Urabá', 'Juan Carlos Vizcaino Sierra', 'Apartadó', 'juan.vizcaino@unidadvictimas.gov.co'),
    (2, 'Atlántico', 'Luz Marina Devia Barrios', 'Barranquilla', 'luz.devia@unidadvictimas.gov.co'),
    (2, 'Bolívar', 'Hernando Zúñiga Herazo', 'Cartagena', 'hernando.zuniga@unidadvictimas.gov.co'),
    (2, 'Córdoba', 'Jorge Luis Suarez Hernandez', 'Montería', 'jorgeluis.suarez@unidadvictimas.gov.co'),
    (2, 'Sucre', 'Sergio Andrés Osorio Herrera', 'Sincelejo', 'sergio.osorio@unidadvictimas.gov.co'),
    (2, 'Magdalena', 'Yomara Gómez Sánchez', 'Santa Marta', 'yomara.gomez@unidadvictimas.gov.co'),
    (2, 'Cesar - Guajira', 'Jorge Orlando Sandoval Millan', 'Valledupar', 'jorge.sandoval@unidadvictimas.gov.co'),
    (2, 'Cesar - Guajira', 'Norlys Patricia Aristizabal Vanegas', 'Valledupar', 'norlys.aristizabal@unidadvictimas.gov.co'),
    (2, 'Chocó', 'Flor Yuleydis Cordoba Mena', 'Quibdó', 'flor.cordoba@unidadvictimas.gov.co'),
    (2, 'Magdalena Medio', 'Andrea Paola Chinchilla Lopez', 'Barrancabermeja', 'andrea.chinchilla@unidadvictimas.gov.co'),
    (2, 'Santander', 'German Darío Corzo Patiño', 'Bucaramanga', 'german.corzo@unidadvictimas.gov.co'),
    (2, 'Santander', 'Johao Antonio Pinzon Pelayo', 'Bucaramanga', 'johao.pinzon@unidadvictimas.gov.co'),
    (2, 'N. de Santander - Arauca', 'Ricardo José Santos Rodríguez', 'Arauca', 'ricardo.santos@unidadvictimas.gov.co'),
    (2, 'N. de Santander - Arauca', 'Luis Fernando Lizcano Quintero', 'Cúcuta', 'luis.lizcano@unidadvictimas.gov.co'),
    (2, 'N. de Santander - Arauca', 'Andrea Contreras Buitrago', 'Cúcuta', 'andrea.contreras@unidadvictimas.gov.co'),

    # ── Sesión 3 · martes 29 de septiembre · Grupo B (virtual) ──────────────
    (3, 'Central', 'Jhonathan Guarin', 'Bogotá', 'jhonathan.guarin@unidadvictimas.gov.co'),
    (3, 'Central', 'Gloria Yamile Suarez Leal', 'Tunja', 'gloria.suarez@unidadvictimas.gov.co'),
    (3, 'Central', 'Luis Ariel Forero Bocanegra', 'Ibagué', 'luis.forero@unidadvictimas.gov.co'),
    (3, 'Caquetá - Huila', 'Norma Maritza Varón Trujillo', 'Florencia', 'norma.varon@unidadvictimas.gov.co'),
    (3, 'Caquetá - Huila', 'Maria Eugenia Rojas Puentes', 'Neiva', 'maria.rojas@unidadvictimas.gov.co'),
    (3, 'Cauca', 'Deissy Judith Arciniegas Chamorro', 'Popayán', 'deissy.arciniegas@unidadvictimas.gov.co'),
    (3, 'Cauca', 'Audrey Karin Hernández Castellar', 'Popayán', 'audrey.hernandez@unidadvictimas.gov.co'),
    (3, 'Cauca', 'Esther Julia Morantes Narvaez', 'Popayán', 'esther.morantes@unidadvictimas.gov.co'),
    (3, 'Valle del Cauca', 'Claudia Bibiana Duque Rojas', 'Cali', 'claudia.duque@unidadvictimas.gov.co'),
    (3, 'Nariño', 'Sonia Maribel Lasso Paz', 'Pasto', 'sonia.lasso@unidadvictimas.gov.co'),
    (3, 'Nariño', 'Nathalia Stefania Manrique Delgado', 'Pasto', 'nathalia.manrique@unidadvictimas.gov.co'),
    (3, 'Putumayo', 'Zuleyma Yanina Ordoñez Rojas', 'Mocoa', 'zuleyma.ordonez@unidadvictimas.gov.co'),
    (3, 'Eje Cafetero', 'Sonia Stella Cardona Castaño', 'Pereira', 'soniaste.cardona@unidadvictimas.gov.co'),
    (3, 'Llanos', 'Javier Antonio Parra Valencia', 'Villavicencio', 'javier.parra@unidadvictimas.gov.co'),
]


# ───────────────────────────────────────────────────────────────────────────
# Código de usuario
# ───────────────────────────────────────────────────────────────────────────

def sin_tildes(texto: str) -> str:
    """
    Quita las tildes y **conserva la Ñ**.

    La Ñ no es un acento: `MUÑOZ` sin ella es otro apellido. Y ya está en los
    códigos reales del sistema (`KLMUÑOZM`), así que quitarla acá produciría un
    código que no coincide con la convención con la que se generaron las 1.158
    encuestadoras. Se protege antes de normalizar y se repone después.
    """
    texto = texto.replace('Ñ', '\x01').replace('ñ', '\x02')
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.replace('\x01', 'Ñ').replace('\x02', 'ñ')


def codigo_de(nombre_completo: str) -> str:
    """
    Iniciales de los nombres + primer apellido + inicial del segundo apellido.

        Karen Liliana Muñoz Mora   → KLMUÑOZM
        Dora Lilia Vivas Loaiza    → DLVIVASL
        Jhonathan Guarin           → JGUARIN

    La regla de corte es la colombiana: **los dos últimos tokens son los
    apellidos**. Con menos de tres tokens se asume un nombre y un apellido, que
    es lo que hay en el roster para «Jhonathan Guarin».
    """
    partes = [p for p in sin_tildes(nombre_completo).upper().split() if p]
    if len(partes) < 2:
        raise CommandError(f'Nombre sin apellido, no se puede generar código: {nombre_completo!r}')
    if len(partes) == 2:
        nombres, apellidos = partes[:1], partes[1:]
    else:
        nombres, apellidos = partes[:-2], partes[-2:]
    iniciales = ''.join(n[0] for n in nombres)
    primer_apellido = apellidos[0]
    inicial_segundo = apellidos[1][0] if len(apellidos) > 1 else ''
    return f'{iniciales}{primer_apellido}{inicial_segundo}'


def clave_nueva() -> str:
    """
    Clave de jornada: legible, dictable y por encima del mínimo de 10.

    `Sicav.xxxxxx` — el prefijo hace obvio de qué sistema es cuando la persona
    la ve escrita en el formato del Anexo H tres días después, y el sufijo
    aleatorio la hace única por participante. Pasa los cuatro validadores de
    Django: 12 caracteres, no es común, no es numérica y no se parece al código
    de usuario ni al correo.
    """
    return 'Sicav.' + ''.join(secrets.choice(ALFABETO_CLAVE) for _ in range(6))


# ───────────────────────────────────────────────────────────────────────────
# Comando
# ───────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = ('Prepara cuentas y datos de práctica de las jornadas de capacitación. '
            'Sin --confirmar es DRY-RUN.')

    def add_arguments(self, parser):
        parser.add_argument('--confirmar', action='store_true',
                            help='Escribe en la base. Sin esto, DRY-RUN.')
        parser.add_argument('--sesion', type=int, choices=[1, 2, 3], default=None,
                            help='Preparar solo una sesión. Por defecto, las tres.')
        parser.add_argument('--conservar-claves', action='store_true',
                            help='No rota la clave de quien ya tiene una utilizable. '
                                 'Úselo entre corridas para no invalidar lo ya repartido.')
        parser.add_argument('--salida', default=None,
                            help='Ruta de un CSV con las credenciales. Contiene claves '
                                 'en texto plano: bórrelo después de repartirlas.')
        parser.add_argument('--sin-datos', action='store_true',
                            help='Solo las cuentas; no siembra personas de práctica.')

    # ── entrada ────────────────────────────────────────────────────────────
    def handle(self, *args, **o):
        from apps.autenticacion.models import Perfil

        confirmar = o['confirmar']
        roster = [r for r in ROSTER if o['sesion'] is None or r[0] == o['sesion']]
        if not roster:
            raise CommandError('El roster quedó vacío con ese filtro.')

        # El índice del documento de práctica es la posición en el ROSTER
        # COMPLETO, no en el filtrado: si fuera el filtrado, correr `--sesion 2`
        # le daría a los enlaces los mismos documentos que ya tiene el equipo de
        # la sesión 1, y dos personas compartirían hogar de práctica.
        indice = {r[2]: i for i, r in enumerate(ROSTER, start=1)}

        perfil = Perfil.objects.filter(codigo=PERFIL).first()
        if perfil is None:
            raise CommandError(
                f'No existe el perfil {PERFIL}. Cárguelo antes de preparar la jornada.')
        if not perfil.activo:
            raise CommandError(f'El perfil {PERFIL} está inactivo: nadie podría entrar.')

        w = self.stdout.write
        w('═' * 78)
        w(f'PREPARAR CAPACITACIÓN — {len(roster)} participantes · perfil {PERFIL}')
        w('═' * 78)
        if not confirmar:
            w(self.style.WARNING('DRY-RUN — no se escribe nada. Use --confirmar.'))
        w('')

        # Los códigos se resuelven ANTES de escribir: un choque entre dos
        # participantes hay que verlo entero, no descubrirlo a mitad de la carga
        # con la mitad de las cuentas ya creadas.
        plan = self._planear(roster, indice)
        self._informar_plan(plan)

        if not confirmar:
            w('')
            w(self.style.WARNING('DRY-RUN terminado. Nada se escribió.'))
            return

        with transaction.atomic():
            filas = self._aplicar(plan, perfil, o['conservar_claves'],
                                  sembrar=not o['sin_datos'])

        self._informar_resultado(filas, sembrar=not o['sin_datos'])

        if o['salida']:
            self._escribir_csv(o['salida'], filas)
            w('')
            w(self.style.WARNING(
                f'Credenciales en {o["salida"]} — texto plano. Bórrelo al repartirlas.'))

    # ── planeación ─────────────────────────────────────────────────────────
    def _planear(self, roster, indice):
        """Resuelve códigos y detecta choques sin tocar la base."""
        from apps.autenticacion.models import Usuario

        plan, vistos = [], {}
        for sesion, dt, nombre, ciudad, correo in roster:
            codigo = codigo_de(nombre)
            idx = indice[nombre]

            choque = None
            if codigo in vistos:
                choque = f'choca dentro del roster con {vistos[codigo]}'
            else:
                otro = Usuario.objects.filter(codigo_usuario=codigo).first()
                if otro and (otro.email or '').lower() != correo.lower():
                    choque = f'el código ya es de {otro.nombre_completo} ({otro.email})'
            vistos[codigo] = nombre

            # Una cuenta que ya existe con OTRO código pero el mismo correo es la
            # misma persona: el correo es único en la tabla, así que crear una
            # segunda cuenta fallaría el INSERT. Se reutiliza la que hay.
            por_correo = Usuario.objects.filter(email__iexact=correo).first()

            plan.append(dict(
                sesion=sesion, dt=dt, nombre=nombre, ciudad=ciudad, correo=correo,
                codigo=codigo, idx=idx, choque=choque,
                existente=por_correo.codigo_usuario if por_correo else None,
            ))
        return plan

    def _informar_plan(self, plan):
        w = self.stdout.write
        w(f'{"#":>3} {"S":>2} {"CÓDIGO":<16} {"NOMBRE":<36} {"DOCS 999…":<12} ESTADO')
        w('─' * 78)
        for p in plan:
            docs = f'999{p["idx"]:02d}0000x'
            if p['choque']:
                estado = self.style.ERROR(f'⚠ {p["choque"]}')
            elif p['existente'] and p['existente'] != p['codigo']:
                estado = self.style.WARNING(f'reusa cuenta {p["existente"]}')
            elif p['existente']:
                estado = 'actualiza'
            else:
                estado = self.style.SUCCESS('crea')
            w(f'{p["idx"]:>3} {p["sesion"]:>2} {p["codigo"]:<16} {p["nombre"][:36]:<36} {docs:<12} {estado}')

        choques = [p for p in plan if p['choque']]
        if choques:
            w('')
            w(self.style.ERROR(
                f'{len(choques)} choque(s) de código. Se resuelven con un sufijo '
                f'numérico al aplicar, y quedan marcados en el CSV para revisarlos.'))

    # ── aplicación ─────────────────────────────────────────────────────────
    def _aplicar(self, plan, perfil, conservar, *, sembrar):
        from apps.autenticacion.models import Usuario

        filas = []
        for p in plan:
            codigo = self._codigo_libre(p, Usuario)
            usuario, clave, accion = self._usuario(p, codigo, perfil, conservar, Usuario)
            fila = dict(p, codigo=codigo, clave=clave, accion=accion)
            if sembrar:
                fila.update(self._sembrar(usuario, p['idx'], p['ciudad']))
            filas.append(fila)
        return filas

    def _codigo_libre(self, p, Usuario):
        """
        El código que le toca a esta persona.

        Si ya tiene cuenta por correo, ese es su código y no se le cambia:
        renombrarla le rompería el acceso que ya usa. Si el código calculado lo
        ocupa **otra** persona, se le agrega un sufijo numérico — feo, pero
        preferible a pisarle la cuenta a alguien.
        """
        if p['existente']:
            return p['existente']
        codigo = p['codigo']
        if not Usuario.objects.filter(codigo_usuario=codigo).exists():
            return codigo
        for n in range(2, 100):
            candidato = f'{codigo}{n}'
            if not Usuario.objects.filter(codigo_usuario=candidato).exists():
                return candidato
        raise CommandError(f'No se encontró un código libre para {p["nombre"]}.')

    def _usuario(self, p, codigo, perfil, conservar, Usuario):
        u = Usuario.objects.filter(codigo_usuario=codigo).first()
        if u is None:
            clave = clave_nueva()
            u = Usuario.objects.create_user(
                codigo_usuario=codigo, password=clave, nombre_completo=p['nombre'],
                email=p['correo'], perfil=perfil, activo=True)
            return u, clave, 'creado'

        perfil_antes = u.perfil.codigo if u.perfil_id else '(sin perfil)'
        u.nombre_completo = p['nombre']
        u.email = p['correo']
        u.perfil = perfil
        u.activo = True

        if conservar and u.has_usable_password():
            u.save()
            accion = 'conservado' if perfil_antes == perfil.codigo else f'{perfil_antes}→{perfil.codigo}'
            return u, '(la que ya tenía)', accion

        clave = clave_nueva()
        u.set_password(clave)
        u.save()
        accion = 'actualizado' if perfil_antes == perfil.codigo else f'{perfil_antes}→{perfil.codigo}'
        return u, clave, accion

    # ── datos de práctica ──────────────────────────────────────────────────
    def _sembrar(self, usuario, idx, ciudad):
        """
        Las cinco personas de práctica del participante, y su hogar bloqueado.

        Devuelve lo que el CSV necesita para que el facilitador sepa qué
        documento darle a cada quien en cada caso.
        """
        from apps.encuestas.models import ExcepcionVigencia, SesionEncuesta
        from apps.formulario.models import Instrumento
        from apps.hogares.models import Hogar, MiembroHogar
        from apps.parametricas.models import Departamento, Municipio, TipoDocumento
        from apps.victimas.models import Victima

        tipo, _ = TipoDocumento.objects.get_or_create(
            codigo='CC', defaults={'nombre': 'Cédula de ciudadanía'})
        muni = self._municipio(ciudad, Municipio, Departamento)

        hoy = timezone.now().date()
        # `replace` sobre el año y no `timedelta`: una edad se cuenta en años,
        # y 14 × 365 días se corre de fecha en los bisiestos. El 29 de febrero
        # se lleva al 28, que es la convención civil.
        def hace_anios(n):
            try:
                return hoy.replace(year=hoy.year - n)
            except ValueError:
                return hoy.replace(year=hoy.year - n, day=28)

        def doc(sufijo):
            return f'999{idx:02d}0000{sufijo}'

        def persona(sufijo, nombre, apellido, genero, nacimiento, *, con_ficha):
            v, _ = Victima.objects.update_or_create(
                numero_documento_hash=_hash_cc(doc(sufijo)),
                defaults=dict(
                    tipo_documento=tipo, numero_documento=doc(sufijo),
                    primer_nombre=nombre, primer_apellido=apellido,
                    segundo_apellido=f'P{idx:02d}',
                    # Cadena y no `date`: el campo va cifrado y el cifrado
                    # trabaja sobre el texto.
                    fecha_nacimiento=nacimiento.isoformat(),
                    genero=genero, estado_ruv='INCLUIDO',
                    # Es un dato sembrado por nosotros, no verificado contra el
                    # RUV. Decir `UNIVERSO_RUV` sería exactamente el error que
                    # costó 5,9 M de filas con un estado que nadie comprobó.
                    estado_ruv_fuente='SIN_VERIFICAR',
                    pertenencia_etnica='NINGUNA', discapacidad=False,
                    municipio_residencia=muni, fuente_origen='MANUAL',
                    fecha_ult_caracterizacion=(_hace_meses(MESES_FICHA_VIGENTE)
                                               if con_ficha else None),
                    habilitado_para_caracterizacion=not con_ficha,
                    creado_por=usuario,
                ))
            return v

        vigente_1 = persona(1, 'ANA', 'PRACTICA', 'F', hace_anios(40), con_ficha=True)
        vigente_2 = persona(2, 'MARIA', 'PRACTICA', 'F', hace_anios(19), con_ficha=True)
        libre_1 = persona(3, 'ROSA', 'PRACTICA', 'F', hace_anios(38), con_ficha=False)
        persona(4, 'JUAN', 'PRACTICA', 'M', hace_anios(14), con_ficha=False)
        persona(5, 'CARMEN', 'PRACTICA', 'F', hace_anios(71), con_ficha=False)

        # El hogar que ANA ya tiene, con su familia. `creado_por=usuario` a
        # propósito: la búsqueda solo adjunta como `hogar_activo` un hogar del
        # propio usuario, así que si lo creara otro, el participante no vería el
        # atajo «Ver hogar registrado» y su caso 2 empezaría por el camino largo.
        #
        # El caso del hogar conformado por OTRO encuestador —que desde el
        # 11-sep-2026 también funciona— se demuestra una vez en plenaria con dos
        # cuentas, no se le pone a cada participante: si esa ruta fallara, 37
        # personas quedarían trabadas a la vez en lugar de una demostración.
        hogar = Hogar.objects.filter(autorizado=vigente_1, creado_por=usuario).first()
        if hogar is None:
            hogar = Hogar.objects.create(
                autorizado=vigente_1, municipio=muni, creado_por=usuario,
                numero_personas=2)
        for v, parentesco, es_aut in [(vigente_1, '', True), (vigente_2, 'HIJO', False)]:
            MiembroHogar.objects.get_or_create(
                hogar=hogar, victima=v,
                defaults=dict(tipo_documento=tipo, parentesco=parentesco,
                              genero=v.genero, es_autorizado=es_aut, rol='MIEMBRO'))

        instrumento = (Instrumento.objects.filter(activo=True).first()
                       or Instrumento.objects.first())
        sesion = SesionEncuesta.objects.filter(hogar=hogar).first()
        if sesion is None and instrumento is not None:
            sesion = SesionEncuesta.objects.create(
                hogar=hogar, instrumento=instrumento, encuestador=usuario,
                ruta_entrevista='GENERAL', estado='COMPLETADA',
                fecha_fin=timezone.now(), porcentaje_completado=100)

        abiertas = ExcepcionVigencia.objects.filter(
            victima__in=[vigente_1, vigente_2],
            estado=ExcepcionVigencia.VIGENTE).count()

        return dict(
            doc_caso2=doc(1), doc_caso2_miembro=doc(2),
            doc_caso1=doc(3), doc_caso1_hijo=doc(4), doc_caso1_madre=doc(5),
            doc_caso3=doc(9),
            # `sesion_encuesta` y no `sesion`: la fila ya trae `sesion` con el
            # NÚMERO de jornada (1, 2 o 3), y este dict se mezcla sobre ella. Con
            # el mismo nombre, el id de la sesión de encuesta pisaba el número de
            # la jornada y el CSV de credenciales salía con un UUID en la columna
            # que le dice al facilitador qué día va cada participante.
            hogar=str(hogar.id), sesion_encuesta=str(sesion.id) if sesion else '',
            excepciones_abiertas=abiertas,
            municipio=muni.nombre if muni else '',
        )

    def _municipio(self, ciudad, Municipio, Departamento):
        """
        El municipio del participante, o Bogotá si no está en la paramétrica.

        No se crea el municipio que falte: la tabla es paramétrica oficial con
        código DANE, e inventarle una fila para una jornada de práctica dejaría
        un municipio falso conviviendo con los reales.
        """
        m = Municipio.objects.filter(nombre__iexact=ciudad).first()
        if m:
            return m
        depto, _ = Departamento.objects.get_or_create(
            codigo_dane='11', defaults={'nombre': 'Bogotá D.C.'})
        m, _ = Municipio.objects.get_or_create(
            codigo_dane='11001',
            defaults={'nombre': 'Bogotá D.C.', 'departamento': depto})
        return m

    # ── salida ─────────────────────────────────────────────────────────────
    def _informar_resultado(self, filas, *, sembrar):
        w = self.stdout.write
        w('')
        w(self.style.SUCCESS(f'{len(filas)} participantes listos.'))
        w('')
        w(f'{"S":>2} {"CÓDIGO":<16} {"CLAVE":<16} {"NOMBRE":<32} ACCIÓN')
        w('─' * 78)
        for f in filas:
            w(f'{f["sesion"]:>2} {f["codigo"]:<16} {f["clave"]:<16} '
              f'{f["nombre"][:32]:<32} {f["accion"]}')

        if sembrar:
            abiertas = sum(f.get('excepciones_abiertas', 0) for f in filas)
            sin_sesion = [f['codigo'] for f in filas if not f.get('sesion_encuesta')]
            w('')
            w('  Cada participante practica sobre SUS documentos 999NNxxxxx:')
            w('    …00001  CASO 2 — ya caracterizada hace 8 meses: se continúa sin permiso')
            w('    …00002  CASO 2 — el integrante que se RETIRA del hogar')
            w('    …00003  CASO 1 — la señora que recibe (sin ficha previa)')
            w('    …00004  CASO 1 — hijo, 14 años')
            w('    …00005  CASO 1 — madre, 71 años')
            w('    …00009  CASO 3 — NO existe: es el alta manual')
            if abiertas:
                w('')
                w(self.style.WARNING(
                    f'  ⚠ {abiertas} excepción(es) VIGENTE(s) de una corrida anterior. '
                    f'Esas personas aparecen habilitadas de entrada y el caso 2 no se '
                    f've. Anúlelas desde el panel antes de la jornada.'))
            if sin_sesion:
                w('')
                w(self.style.WARNING(
                    f'  ⚠ {len(sin_sesion)} hogar(es) sin sesión: no hay instrumento '
                    f'cargado. Cargue uno con `cargar_perfil` y vuelva a correr esto.'))

    def _escribir_csv(self, ruta, filas):
        columnas = ['sesion', 'dt', 'nombre', 'correo', 'codigo', 'clave', 'accion',
                    'municipio', 'doc_caso1', 'doc_caso1_hijo', 'doc_caso1_madre',
                    'doc_caso2', 'doc_caso2_miembro', 'doc_caso3', 'hogar', 'choque']
        with open(ruta, 'w', newline='', encoding='utf-8') as fh:
            escritor = csv.DictWriter(fh, fieldnames=columnas, extrasaction='ignore')
            escritor.writeheader()
            for f in filas:
                escritor.writerow(f)


# ───────────────────────────────────────────────────────────────────────────
# Auxiliares que necesitan el ORM cargado
# ───────────────────────────────────────────────────────────────────────────

def _hash_cc(numero: str) -> str:
    """Hash de identidad de una CC, con la ÚNICA definición que hay del hash."""
    from apps.victimas.repository.base import doc_hash
    return doc_hash('CC', numero)


def _hace_meses(meses: int):
    """
    Un datetime de hace N meses, sin dependencias externas.

    Se resta por aritmética de meses y no por días: `MESES_FICHA_VIGENTE` es
    parte del enunciado del caso —«hace ocho meses»— y con 30 × 8 días el
    número que ve el participante en pantalla no sería ocho.
    """
    ahora = timezone.now()
    total = ahora.month - 1 - meses
    anio = ahora.year + total // 12
    mes = total % 12 + 1
    dia = min(ahora.day, [31, 29 if anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)
                          else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return ahora.replace(year=anio, month=mes, day=dia)
