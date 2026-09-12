-- =====================================================================
-- 02_seed_30_per_table.sql
-- Genera 30 registros sintéticos por tabla usando generate_series.
-- Requiere la extensión pgcrypto para generar hashes bcrypt reales
-- (compatibles con bcryptjs usado en la app Node.js).
-- =====================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
-- USERS: 1 administrador + 29 usuarios regulares
-- Password de todos los usuarios sintéticos: "Passw0rd!"
-- ---------------------------------------------------------------------
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@libreria.local', crypt('Passw0rd!', gen_salt('bf')), 'admin');

INSERT INTO users (username, email, password_hash, role)
SELECT
    'usuario' || n,
    'usuario' || n || '@correo.com',
    crypt('Passw0rd!', gen_salt('bf')),
    'user'
FROM generate_series(1, 29) AS n;

-- ---------------------------------------------------------------------
-- FORMATS (catálogo independiente) - 30 combinaciones únicas
-- ---------------------------------------------------------------------
INSERT INTO formats (name)
SELECT DISTINCT base.nombre || CASE WHEN suf.n > 1 THEN ' ' || suf.n ELSE '' END
FROM (VALUES ('Tapa dura'), ('Rústica'), ('Digital (ePub)'), ('Digital (PDF)'),
             ('Audiolibro'), ('Bolsillo'), ('Edición especial'), ('Pasta blanda'),
             ('Empastado'), ('Coleccionista')) AS base(nombre)
CROSS JOIN generate_series(1, 3) AS suf(n)
LIMIT 30;

-- ---------------------------------------------------------------------
-- CATEGORIES (catálogo independiente) - 30 categorías
-- ---------------------------------------------------------------------
INSERT INTO categories (name) VALUES
('Ficción'), ('No ficción'), ('Ciencia'), ('Tecnología'), ('Historia'),
('Biografía'), ('Infantil'), ('Juvenil'), ('Poesía'), ('Filosofía'),
('Negocios'), ('Autoayuda'), ('Arte'), ('Cocina'), ('Viajes'),
('Misterio'), ('Terror'), ('Fantasía'), ('Ciencia ficción'), ('Romance'),
('Ensayo'), ('Política'), ('Psicología'), ('Educación'), ('Deportes'),
('Religión'), ('Salud'), ('Economía'), ('Derecho'), ('Matemáticas');

-- ---------------------------------------------------------------------
-- AUTHORS - 30 autores sintéticos
-- ---------------------------------------------------------------------
INSERT INTO authors (name) VALUES
('Elena Martínez'), ('Carlos Fuentes Jr.'), ('Laura Gómez'), ('Miguel Ángel Ruiz'),
('Sofía Torres'), ('Javier Morales'), ('Ana Belén Castro'), ('Ricardo Salinas'),
('Patricia Núñez'), ('Fernando León'), ('Isabel Prado'), ('Diego Herrera'),
('Camila Rivas'), ('Andrés Paredes'), ('Valeria Soto'), ('Tomás Aguilar'),
('Lucía Vega'), ('Emilio Cordero'), ('Marta Delgado'), ('Sergio Navarro'),
('Daniela Reyes'), ('Hugo Campos'), ('Renata Silva'), ('Iván Domínguez'),
('Paula Cabrera'), ('Alejandro Vidal'), ('Gabriela Ortiz'), ('Raúl Escobar'),
('Natalia Peña'), ('Mario Contreras');

-- ---------------------------------------------------------------------
-- GENRES - 30 géneros
-- ---------------------------------------------------------------------
INSERT INTO genres (name) VALUES
('Drama'), ('Aventura'), ('Distopía'), ('Realismo mágico'), ('Thriller'),
('Comedia'), ('Épica'), ('Gótico'), ('Policiaco'), ('Utopía'),
('Costumbrista'), ('Bélico'), ('Satírico'), ('Experimental'), ('Histórico'),
('Steampunk'), ('Cyberpunk'), ('Western'), ('Fábula'), ('Alegoría'),
('Melodrama'), ('Slice of life'), ('Noir'), ('Absurdo'), ('Gótico sureño'),
('Postapocalíptico'), ('Space opera'), ('Bildungsroman'), ('Picaresca'), ('Surrealista');

