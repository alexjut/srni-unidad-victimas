"""
Validadores cruzados del hogar.
Fuente: Manual Usuario VIVANTO — Entrevista de Caracterización, Perfil Asistencia
        (UARIV 520.06.06-1 v01, 07/10/2021)

Cada validador retorna None si pasa, o levanta ValidationError con mensaje humano
que indica la sección del manual para trazabilidad ante el supervisor SRNI.
"""
from datetime import date
from django.core.exceptions import ValidationError


class HogarValidator:

    @staticmethod
    def validar_tutor_tiene_menores(hogar) -> None:
        """V1: rol=TUTOR (tipo_persona 5002) requiere ≥1 miembro menor de 18 años."""
        miembros_menores = [
            m for m in hogar.miembros.all()
            if HogarValidator._edad(m.fecha_nacimiento) < 18
        ]
        tutores = hogar.miembros.filter(rol="TUTOR")
        if tutores.exists() and not miembros_menores:
            raise ValidationError(
                "Para asignar un TUTOR el hogar debe tener al menos un miembro "
                "menor de 18 años. (Manual §5.1.2)"
            )

    @staticmethod
    def validar_cuidador_tiene_dependientes(hogar) -> None:
        """V2: rol=CUIDADOR_PERMANENTE (tipo_persona 5003) requiere ≥1 miembro ≥18
        con discapacidad o enfermedad ruinosa."""
        cuidadores = hogar.miembros.filter(rol="CUIDADOR_PERMANENTE")
        if not cuidadores.exists():
            return
        dependientes = [
            m for m in hogar.miembros.all()
            if HogarValidator._edad(m.fecha_nacimiento) >= 18
            and (m.tiene_discapacidad or m.tiene_enfermedad_ruinosa)
        ]
        if not dependientes:
            raise ValidationError(
                "Para asignar un CUIDADOR PERMANENTE el hogar debe tener al menos un "
                "miembro mayor de 18 años con discapacidad o enfermedad ruinosa. "
                "(Manual §5.1.2)"
            )

    @staticmethod
    def validar_autorizado(miembro) -> None:
        """V3: el AUTORIZADO (es_autorizado=True, tipo_persona 5001) debe tener
        ≥18 años e incluido en RUV."""
        if not getattr(miembro, "es_autorizado", False):
            return
        if HogarValidator._edad(miembro.fecha_nacimiento) < 18:
            raise ValidationError(
                f"El miembro {miembro} no puede ser AUTORIZADO: debe ser mayor de edad. "
                "(Manual §5.1.2)"
            )
        if not miembro.incluido_ruv:
            raise ValidationError(
                f"El miembro {miembro} no puede ser AUTORIZADO: debe estar incluido en el RUV. "
                "(Manual §5.1.2)"
            )

    @staticmethod
    def validar_un_jefe(hogar) -> None:
        """V4: Exactamente un JEFE(A) por hogar (pregunta B23).

        PENDIENTE: el modelo MiembroHogar ya NO tiene parentesco='JEFE'
        (eliminado — el jefe de hogar se captura DENTRO de la entrevista, como
        respuesta a la pregunta B23, no en MiembroHogar). Este validador no
        aplica sobre MiembroHogar y por eso NO se invoca desde validar_todo.
        Reubicarlo a nivel de respuestas de encuesta requiere definir de qué
        pregunta leer el jefe — no se adivina aquí.
        """
        jefes = hogar.miembros.filter(parentesco="JEFE")
        if jefes.count() != 1:
            raise ValidationError(
                f"El hogar debe tener exactamente un jefe (encontrados: {jefes.count()}). "
                "(Manual §6.2, pregunta B23)"
            )

    @staticmethod
    def validar_edad_jefe(hogar) -> None:
        """V5: Jefe de hogar debe tener ≥14 años.

        PENDIENTE: igual que validar_un_jefe — depende de parentesco='JEFE',
        que ya no existe en MiembroHogar. No se invoca desde validar_todo.
        """
        jefe = hogar.miembros.filter(parentesco="JEFE").first()
        if jefe and HogarValidator._edad(jefe.fecha_nacimiento) < 14:
            raise ValidationError(
                "El jefe de hogar no puede ser menor de 14 años. (Manual §6.2, B23)"
            )

    @staticmethod
    def validar_todo(hogar) -> None:
        """Ejecuta las validaciones aplicables a MiembroHogar. Llamar al
        cerrar/completar la entrevista.

        NOTA: validar_un_jefe / validar_edad_jefe NO se invocan: el modelo
        MiembroHogar ya no tiene parentesco='JEFE' (el jefe se captura en la
        entrevista). Quedan PENDIENTES de reubicación a nivel de respuestas.
        """
        HogarValidator.validar_tutor_tiene_menores(hogar)
        HogarValidator.validar_cuidador_tiene_dependientes(hogar)
        for miembro in hogar.miembros.all():
            HogarValidator.validar_autorizado(miembro)

    @staticmethod
    def _edad(fecha_nacimiento) -> int:
        if not fecha_nacimiento:
            return 0
        hoy = date.today()
        return hoy.year - fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
