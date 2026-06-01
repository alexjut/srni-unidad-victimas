"""
Modelos paramétricos del SRNI.
Tablas de referencia de solo lectura que alimentan formularios y búsquedas.
"""
from django.db import models


class Departamento(models.Model):
    codigo_dane = models.CharField(max_length=2, unique=True, db_index=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'

    def __str__(self):
        return f'{self.codigo_dane} — {self.nombre}'


class Municipio(models.Model):
    codigo_dane = models.CharField(max_length=5, unique=True, db_index=True)
    nombre = models.CharField(max_length=150)
    departamento = models.ForeignKey(
        Departamento, on_delete=models.PROTECT, related_name='municipios'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['departamento__nombre', 'nombre']
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'

    def __str__(self):
        return f'{self.codigo_dane} — {self.nombre}'


class Vereda(models.Model):
    codigo_dane = models.CharField(max_length=13, db_index=True)
    nombre = models.CharField(max_length=200)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name='veredas'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['municipio__nombre', 'nombre']
        unique_together = [('codigo_dane', 'municipio')]
        verbose_name = 'Vereda'
        verbose_name_plural = 'Veredas'

    def __str__(self):
        return f'{self.nombre} ({self.municipio.nombre})'


class ComunidadNegra(models.Model):
    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name='comunidades_negras'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Comunidad Negra'
        verbose_name_plural = 'Comunidades Negras'

    def __str__(self):
        return self.nombre


class ResguardoIndigena(models.Model):
    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name='resguardos'
    )
    pueblo = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Resguardo Indígena'
        verbose_name_plural = 'Resguardos Indígenas'

    def __str__(self):
        return self.nombre


class TipoDocumento(models.Model):
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    nombre = models.CharField(max_length=100)
    aplica_nacionales = models.BooleanField(default=True)
    aplica_extranjeros = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documento'

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'


class DireccionTerritorial(models.Model):
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    nombre = models.CharField(max_length=150)
    departamentos = models.ManyToManyField(Departamento, related_name='direcciones_territoriales')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Dirección Territorial'
        verbose_name_plural = 'Direcciones Territoriales'

    def __str__(self):
        return self.nombre


class PuntoAtencion(models.Model):
    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    direccion_territorial = models.ForeignKey(
        DireccionTerritorial, on_delete=models.PROTECT, related_name='puntos_atencion'
    )
    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name='puntos_atencion'
    )
    direccion_fisica = models.CharField(max_length=300, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Punto de Atención'
        verbose_name_plural = 'Puntos de Atención'

    def __str__(self):
        return self.nombre
