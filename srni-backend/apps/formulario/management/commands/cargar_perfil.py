"""
Comando idempotente genérico para cargar cualquier instrumento de caracterización SRNI.

Uso:
    python manage.py cargar_perfil --instrumento TERRITORIAL
    python manage.py cargar_perfil --fixture apps/formulario/fixtures/instrumento_territorial_v7.json
    python manage.py cargar_perfil --instrumento ASISTENCIA --dry-run

Nota: el argumento --perfil se acepta como alias de --instrumento para compatibilidad
con fixtures con nombre antiguo (perfil_*.json). --fixture tiene precedencia sobre ambos.

El comando puede ejecutarse múltiples veces sin duplicar registros.
En cada ejecución, actualiza los registros existentes (upsert por código/versión).
Las reglas de skip logic se regeneran completas en cada ejecución.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.formulario.models import Instrumento, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic

OPCIONES_COMPARTIDAS_PATH = Path("apps/formulario/fixtures/opciones_compartidas.json")

# TODO: crear fixtures instrumento_<codigo>_v*.json para instrumentos sin contenido completo:
#       BUENAVENTURA (stub V7), SAN_ANDRES (stub V7), TELEFONICO (V8),
#       URBANO_ETNICO (stub V1), RURAL_ETNICO (stub V1).
#       Pendiente acceso a Oracle / confirmación de contenido con área funcional UARIV.
#       Todos deben cargarse exclusivamente via este comando — NO via loaddata paralelo.


class Command(BaseCommand):
    help = "Carga un instrumento de caracterización SRNI desde fixture JSON (idempotente)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="",
            help=(
                "Ruta al fixture JSON relativa al directorio srni-backend. "
                "Tiene precedencia sobre --instrumento."
            ),
        )
        parser.add_argument(
            "--instrumento",
            default="",
            help=(
                "Código del instrumento (ej: TERRITORIAL, ASISTENCIA). "
                "Busca fixtures con nombre instrumento_<codigo_lower>_v*.json "
                "o el nombre legacy perfil_<codigo_lower>_v*.json."
            ),
        )
        # Alias de --instrumento para compatibilidad con fixtures legacy
        parser.add_argument(
            "--perfil",
            default="",
            help="Alias de --instrumento (compatibilidad con nombre legacy).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la carga sin persistir. Útil para validar el fixture.",
        )
        parser.add_argument(
            "--reemplazar",
            action="store_true",
            help=(
                "Purga los capítulos/preguntas/opciones existentes del instrumento "
                "(cascade) ANTES de cargar, para evitar preguntas huérfanas al cambiar "
                "de versión/reconstrucción. Falla si hay respuestas que las protegen."
            ),
        )

    def handle(self, *args, **opts):
        fixture_arg = opts.get("fixture", "").strip()
        instrumento_arg = (opts.get("instrumento") or opts.get("perfil", "")).strip()

        if fixture_arg:
            fixture_path = Path(fixture_arg)
        elif instrumento_arg:
            nombre_lower = instrumento_arg.lower()
            fixtures_dir = Path("apps/formulario/fixtures")
            # Busca nuevo nombre primero, luego legacy
            candidatos = sorted(fixtures_dir.glob(f"instrumento_{nombre_lower}_v*.json"))
            if not candidatos:
                candidatos = sorted(fixtures_dir.glob(f"perfil_{nombre_lower}_v*.json"))
            if not candidatos:
                raise CommandError(
                    f"No se encontró fixture para instrumento '{instrumento_arg}' en {fixtures_dir}. "
                    f"Use --fixture para especificar la ruta exacta."
                )
            fixture_path = candidatos[-1]
            self.stdout.write(f"  Usando fixture: {fixture_path}")
        else:
            raise CommandError("Debe especificar --fixture o --instrumento.")

        if not fixture_path.exists():
            raise CommandError(f"Fixture no encontrado: {fixture_path}")

        catalogo = self._cargar_catalogo()

        try:
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CommandError(f"Fixture JSON inválido: {e}")

        self._validar_estructura(data)

        with transaction.atomic():
            instrumento = self._upsert_instrumento(data)
            if opts.get("reemplazar"):
                n_cap = instrumento.capitulos.count()
                instrumento.capitulos.all().delete()  # cascade: preguntas, opciones, reglas
                self.stdout.write(self.style.WARNING(
                    f"  --reemplazar: purgados {n_cap} capítulos previos (cascade)."
                ))
            capitulos_map = self._upsert_capitulos(instrumento, data["capitulos"])
            preguntas_map = self._upsert_preguntas(capitulos_map, data["preguntas"], catalogo)
            n_reglas = self._upsert_reglas(
                instrumento, preguntas_map, capitulos_map, data.get("reglas_skip_logic", [])
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
            f"OK Cargado: instrumento={instrumento} | "
            f"capitulos={len(capitulos_map)} | preguntas={len(preguntas_map)} | "
            f"reglas={n_reglas}"
        ))

    def _cargar_catalogo(self):
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

    def _validar_estructura(self, data):
        """Acepta formato nuevo (instrumento) y legado (perfil + instrumento_version)."""
        tiene_nuevo = "instrumento" in data
        tiene_legacy = "perfil" in data and "instrumento_version" in data
        if not tiene_nuevo and not tiene_legacy:
            raise CommandError(
                "Fixture incompleto — debe tener sección 'instrumento' "
                "o las secciones legado 'perfil' + 'instrumento_version'."
            )
        for clave in ("capitulos", "preguntas"):
            if clave not in data:
                raise CommandError(f"Fixture incompleto — falta sección '{clave}'.")

    def _upsert_instrumento(self, data) -> Instrumento:
        """Soporta formato nuevo y formato legado (perfil + instrumento_version)."""
        if "instrumento" in data:
            d = data["instrumento"]
            instrumento, created = Instrumento.objects.update_or_create(
                codigo=d["codigo"],
                version=d["version"],
                defaults={
                    "nombre": d["nombre"],
                    "activo": d.get("activo", True),
                    "vigente_desde": d["vigente_desde"],
                    "vigente_hasta": d.get("vigente_hasta"),
                    "fuente_documental": d.get("fuente_documental", ""),
                },
            )
        else:
            # Formato legado: combina secciones perfil + instrumento_version
            p = data["perfil"]
            v = data["instrumento_version"]
            instrumento, created = Instrumento.objects.update_or_create(
                codigo=p["codigo"],
                version=v["numero"],
                defaults={
                    "nombre": p["nombre"],
                    "activo": True,
                    "vigente_desde": v["vigente_desde"],
                    "vigente_hasta": v.get("vigente_hasta"),
                    "fuente_documental": v.get("fuente_documental", ""),
                },
            )
        accion = "Creado" if created else "Actualizado"
        self.stdout.write(f"  {accion} instrumento: {instrumento}")
        return instrumento

    def _upsert_capitulos(self, instrumento: Instrumento, capitulos_data: list) -> dict:
        result = {}
        for cap_data in capitulos_data:
            campos = {
                "instrumento": instrumento,
                "codigo": cap_data["codigo"],
                "nombre": cap_data["nombre"],
                "orden": cap_data["orden"],
                "nivel": cap_data.get("nivel", "HOGAR"),
                "objetivo": cap_data.get("objetivo", ""),
                "poblacion_objetivo": cap_data.get("poblacion_objetivo", "TODOS_MIEMBROS"),
                "aplicabilidad": cap_data.get("aplicabilidad", {}),
            }
            # UUID determinista del fixture: el mismo código → mismo id en BD local
            # y servidor, para que la sincronización del APK cuadre. Si no viene id,
            # se busca por (instrumento, código) como antes.
            if cap_data.get("id"):
                cap, _ = Capitulo.objects.update_or_create(id=cap_data["id"], defaults=campos)
            else:
                cap, _ = Capitulo.objects.update_or_create(
                    instrumento=instrumento, codigo=cap_data["codigo"],
                    defaults={k: v for k, v in campos.items() if k not in ("instrumento", "codigo")},
                )
            result[cap_data["codigo"]] = cap
        self.stdout.write(f"  Capítulos procesados: {len(result)}")
        return result

    def _upsert_preguntas(self, capitulos: dict, preguntas_data: list, catalogo: dict) -> dict:
        result = {}
        errores = []
        for p_data in preguntas_data:
            cap_codigo = p_data.get("capitulo_codigo")
            if cap_codigo not in capitulos:
                errores.append(
                    f"Capítulo '{cap_codigo}' no existe para pregunta '{p_data.get('codigo_externo')}'"
                )
                continue

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
            campos = {
                "capitulo": cap,
                "codigo_externo": p_data["codigo_externo"],
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
                "no_pregunta": p_data.get("no_pregunta", ""),
                "id_preg": p_data.get("id_preg"),
                "es_precargada": p_data.get("es_precargada", False),
                "fuente_precarga": p_data.get("fuente_precarga", ""),
                "activa": p_data.get("activa", True),
            }
            # UUID determinista del fixture (ver _upsert_capitulos).
            if p_data.get("id"):
                pregunta, _ = Pregunta.objects.update_or_create(id=p_data["id"], defaults=campos)
            else:
                pregunta, _ = Pregunta.objects.update_or_create(
                    capitulo=cap, codigo_externo=p_data["codigo_externo"],
                    defaults={k: v for k, v in campos.items() if k not in ("capitulo", "codigo_externo")},
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

    def _upsert_reglas(
        self,
        instrumento: Instrumento,
        preguntas: dict,
        capitulos: dict,
        reglas_data: list,
    ) -> int:
        ReglaSkipLogic.objects.filter(instrumento=instrumento).delete()
        creadas = 0

        for r in reglas_data:
            pregunta_origen = preguntas.get(r.get("origen")) if r.get("origen") else None
            base = {
                "instrumento": instrumento,
                "pregunta_origen": pregunta_origen,
                "valor_trigger": r.get("valor_trigger", ""),
                "accion": r["accion"],
                "descripcion": r.get("descripcion", ""),
                "expresion_origen": r.get("origen_expr", ""),
            }

            if "afecta" in r:
                p = preguntas.get(r["afecta"])
                if p:
                    ReglaSkipLogic.objects.create(**base, pregunta_afectada=p)
                    creadas += 1

            for cod in r.get("afecta_multiple", []):
                p = preguntas.get(cod)
                if p:
                    ReglaSkipLogic.objects.create(**base, pregunta_afectada=p)
                    creadas += 1

            if "afecta_capitulo" in r:
                cap = capitulos.get(r["afecta_capitulo"])
                if cap:
                    ReglaSkipLogic.objects.create(**base, capitulo_afectado=cap)
                    creadas += 1

            for cod in r.get("afecta_capitulos_multiple", []):
                cap = capitulos.get(cod)
                if cap:
                    ReglaSkipLogic.objects.create(**base, capitulo_afectado=cap)
                    creadas += 1

        self.stdout.write(f"  Reglas skip logic: {creadas}")
        return creadas
