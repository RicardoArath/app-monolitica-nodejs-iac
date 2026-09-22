-- =====================================================================
-- 07_migration_auth_service.sql
-- Migración para el microservicio de autenticación Flask.
-- Agrega columnas de nombre a users, columna email_verified,
-- tabla de tokens de verificación de email, y actualiza
-- sp_register_user para aceptar los nuevos campos.
--
-- Ejecutar conectado a la base "libreria_online":
--   psql -U libreria_app -h localhost -d libreria_online -f db/07_migration_auth_service.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1) Columnas de nombre y verificación en la tabla users
-- ---------------------------------------------------------------------
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS nombre           VARCHAR(100),
  ADD COLUMN IF NOT EXISTS apellido_paterno VARCHAR(100),
  ADD COLUMN IF NOT EXISTS apellido_materno VARCHAR(100),
  ADD COLUMN IF NOT EXISTS email_verified   BOOLEAN NOT NULL DEFAULT false;

-- ---------------------------------------------------------------------
-- 2) Tabla para tokens de verificación de email
--    Cada token expira en 24 horas y solo puede usarse una vez.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       VARCHAR(128) NOT NULL UNIQUE,
    expires_at  TIMESTAMP    NOT NULL,
    used        BOOLEAN      NOT NULL DEFAULT false,
    created_at  TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evt_token   ON email_verification_tokens (token);
CREATE INDEX IF NOT EXISTS idx_evt_user_id ON email_verification_tokens (user_id);

-- ---------------------------------------------------------------------
-- 3) Actualizar sp_register_user con campos nuevos (retrocompatible)
--    Los tres parámetros nuevos tienen DEFAULT NULL, así que las
--    llamadas existentes desde Node.js siguen funcionando sin cambios.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_register_user(
    p_username        TEXT,
    p_email           TEXT,
    p_password_hash   TEXT,
    p_nombre          TEXT DEFAULT NULL,
    p_apellido_paterno TEXT DEFAULT NULL,
    p_apellido_materno TEXT DEFAULT NULL
) RETURNS INT AS $$
DECLARE
    v_id INT;
BEGIN
    INSERT INTO users (username, email, password_hash, role,
                       nombre, apellido_paterno, apellido_materno,
                       email_verified)
    VALUES (p_username, p_email, p_password_hash, 'user',
            p_nombre, p_apellido_paterno, p_apellido_materno,
            false)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 4) Marcar usuarios existentes (seed) como verificados para no
--    romper el flujo del monolito Node.js
-- ---------------------------------------------------------------------
UPDATE users SET email_verified = true WHERE email_verified = false;

COMMIT;

