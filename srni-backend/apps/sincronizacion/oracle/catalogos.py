"""
Crosswalk SICAV → catálogos Oracle (Etapa A).

Valores REALES leídos de prod (RNIENTREVISTA, solo lectura, 2026-07-15) y cruzados
por nombre con los códigos SICAV. El volcado completo (incl. los 1370 registros de
GIC_N_DT_PUNTOS_ATENCION) está en `catalogos_oracle.json` (versionado, sin PII).

Regla: si un código SICAV no tiene entrada aquí, el resolver LANZA MapeoDesconocido
(modo estricto/confirmado). NUNCA se inventa un valor por defecto.
Claves = valor SICAV (código del modelo Django). Valores = id Oracle real.
"""

# ── Catálogo 2 — tipo de caracterización (GIC_TIPOCARACTERIZACION) ───────────
# Oracle distingue solo 1=INDIVIDUO / 2=HOGAR (NO por instrumento). GIC_INSERT_HOGAR1
# crea una caracterización de HOGAR ⇒ SICAV usa 2. ⚠️ CONFIRMAR si algún flujo SICAV
# debe registrarse como INDIVIDUO (1).
TIPO_CARACTERIZACION_HOGAR = 2
TIPO_CARACTERIZACION_INDIVIDUO = 1

# ── Catálogo 3 — tipo de documento (parametricas.TipoDocumento.codigo → GIC_TIPODOC.TIP_IDTIPO) ──
# Cruce por nombre con las 8 filas del seed SICAV (cargar_tipos_documento.py).
TIPO_DOCUMENTO = {
    "CC": 1,    # Cédula de Ciudadanía
    "TI": 2,    # Tarjeta de Identidad
    "CE": 3,    # Cédula de Extranjería
    "RC": 4,    # Registro Civil de Nacimiento
    "PA": 7,    # Pasaporte
    "NIT": 9,   # Número de Identificación Tributaria
    # ⚠️ SIN equivalente claro en GIC_TIPODOC (14 filas) — decisión de negocio:
    #   "PE"  (Permiso Especial de Permanencia / PEP) → ¿Otro=13? ¿alta en catálogo?
    #   "NES" (Número de Entrada al Sistema, sin doc)  → ¿Indocumentado=14? ¿Ninguno=12?
    # Se dejan SIN mapear a propósito: el resolver lanzará MapeoDesconocido.
}

# ── Catálogo 4a — parentesco (MiembroHogar.parentesco → GIC_PARENTESCOGENEALOGICO.PRST_ID) ──
# Cruce por nombre con las 12 filas Oracle; las 8 choices SICAV mapean limpio.
PARENTESCO = {
    "CONYUGE": 4,        # Esposo(a)/Compañero(a)
    "HIJO_A": 3,         # Hijo(a)/Hijastro(a)
    "YERNO_NUERA": 8,    # Yerno/Nuera
    "NIETO_A": 5,        # Nieto(a)
    "PADRE_MADRE": 2,    # Padre o Madre
    "HERMANO_A": 7,      # Hermanos o Cuñados
    "OTRO_PARIENTE": 9,  # Otros Parientes
    "NO_PARIENTE": 10,   # No pariente
    # (Oracle 1=Jefe de hogar, 6=Suegros, 11=No sabe, 12=No responde no tienen
    #  choice SICAV directo; el jefe se marca por es_autorizado, no por parentesco.)
}

# ── Catálogo 4b — tipo de víctima → GIC_PERSONA.PER_TIPOVICTIMA ──────────────
# ⚠️ PENDIENTE: no se identificó tabla catálogo ni campo SICAV de origen. Vacío.
TIPO_VICTIMA: dict = {}

# Nombre canónico de cada catálogo (para mensajes de error y auditoría).
NOMBRES = {
    "tipo_caracterizacion": "GIC_TIPOCARACTERIZACION.TPOCRN_ID",
    "tipo_documento": "GIC_TIPODOC.TIP_IDTIPO",
    "parentesco": "GIC_PARENTESCOGENEALOGICO.PRST_ID",
    "tipo_victima": "GIC_PERSONA.PER_TIPOVICTIMA",
    "territorio": "GIC_N_DT_PUNTOS_ATENCION",
}
