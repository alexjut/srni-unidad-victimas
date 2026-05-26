"""
Endpoint de debug para recibir errores de la app móvil y registrarlos
en el log del servidor (Django runserver).

Útil cuando el desarrollador no puede ver los logs de Metro/Expo directamente.

NO incluir en producción — solo desarrollo / staging.
"""
import logging
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('srni.mobile_debug')


@api_view(['POST'])
@permission_classes([AllowAny])
def log_error_mobile(request):
    """
    POST /api/_debug/log/
    Body:
      {
        "nivel": "error" | "warn" | "info",
        "mensaje": "...",
        "stack": "...",
        "pantalla": "/(main)/hogares/conformar",
        "contexto": { "hogarId": "...", "instrumentoId": "..." },
        "dispositivo": "Android 14 / Pixel 6"
      }
    Imprime el error en la terminal del Django runserver con formato visible.
    """
    data = request.data or {}
    nivel = (data.get('nivel') or 'error').upper()
    mensaje = data.get('mensaje') or '(sin mensaje)'
    stack = data.get('stack') or '(sin stack)'
    pantalla = data.get('pantalla') or '(sin pantalla)'
    contexto = data.get('contexto') or {}
    dispositivo = data.get('dispositivo') or '?'
    ts = datetime.utcnow().isoformat()

    sep = '═' * 70
    print()
    print(sep)
    print(f'  📱 ERROR MOBILE [{nivel}]  {ts}')
    print(sep)
    print(f'  Pantalla:    {pantalla}')
    print(f'  Dispositivo: {dispositivo}')
    print(f'  Mensaje:     {mensaje}')
    if contexto:
        print(f'  Contexto:    {contexto}')
    print('  ── Stack ──')
    for line in str(stack).splitlines()[:40]:
        print(f'    {line}')
    print(sep)
    print()

    return Response({'ok': True}, status=status.HTTP_200_OK)