-- ---------------------------------------------------------------------
-- BOOKS - 30 libros
-- ---------------------------------------------------------------------
INSERT INTO books (isbn, title, publication_year, price, stock, format_id, category_id, description)
VALUES
    ('978-607-9876-54-3', 'La Biblioteca de los Sueños Olvidados', 2023, 299.00, 18, 17, 18, 'Entre muros infinitos y estanterías que cambian cada noche, existe una biblioteca que guarda los sueños que las personas han olvidado. Cuando Lucía encuentra un libro con su nombre, descubre que para recuperar su propio sueño deberá desafiar las reglas de ese misterioso lugar.'),
    ('978-0-000002-2', 'El Secreto del Valle Perdido', 1982, 224.00, 6, 2, 2, 'La crónica de una expedición a través de la selva nubosa, donde un equipo de naturalistas redescubre un cañón prehistórico aislado del mundo durante milenios, enfrentando los enigmas más profundos de una civilización olvidada.'),
    ('978-0-000003-3', 'El Eco de las Estrellas Frías', 1983, 261.00, 9, 3, 3, 'En un observatorio polar en medio del invierno eterno, un grupo de astrónomos intenta descifrar una última transmisión interestelar mientras su comunidad sobrevive al aislamiento y a la escasez en el fin del mundo.'),
    ('978-0-000004-4', 'El Algoritmo de las Mariposas', 1984, 298.00, 12, 4, 4, 'En un pueblo costero donde las redes neuronales conviven con la magia ancestral, un programador diseña un código capaz de predecir el aleteo de mariposas bioluminiscentes que alteran el destino de sus habitantes.'),
    ('978-0-000005-5', 'La Conspiración del Reloj de Arena', 1985, 335.00, 15, 5, 5, 'Una mordaz intriga política en la Florencia renacentista, donde un diplomático desacreditado y un fabricante de autómatas desentrañan un complot papal oculto tras las manecillas de un reloj monumental.'),
    ('978-0-000006-6', 'Memorias de un Cómico Errante', 1986, 372.00, 18, 6, 6, 'Las desopilantes y conmovedoras andanzas de un actor de teatro ambulante que recorrió las provincias del siglo XX entre enredos amorosos, quiebras teatrales y aplausos inolvidables.'),
    ('978-0-000007-7', 'El Pequeño Guardián del Reino Dorado', 1987, 409.00, 21, 7, 7, 'La entrañable historia de Lucas y su cachorro de dragón dorado, quienes deben emprender un viaje épico a través de valles encantados para restaurar la luz del antiguo castillo real.'),
    ('978-0-000008-8', 'Sombras sobre la Mansión Blackwood', 1988, 446.00, 24, 8, 8, 'Al heredar una vieja casona victoriana al borde de un acantilado tempestuoso, un joven estudiante descubre cartas selladas y apariciones nocturnas que desvelan el oscuro pacto de su linaje.'),
    ('978-0-000009-9', 'Lluvia de Neón en Medianoche', 1989, 483.00, 27, 9, 9, 'Un detective cibernético y poeta callejero recorre los callejones empapados por lluvia ácida de Neo-Kioto, persiguiendo los versos encriptados de una inteligencia artificial prófuga.'),
    ('978-0-000010-0', 'La Ciudad de los Espejos Pensantes', 1990, 520.00, 30, 10, 10, 'Un tratado narrativo sobre una metrópoli flotante de cristal donde la arquitectura refleja y amplifica las dudas éticas, los ideales de justicia y la conciencia de sus ciudadanos.'),
    ('978-0-000011-1', 'La Sabiduría del Halcón y el Zorro', 1991, 557.00, 33, 11, 11, 'A través de fábulas campestres protagonizadas por animales comerciantes, este libro desglosa principios eternos sobre negociación, honor comercial y liderazgo prudente.'),
    ('978-0-000012-2', 'El Arte de Vencer las Batallas Interiores', 1992, 594.00, 36, 12, 12, 'Inspirado en las estrategias de los antiguos tratados militares, este manual ofrece tácticas psicológicas para dominar la ansiedad, superar la adversidad y alcanzar la fortaleza mental.'),
    ('978-0-000013-3', 'El Pintor de Sombras y Recuerdos', 1993, 631.00, 39, 13, 13, 'En el París bohemio, un retratista inconformista finge su propia desaparición para disparar la cotización de sus cuadros, desatando un melodrama desenfrenado en los salones de arte.'),
    ('978-0-000014-4', 'Alquimia en los Fogones Olvidados', 1994, 668.00, 2, 14, 14, 'Un fascinante recorrido culinario que rescata ingredientes ancestrales y técnicas de fermentación mística para crear platillos que desafían los sentidos de los comensales.'),
    ('978-0-000015-5', 'Crónicas desde el Callejón de Niebla', 1995, 705.00, 5, 15, 15, 'Un periodista exiliado recorre los puertos marítimos de entreguerras, registrando en su cuaderno las historias turbias, los cafés clandestinos y las sombras de una Europa en cambio.'),
    ('978-0-000016-6', 'El Enigma del Relojero de Vapor', 1996, 742.00, 8, 16, 16, 'Cuando el gran reloj astronómico de la capital se detiene, un relojero clandestino descubre que cada engranaje oculta los planos de una maquinaria capaz de manipular el vapor a escala continental.'),
    ('978-0-000017-7', 'Ecos en el Pantano del Olvido', 1997, 779.00, 11, 17, 17, 'En las profundidades de los pantanos de Luisiana, una estación de procesamiento biotecnológico abandonada comienza a emitir susurros misteriosos a través de las frecuencias de radio locales.'),
    ('978-0-000018-8', 'El Pistolero de las Tierras Encantadas', 1998, 816.00, 14, 18, 18, 'Un forajido armado con revólveres bendecidos con runas mágicas cabalga por cañones custodiados por espíritus antiguos para saldar una deuda de sangre con un hechicero inmortal.'),
    ('978-0-000019-9', 'Viajeros del Vórtice Estelar', 1999, 153.00, 17, 19, 19, 'Una tripulación multicolor a bordo de un carguero estelar navega a través de anomalías hiperespaciales habitadas por criaturas celestiales que conceden deseos a cambio de recuerdos preciosos.'),
    ('978-0-000020-0', 'Promesas bajo el Cerezo Eterno', 2000, 190.00, 20, 20, 20, 'Dos almas que se encuentran en diferentes épocas históricas coinciden siempre bajo las ramas florecidas del mismo cerezo milenario, desafiando las barreras del tiempo y la memoria.'),
    ('978-0-000021-1', 'Tratado sobre el Ingenio Humano', 2001, 227.00, 23, 21, 21, 'Un ensayo brillante y mordaz que explora cómo la picardía, la supervivencia y las pasiones trágicas han modelado el progreso y las contradicciones de la sociedad moderna.'),
    ('978-0-000022-2', 'Los Pasillos del Poder Invisible', 2002, 264.00, 26, 22, 22, 'La vida cotidiana de los asesores, secretarios y archivistas de un parlamento federal, revelando cómo los pequeños detalles del día a día deciden el rumbo de una nación entera.'),
    ('978-0-000023-3', 'Laberintos de la Mente Herida', 2003, 301.00, 29, 23, 23, 'Una psiquiatra forense en una ciudad nocturna debe desentrañar el testimonio fragmentado de un testigo con amnesia selectiva antes de que el verdadero culpable borre sus huellas.'),
    ('978-0-000024-4', 'La Academia de lo Extraordinario', 2004, 338.00, 32, 24, 24, 'Una satírica y divertida crónica sobre un internado donde los profesores enseñan materias imposibles como ''Aritmética de las Casualidades'' y ''Gramática del Silencio''.'),
    ('978-0-000025-5', 'La Última Carrera por la Libertad', 2005, 375.00, 35, 25, 25, 'En un circuito desolado bajo el sol ardiente de un páramo distópico, un piloto veterano compite en una peligrosa carrera clandestina donde el único premio es la libertad de su pueblo.'),
    ('978-0-000026-6', 'El Santuario tras el Fin del Mundo', 2006, 412.00, 38, 26, 26, 'Tras el colapso global, una orden de monjes eremitas resguarda los textos sagrados y filosóficos de la humanidad en un monasterio fortificado entre las cumbres andinas.'),
    ('978-0-000027-7', 'El Código del Génesis Perdido', 2007, 449.00, 1, 27, 27, 'Una viróloga espacial descubre en el ADN de una especie alienígena la clave para curar una plaga que azota a la flota estelar, enfrentándose a corporaciones médicas sin escrúpulos.'),
    ('978-0-000028-8', 'El Forjador de Fortunas', 2008, 486.00, 4, 28, 28, 'La épica trayectoria de un humilde aprendiz de impresor que, a través de su visión para el comercio y el valor del crédito, construye el primer gran imperio editorial y financiero de su era.'),
    ('978-0-000029-9', 'La Balanza de los Héroes Justos', 2009, 523.00, 7, 29, 29, 'Un joven abogado rebelde y de verbo afilado desafía a los tribunales más corruptos del reino, utilizando la astucia callejera y los principios del derecho para defender a los desposeídos.'),
    ('978-0-000030-0', 'Geometría de los Sueños Infinitos', 2010, 560.00, 10, 30, 30, 'Un matemático obsesionado con la cuarta dimensión descubre que sus fórmulas fractales abren pasadizos a laberintos oníricos donde las leyes físicas se transforman en poesía visual.'),
    ('978-607-1234-56-7', 'El Último Horizonte', 2024, 349.00, 25, 8, 19, 'En un futuro donde la humanidad ha colonizado los confines del sistema solar, una joven ingeniera descubre una señal proveniente de un planeta considerado inhabitable. Su investigación la llevará a cuestionar todo lo que conoce sobre el origen de la humanidad y el futuro de la civilización.');

