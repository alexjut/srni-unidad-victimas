# -*- coding: utf-8 -*-
# Reseteo (borra hogares/sesiones, deja vírgenes a las víctimas) + hogar de demo
# Territorial con varios miembros que cubren las restricciones de skip-logic.
#
# Se ejecuta DENTRO del contenedor del backend, alimentando `manage.py shell`:
#   # DRY-RUN (solo cuenta, no toca nada):
#   ssh admin_rni@30.0.1.109 'cd ~/caracterizacion && docker compose exec -T cz_backend python manage.py shell' < scripts/reset_y_demo_territorial.py
#   # APLICAR (destructivo):
#   ssh admin_rni@30.0.1.109 'cd ~/caracterizacion && docker compose exec -e DEMO_APPLY=1 -T cz_backend python manage.py shell' < scripts/reset_y_demo_territorial.py
#
# DESTRUCTIVO solo si la variable de entorno DEMO_APPLY == '1' (si no, DRY-RUN).
import os
import datetime as dt

from apps.hogares.models import Hogar, MiembroHogar
from apps.victimas.models import Victima
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.parametricas.models import Municipio

APLICAR = os.environ.get("DEMO_APPLY") == "1"

print("=" * 64)
print("ESTADO ACTUAL")
print("=" * 64)
print(f"  Hogares:                    {Hogar.objects.count()}")
print(f"  Miembros de hogar:          {MiembroHogar.objects.count()}")
print(f"  Sesiones de encuesta:       {SesionEncuesta.objects.count()}")
print(f"  Respuestas de encuesta:     {RespuestaEncuesta.objects.count()}")
print(f"  Víctimas (padrón):          {Victima.objects.count()}  (NO se borran)")
print(f"  Víctimas ya caracterizadas: {Victima.objects.filter(fecha_ult_caracterizacion__isnull=False).count()}")

if not APLICAR:
    print("\n>>> DRY-RUN: no se borró ni creó nada. (DEMO_APPLY != 1)")
    print(">>> Con DEMO_APPLY=1 se borran Sesiones+Hogares, se resetean las víctimas")
    print(">>> y se crea 1 hogar Territorial de demo con 7 personas.")
else:
    print("\n" + "=" * 64)
    print("APLICANDO RESETEO")
    print("=" * 64)
    dr = RespuestaEncuesta.objects.all().delete()
    ds = SesionEncuesta.objects.all().delete()
    dh = Hogar.objects.all().delete()   # cascade → MiembroHogar
    up = Victima.objects.update(fecha_ult_caracterizacion=None,
                                habilitado_para_caracterizacion=True)
    print(f"  Respuestas borradas: {dr}")
    print(f"  Sesiones borradas:   {ds}")
    print(f"  Hogares borrados:    {dh}")
    print(f"  Víctimas reseteadas (virgen): {up}")

    print("\n" + "=" * 64)
    print("CREANDO HOGAR DEMO TERRITORIAL (sin caracterización iniciada)")
    print("=" * 64)
    aut = (Victima.objects.filter(habilitado_para_caracterizacion=True,
                                  estado_ruv="INCLUIDO", genero="F").first()
           or Victima.objects.filter(habilitado_para_caracterizacion=True).first())
    if not aut:
        print("  ERROR: no hay víctimas en el padrón para usar como autorizado.")
    else:
        muni = getattr(aut, "municipio_residencia", None) or Municipio.objects.first()
        try:
            aut_fnac = dt.date.fromisoformat(str(aut.fecha_nacimiento).strip()[:10])
        except Exception:
            aut_fnac = dt.date(1990, 5, 10)

        hogar = Hogar.objects.create(
            autorizado=aut, municipio=muni, estado="BORRADOR",
            tipo_vivienda="CASA", condicion_ocupacion="ARRIENDO",
            estrato=1, numero_cuartos=3, numero_personas=7,
            observaciones="Hogar DEMO Territorial (skip-logic) — pruebas en vivo.",
        )
        MiembroHogar.objects.create(
            hogar=hogar, victima=aut, es_autorizado=True, rol="MIEMBRO",
            parentesco="", genero=aut.genero or "F", fecha_nacimiento=aut_fnac,
            estado_inclusion="INCLUIDO", fuente_origen="RUV",
            tiene_discapacidad=bool(aut.discapacidad),
        )
        HOY = dt.date(2026, 7, 1)
        def nac(edad):
            return dt.date(HOY.year - edad, HOY.month, min(HOY.day, 28))
        miembros = [
            ("Carlos Andrés Ríos",   "CONYUGE",      "M", 45, False, False, "MIEMBRO"),
            ("María Fernanda Ríos",  "HIJO_A",       "F", 15, False, False, "MIEMBRO"),
            ("Juan David Ríos",      "HIJO_A",       "M", 8,  False, False, "MIEMBRO"),
            ("Sara Sofía Ríos",      "HIJO_A",       "F", 4,  False, False, "MIEMBRO"),
            ("Rosa Elena Vda",       "PADRE_MADRE",  "F", 68, True,  True,  "CUIDADOR_PERMANENTE"),
            ("Pedro Antonio Gómez",  "OTRO_PARIENTE","M", 72, False, True,  "MIEMBRO"),
        ]
        for nombre, par, gen, edad, incl, disc, rol in miembros:
            MiembroHogar.objects.create(
                hogar=hogar, victima=None, es_autorizado=False, rol=rol,
                parentesco=par, genero=gen, fecha_nacimiento=nac(edad),
                nombre_completo=nombre,
                estado_inclusion="INCLUIDO" if incl else "NO_INCLUIDO",
                fuente_origen="ENCUESTADOR", tiene_discapacidad=disc,
            )
        try:
            doc = str(aut.numero_documento)
        except Exception:
            doc = "(cifrado)"
        print(f"  Hogar demo creado: id={hogar.id}")
        print(f"  Estado: {hogar.estado} (SIN sesión de caracterización)")
        print(f"  Miembros: {hogar.miembros.count()} (1 autorizado + 6)")
        print(f"  >>> BUSCAR EN LA APP el documento del autorizado: {doc}")
        print(f"      (tipo_documento_id={aut.tipo_documento_id}, genero={aut.genero})")
print("\nFIN.")
