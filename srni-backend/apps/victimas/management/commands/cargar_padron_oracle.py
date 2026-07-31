"""
Management command: cargar_padron_oracle

Puebla el padrón de SICAV desde el Oracle legacy. Es la última pieza del circuito:

    .9 (Oracle UARIV) ──▶ ESTA CARGA ──▶ Victima (PostgreSQL) ──▶ padrón SQLite ──▶ APK

Qué carga: SOLO VÍCTIMAS INCLUIDAS
-----------------------------------
El padrón no es "todas las personas de la base": es **quién puede ser caracterizado**.
Por norma, se caracteriza a las **víctimas incluidas en el RUV**, y se las
**recaracteriza cada 2 años** para actualizar sus datos.

Así que la carga filtra por `ESTADO_RUV = 1` (Incluido) desde el corte de Vivanto,
que es la única autoridad sobre quién es víctima. → `homologacion.es_victima()`

De dónde sale cada dato
-----------------------
| Aporta | Tabla | Cómo se alcanza |
|---|---|---|
| **quién entra** (estado RUV) | `M_CARACT_TABLA_RA_PER` | `RNIPAQUETES` vía `DBL_VIVANTO` |
| documento, tipo, nombres, fecha nac. | `GIC_PERSONA` | esquema propio en `.9` |
| etnia, discapacidad, género | `M_CARACT_TABLA_RA_PER` | el mismo corte |
| cuándo se caracterizó | `GIC_HOGAR` | → `cargar_fechas_caracterizacion` |

Se unen por `GIC_PERSONA.PER_IDPERSONA = corte.CONS_PERONA`.

Por qué NO se usa `MI_PERSONAS`
--------------------------------
`RNI_MI_PRU.MI_PERSONAS` (49,5 M) es la fuente más completa y era el origen que
queríamos. **Hoy no se puede usar sin riesgo de asignar datos de otra persona:**

* su `PER_ID` no se alcanza desde `GIC_PERSONA.PER_IDMODELOINT` (0 de 20.000);
* el puente `DEP_RUV_PERSONAS_MI` mezcla RUPD/RUV/SIV y el `CONS_PERONA` del corte
  cruza con dos fuentes a la vez → ~2 filas por persona, sin forma de elegir;
* el cruce por documento revienta: 20.000 documentos → 1.159 millones de filas,
  porque hay 1,2 M de documentos de **un solo carácter**.

El detalle y las preguntas para OTI:
`docs/oracle-legacy-padron/hallazgos_identidad_padron.md`

Cobertura — lo que hay que saber
---------------------------------
| | Personas |
|---|---:|
| Víctimas incluidas según el corte | 7.821.641 |
| …que además están en `GIC_PERSONA` | **5.936.769** ← lo que carga esto |
| **Sin identidad en la .9** | **~1,88 M (24 %)** |

Esa cuarta parte **no queda en el padrón** porque la .9 no tiene sus datos. Es
justamente lo que `MI_PERSONAS` resolvería cuando el puente esté aclarado. Mientras
tanto, la APK debe permitir **alta manual** de quien no aparezca.

Rendimiento — medido contra producción el 2026-07-31
----------------------------------------------------
| Consulta | Ritmo | Total |
|---|---:|---:|
| padrón filtrado (JOIN + `estado_ruv=1`) | 3.943 filas/s | **~25 min** |
| fechas de caracterización (local) | 37.078 filas/s | ~1 min |

Nota: una versión anterior medía 220 filas/s con `LEFT JOIN` sin filtro (~10 h). El
`INNER JOIN` con `WHERE estado_ruv = 1` deja a Oracle usar *hash join* en vez de
lookups fila a fila: **18 veces más rápido**, y encima trae menos filas.

Uso
---
    python manage.py cargar_padron_oracle --limite 500                 # prueba
    python manage.py cargar_padron_oracle --carga-inicial --confirmar  # ~25 min
    python manage.py cargar_fechas_caracterizacion --confirmar         # ~1 min

DRY-RUN por defecto. Idempotente: reprocesa por `cons_persona` sin duplicar.
"""
import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.victimas import homologacion as H

