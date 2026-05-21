from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """5 intentos de login por minuto por IP — protección anti-fuerza-bruta."""
    scope = 'login'


class BusquedaRNIThrottle(UserRateThrottle):
    """30 búsquedas RNI por hora por usuario — protección anti-enumeración."""
    scope = 'busqueda_rni'


class IAConsultaThrottle(UserRateThrottle):
    """20 consultas IA por hora por usuario."""
    scope = 'ia_consulta'
