-- Inicialización de PostgreSQL para SRNI
-- Habilitar pgcrypto para cifrado de campos PII
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Para búsqueda de texto similar

-- Usuario de aplicación con permisos mínimos
-- (se crea en el proceso de configuración, no aquí para no exponer credenciales)

-- Configuración de auditoría: tabla de log sin DELETE/UPDATE para la app
-- Se aplica restricción a nivel de usuario de BD
