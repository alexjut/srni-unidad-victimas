"""
Convierte el export crudo de la Query A v2 (TSV) en `respuestas_oracle.json`.

El catálogo de respuestas de Oracle NO se edita a mano: se genera desde el export de
prod. Este comando es el único paso entre el TSV que sale del cliente SQL y el JSON
que carga el resolver, para que siempre se pueda contestar "¿de dónde salió este id?"
con "de esta consulta, este día".

    python manage.py generar_catalogo_respuestas docs/oracle-legacy/query_a_v2.tsv

Sobre el truncado: si el export trae exactamente 200 filas, casi seguro lo cortó el
cliente SQL (el SQL no lleva límite). El comando lo detecta y lo AVISA, pero genera
igual y deja `_meta.completo = false`: un catálogo parcial declarado como parcial es
útil; uno parcial que se cree completo haría que el resolver concluyera "esta pregunta
no existe en Oracle" cuando lo cierto es "no la exportamos".
"""
import collections
import json
import pathlib

from django.core.management.base import BaseCommand, CommandError

from apps.sincronizacion.oracle import catalogos

COLUMNAS = [
    "INS_IDINSTRUMENTO", "TEM_IDTEMA", "IXP_ORDEN", "PRE_TIPOPREGUNTA",
    "PRE_IDPREGUNTA", "PRE_PREGUNTA", "RES_IDRESPUESTA", "RES_RESPUESTA",
    "RES_ACTIVA", "ESCRIBIBLE",
]
# Tamaño de rejilla con el que ya nos cortó dos veces el export.
CORTE_TIPICO_DEL_CLIENTE = 200
# Referencia para dimensionar lo que falta (territorial de SICAV).
PREGUNTAS_ESPERADAS = 290


