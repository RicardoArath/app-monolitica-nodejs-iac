#!/usr/bin/env python3
"""
update_db_vm.py
----------------
Actualiza la base de datos PostgreSQL en la máquina virtual con los nuevos
títulos literarios, descripciones y asignaciones de imágenes sin requerir Node.js.
"""
import psycopg2
import os

BOOKS = [
    (1, 'La Biblioteca de los Sueños Olvidados', 'Entre muros infinitos y estanterías que cambian cada noche, existe una biblioteca que guarda los sueños que las personas han olvidado. Cuando Lucía encuentra un libro con su nombre, descubre que para recuperar su propio sueño deberá desafiar las reglas de ese misterioso lugar.'),
    (2, 'El Secreto del Valle Perdido', 'La crónica de una expedición a través de la selva nubosa, donde un equipo de naturalistas redescubre un cañón prehistórico aislado del mundo durante milenios, enfrentando los enigmas más profundos de una civilización olvidada.'),
    (3, 'El Eco de las Estrellas Frías', 'En un observatorio polar en medio del invierno eterno, un grupo de astrónomos intenta descifrar una última transmisión interestelar mientras su comunidad sobrevive al aislamiento y a la escasez en el fin del mundo.'),
    (4, 'El Algoritmo de las Mariposas', 'En un pueblo costero donde las redes neuronales conviven con la magia ancestral, un programador diseña un código capaz de predecir el aleteo de mariposas bioluminiscentes que alteran el destino de sus habitantes.'),
    (5, 'La Conspiración del Reloj de Arena', 'Una mordaz intriga política en la Florencia renacentista, donde un diplomático desacreditado y un fabricante de autómatas desentrañan un complot papal oculto tras las manecillas de un reloj monumental.'),
    (6, 'Memorias de un Cómico Errante', 'Las desopilantes y conmovedoras andanzas de un actor de teatro ambulante que recorrió las provincias del siglo XX entre enredos amorosos, quiebras teatrales y aplausos inolvidables.'),
    (7, 'El Pequeño Guardián del Reino Dorado', 'La entrañable historia de Lucas y su cachorro de dragón dorado, quienes deben emprender un viaje épico a través de valles encantados para restaurar la luz del antiguo castillo real.'),
    (8, 'Sombras sobre la Mansión Blackwood', 'Al heredar una vieja casona victoriana al borde de un acantilado tempestuoso, un joven estudiante descubre cartas selladas y apariciones nocturnas que desvelan el oscuro pacto de su linaje.'),
    (9, 'Lluvia de Neón en Medianoche', 'Un detective cibernético y poeta callejero recorre los callejones empapados por lluvia ácida de Neo-Kioto, persiguiendo los versos encriptados de una inteligencia artificial prófuga.'),
    (10, 'La Ciudad de los Espejos Pensantes', 'Un tratado narrativo sobre una metrópoli flotante de cristal donde la arquitectura refleja y amplifica las dudas éticas, los ideales de justicia y la conciencia de sus ciudadanos.'),
    (11, 'La Sabiduría del Halcón y el Zorro', 'A través de fábulas campestres protagonizadas por animales comerciantes, este libro desglosa principios eternos sobre negociación, honor comercial y liderazgo prudente.'),
    (12, 'El Arte de Vencer las Batallas Interiores', 'Inspirado en las estrategias de los antiguos tratados militares, este manual ofrece tácticas psicológicas para dominar la ansiedad, superar la adversidad y alcanzar la fortaleza mental.'),
    (13, 'El Pintor de Sombras y Recuerdos', 'En el París bohemio, un retratista inconformista finge su propia desaparición para disparar la cotización de sus cuadros, desatando un melodrama desenfrenado en los salones de arte.'),
    (14, 'Alquimia en los Fogones Olvidados', 'Un fascinante recorrido culinario que rescata ingredientes ancestrales y técnicas de fermentación mística para crear platillos que desafían los sentidos de los comensales.'),
    (15, 'Crónicas desde el Callejón de Niebla', 'Un periodista exiliado recorre los puertos marítimos de entreguerras, registrando en su cuaderno las historias turbias, los cafés clandestinos y las sombras de una Europa en cambio.'),
    (16, 'El Enigma del Relojero de Vapor', 'Cuando el gran reloj astronómico de la capital se detiene, un relojero clandestino descubre que cada engranaje oculta los planos de una maquinaria capaz de manipular el vapor a escala continental.'),
    (17, 'Ecos en el Pantano del Olvido', 'En las profundidades de los pantanos de Luisiana, una estación de procesamiento biotecnológico abandonada comienza a emitir susurros misteriosos a través de las frecuencias de radio locales.'),
    (18, 'El Pistolero de las Tierras Encantadas', 'Un forajido armado con revólveres bendecidos con runas mágicas cabalga por cañones custodiados por espíritus antiguos para saldar una deuda de sangre con un hechicero inmortal.'),
    (19, 'Viajeros del Vórtice Estelar', 'Una tripulación multicolor a bordo de un carguero estelar navega a través de anomalías hiperespaciales habitadas por criaturas celestiales que conceden deseos a cambio de recuerdos preciosos.'),
    (20, 'Promesas bajo el Cerezo Eterno', 'Dos almas que se encuentran en diferentes épocas históricas coinciden siempre bajo las ramas florecidas del mismo cerezo milenario, desafiando las barreras del tiempo y la memoria.'),
    (21, 'Tratado sobre el Ingenio Humano', 'Un ensayo brillante y mordaz que explora cómo la picardía, la supervivencia y las pasiones trágicas han modelado el progreso y las contradicciones de la sociedad moderna.'),
    (22, 'Los Pasillos del Poder Invisible', 'La vida cotidiana de los asesores, secretarios y archivistas de un parlamento federal, revelando cómo los pequeños detalles del día a día deciden el rumbo de una nación entera.'),
    (23, 'Laberintos de la Mente Herida', 'Una psiquiatra forense en una ciudad nocturna debe desentrañar el testimonio fragmentado de un testigo con amnesia selectiva antes de que el verdadero culpable borre sus huellas.'),
    (24, 'La Academia de lo Extraordinario', 'Una satírica y divertida crónica sobre un internado donde los profesores enseñan materias imposibles como Aritmética de las Casualidades y Gramática del Silencio.'),
    (25, 'La Última Carrera por la Libertad', 'En un circuito desolado bajo el sol ardiente de un páramo distópico, un piloto veterano compite en una peligrosa carrera clandestina donde el único premio es la libertad de su pueblo.'),
    (26, 'El Santuario tras el Fin del Mundo', 'Tras el colapso global, una orden de monjes eremitas resguarda los textos sagrados y filosóficos de la humanidad en un monasterio fortificado entre las cumbres andinas.'),
    (27, 'El Código del Génesis Perdido', 'Una viróloga espacial descubre en el ADN de una especie alienígena la clave para curar una plaga que azota a la flota estelar, enfrentándose a corporaciones médicas sin escrúpulos.'),
    (28, 'El Forjador de Fortunas', 'La épica trayectoria de un humilde aprendiz de impresor que, a través de su visión para el comercio y el valor del crédito, construye el primer gran imperio editorial y financiero de su era.'),
    (29, 'La Balanza de los Héroes Justos', 'Un joven abogado rebelde y de verbo afilado desafía a los tribunales más corruptos del reino, utilizando la astucia callejera y los principios del derecho para defender a los desposeídos.'),
    (30, 'Geometría de los Sueños Infinitos', 'Un matemático obsesionado con la cuarta dimensión descubre que sus fórmulas fractales abren pasadizos a laberintos oníricos donde las leyes físicas se transforman en poesía visual.'),
    (31, 'El Último Horizonte', 'En un futuro donde la humanidad ha colonizado los confines del sistema solar, una joven ingeniera descubre una señal proveniente de un planeta considerado inhabitable. Su investigación la llevará a cuestionar todo lo que conoce sobre el origen de la humanidad y el futuro de la civilización.')
]

