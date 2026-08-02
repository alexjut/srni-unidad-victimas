"""
De qué dirección viene una petición, con la respuesta que la auditoría acepta.

Existe porque el mismo error se repitió en cinco módulos: cada uno leía
`X-Forwarded-For` por su cuenta y ninguno quitaba el puerto. El WAF de la entidad
(FortiWeb) reenvía al cliente como `IP:puerto` —`186.29.187.18:62432`—, y
`LogAcceso.ip_origen` es un `GenericIPAddressField`: al guardar el log, el INSERT
falla y **la petición entera responde 500**.

Y no falla en cualquier lado: por `localhost` la IP viene limpia y todo anda, así
que el defecto solo aparece cuando se entra por el dominio, que es exactamente
como entran los usuarios. Ese fue el síntoma el 2-ago: la búsqueda funcionaba en
las pruebas locales y devolvía 500 en producción.
"""
from __future__ import annotations


def sin_puerto(direccion: str) -> str:
    """
    Quita el puerto si viene pegado a la dirección.

    IPv4 (`a.b.c.d:puerto`) e IPv6 entre corchetes (`[::1]:puerto`). Una IPv6 sin
    corchetes se deja intacta: tiene varios `:` y ninguno es un puerto.
    """
    direccion = (direccion or '').strip()
    if not direccion:
        return ''
    if direccion.startswith('['):          # [IPv6]:puerto
        return direccion[1:].split(']', 1)[0]
    if direccion.count(':') == 1:          # IPv4:puerto
        return direccion.split(':', 1)[0]
    return direccion                        # IPv4 limpia o IPv6 sin puerto


def ip_de_request(request, *, default: str = '0.0.0.0') -> str:
    """
    IP del cliente detrás de proxies (nginx, ngrok, el WAF), lista para guardar.

    Se toma el primer valor de `X-Forwarded-For` —el cliente original; los que
    siguen son los proxies por los que pasó— y se le quita el puerto. Si no hay
    cabecera, se usa `REMOTE_ADDR`.

    Nunca devuelve algo que rompa un `GenericIPAddressField`: ante cualquier valor
    inválido devuelve `default`. Perder la precisión de una IP en el registro es
    malo; tumbar la operación del encuestador por no poder registrarla, peor.
    """
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    crudo = xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR', '')
    limpia = sin_puerto(crudo)
    if not limpia:
        return default

    # Validación con la misma librería que usa el campo del modelo, para que no
    # pueda pasar nada que el INSERT vaya a rechazar.
    import ipaddress
    try:
        ipaddress.ip_address(limpia)
    except ValueError:
        return default
    return limpia
