-- =====================================================================
-- 00_create_database.sql
-- Ejecutar como superusuario (postgres) conectado a la BD "postgres":
--   psql -U postgres -h <host> -f db/00_create_database.sql
-- =====================================================================

-- Elimina la base si existe (solo entornos de práctica/laboratorio)
DROP DATABASE IF EXISTS libreria_online;

-- Usuario administrador de la aplicación (ajustar password antes de usar)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'libreria_app') THEN
    CREATE ROLE libreria_app LOGIN PASSWORD 'CAMBIA_ESTA_CLAVE';
  END IF;
END
$$;

CREATE DATABASE libreria_online
  OWNER = libreria_app
  ENCODING = 'UTF8'
  TEMPLATE = template0;

GRANT ALL PRIVILEGES ON DATABASE libreria_online TO libreria_app;

-- Después de este script:
--   psql -U libreria_app -h <host> -d libreria_online -f db/01_schema.sql
--   psql -U libreria_app -h <host> -d libreria_online -f db/02_seed_30_per_table.sql
