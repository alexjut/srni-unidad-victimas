# -*- coding: utf-8 -*-
# Reset dirigido de PROD: conserva SOLO el hogar "05" (autorizado cons_persona=10005,
# doc 9990100005, ejemplo completo) con su sesión/respuestas; borra el resto de
# hogares/sesiones/respuestas y deja VÍRGENES a las demás víctimas (listas para
# caracterizar desde 0). NO crea demo nuevo.
#
# DRY-RUN (default):  ... 'docker exec -i cz_backend python manage.py shell' < reset_conservar_hogar05.py
# APLICAR:            ... 'docker exec -i -e RESET_APPLY=1 cz_backend python manage.py shell' < reset_conservar_hogar05.py
import os
from apps.hogares.models import Hogar, MiembroHogar
from apps.victimas.models import Victima
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta

APLICAR = os.environ.get("RESET_APPLY") == "1"
KEEP_CONS = 10005  # autorizado del hogar "05" (doc 9990100005)

keep_ids = list(Hogar.objects.filter(autorizado__cons_persona=KEEP_CONS).values_list("id", flat=True))

# FK de RespuestaEncuesta hacia la sesión (nombre robusto)
resp_fk = next((f.name for f in RespuestaEncuesta._meta.get_fields()
                if getattr(f, "related_model", None) is SesionEncuesta), None)

ses_keep = SesionEncuesta.objects.filter(hogar_id__in=keep_ids)
ses_del = SesionEncuesta.objects.exclude(hogar_id__in=keep_ids)
resp_keep = RespuestaEncuesta.objects.filter(**{f"{resp_fk}__in": ses_keep}) if resp_fk else RespuestaEncuesta.objects.none()
resp_del = RespuestaEncuesta.objects.filter(**{f"{resp_fk}__in": ses_del}) if resp_fk else RespuestaEncuesta.objects.none()

print("=" * 60)
print("PLAN")
print("=" * 60)
print(f"  KEEP hogar(es) 05 (cons={KEEP_CONS}): {len(keep_ids)}  ids={[str(i)[:8] for i in keep_ids]}")
print(f"    - miembros que quedan:  {MiembroHogar.objects.filter(hogar_id__in=keep_ids).count()}")
print(f"    - sesiones que quedan:  {ses_keep.count()}  respuestas: {resp_keep.count()}")
print(f"  BORRAR hogares:           {Hogar.objects.exclude(id__in=keep_ids).count()}")
print(f"    - miembros a borrar:    {MiembroHogar.objects.exclude(hogar_id__in=keep_ids).count()}")
print(f"    - sesiones a borrar:    {ses_del.count()}  respuestas: {resp_del.count()}")
print(f"  Víctimas a dejar vírgenes (todas menos cons={KEEP_CONS}): "
      f"{Victima.objects.exclude(cons_persona=KEEP_CONS).count()}")
print(f"  (RespuestaEncuesta FK a sesión = {resp_fk!r})")

if not APLICAR:
    print("\n>>> DRY-RUN: nada se tocó. Con RESET_APPLY=1 se aplica.")
else:
    print("\n" + "=" * 60)
    print("APLICANDO")
    print("=" * 60)
    dr = resp_del.delete()
    ds = ses_del.delete()
    dh = Hogar.objects.exclude(id__in=keep_ids).delete()  # cascade -> MiembroHogar
    uv = Victima.objects.exclude(cons_persona=KEEP_CONS).update(
        fecha_ult_caracterizacion=None, habilitado_para_caracterizacion=True)
    print(f"  Respuestas borradas: {dr}")
    print(f"  Sesiones borradas:   {ds}")
    print(f"  Hogares borrados:    {dh}")
    print(f"  Víctimas vírgenes:   {uv}")
    print("\n  ESTADO FINAL:")
    print(f"    Hogares: {Hogar.objects.count()} | Miembros: {MiembroHogar.objects.count()} | "
          f"Sesiones: {SesionEncuesta.objects.count()} | Respuestas: {RespuestaEncuesta.objects.count()}")
print("\nFIN.")
