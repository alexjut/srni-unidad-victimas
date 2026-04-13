"""
Campo de cifrado simétrico para PII.
Usa Fernet (AES-128-CBC + HMAC-SHA256) de la librería cryptography.
La clave de 32 bytes base64 se lee desde settings.FIELD_ENCRYPTION_KEY.
"""
import base64
import hashlib
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet():
    raw_key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
    if not raw_key:
        raise ValueError(
            'FIELD_ENCRYPTION_KEY no está configurado. '
            'Añade la variable al .env antes de guardar datos cifrados.'
        )
    # La clave puede ser un string base64 de 32 bytes o una Fernet key de 44 chars.
    key_bytes = raw_key.encode() if isinstance(raw_key, str) else raw_key
    # Fernet requiere exactamente 32 bytes codificados en base64url (44 chars).
    # Si el usuario proveyó 32 bytes planos en base64, los usamos directamente.
    try:
        decoded = base64.urlsafe_b64decode(key_bytes + b'==')
        if len(decoded) == 32:
            fernet_key = base64.urlsafe_b64encode(decoded)
        else:
            fernet_key = key_bytes
    except Exception:
        fernet_key = key_bytes
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Cifra un string y devuelve el token Fernet como string."""
    if not plaintext:
        return plaintext
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt_value(ciphertext: str) -> str:
    """Descifra un token Fernet y devuelve el plaintext."""
    if not ciphertext:
        return ciphertext
    fernet = _get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        # Si no se puede descifrar, devuelve el valor tal cual
        # (p.ej. en migraciones en blanco o datos legacy).
        return ciphertext


def sha256_hash(value: str) -> str:
    """SHA-256 del plaintext para búsquedas por índice sin exponer el dato."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class EncryptedField(models.TextField):
    """
    TextField que cifra antes de escribir en DB y descifra al leer.
    - get_prep_value: plaintext → ciphertext (escrito en DB)
    - from_db_value: ciphertext → plaintext (leído de DB)
    Nunca expone el ciphertext en el serializador; los serializers
    deben usar solo los campos _hash o campos de solo escritura.
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value
        # Si ya está cifrado (empieza con 'gAAAAA'), no volver a cifrar.
        if isinstance(value, str) and value.startswith('gAAAAA'):
            return value
        return encrypt_value(value)

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        return decrypt_value(value)

    def to_python(self, value):
        return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