class Command(BaseCommand):
    help = "Genera respuestas_oracle.json desde el export TSV de la Query A v2."

    def add_arguments(self, parser):
        parser.add_argument("tsv", help="Ruta del export crudo (TSV con cabecera).")
        parser.add_argument(
            "--salida", default=str(catalogos.ARCHIVO_RESPUESTAS),
            help="Destino del JSON (por defecto, el que carga el resolver).")
        parser.add_argument(
            "--fecha", required=True,
            help="Fecha del export contra prod (YYYY-MM-DD), para la trazabilidad.")

    def handle(self, *args, **opciones):
        origen = pathlib.Path(opciones["tsv"])
        if not origen.exists():
            raise CommandError(f"No existe el export: {origen}")
        filas = self._leer(origen)
        preguntas = self._agrupar(filas)

        instrumentos = {int(f["INS_IDINSTRUMENTO"]) for f in filas}
        if instrumentos != {catalogos.INS_IDINSTRUMENTO_CARACTERIZACION}:
            raise CommandError(
                f"El export trae los instrumentos {sorted(instrumentos)} y Oracle solo "
                f"tiene el 1 (Query B). Revisar la consulta antes de generar nada.")

        completo = self._es_completo(len(filas), len(preguntas))
        catalogo = self._armar(filas, preguntas, origen, opciones["fecha"], completo)
        destino = pathlib.Path(opciones["salida"])
        destino.write_text(
            json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._informar(catalogo, destino, len(filas))

    def _leer(self, origen):
        filas = []
        with open(origen, encoding="utf-8") as fh:
            cabecera = fh.readline().rstrip("\n").split("\t")
            if cabecera != COLUMNAS:
                raise CommandError(
                    f"Cabecera inesperada.\n  esperada: {COLUMNAS}\n  recibida: {cabecera}\n"
                    f"El export debe salir de la Query A v2 de §3b-bis-D del traspaso.")
            for n, linea in enumerate(fh, start=2):
                linea = linea.rstrip("\n")
                if not linea.strip():
                    continue
                campos = linea.split("\t")
                if len(campos) != len(COLUMNAS):
                    raise CommandError(
                        f"Línea {n}: {len(campos)} columnas, se esperaban {len(COLUMNAS)}. "
                        f"¿El texto de alguna pregunta trae un tabulador?")
                filas.append(dict(zip(COLUMNAS, campos)))
        if not filas:
            raise CommandError("El export no trae ni una fila de datos.")
        return filas

    def _agrupar(self, filas):
        preguntas = collections.OrderedDict()
        for f in filas:
            pre = int(f["PRE_IDPREGUNTA"])
            if pre not in preguntas:
                preguntas[pre] = {
                    "pre_idpregunta": pre,
                    "tem_idtema": int(f["TEM_IDTEMA"]),
                    "ixp_orden": int(f["IXP_ORDEN"]),
                    "pre_tipopregunta": f["PRE_TIPOPREGUNTA"],
                    "pre_pregunta": f["PRE_PREGUNTA"],
                    "respuestas": [],
                }
            preguntas[pre]["respuestas"].append({
                "res_idrespuesta": int(f["RES_IDRESPUESTA"]),
                "res_respuesta": f["RES_RESPUESTA"],
                "res_activa": f["RES_ACTIVA"],
                # La columna que evita el fallo silencioso: sin fila en
                # GIC_N_INSTRUMENTOXRESP, el procedure traga NO_DATA_FOUND.
                "escribible": f["ESCRIBIBLE"] == "SI",
            })
        return preguntas

    def _es_completo(self, n_filas, n_preguntas):
        if n_filas == CORTE_TIPICO_DEL_CLIENTE:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  El export trae EXACTAMENTE {CORTE_TIPICO_DEL_CLIENTE} filas: ese "
                f"número redondo es la firma del cliente SQL cortando, no el final del "
                f"instrumento.\n    El catálogo se marca completo=false. Reexportar A "
                f"ARCHIVO (SPOOL / 'export to file'), no a la rejilla.\n"))
            return False
        if n_preguntas < PREGUNTAS_ESPERADAS:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  {n_preguntas} preguntas, y el territorial de SICAV tiene "
                f"{PREGUNTAS_ESPERADAS} con id_preg. Se marca completo=false: puede que "
                f"Oracle tenga menos, pero eso hay que comprobarlo, no suponerlo.\n"))
            return False
        return True

    def _armar(self, filas, preguntas, origen, fecha, completo):
        temas = sorted({p["tem_idtema"] for p in preguntas.values()})
        orden_max = max(p["ixp_orden"] for p in preguntas.values())
        ultima = list(preguntas.values())[-1]["pre_idpregunta"]
        no_escribibles = [
            {"res_idrespuesta": r["res_idrespuesta"], "res_respuesta": r["res_respuesta"],
             "pre_idpregunta": p["pre_idpregunta"], "pre_pregunta": p["pre_pregunta"]}
            for p in preguntas.values() for r in p["respuestas"] if not r["escribible"]
        ]
        meta = {
            "fuente": f"Query A v2 contra RNIENTREVISTA (prod, solo lectura, {fecha})",
            "export": str(origen).replace("\\", "/"),
            "generado_por": "python manage.py generar_catalogo_respuestas",
            "instrumento": {
                "ins_idinstrumento": catalogos.INS_IDINSTRUMENTO_CARACTERIZACION,
                "nombre": "CARACTERIZACION",
                "nota": "Query B: GIC_INSTRUMENTO tiene 1 sola fila. Oracle no separa "
                        "por instrumento como SICAV (que tiene 8).",
            },
            "completo": completo,
            "escribibilidad_verificada": True,
            "escribibilidad_alcance": (
                "Solo las filas exportadas. Query C2 contó 153 huérfanas en toda la "
                f"tabla; aquí se identifican {len(no_escribibles)}."),
            "riesgo_too_many_rows": False,
            "riesgo_too_many_rows_nota": (
                "Query C3: 0 preguntas y 0 respuestas en varios instrumentos ⇒ el "
                "SELECT INTO sin filtro de instrumento no puede devolver 2+ filas."),
            "conteos": {
                "preguntas": len(preguntas),
                "respuestas": sum(len(p["respuestas"]) for p in preguntas.values()),
                "respuestas_no_escribibles": len(no_escribibles),
            },
        }
        if not completo:
            meta["truncado"] = {
                "motivo": "El cliente SQL cortó el export; el SQL no lleva límite.",
                "filas_exportadas": len(filas),
                "temas_cubiertos": temas,
                "ultimo_ixp_orden": orden_max,
                "ultima_pregunta": ultima,
                "referencia": f"SICAV territorial tiene {PREGUNTAS_ESPERADAS} preguntas "
                              f"con id_preg.",
                "consecuencia": "Una pregunta AUSENTE de este catálogo NO significa que "
                                "no exista en Oracle: significa que no la exportamos.",
            }
        return {"_meta": meta, "no_escribibles": no_escribibles,
                "preguntas": list(preguntas.values())}

    def _informar(self, catalogo, destino, n_filas):
        c = catalogo["_meta"]["conteos"]
        self.stdout.write(self.style.SUCCESS(f"Catálogo generado: {destino}"))
        self.stdout.write(
            f"  {c['preguntas']} preguntas / {c['respuestas']} respuestas "
            f"({n_filas} filas del export)")
        completo = catalogo["_meta"]["completo"]
        etiqueta = "COMPLETO" if completo else "PARCIAL (declarado como tal)"
        self.stdout.write(f"  cobertura: {etiqueta}")
        if catalogo["no_escribibles"]:
            self.stdout.write(self.style.WARNING(
                f"\n  {len(catalogo['no_escribibles'])} respuestas NO escribibles "
                f"(Oracle las ofrece pero no sabe guardarlas ⇒ pendiente de negocio):"))
            por_pregunta = collections.defaultdict(list)
            for n in catalogo["no_escribibles"]:
                por_pregunta[n["pre_idpregunta"]].append(n["res_respuesta"])
            for pre, opciones in sorted(por_pregunta.items()):
                self.stdout.write(f"    preg {pre}: {', '.join(opciones)}")