def main():
    conn = psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', 5432)),
        dbname=os.getenv('PGDATABASE', 'libreria_online'),
        user=os.getenv('PGUSER', 'libreria_app'),
        password=os.getenv('PGPASSWORD', 'libreria_app_pass')
    )
    cur = conn.cursor()

    cur.execute("ALTER TABLE book_images ADD COLUMN IF NOT EXISTS alt_text VARCHAR(255);")
    cur.execute("ALTER TABLE book_concepts ADD COLUMN IF NOT EXISTS chapter VARCHAR(100), ADD COLUMN IF NOT EXISTS page_number INT CHECK (page_number IS NULL OR page_number > 0);")

    for book_id, title, desc in BOOKS:
        cur.execute("UPDATE books SET title = %s, description = %s WHERE id = %s", (title, desc, book_id))
        cur.execute("DELETE FROM book_images WHERE book_id = %s", (book_id,))
        filename = f"cover-book-{book_id}.jpg"
        cur.execute("""
            INSERT INTO book_images (book_id, filename, mime_type, alt_text, is_primary)
            VALUES (%s, %s, 'image/jpeg', %s, true)
        """, (book_id, filename, f"Portada de {title}"))

    conn.commit()
    cur.close()
    conn.close()
    print("¡Base de datos actualizada con los 31 títulos literarios y portadas!")

if __name__ == '__main__':
    main()

