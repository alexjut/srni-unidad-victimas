"""
Sprint 21 Fase A — Probador end-to-end de la validación HOGAR/PERSONA.
"""
import os
import sys
import django

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'srni.settings.development')
django.setup()

import requests
from rest_framework_simplejwt.tokens import RefreshToken
from apps.autenticacion.models import Usuario
from apps.encuestas.models import SesionEncuesta
from apps.formulario.models import Pregunta
from apps.hogares.models import MiembroHogar


def main():
    u = Usuario.objects.get(codigo_usuario='ALEXJUT')
    token = str(RefreshToken.for_user(u).access_token)
    H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    BASE = 'http://127.0.0.1:8001/api/encuestas'

    # Tomar una sesión en progreso con su hogar
    sesion = SesionEncuesta.objects.exclude(estado='COMPLETADA').first()
    if not sesion:
        print('ERROR: no hay sesión INICIADA/EN_PROGRESO en BD')
        return
    print(f'Sesion: {sesion.id} hogar={sesion.hogar_id} instr={sesion.instrumento.codigo}')

    # Tomar una pregunta HOGAR del instrumento
    p_hogar = Pregunta.objects.filter(
        capitulo__instrumento=sesion.instrumento, activa=True, nivel='HOGAR'
    ).first()
    p_persona = Pregunta.objects.filter(
        capitulo__instrumento=sesion.instrumento, activa=True, nivel='PERSONA'
    ).first()
    miembro = MiembroHogar.objects.filter(hogar=sesion.hogar_id).first()

    print(f'Pregunta HOGAR:   {p_hogar.codigo_externo if p_hogar else "NINGUNA"}')
    print(f'Pregunta PERSONA: {p_persona.codigo_externo if p_persona else "NINGUNA"}')
    print(f'Miembro 1: {miembro.id if miembro else "NINGUNO"}')

    if not (p_hogar and p_persona and miembro):
        print('ERROR: falta dato para probar')
        return

    # Caso 1: HOGAR sin miembro_id (correcto)
    r = requests.post(f'{BASE}/{sesion.id}/responder/', json={
        'pregunta_id': str(p_hogar.id), 'valor': 'TEST_HOGAR',
    }, headers=H, timeout=5)
    print(f'\n1) HOGAR sin miembro_id: status={r.status_code}  {r.text[:120]}')

    # Caso 2: HOGAR con miembro_id (debe fallar)
    r = requests.post(f'{BASE}/{sesion.id}/responder/', json={
        'pregunta_id': str(p_hogar.id), 'miembro_id': str(miembro.id), 'valor': 'XX',
    }, headers=H, timeout=5)
    print(f'2) HOGAR con miembro_id: status={r.status_code}  {r.text[:160]}')

    # Caso 3: PERSONA con miembro_id (correcto)
    r = requests.post(f'{BASE}/{sesion.id}/responder/', json={
        'pregunta_id': str(p_persona.id), 'miembro_id': str(miembro.id), 'valor': 'PERSONA_1',
    }, headers=H, timeout=5)
    print(f'3) PERSONA con miembro_id: status={r.status_code}  {r.text[:140]}')

    # Caso 4: PERSONA sin miembro_id (debe fallar)
    r = requests.post(f'{BASE}/{sesion.id}/responder/', json={
        'pregunta_id': str(p_persona.id), 'valor': 'XX',
    }, headers=H, timeout=5)
    print(f'4) PERSONA sin miembro_id: status={r.status_code}  {r.text[:160]}')

    # Caso 5: PERSONA con miembro de OTRO hogar
    otro = MiembroHogar.objects.exclude(hogar=sesion.hogar_id).first()
    if otro:
        r = requests.post(f'{BASE}/{sesion.id}/responder/', json={
            'pregunta_id': str(p_persona.id), 'miembro_id': str(otro.id), 'valor': 'XX',
        }, headers=H, timeout=5)
        print(f'5) PERSONA con miembro foráneo: status={r.status_code}  {r.text[:160]}')


if __name__ == '__main__':
    main()
