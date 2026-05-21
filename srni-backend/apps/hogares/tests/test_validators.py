"""
Tests de validadores cruzados del hogar.
Fuente: Manual UARIV 520.06.06-1 v01, §5.1.2
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, PropertyMock
from django.core.exceptions import ValidationError
from apps.hogares.validators import HogarValidator


def make_miembro(**kwargs):
    """Factory ligera de MiembroHogar con MagicMock."""
    defaults = {
        "tipo_persona": "OTRO",
        "fecha_nacimiento": date(1990, 1, 1),
        "incluido_ruv": False,
        "tiene_discapacidad": False,
        "tiene_enfermedad_ruinosa": False,
        "parentesco": "HIJO_A",
    }
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def make_hogar(miembros):
    """Factory ligera de Hogar con lista de miembros."""
    hogar = MagicMock()
    miembros_qs = MagicMock()
    miembros_qs.all.return_value = miembros
    miembros_qs.filter = lambda **kwargs: MagicMock(
        exists=lambda: any(
            all(getattr(m, k) == v for k, v in kwargs.items()) for m in miembros
        ),
        count=lambda: sum(
            1 for m in miembros
            if all(getattr(m, k) == v for k, v in kwargs.items())
        ),
        first=lambda: next(
            (m for m in miembros if all(getattr(m, k) == v for k, v in kwargs.items())),
            None,
        ),
    )
    hogar.miembros = miembros_qs
    return hogar


class TestValidarTutorTieneMenores:

    def test_tutor_sin_menores_falla(self):
        adulto_tutor = make_miembro(tipo_persona="TUTOR", fecha_nacimiento=date(1985, 1, 1))
        adulto_otro = make_miembro(tipo_persona="OTRO", fecha_nacimiento=date(1990, 1, 1))
        hogar = make_hogar([adulto_tutor, adulto_otro])
        with pytest.raises(ValidationError, match="TUTOR"):
            HogarValidator.validar_tutor_tiene_menores(hogar)

    def test_tutor_con_menor_pasa(self):
        tutor = make_miembro(tipo_persona="TUTOR", fecha_nacimiento=date(1985, 1, 1))
        menor = make_miembro(tipo_persona="OTRO", fecha_nacimiento=date(2015, 6, 1))
        hogar = make_hogar([tutor, menor])
        HogarValidator.validar_tutor_tiene_menores(hogar)  # no debe levantar

    def test_sin_tutor_no_valida(self):
        adulto = make_miembro(tipo_persona="OTRO", fecha_nacimiento=date(1990, 1, 1))
        hogar = make_hogar([adulto])
        HogarValidator.validar_tutor_tiene_menores(hogar)  # no debe levantar


class TestValidarAutorizado:

    def test_autorizado_menor_edad_falla(self):
        m = make_miembro(tipo_persona="AUTORIZADO", fecha_nacimiento=date(2010, 1, 1))
        with pytest.raises(ValidationError, match="mayor de edad"):
            HogarValidator.validar_autorizado(m)

    def test_autorizado_sin_ruv_falla(self):
        m = make_miembro(tipo_persona="AUTORIZADO", fecha_nacimiento=date(1990, 1, 1), incluido_ruv=False)
        with pytest.raises(ValidationError, match="RUV"):
            HogarValidator.validar_autorizado(m)

    def test_autorizado_valido_pasa(self):
        m = make_miembro(tipo_persona="AUTORIZADO", fecha_nacimiento=date(1990, 1, 1), incluido_ruv=True)
        HogarValidator.validar_autorizado(m)  # no debe levantar

    def test_no_autorizado_no_valida(self):
        m = make_miembro(tipo_persona="TUTOR", fecha_nacimiento=date(2010, 1, 1))
        HogarValidator.validar_autorizado(m)  # no debe levantar aunque sea menor


class TestValidarJefe:

    def test_sin_jefe_falla(self):
        m1 = make_miembro(parentesco="HIJO_A")
        m2 = make_miembro(parentesco="CONYUGE")
        hogar = make_hogar([m1, m2])
        with pytest.raises(ValidationError, match="exactamente un jefe"):
            HogarValidator.validar_un_jefe(hogar)

    def test_dos_jefes_falla(self):
        j1 = make_miembro(parentesco="JEFE")
        j2 = make_miembro(parentesco="JEFE")
        hogar = make_hogar([j1, j2])
        with pytest.raises(ValidationError, match="exactamente un jefe"):
            HogarValidator.validar_un_jefe(hogar)

    def test_un_jefe_pasa(self):
        jefe = make_miembro(parentesco="JEFE", fecha_nacimiento=date(1980, 1, 1))
        otro = make_miembro(parentesco="HIJO_A")
        hogar = make_hogar([jefe, otro])
        HogarValidator.validar_un_jefe(hogar)  # no debe levantar

    def test_jefe_menor_14_falla(self):
        jefe = make_miembro(parentesco="JEFE", fecha_nacimiento=date(2015, 1, 1))
        hogar = make_hogar([jefe])
        with pytest.raises(ValidationError, match="14 años"):
            HogarValidator.validar_edad_jefe(hogar)

    def test_jefe_14_anos_pasa(self):
        nacimiento = date(date.today().year - 14, 1, 1)
        jefe = make_miembro(parentesco="JEFE", fecha_nacimiento=nacimiento)
        hogar = make_hogar([jefe])
        HogarValidator.validar_edad_jefe(hogar)  # no debe levantar


class TestValidarCuidador:

    def test_cuidador_sin_dependientes_falla(self):
        cuidador = make_miembro(tipo_persona="CUIDADOR", fecha_nacimiento=date(1980, 1, 1))
        adulto_sano = make_miembro(
            tipo_persona="OTRO", fecha_nacimiento=date(1970, 1, 1),
            tiene_discapacidad=False, tiene_enfermedad_ruinosa=False,
        )
        hogar = make_hogar([cuidador, adulto_sano])
        with pytest.raises(ValidationError, match="CUIDADOR"):
            HogarValidator.validar_cuidador_tiene_dependientes(hogar)

    def test_cuidador_con_dependiente_discapacidad_pasa(self):
        cuidador = make_miembro(tipo_persona="CUIDADOR", fecha_nacimiento=date(1980, 1, 1))
        dependiente = make_miembro(
            tipo_persona="OTRO", fecha_nacimiento=date(1960, 1, 1),
            tiene_discapacidad=True, tiene_enfermedad_ruinosa=False,
        )
        hogar = make_hogar([cuidador, dependiente])
        HogarValidator.validar_cuidador_tiene_dependientes(hogar)  # no debe levantar

    def test_sin_cuidador_no_valida(self):
        adulto = make_miembro(tipo_persona="OTRO", fecha_nacimiento=date(1990, 1, 1))
        hogar = make_hogar([adulto])
        HogarValidator.validar_cuidador_tiene_dependientes(hogar)  # no debe levantar


class TestEdadHelper:

    def test_edad_calculada_correctamente(self):
        nacimiento = date(date.today().year - 25, date.today().month, date.today().day)
        assert HogarValidator._edad(nacimiento) == 25

    def test_fecha_none_retorna_cero(self):
        assert HogarValidator._edad(None) == 0