# El corte está al otro lado del dblink, así que se trae solo lo que se usa: pedir
# `SELECT *` sobre 10 M filas por dblink es la diferencia entre minutos y horas.
#
# `INNER JOIN` (no LEFT) + `WHERE c.estado_ruv IN (...)` es lo que hace viable esta
# consulta: con LEFT y sin filtro, Oracle resolvía el corte con lookups fila a fila
# (220 filas/s → 10 h). Filtrando, usa hash join: 3.943 filas/s → 25 min.
CONSULTA_PADRON = """
    SELECT p.per_idpersona, p.per_tipodoc, p.per_numerodoc,
           p.per_primernombre, p.per_segundonombre,
           p.per_primerapellido, p.per_segundoapellido,
           p.per_fechanacimiento,
           c.pert_etnica, c.genero_hom, c.discap, c.estado_ruv
      FROM gic_persona p
      JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
        ON c.cons_perona = p.per_idpersona
     WHERE c.estado_ruv IN ({estados})
       AND p.per_numerodoc IS NOT NULL
       AND TRIM(p.per_numerodoc) IS NOT NULL
       AND p.per_idpersona > :desde
"""
# ⚠️ SIN `ORDER BY`, y es deliberado — medido el 2026-07-31:
#
#     sin ORDER BY   5.424 filas/s  →  0,4 h  (24 minutos)
#     con ORDER BY     170 filas/s  →  12,7 h
#
# **32 veces más lento.** La causa: `GIC_PERSONA` tiene 15 índices —sobre documento,
# nombres y apellidos— pero **ninguno sobre `PER_IDPERSONA`**, así que ordenar por él
# obliga a un full scan más un sort de 7,7 millones de filas.
#
# La primera versión llevaba `ORDER BY` para poder reanudar con `--desde` tras un
# corte de red. No compensa: reanudar ahorraba minutos y el orden costaba doce horas.
# Como la carga es **idempotente por `cons_persona`**, si se corta basta con volver a
# correrla entera — 25 minutos— y las ya cargadas se actualizan sin duplicar.
#
# `--desde` se mantiene como filtro opcional (útil para acotar un rango a mano), pero
# ya no es el mecanismo de recuperación: el mecanismo es la idempotencia.


