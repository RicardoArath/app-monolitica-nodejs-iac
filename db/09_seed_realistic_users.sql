-- ==============================================================================
-- 09_seed_realistic_users.sql
-- Actualiza los usuarios iniciales (IDs 2 al 30) con nombres reales en español,
-- apellidos paternos y maternos, nombres de usuario estilizados y correos realistas.
-- ==============================================================================

BEGIN;

UPDATE users SET nombre = 'Sofía', apellido_paterno = 'Hernández', apellido_materno = 'López', username = 'sofia.hernandez', email = 'sofia.hernandez@libreria.com' WHERE id = 2;
UPDATE users SET nombre = 'Alejandro', apellido_paterno = 'Morales', apellido_materno = 'Castillo', username = 'alejandro.morales', email = 'alejandro.morales@libreria.com' WHERE id = 3;
UPDATE users SET nombre = 'Mariana', apellido_paterno = 'Castillo', apellido_materno = 'Gómez', username = 'mariana.castillo', email = 'mariana.castillo@correo.com' WHERE id = 4;
UPDATE users SET nombre = 'Diego', apellido_paterno = 'Ramírez', apellido_materno = 'Torres', username = 'diego.ramirez', email = 'diego.ramirez@correo.com' WHERE id = 5;
UPDATE users SET nombre = 'Valeria', apellido_paterno = 'Gutiérrez', apellido_materno = 'Vargas', username = 'valeria.gutierrez', email = 'valeria.gutierrez@libreria.com' WHERE id = 6;
UPDATE users SET nombre = 'Fernando', apellido_paterno = 'López', apellido_materno = 'Ramos', username = 'fernando.lopez', email = 'fernando.lopez@correo.com' WHERE id = 7;
UPDATE users SET nombre = 'Camila', apellido_paterno = 'Navarro', apellido_materno = 'Flores', username = 'camila.navarro', email = 'camila.navarro@correo.com' WHERE id = 8;
UPDATE users SET nombre = 'Mateo', apellido_paterno = 'Herrera', apellido_materno = 'Cruz', username = 'mateo.herrera', email = 'mateo.herrera@libreria.com' WHERE id = 9;
UPDATE users SET nombre = 'Lucía', apellido_paterno = 'Ortiz', apellido_materno = 'Mendoza', username = 'lucia.ortiz', email = 'lucia.ortiz@correo.com' WHERE id = 10;
UPDATE users SET nombre = 'Gabriel', apellido_paterno = 'Vargas', apellido_materno = 'Reyes', username = 'gabriel.vargas', email = 'gabriel.vargas@correo.com' WHERE id = 11;
UPDATE users SET nombre = 'Daniela', apellido_paterno = 'Reyes', apellido_materno = 'Silva', username = 'daniela.reyes', email = 'daniela.reyes@libreria.com' WHERE id = 12;
UPDATE users SET nombre = 'Sebastián', apellido_paterno = 'Castro', apellido_materno = 'Morales', username = 'sebastian.castro', email = 'sebastian.castro@correo.com' WHERE id = 13;
UPDATE users SET nombre = 'Andrea', apellido_paterno = 'Méndez', apellido_materno = 'Delgado', username = 'andrea.mendez', email = 'andrea.mendez@correo.com' WHERE id = 14;
UPDATE users SET nombre = 'Leonardo', apellido_paterno = 'Silva', apellido_materno = 'Paredes', username = 'leonardo.silva', email = 'leonardo.silva@libreria.com' WHERE id = 15;
UPDATE users SET nombre = 'Natalia', apellido_paterno = 'Delgado', apellido_materno = 'Guerrero', username = 'natalia.delgado', email = 'natalia.delgado@correo.com' WHERE id = 16;
UPDATE users SET nombre = 'Javier', apellido_paterno = 'Romero', apellido_materno = 'Aguilar', username = 'javier.romero', email = 'javier.romero@correo.com' WHERE id = 17;
UPDATE users SET nombre = 'Paula', apellido_paterno = 'Guerrero', apellido_materno = 'Medina', username = 'paula.guerrero', email = 'paula.guerrero@libreria.com' WHERE id = 18;
UPDATE users SET nombre = 'Rodrigo', apellido_paterno = 'Medina', apellido_materno = 'Salazar', username = 'rodrigo.medina', email = 'rodrigo.medina@correo.com' WHERE id = 19;
UPDATE users SET nombre = 'Isabella', apellido_paterno = 'Flores', apellido_materno = 'Rojas', username = 'isabella.flores', email = 'isabella.flores@correo.com' WHERE id = 20;
UPDATE users SET nombre = 'Adrián', apellido_paterno = 'Peña', apellido_materno = 'Soto', username = 'adrian.pena', email = 'adrian.pena@libreria.com' WHERE id = 21;
UPDATE users SET nombre = 'Carmen', apellido_paterno = 'Aguilar', apellido_materno = 'Cordero', username = 'carmen.aguilar', email = 'carmen.aguilar@correo.com' WHERE id = 22;
UPDATE users SET nombre = 'Emilio', apellido_paterno = 'Salazar', apellido_materno = 'Vega', username = 'emilio.salazar', email = 'emilio.salazar@correo.com' WHERE id = 23;
UPDATE users SET nombre = 'Renata', apellido_paterno = 'Paredes', apellido_materno = 'Campos', username = 'renata.paredes', email = 'renata.paredes@libreria.com' WHERE id = 24;
UPDATE users SET nombre = 'Samuel', apellido_paterno = 'Cruz', apellido_materno = 'Navarrete', username = 'samuel.cruz', email = 'samuel.cruz@correo.com' WHERE id = 25;
UPDATE users SET nombre = 'Ximena', apellido_paterno = 'Rojas', apellido_materno = 'Pacheco', username = 'ximena.rojas', email = 'ximena.rojas@correo.com' WHERE id = 26;
UPDATE users SET nombre = 'Mauricio', apellido_paterno = 'Soto', apellido_materno = 'Fuentes', username = 'mauricio.soto', email = 'mauricio.soto@libreria.com' WHERE id = 27;
UPDATE users SET nombre = 'Victoria', apellido_paterno = 'Luna', apellido_materno = 'Domínguez', username = 'victoria.luna', email = 'victoria.luna@correo.com' WHERE id = 28;
UPDATE users SET nombre = 'Esteban', apellido_paterno = 'Cordero', apellido_materno = 'Valencia', username = 'esteban.cordero', email = 'esteban.cordero@correo.com' WHERE id = 29;
UPDATE users SET nombre = 'Montserrat', apellido_paterno = 'Vega', apellido_materno = 'Cabrera', username = 'montserrat.vega', email = 'montserrat.vega@libreria.com' WHERE id = 30;

COMMIT;
