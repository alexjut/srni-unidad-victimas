"""
Comando idempotente para cargar el perfil ASISTENCIA V8.

Uso:
    python manage.py cargar_diccionario_v8
    python manage.py cargar_diccionario_v8 --fixture=ruta/al/fixture.json
    python manage.py cargar_diccionario_v8 --dry-run

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


class Command(BaseCommand):
    help = "Carga el perfil ASISTENCIA V8 desde fixture JSON (idempotente)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="apps/formulario/fixtures/perfil_asistencia_v8.json",
            help="Ruta al fixture JSON relativa al directorio srni-backend",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la carga sin persistir. Útil para validar el fixture.",
        )

    def handle(self, *args, **opts):
        fixture_path = Path(opts["fixture"])
        if not fixture_path.exists():
            raise CommandError(f"Fixture no encontrado: {fixture_path}")

        try:
            data = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CommandError(f"Fixture JSON inválido: {e}")

        self._validar_estructura(data)

        with transaction.atomic():
            perfil = self._upsert_perfil(data["perfil"])
            version = self._upsert_version(perfil, data["instrumento_version"])
            capitulos_map = self._upsert_capitulos(version, data["capitulos"])
            preguntas_map = self._upsert_preguntas(capitulos_map, data["preguntas"])
            n_reglas = self._upsert_reglas(
                version, preguntas_map, capitulos_map, data.get("reglas_skip_logic", [])
            )

            if opts["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING(
                    f"DRY RUN - sin cambios en BD. "
                    f"Se habrian cargado: {len(capitulos_map)} capitulos, "
                    f"{len(preguntas_map)} preguntas, {n_reglas} reglas."
                ))
                return

        self.stdout.write(self.style.SUCCESS(
            f"OK Cargado: perfil={perfil.codigo} version={version.numero} | "
            f"capitulos={len(capitulos_map)} | preguntas={len(preguntas_map)} | "
            f"reglas={n_reglas}"
        ))

    def _validar_estructura(self, data):
        requeridos = ["perfil", "instrumento_version", "capitulos", "preguntas"]
        faltantes = [k for k in requeridos if k not in data]
        if faltantes:
            raise CommandError(f"Fixture incompleto — faltan secciones: {faltantes}")

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

    def _upsert_preguntas(self, capitulos, preguntas_data):
        result = {}
        errores = []
        for p_data in preguntas_data:
            cap_codigo = p_data.get("capitulo_codigo")
            if cap_codigo not in capitulos:
                errores.append(
                    f"⚠ Capítulo '{cap_codigo}' no existe para pregunta '{p_data.get('codigo_externo')}'"
                )
                continue

            cap = capitulos[cap_codigo]
            pregunta, _ = Pregunta.objects.update_or_create(
                capitulo=cap,
                codigo_externo=p_data["codigo_externo"],
                defaults={
                    "texto": p_data["texto"],
                    "variable_bd": p_data.get("variable_bd", p_data["codigo_externo"].replace("_tel", "")),
                    "tipo": p_data["tipo"],
                    "nivel": p_data.get("nivel", "PERSONA"),
                    "orden": p_data.get("orden", 0),
                    "obligatoria": p_data.get("obligatoria", True),
                    "validaciones": p_data.get("validaciones", {}),
                    "descripcion_ayuda": p_data.get("descripcion_ayuda", ""),
                    "codigo_diagrama": p_data["codigo_externo"].replace("_tel", ""),
                },
            )
            result[p_data["codigo_externo"]] = pregunta

            for opt_data in p_data.get("opciones", []):
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
            self.stderr.write(e)
        self.stdout.write(f"  Preguntas procesadas: {len(result)} ({len(errores)} errores)")
        return result

    def _upsert_reglas(self, version, preguntas, capitulos, reglas_data):
        # Las reglas son declarativas — se regeneran en cada carga
        ReglaSkipLogic.objects.filter(instrumento=version).delete()
        creadas = 0

        for r in reglas_data:
            pregunta_origen = preguntas.get(r.get("origen")) if r.get("origen") else None
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
