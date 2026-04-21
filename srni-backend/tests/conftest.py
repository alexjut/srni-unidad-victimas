"""
Configuración global de pytest para el backend SRNI.

Garantiza que FIELD_ENCRYPTION_KEY siempre sea válida en todos los tests,
independientemente del valor del .env local.
"""
import pytest
from cryptography.fernet import Fernet


# Clave de prueba fija — solo para tests, nunca en producción.
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def set_encryption_key(settings):
    """Sobreescribe FIELD_ENCRYPTION_KEY con una clave Fernet válida para cada test."""
    settings.FIELD_ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
