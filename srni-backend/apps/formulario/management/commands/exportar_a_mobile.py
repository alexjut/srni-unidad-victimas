"""
python manage.py exportar_a_mobile

Exporta los 8 instrumentos cargados en BD a srni-mobile/assets/instrumentos/
en el formato exacto que devuelve InstrumentoCompletoView. Genera un index.json.

Habilita la arquitectura híbrida: el APK trae los instrumentos pre-empaquetados
y funciona offline desde el primer login. La sincronización remota solo se
usa para versiones más nuevas.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand

from apps.formulario.models import Instrumento


class Command(BaseCommand):
    help = 'Exporta los instrumentos a srni-mobile/assets/instrumentos/'

    def handle(self, *args, **opts):
        root = Path(__file__).resolve().parents[5]  # srni-backend/apps/formulario/management/commands/X.py → root
        out_dir = root / 'srni-mobile' / 'assets' / 'instrumentos'
        out_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write('=' * 60)
        self.stdout.write('EXPORTANDO INSTRUMENTOS A srni-mobile/assets/instrumentos/')
        self.stdout.write('=' * 60)

        indice = []
        total_bytes = 0

        for instr in Instrumento.objects.filter(activo=True).order_by('codigo'):
            data = self._serializar(instr)
            archivo = f'{instr.codigo.lower()}_{instr.version.lower()}.json'
            ruta = out_dir / archivo
            ruta.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

            n_caps = len(data['capitulos'])
            n_pregs = sum(len(c['preguntas']) for c in data['capitulos'])
            n_opcs = sum(len(p['opciones']) for c in data['capitulos'] for p in c['preguntas'])
            n_reglas = len(data['reglas'])
            size_kb = ruta.stat().st_size / 1024
            total_bytes += ruta.stat().st_size

            indice.append({
                'codigo': instr.codigo,
                'version': instr.version,
                'nombre': instr.nombre,
                'archivo': archivo,
                'capitulos': n_caps,
                'preguntas': n_pregs,
            })

            self.stdout.write(
                f'  {instr.codigo:<18} {instr.version:<5}  '
                f'caps={n_caps:>3}  pregs={n_pregs:>4}  '
                f'opcs={n_opcs:>4}  reglas={n_reglas:>3}  ({size_kb:>6.1f} KB)'
            )

        indice_ruta = out_dir / 'index.json'
        indice_ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding='utf-8')
        total_bytes += indice_ruta.stat().st_size

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'OK. {len(indice)} instrumentos exportados, {total_bytes / 1024:.1f} KB total.'
        ))
        self.stdout.write(f'   Directorio: {out_dir}')

    def _serializar(self, instr):
        """Mismo formato que InstrumentoCompletoView del backend."""
        capitulos = []
        for cap in instr.capitulos.all().order_by('orden'):
            preguntas = []
            for p in cap.preguntas.filter(activa=True).order_by('orden'):
                opciones = [
                    {
                        'id': str(o.id),
                        'valor': o.valor,
                        'etiqueta': o.etiqueta,
                        'orden': o.orden,
                        'finaliza_capitulo': o.finaliza_capitulo,
                    }
                    for o in p.opciones.all().order_by('orden')
                ]
                preguntas.append({
                    'id': str(p.id),
                    'codigo_externo': p.codigo_externo,
                    'no_pregunta': p.no_pregunta or '',
                    'texto': p.texto,
                    'descripcion_ayuda': p.descripcion_ayuda or '',
                    'tipo': p.tipo,
                    'nivel': p.nivel,
                    'orden': p.orden,
                    'obligatoria': p.obligatoria,
                    'activa': p.activa,
                    'validaciones': p.validaciones or {},
                    'opciones': opciones,
                })
            capitulos.append({
                'id': str(cap.id),
                'codigo': cap.codigo,
                'nombre': cap.nombre,
                'orden': cap.orden,
                'nivel': cap.nivel,
                'preguntas': preguntas,
            })

        reglas = []
        for r in instr.reglas.select_related('pregunta_origen', 'pregunta_afectada').all():
            reglas.append({
                'id': str(r.id),
                'pregunta_origen': str(r.pregunta_origen_id) if r.pregunta_origen_id else None,
                'pregunta_origen_codigo': r.pregunta_origen.codigo_externo if r.pregunta_origen_id else None,
                'valor_trigger': r.valor_trigger,
                'expresion_origen': r.expresion_origen or '',
                'pregunta_afectada': str(r.pregunta_afectada_id) if r.pregunta_afectada_id else None,
                'pregunta_afectada_codigo': r.pregunta_afectada.codigo_externo if r.pregunta_afectada_id else None,
                'capitulo_afectado': str(r.capitulo_afectado_id) if r.capitulo_afectado_id else None,
                'accion': r.accion,
            })

        return {
            'id': str(instr.id),
            'codigo': instr.codigo,
            'nombre': instr.nombre,
            'version': instr.version,
            'capitulos': capitulos,
            'reglas': reglas,
        }
