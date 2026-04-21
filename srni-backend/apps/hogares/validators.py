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
        """V1: tipo_persona=TUTOR requiere ≥1 miembro menor de 18 años."""
        miembros_menores = [
            m for m in hogar.miembros.all()
            if HogarValidator._edad(m.fecha_nacimiento) < 18
        ]
        tutores = hogar.miembros.filter(tipo_persona="TUTOR")
        if tutores.exists() and not miembros_menores:
            raise ValidationError(
                "Para asignar un TUTOR el hogar debe tener al menos un miembro "
                "menor de 18 años. (Manual §5.1.2)"
            )

    @staticmethod
    def validar_cuidador_tiene_dependientes(hogar) -> None:
        """V2: CUIDADOR requiere ≥1 miembro ≥18 con discapacidad o enfermedad ruinosa."""
        cuidadores = hogar.miembros.filter(tipo_persona="CUIDADOR")
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
        """V3: AUTORIZADO debe tener ≥18 años e incluido en RUV."""
        if miembro.tipo_persona != "AUTORIZADO":
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
        """V4: Exactamente un JEFE(A) por hogar (pregunta B23)."""
        jefes = hogar.miembros.filter(parentesco="JEFE")
        if jefes.count() != 1:
            raise ValidationError(
                f"El hogar debe tener exactamente un jefe (encontrados: {jefes.count()}). "
                "(Manual §6.2, pregunta B23)"
            )

    @staticmethod
    def validar_edad_jefe(hogar) -> None:
        """V5: Jefe de hogar debe tener ≥14 años."""
        jefe = hogar.miembros.filter(parentesco="JEFE").first()
        if jefe and HogarValidator._edad(jefe.fecha_nacimiento) < 14:
            raise ValidationError(
                "El jefe de hogar no puede ser menor de 14 años. (Manual §6.2, B23)"
            )

    @staticmethod
    def validar_todo(hogar) -> None:
        """Ejecuta todas las validaciones. Llamar al cerrar/completar la entrevista."""
        HogarValidator.validar_un_jefe(hogar)
        HogarValidator.validar_edad_jefe(hogar)
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