class Command(BaseCommand):
    help = ("Carga el padrón de víctimas desde el Oracle legacy hacia la base de "
            "SICAV. DRY-RUN por defecto.")

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true",
                            help="Escribe de verdad. Sin él, solo informa.")
        parser.add_argument("--limite", type=int, default=0,
                            help="Procesa solo N personas (para probar).")
        parser.add_argument("--lote", type=int, default=1000,
                            help="Filas por fetch (default 1000).")
        parser.add_argument("--carga-inicial", action="store_true",
                            help="Inserta por lotes (bulk) en vez de upsert fila a "
                                 "fila: 51 filas/s -> minutos. Solo para la PRIMERA "
                                 "carga; exige que la tabla este vacia porque no "
                                 "deduplica.")
        parser.add_argument("--estados", default="1",
                            help="Estados del RUV a cargar, separados por coma. Por "
                                 "defecto '1' (Incluido), que es la definición de "
                                 "quién puede ser caracterizado. Usar otros valores "
                                 "solo para análisis: mete al padrón a gente que NO "
                                 "es víctima incluida.")
        parser.add_argument("--desde", type=int, default=0,
                            help="Procesa solo per_idpersona mayores a este (para "
                                 "acotar un rango a mano; NO es el mecanismo de "
                                 "recuperación: para eso basta con volver a correr, "
                                 "que es idempotente).")

    def handle(self, *args, **opts):
        from apps.victimas.models import CargaPadron

        confirmar, limite, lote = opts["confirmar"], opts["limite"], opts["lote"]
        desde = opts["desde"]
        carga_inicial = opts["carga_inicial"]

        # Los estados se interpolan en el SQL, no van como bind: Oracle no acepta una
        # lista en un solo bind de `IN`. Por eso se validan como enteros primero —
        # interpolar texto sin validar en un SQL es cómo se inyecta.
        try:
            estados = [int(e) for e in opts["estados"].split(",") if e.strip()]
        except ValueError:
            raise CommandError(f"--estados debe ser números separados por coma, "
                               f"no {opts['estados']!r}")
        if not estados:
            raise CommandError("--estados no puede quedar vacío.")
        consulta = CONSULTA_PADRON.format(estados=", ".join(str(e) for e in estados))
        if estados != [H.ESTADO_INCLUIDO]:
            self.stdout.write(self.style.WARNING(
                f"  ⚠ cargando estados {estados} — el padrón normal es solo "
                f"[{H.ESTADO_INCLUIDO}] (Incluido). Con otros estados entra al padrón "
                f"gente que NO es víctima incluida."))
        if carga_inicial and confirmar:
            # El criterio NO es "la tabla está vacía" —siempre hay algún registro de
            # prueba o de alta manual— sino "¿ya hubo una carga masiva?". Insertar por
            # lotes no deduplica, así que repetirla duplicaría el padrón entero.
            previa = CargaPadron.objects.filter(estado="COMPLETADA",
                                                creadas__gt=1000).first()
            if previa:
                raise CommandError(
                    f"Ya hay una carga inicial del {previa.iniciada_en:%Y-%m-%d %H:%M} "
                    f"con {previa.creadas:,} personas. `--carga-inicial` inserta sin "
                    f"deduplicar, así que duplicaría el padrón.\n"
                    f"Para recargar o actualizar, corre SIN `--carga-inicial`: el "
                    f"upsert es más lento pero es idempotente.")
        acumulador = [] if (carga_inicial and confirmar) else None

        conexion = self._abrir()
        catalogo_tipos = H.cargar_catalogo_tipodoc_oracle()
        tipos_sicav = self._tipos_sicav()

        carga = CargaPadron.objects.create(
            origen=(f"{conexion['dsn']} · GIC_PERSONA + M_CARACT_TABLA_RA_PER "
                    f"(estado_ruv={','.join(str(e) for e in estados)})"),
            estado="EN_CURSO" if confirmar else "SIMULADA",
        )
        self.stdout.write(self.style.WARNING(
            f"\n{'ESCRITURA REAL' if confirmar else 'DRY-RUN (no escribe)'} — "
            f"origen {conexion['dsn']}\n"
            f"  catálogo de tipos de documento de Oracle: {len(catalogo_tipos)} entradas\n"
        ))

        contadores = {"leidas": 0, "creadas": 0, "actualizadas": 0,
                      "descartadas": 0, "sin_tipo_documento": 0}
        motivos, inicio = {}, time.monotonic()
        ultimo_id = desde
        if desde:
            self.stdout.write(f"  reanudando desde per_idpersona > {desde:,}\n")

        try:
            cursor = conexion["con"].cursor()
            cursor.arraysize = lote
            cursor.execute(consulta, {"desde": desde})
            while True:
                filas = cursor.fetchmany(lote)
                if not filas:
                    break
                for fila in filas:
                    self._procesar(fila, contadores, motivos, catalogo_tipos,
                                   tipos_sicav, confirmar, acumulador)
                    ultimo_id = fila[0] or ultimo_id
                    if limite and contadores["leidas"] >= limite:
                        break
                if acumulador is not None and len(acumulador) >= 2000:
                    self._volcar(acumulador)
                self.stdout.write(
                    f"  {contadores['leidas']:>9,} leídas · "
                    f"{contadores['creadas']:>8,} nuevas · "
                    f"{contadores['actualizadas']:>8,} actualizadas · "
                    f"{contadores['descartadas']:>7,} descartadas")
                if limite and contadores["leidas"] >= limite:
                    break
        except Exception as exc:                                   # noqa: BLE001
            carga.estado = "FALLIDA"
            carga.detalle = (f"{type(exc).__name__}: {exc}"[:1900] +
                             f" | reanudar con --desde {ultimo_id}")
            self._cerrar(carga, contadores, motivos)
            raise CommandError(
                f"La carga falló tras {contadores['leidas']:,} filas: {exc}\n"
                f"La carga es idempotente: volver a correrla entera (~25 min) "
                f"actualiza lo ya cargado sin duplicar.\n"
                f"Último per_idpersona visto: {ultimo_id} (el orden no está "
                f"garantizado, así que NO sirve como punto de corte exacto).")
            if acumulador:
                self._volcar(acumulador)
        finally:
            conexion["con"].close()

        if carga.estado == "EN_CURSO":
            carga.estado = "COMPLETADA"
        self._cerrar(carga, contadores, motivos)

        segundos = time.monotonic() - inicio
        self.stdout.write(self.style.SUCCESS(
            f"\n{'Cargadas' if confirmar else 'Simuladas'} {contadores['leidas']:,} "
            f"personas en {segundos:.0f}s"))
        self.stdout.write(
            f"  nuevas {contadores['creadas']:,} · actualizadas "
            f"{contadores['actualizadas']:,} · descartadas {contadores['descartadas']:,}")
        self.stdout.write(self.style.WARNING(
            f"  sin tipo de documento: {contadores['sin_tipo_documento']:,} "
            f"— se encuentran por el índice de respaldo, con aviso al encuestador"))
        for motivo, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f"    descarte · {motivo}: {n:,}")
        self.stdout.write(self.style.NOTICE(
            f"  filtrado por estado_ruv IN ({', '.join(str(e) for e in estados)}) "
            f"— el padrón lleva solo víctimas incluidas"))
        self.stdout.write(self.style.NOTICE(
            "  SIGUIENTE PASO: `cargar_fechas_caracterizacion --confirmar` (~1 min) "
            "para la regla de recaracterización a 2 años"))
        self.stdout.write(f"  último per_idpersona visto: {ultimo_id:,}")

    # ── piezas ───────────────────────────────────────────────────────────────
    def _abrir(self):
        """Conexión de LECTURA al Oracle legacy, reusando la capa que ya existe."""
        from apps.sincronizacion.oracle import conexion as cx
        try:
            cfg = cx.resolver_config(cx.DESTINO_PRODUCCION)
        except cx.DestinoNoConfigurado as exc:
            raise CommandError(
                f"{exc}\nExporta ORACLE_PROD_HOST/SERVICE/USER/PASSWORD antes de correr.")
        return {"con": cx.abrir_conexion(cx.DESTINO_PRODUCCION),
                "dsn": f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['service']}"}

    @staticmethod
    def _tipos_sicav():
        from apps.parametricas.models import TipoDocumento
        return {t.codigo: t for t in TipoDocumento.objects.all()}

    def _procesar(self, fila, contadores, motivos, catalogo_tipos, tipos_sicav,
                  confirmar, acumulador=None):
        from apps.victimas.models import Victima

        (cons, tipodoc_raw, numero, n1, n2, a1, a2, f_nac,
         etnia, genero, discap, estado) = fila
        contadores["leidas"] += 1

        numero = (numero or "").strip()
        if not numero:
            contadores["descartadas"] += 1
            motivos["sin número de documento"] = motivos.get("sin número de documento", 0) + 1
            return

        codigo_tipo = H.homologar_tipo_documento(tipodoc_raw, catalogo_tipos)
        tipo = tipos_sicav.get(codigo_tipo) if codigo_tipo else None
        if tipo is None:
            contadores["sin_tipo_documento"] += 1

        if not confirmar:
            return

        # ── carga inicial: se acumula para insertar por lotes ────────────────
        # `update_or_create` hace un SELECT y un INSERT por persona: medido, 51
        # filas/s → **42 horas** para el padrón completo. Con `bulk_create` el mismo
        # trabajo se hace en lotes y baja a minutos.
        #
        # El precio es que `bulk_create` NO llama a `save()`, así que los dos hashes
        # —que normalmente calcula el modelo— hay que calcularlos aquí. Se usan las
        # MISMAS funciones (`doc_hash` / `num_hash`), nunca una fórmula reescrita:
        # duplicar esa lógica es exactamente el defecto que costó una tarde arreglar.
        if acumulador is not None:
            from apps.victimas.repository.base import doc_hash, num_hash
            acumulador.append(Victima(
                cons_persona=cons,
                tipo_documento=tipo,
                numero_documento=numero,
                numero_documento_hash=doc_hash(codigo_tipo or "", numero),
                numero_documento_hash_sin_tipo=num_hash(numero),
                primer_nombre=(n1 or "").strip(),
                segundo_nombre=(n2 or "").strip(),
                primer_apellido=(a1 or "").strip(),
                segundo_apellido=(a2 or "").strip(),
                fecha_nacimiento=f_nac.date().isoformat() if f_nac else "",
                genero=H.homologar_genero(genero),
                pertenencia_etnica=H.homologar_etnia(etnia),
                discapacidad=H.homologar_discapacidad(discap),
                # Informativo: NO se deriva de aquí la habilitación (ver homologacion).
                estado_ruv=H.homologar_estado_ruv(estado) or "EN_PROCESO",
                fuente_origen="RUV",
            ))
            contadores["creadas"] += 1
            return

        # Idempotencia por `cons_persona`: es el id de la persona en el legacy, así que
        # reprocesar actualiza en vez de duplicar. Los duplicados de documento SÍ se
        # cargan como registros separados —decisión del 29-jul— porque pueden ser
        # personas distintas y fusionarlos borraría a una del padrón.
        _, creada = Victima.objects.update_or_create(
            cons_persona=cons,
            defaults={
                "tipo_documento": tipo,
                "numero_documento": numero,
                "primer_nombre": (n1 or "").strip(),
                "segundo_nombre": (n2 or "").strip(),
                "primer_apellido": (a1 or "").strip(),
                "segundo_apellido": (a2 or "").strip(),
                "fecha_nacimiento": f_nac.date().isoformat() if f_nac else "",
                "genero": H.homologar_genero(genero),
                "pertenencia_etnica": H.homologar_etnia(etnia),
                "discapacidad": H.homologar_discapacidad(discap),
                "estado_ruv": H.homologar_estado_ruv(estado) or "EN_PROCESO",
                "fuente_origen": "RUV",
                # estado_ruv y habilitado_para_caracterizacion se dejan en el default
                # del modelo: ver el docstring del comando.
            },
        )
        contadores["creadas" if creada else "actualizadas"] += 1

    @staticmethod
    def _volcar(acumulador):
        """Inserta el lote acumulado y lo vacía. `ignore_conflicts` es una red por si
        la fuente trajera un `cons_persona` repetido: mejor perder ese duplicado que
        abortar una carga de millones."""
        from apps.victimas.models import Victima
        Victima.objects.bulk_create(acumulador, batch_size=500, ignore_conflicts=True)
        acumulador.clear()

    @staticmethod
    def _cerrar(carga, contadores, motivos):
        for campo, valor in contadores.items():
            setattr(carga, campo, valor)
        carga.motivos_descarte = motivos
        carga.terminada_en = timezone.now()
        carga.save()