-- ---------------------------------------------------------------------
-- BOOK_AUTHORS - al menos 30 relaciones (1 a 2 autores por libro)
-- ---------------------------------------------------------------------
INSERT INTO book_authors (book_id, author_id)
SELECT b.id, ((b.id - 1) % 30) + 1
FROM books b;

INSERT INTO book_authors (book_id, author_id)
SELECT b.id, ((b.id + 4) % 30) + 1
FROM books b
WHERE b.id % 2 = 0
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- BOOK_GENRES - al menos 30 relaciones (1 a 2 géneros por libro)
-- ---------------------------------------------------------------------
INSERT INTO book_genres (book_id, genre_id)
SELECT b.id, ((b.id - 1) % 30) + 1
FROM books b;

INSERT INTO book_genres (book_id, genre_id)
SELECT b.id, ((b.id + 7) % 30) + 1
FROM books b
WHERE b.id % 2 = 1
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- BOOK_CONCEPTS - 30 conceptos (un mismo nombre puede repetirse
-- en libros distintos con definición distinta, como pide el enunciado)
-- ---------------------------------------------------------------------
INSERT INTO book_concepts (book_id, name, definition, chapter, page_number)
SELECT
    b.id,
    (ARRAY['Protagonista', 'Antagonista', 'Clímax', 'Metáfora central', 'Tema principal'])[((b.id - 1) % 5) + 1],
    'Definición sintética del concepto para el libro ' || b.id || ', en el contexto de su trama particular.',
    'Capítulo ' || (((b.id - 1) % 10) + 1),
    ((b.id - 1) % 10) + 1
