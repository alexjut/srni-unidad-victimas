"""
Escribe (o SIMULA) una caracterización SICAV hacia Oracle legacy vía procedures
oficiales — ETAPA A del strangler-fig.

DRY-RUN por defecto: imprime, por cada paso, el bloque PL/SQL EXACTO que se
ejecutaría (binds PII redactados) y registra el plan en el ledger
RegistroEscrituraOracle. NO conecta a Oracle ni escribe.

Ejecución real (requiere aprobación explícita de Javier):
    python manage.py escribir_a_oracle --hogar <CODIGO_HOGAR> --confirmar --destino local
El destino 'produccion' además exige exportar ORACLE_PROD_* en el entorno.

Ejemplos:
    # DRY-RUN de un hogar (seguro, no toca Oracle):
    python manage.py escribir_a_oracle --hogar 228206-6I0D6
    # DRY-RUN de todos los hogares abiertos:
    python manage.py escribir_a_oracle --todos-abiertos
"""
from django.core.management.base import BaseCommand, CommandError

from apps.hogares.models import Hogar
from apps.sincronizacion.oracle import mapeo
from apps.sincronizacion.oracle.escritor import EscritorOracle


class Command(BaseCommand):
    help = "Escribe/simula una caracterización SICAV hacia Oracle legacy (Etapa A, DRY-RUN por defecto)."

    def add_arguments(self, parser):
        parser.add_argument("--hogar", help="codigo_hogar SICAV a procesar.")
        parser.add_argument("--todos-abiertos", action="store_true",
                            help="Procesa todos los hogares en estado BORRADOR (abierto).")
        parser.add_argument("--confirmar", action="store_true",
                            help="EJECUTA de verdad contra Oracle. Sin él es DRY-RUN.")
        parser.add_argument("--destino", choices=["local", "produccion"], default="",
                            help="Destino real (obligatorio con --confirmar).")
        parser.add_argument("--mostrar-plsql", action="store_true", default=True,
                            help="Imprime el bloque PL/SQL de cada paso (por defecto sí).")

    def handle(self, *args, **opts):
        confirmar = opts["confirmar"]
        destino = opts["destino"]

        if confirmar:
            if not destino:
                raise CommandError("--confirmar exige --destino local|produccion.")
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  MODO ESCRITURA REAL sobre Oracle '{destino}'.\n"
                "    Esto NO es DRY-RUN. Aprobado por Javier (Escalón 1, 2026-07-24).\n"
            ))
            hogares = self._seleccionar_hogares(opts)
            if not hogares:
                self.stdout.write(self.style.NOTICE("No hay hogares que procesar."))
                return
            catalogos_real = mapeo.ResolverCatalogos.desde_settings(estricto=True)
            with EscritorOracle(confirmar=True, destino=destino,
                                catalogos=catalogos_real) as escritor:
                for hogar in hogares:
                    resultado = escritor.procesar_hogar(hogar)
                    self._imprimir_hogar(resultado, mostrar_plsql=opts["mostrar_plsql"])
            return

        # ── DRY-RUN ──────────────────────────────────────────────────────────
        hogares = self._seleccionar_hogares(opts)
        if not hogares:
            self.stdout.write(self.style.NOTICE("No hay hogares que procesar."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"DRY-RUN — {len(hogares)} hogar(es). No se conecta ni escribe en Oracle.\n"))

        for hogar in hogares:
            escritor = EscritorOracle(confirmar=False)
            resultado = escritor.procesar_hogar(hogar)
            self._imprimir_hogar(resultado, mostrar_plsql=opts["mostrar_plsql"])

    def _seleccionar_hogares(self, opts):
        if opts["hogar"]:
            try:
                return [Hogar.objects.get(codigo_hogar=opts["hogar"])]
            except Hogar.DoesNotExist:
                raise CommandError(f"No existe el hogar {opts['hogar']!r}.")
        if opts["todos_abiertos"]:
            return list(Hogar.objects.filter(estado="BORRADOR"))
        raise CommandError("Indica --hogar <codigo> o --todos-abiertos.")

    def _imprimir_hogar(self, resultado, *, mostrar_plsql):
        self.stdout.write(self.style.HTTP_INFO(
            f"\n══ Hogar {resultado.hog_codigo_sicav} ══ resumen: {resultado.resumen()}"))
        for paso in resultado.pasos:
            self.stdout.write(f"  • {paso.paso:<10} origen={paso.origen_id} → {paso.estado}")
            if paso.detalle:
                self.stdout.write(f"    detalle: {paso.detalle}")
            if mostrar_plsql and paso.bloque:
                bloque = "\n      ".join(paso.bloque.splitlines())
                self.stdout.write(f"      {bloque}")
