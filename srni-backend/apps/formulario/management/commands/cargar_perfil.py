"""
Comando idempotente genérico para cargar cualquier perfil de caracterización SRNI.

Uso:
    python manage.py cargar_perfil --perfil TERRITORIAL
    python manage.py cargar_perfil --fixture apps/formulario/fixtures/perfil_territorial_v7.json
    python manage.py cargar_perfil --perfil ASISTENCIA --dry-run

Diferencias con cargar_diccionario_v8 (mejorado):
  1. Argumento --perfil: deriva la ruta del fixture automáticamente.
     --fixture tiene precedencia sobre --perfil.
  2. Resolución de $ref: si el campo "opciones" de una pregunta es el string
     "$ref:CLAVE", lo reemplaza con la lista del catálogo opciones_compartidas.json.
  3. Bug fix: usa p_data.get("no_pregunta", "") en lugar de codigo_diagrama.

El comando puede ejecutarse múltiples veces sin duplicar registros.
En cada ejecución, actualiza los registros existentes (upsert por código/externo).
Las reglas de skip logic se regeneran completas en cada ejecución.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.formulario.models import (
    Perfil, InstrumentoVersion, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic,
)

# Ruta al catálogo compartido (relativa al directorio srni-backend)
OPCIONES_COMPARTIDAS_PATH = Path("apps/formulario/fixtures/opciones_compartidas.json")


class Command(BaseCommand):
    help = "Carga un perfil de caracterización SRNI desde fixture JSON (idempotente)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="",
            help=(
                "Ruta al fixture JSON relativa al directorio srni-backend. "
                "Tiene precedencia sobre --perfil."
            ),
        )
        parser.add_argument(
            "--perfil",
            default="",
            help=(
                "Nombre del perfil (ej: TERRITORIAL, ASISTENCIA). "
                "Deriva el fixture como apps/formulario/fixtures/perfil_<nombre_lower>_v?.json. "
                "Ignorado si --fixture está presente."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la carga sin persistir. Útil para validar el fixture.",
        )

    def handle(self, *args, **opts):
        # ── Resolución de ruta del fixture ────────────────────────────────────
        fixture_arg = opts.get("fixture", "").strip()
        perfil_arg = opts.get("perfil", "").strip()

        if fixture_arg:
            fixture_path = Path(fixture_arg)
        elif perfil_arg:
            # Convención: perfil_<nombre_en_minúsculas>_v?.json
            nombre_lower = perfil_arg.lower()
            # Busca el primer archivo que coincida con el patrón
            patron = f"perfil_{nombre_lower}_v*.json"
            fixtures_dir = Path("apps/formulario/fixtures")
            candidatos = sorted(fixtures_dir.glob(patron))
            if not candidatos:
                raise CommandError(
                    f"No se encontró ningún fixture con patrón '{patron}' en {fixtures_dir}. "
                    f"Use --fixture para especificar la ruta exacta."
                )
            fixture_path = candidatos[-1]  # la versión más reciente (orden lexicográfico)
            self.stdout.write(f"  Usando fixture: {fixture_path}")
        else:
            raise CommandError("Debe especificar --fixture o --perfil.")

        if not fixture_path.exists():
            raise CommandError(f"Fixture no encontrado: {fixture_path}")

        # ── Carga del catálogo compartido ($ref) ──────────────────────────────
        catalogo = self._cargar_catalogo()

        # ── Carga del fixture principal ───────────────────────────────────────
        try:
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CommandError(f"Fixture JSON inválido: {e}")

        self._validar_estructura(data)

        with transaction.atomic():
            perfil = self._upsert_perfil(data["perfil"])
            version = self._upsert_version(perfil, data["instrumento_version"])
            capitulos_map = self._upsert_capitulos(version, data["capitulos"])
            preguntas_map = self._upsert_preguntas(capitulos_map, data["preguntas"], catalogo)
            n_reglas = self._upsert_reglas(
                version, preguntas_map, capitulos_map, data.get("reglas_skip_logic", [])
            )

            if opts["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING(
                    f"DRY RUN - sin cambios en BD. "
                    f"Se habrían cargado: {len(capitulos_map)} capítulos, "
                    f"{len(preguntas_map)} preguntas, {n_reglas} reglas."
                ))
                return

        self.stdout.write(self.style.SUCCESS(
            f"OK Cargado: perfil={perfil.codigo} version={version.numero} | "
            f"capitulos={len(capitulos_map)} | preguntas={len(preguntas_map)} | "
            f"reglas={n_reglas}"
        ))

    # ── Catálogo compartido ───────────────────────────────────────────────────

    def _cargar_catalogo(self):
        """Carga opciones_compartidas.json. Devuelve dict clave→lista de opciones."""
        if not OPCIONES_COMPARTIDAS_PATH.exists():
            self.stderr.write(
                f"  Aviso: catálogo compartido no encontrado en {OPCIONES_COMPARTIDAS_PATH}. "
                f"Los $ref no serán resueltos."
            )
            return {}
        try:
            raw = json.loads(OPCIONES_COMPARTIDAS_PATH.read_text(encoding="utf-8"))
            catalogo = raw.get("listas", {})
            self.stdout.write(f"  Catálogo compartido: {len(catalogo)} listas cargadas.")
            return catalogo
        except json.JSONDecodeError as e:
            raise CommandError(f"Catálogo opciones_compartidas.json inválido: {e}")

    # ── Validación de estructura ──────────────────────────────────────────────

    def _validar_estructura(self, data):
        requeridos = ["perfil", "instrumento_version", "capitulos", "preguntas"]
        faltantes = [k for k in requeridos if k not in data]
        if faltantes:
            raise CommandError(f"Fixture incompleto — faltan secciones: {faltantes}")

    # ── Upserts ───────────────────────────────────────────────────────────────

    def _upsert_perfil(self, data):
        perfil, created = Perfil.objects.update_or_create(
            codigo=data["codigo"],
            defaults={"nombre": data["nombre"], "activo": True},
        )
        accion = "Creado" if created else "Actualizado"
        self.stdout.write(f"  {accion} perfil: {perfil}")
        return perfil

    def _upsert_version(self, perfil, data):
        version, created = InstrumentoVersion.objects.update_or_create(
            perfil=perfil,
            numero=data["numero"],
            defaults={
                "vigente_desde": data["vigente_desde"],
                "vigente_hasta": data.get("vigente_hasta"),
                "fuente_documental": data.get("fuente_documental", ""),
            },
        )
        accion = "Creada" if created else "Actualizada"
        self.stdout.write(f"  {accion} versión: {version}")
        return version

    def _upsert_capitulos(self, version, capitulos_data):
        result = {}
        for cap_data in capitulos_data:
            cap, created = Capitulo.objects.update_or_create(
                instrumento=version,
                codigo=cap_data["codigo"],
                defaults={
                    "nombre": cap_data["nombre"],
                    "orden": cap_data["orden"],
                    "objetivo": cap_data.get("objetivo", ""),
                    "poblacion_objetivo": cap_data.get(
                        "poblacion_objetivo", "TODOS_MIEMBROS"
                    ),
                    "aplicabilidad": cap_data.get("aplicabilidad", {}),
                },
            )
            result[cap_data["codigo"]] = cap
        self.stdout.write(f"  Capítulos procesados: {len(result)}")
        return result

    def _upsert_preguntas(self, capitulos, preguntas_data, catalogo):
        result = {}
        errores = []
        for p_data in preguntas_data:
            cap_codigo = p_data.get("capitulo_codigo")
            if cap_codigo not in capitulos:
                errores.append(
                    f"Capítulo '{cap_codigo}' no existe para pregunta '{p_data.get('codigo_externo')}'"
                )
                continue

            # ── Resolución de $ref ────────────────────────────────────────────
            opciones_raw = p_data.get("opciones", [])
            if isinstance(opciones_raw, str) and opciones_raw.startswith("$ref:"):
                clave_ref = opciones_raw[len("$ref:"):]
                if clave_ref not in catalogo:
                    raise CommandError(
                        f"$ref no resuelto: clave '{clave_ref}' no existe en "
                        f"opciones_compartidas.json (pregunta '{p_data.get('codigo_externo')}')"
                    )
                opciones_lista = catalogo[clave_ref]
            else:
                opciones_lista = opciones_raw

            cap = capitulos[cap_codigo]
            pregunta, _ = Pregunta.objects.update_or_create(
                capitulo=cap,
                codigo_externo=p_data["codigo_externo"],
                defaults={
                    "texto": p_data["texto"],
                    "variable_bd": p_data.get(
                        "variable_bd",
                        p_data["codigo_externo"].replace("_tel", ""),
                    ),
                    "tipo": p_data["tipo"],
                    "nivel": p_data.get("nivel", "PERSONA"),
                    "orden": p_data.get("orden", 0),
                    "obligatoria": p_data.get("obligatoria", True),
                    "validaciones": p_data.get("validaciones", {}),
                    "descripcion_ayuda": p_data.get("descripcion_ayuda", ""),
                    # Bug fix: se usa no_pregunta, NO codigo_diagrama
                    "no_pregunta": p_data.get("no_pregunta", ""),
                    "id_preg": p_data.get("id_preg"),
                    "es_precargada": p_data.get("es_precargada", False),
                    "fuente_precarga": p_data.get("fuente_precarga", ""),
                    "activa": p_data.get("activa", True),
                },
            )
            result[p_data["codigo_externo"]] = pregunta

            for opt_data in opciones_lista:
                OpcionRespuesta.objects.update_or_create(
                    pregunta=pregunta,
                    valor=opt_data["valor"],
                    defaults={
                        "etiqueta": opt_data["etiqueta"],
                        "id_resp_vivanto": opt_data.get("id_resp_vivanto"),
                        "orden": opt_data.get("orden", 0),
                        "finaliza_capitulo": opt_data.get("finaliza_capitulo", False),
                    },
                )

        for e in errores:
            self.stderr.write(f"  Aviso: {e}")
        self.stdout.write(f"  Preguntas procesadas: {len(result)} ({len(errores)} errores)")
        return result

    def _upsert_reglas(self, version, preguntas, capitulos, reglas_data):
        # Las reglas son declarativas — se regeneran en cada carga
        ReglaSkipLogic.objects.filter(instrumento=version).delete()
        creadas = 0

        for r in reglas_data:
            pregunta_origen = (
                preguntas.get(r.get("origen")) if r.get("origen") else None
            )
            accion = r["accion"]
            base = {
                "instrumento": version,
                "pregunta_origen": pregunta_origen,
                "valor_trigger": r.get("valor_trigger", ""),
                "accion": accion,
                "descripcion": r.get("descripcion", ""),
                "expresion_origen": r.get("origen_expr", ""),
            }

            # Afecta una sola pregunta
            if "afecta" in r:
                p = preguntas.get(r["afecta"])
                if p:
                    ReglaSkipLogic.objects.create(**base, pregunta_afectada=p)
                    creadas += 1

            # Afecta múltiples preguntas
            for cod in r.get("afecta_multiple", []):
                p = preguntas.get(cod)
                if p:
                    ReglaSkipLogic.objects.create(**base, pregunta_afectada=p)
                    creadas += 1

            # Afecta un capítulo completo
            if "afecta_capitulo" in r:
                cap = capitulos.get(r["afecta_capitulo"])
                if cap:
                    ReglaSkipLogic.objects.create(**base, capitulo_afectado=cap)
                    creadas += 1

            # Afecta múltiples capítulos
            for cod in r.get("afecta_capitulos_multiple", []):
                cap = capitulos.get(cod)
                if cap:
                    ReglaSkipLogic.objects.create(**base, capitulo_afectado=cap)
                    creadas += 1

        self.stdout.write(f"  Reglas skip logic: {creadas}")
        return creadas