FROM books b;

-- ---------------------------------------------------------------------
-- BOOK_IMAGES - 30 imágenes de referencia (nombres de archivo simulados)
-- ---------------------------------------------------------------------
INSERT INTO book_images (book_id, filename, mime_type, alt_text, is_primary)
SELECT
    b.id,
    'cover-book-' || b.id || '.jpg', 'image/jpeg',
    'Portada del libro ' || b.title,
    true
FROM books b;

-- ---------------------------------------------------------------------
-- CARTS - un carrito inicial por usuario
-- ---------------------------------------------------------------------
INSERT INTO carts (user_id)
SELECT id FROM users ORDER BY id;

-- ---------------------------------------------------------------------
-- CART_ITEMS - una relación de prueba por carrito
-- ---------------------------------------------------------------------
INSERT INTO cart_items (cart_id, book_id, quantity)
SELECT c.id, b.id, 1
FROM carts c
JOIN books b ON b.id = ((c.id - 1) % 30) + 1;

-- ---------------------------------------------------------------------
-- ORDERS - pedidos sintéticos con un libro por pedido
-- ---------------------------------------------------------------------
INSERT INTO orders (user_id, status, subtotal, total)
SELECT u.id, 'confirmed', b.price, b.price
FROM users u
JOIN books b ON b.id = ((u.id - 1) % 30) + 1
ORDER BY u.id;

INSERT INTO order_items (order_id, book_id, title_snapshot, unit_price, quantity, line_total)
SELECT o.id, b.id, b.title, b.price, 1, b.price
FROM orders o
JOIN books b ON b.id = ((o.id - 1) % 30) + 1
ORDER BY o.id;

INSERT INTO simulated_payments (order_id, method, status, amount)
SELECT id, 'simulated_card', 'approved', total
FROM orders
ORDER BY id;

COMMIT;
