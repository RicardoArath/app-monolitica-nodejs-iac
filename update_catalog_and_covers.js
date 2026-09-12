/**
 * update_catalog_and_covers.js
 * -------------------------------------------------------------
 * Actualiza todos los libros con títulos literarios evocadores,
 * sinopsis ricas y portadas artísticas de alta calidad (combinando
 * las imágenes generadas con IA y portadas temáticas curadas).
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const db = require('./config/db');

const UPLOADS_DIR = path.join(__dirname, 'public', 'uploads');
const AI_DIR = 'C:\\Users\\ricar\\.gemini\\antigravity\\brain\\991b5dcb-f6d6-439b-908c-310cd726a425';

if (!fs.existsSync(UPLOADS_DIR)) {
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

// ── Datos enriquecidos de los 31 libros ─────────────────────────────────────
const BOOKS_DATA = [
  {
    id: 1,
    title: 'La Biblioteca de los Sueños Olvidados',
    description: 'Entre muros infinitos y estanterías que cambian cada noche, existe una biblioteca que guarda los sueños que las personas han olvidado. Cuando Lucía encuentra un libro con su nombre, descubre que para recuperar su propio sueño deberá desafiar las reglas de ese misterioso lugar.',
    aiImage: 'cover_biblioteca_suenos_1789169454173.jpg'
  },
  {
    id: 2,
    title: 'El Secreto del Valle Perdido',
    description: 'La crónica de una expedición a través de la selva nubosa, donde un equipo de naturalistas redescubre un cañón prehistórico aislado del mundo durante milenios, enfrentando los enigmas más profundos de una civilización olvidada.',
    aiImage: 'cover_valle_perdido_1789169691771.jpg'
  },
  {
    id: 3,
    title: 'El Eco de las Estrellas Frías',
    description: 'En un observatorio polar en medio del invierno eterno, un grupo de astrónomos intenta descifrar una última transmisión interestelar mientras su comunidad sobrevive al aislamiento y a la escasez en el fin del mundo.',
    aiImage: 'cover_estrellas_frias_1789169594472.jpg'
  },
  {
    id: 4,
    title: 'El Algoritmo de las Mariposas',
    description: 'En un pueblo costero donde las redes neuronales conviven con la magia ancestral, un programador diseña un código capaz de predecir el aleteo de mariposas bioluminiscentes que alteran el destino de sus habitantes.',
    aiImage: 'cover_algoritmo_mariposas_1789169568901.jpg'
  },
  {
    id: 5,
    title: 'La Conspiración del Reloj de Arena',
    description: 'Una mordaz intriga política en la Florencia renacentista, donde un diplomático desacreditado y un fabricante de autómatas desentrañan un complot papal oculto tras las manecillas de un reloj monumental.',
    aiImage: 'cover_reloj_arena_1789179401408.jpg'
  },
  {
    id: 6,
    title: 'Memorias de un Cómico Errante',
    description: 'Las desopilantes y conmovedoras andanzas de un actor de teatro ambulante que recorrió las provincias del siglo XX entre enredos amorosos, quiebras teatrales y aplausos inolvidables.',
    aiImage: 'cover_comico_errante_1789179519225.jpg'
  },
  {
    id: 7,
    title: 'El Pequeño Guardián del Reino Dorado',
    description: 'La entrañable historia de Lucas y su cachorro de dragón dorado, quienes deben emprender un viaje épico a través de valles encantados para restaurar la luz del antiguo castillo real.',
    aiImage: 'cover_reino_dorado_1789169722213.jpg'
  },
  {
    id: 8,
    title: 'Sombras sobre la Mansión Blackwood',
    description: 'Al heredar una vieja casona victoriana al borde de un acantilado tempestuoso, un joven estudiante descubre cartas selladas y apariciones nocturnas que desvelan el oscuro pacto de su linaje.',
    aiImage: 'cover_mansion_blackwood_1789169544715.jpg'
  },
  {
    id: 9,
    title: 'Lluvia de Neón en Medianoche',
    description: 'Un detective cibernético y poeta callejero recorre los callejones empapados por lluvia ácida de Neo-Kioto, persiguiendo los versos encriptados de una inteligencia artificial prófuga.',
    aiImage: 'cover_lluvia_neon_1789169522158.jpg'
  },
  {
    id: 10,
    title: 'La Ciudad de los Espejos Pensantes',
    description: 'Un tratado narrativo sobre una metrópoli flotante de cristal donde la arquitectura refleja y amplifica las dudas éticas, los ideales de justicia y la conciencia de sus ciudadanos.',
    aiImage: 'cover_ciudad_espejos_1789169656713.jpg'
  },
  {
    id: 11,
    title: 'La Sabiduría del Halcón y el Zorro',
    description: 'A través de fábulas campestres protagonizadas por animales comerciantes, este libro desglosa principios eternos sobre negociación, honor comercial y liderazgo prudente.',
    downloadUrl: 'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 12,
    title: 'El Arte de Vencer las Batallas Interiores',
    description: 'Inspirado en las estrategias de los antiguos tratados militares, este manual ofrece tácticas psicológicas para dominar la ansiedad, superar la adversidad y alcanzar la fortaleza mental.',
    downloadUrl: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 13,
    title: 'El Pintor de Sombras y Recuerdos',
    description: 'En el París bohemio, un retratista inconformista finge su propia desaparición para disparar la cotización de sus cuadros, desatando un melodrama desenfrenado en los salones de arte.',
    downloadUrl: 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 14,
    title: 'Alquimia en los Fogones Olvidados',
    description: 'Un fascinante recorrido culinario que rescata ingredientes ancestrales y técnicas de fermentación mística para crear platillos que desafían los sentidos de los comensales.',
    downloadUrl: 'https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 15,
    title: 'Crónicas desde el Callejón de Niebla',
    description: 'Un periodista exiliado recorre los puertos marítimos de entreguerras, registrando en su cuaderno las historias turbias, los cafés clandestinos y las sombras de una Europa en cambio.',
    downloadUrl: 'https://images.unsplash.com/photo-1509114397022-ed747cca3f65?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 16,
    title: 'El Enigma del Relojero de Vapor',
    description: 'Cuando el gran reloj astronómico de la capital se detiene, un relojero clandestino descubre que cada engranaje oculta los planos de una maquinaria capaz de manipular el vapor a escala continental.',
    aiImage: 'cover_relojero_vapor_1789169501873.jpg'
  },
  {
    id: 17,
    title: 'Ecos en el Pantano del Olvido',
    description: 'En las profundidades de los pantanos de Luisiana, una estación de procesamiento biotecnológico abandonada comienza a emitir susurros misteriosos a través de las frecuencias de radio locales.',
    downloadUrl: 'https://images.unsplash.com/photo-1518457607834-6e8d80c183c5?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 18,
    title: 'El Pistolero de las Tierras Encantadas',
    description: 'Un forajido armado con revólveres bendecidos con runas mágicas cabalga por cañones custodiados por espíritus antiguos para saldar una deuda de sangre con un hechicero inmortal.',
    aiImage: 'cover_pistolero_encantado_1789169628316.jpg'
  },
  {
    id: 19,
    title: 'Viajeros del Vórtice Estelar',
    description: 'Una tripulación multicolor a bordo de un carguero estelar navega a través de anomalías hiperespaciales habitadas por criaturas celestiales que conceden deseos a cambio de recuerdos preciosos.',
    downloadUrl: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 20,
    title: 'Promesas bajo el Cerezo Eterno',
    description: 'Dos almas que se encuentran en diferentes épocas históricas coinciden siempre bajo las ramas florecidas del mismo cerezo milenario, desafiando las barreras del tiempo y la memoria.',
    downloadUrl: 'https://images.unsplash.com/photo-1522383225653-ed111181a951?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 21,
    title: 'Tratado sobre el Ingenio Humano',
    description: 'Un ensayo brillante y mordaz que explora cómo la picardía, la supervivencia y las pasiones trágicas han modelado el progreso y las contradicciones de la sociedad moderna.',
    downloadUrl: 'https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 22,
    title: 'Los Pasillos del Poder Invisible',
    description: 'La vida cotidiana de los asesores, secretarios y archivistas de un parlamento federal, revelando cómo los pequeños detalles del día a día deciden el rumbo de una nación entera.',
    downloadUrl: 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 23,
    title: 'Laberintos de la Mente Herida',
    description: 'Una psiquiatra forense en una ciudad nocturna debe desentrañar el testimonio fragmentado de un testigo con amnesia selectiva antes de que el verdadero culpable borre sus huellas.',
    downloadUrl: 'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 24,
    title: 'La Academia de lo Extraordinario',
    description: 'Una satírica y divertida crónica sobre un internado donde los profesores enseñan materias imposibles como \'Aritmética de las Casualidades\' y \'Gramática del Silencio\'.',
    downloadUrl: 'https://images.unsplash.com/photo-1541339907198-e08756dedf3f?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 25,
    title: 'La Última Carrera por la Libertad',
    description: 'En un circuito desolado bajo el sol ardiente de un páramo distópico, un piloto veterano compite en una peligrosa carrera clandestina donde el único premio es la libertad de su pueblo.',
    downloadUrl: 'https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 26,
    title: 'El Santuario tras el Fin del Mundo',
    description: 'Tras el colapso global, una orden de monjes eremitas resguarda los textos sagrados y filosóficos de la humanidad en un monasterio fortificado entre las cumbres andinas.',
    downloadUrl: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 27,
    title: 'El Código del Génesis Perdido',
    description: 'Una viróloga espacial descubre en el ADN de una especie alienígena la clave para curar una plaga que azota a la flota estelar, enfrentándose a corporaciones médicas sin escrúpulos.',
    downloadUrl: 'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 28,
    title: 'El Forjador de Fortunas',
    description: 'La épica trayectoria de un humilde aprendiz de impresor que, a través de su visión para el comercio y el valor del crédito, construye el primer gran imperio editorial y financiero de su era.',
    downloadUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 29,
    title: 'La Balanza de los Héroes Justos',
    description: 'Un joven abogado rebelde y de verbo afilado desafía a los tribunales más corruptos del reino, utilizando la astucia callejera y los principios del derecho para defender a los desposeídos.',
    downloadUrl: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 30,
    title: 'Geometría de los Sueños Infinitos',
    description: 'Un matemático obsesionado con la cuarta dimensión descubre que sus fórmulas fractales abren pasadizos a laberintos oníricos donde las leyes físicas se transforman en poesía visual.',
    downloadUrl: 'https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=600&h=900&q=85'
  },
  {
    id: 31,
    title: 'El Último Horizonte',
    description: 'En un futuro donde la humanidad ha colonizado los confines del sistema solar, una joven ingeniera descubre una señal proveniente de un planeta considerado inhabitable. Su investigación la llevará a cuestionar todo lo que conoce sobre el origen de la humanidad y el futuro de la civilización.',
    aiImage: 'cover_ultimo_horizonte_1789169472650.jpg'
  }
];

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    const get = url.startsWith('https') ? https.get : http.get;

    get(url, (response) => {
      if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        // Redirección
        return downloadFile(response.headers.location, dest).then(resolve).catch(reject);
      }
      if (response.statusCode !== 200) {
        file.close();
        fs.unlink(dest, () => {});
        return reject(new Error(`HTTP ${response.statusCode}`));
      }
      response.pipe(file);
      file.on('finish', () => {
        file.close(resolve);
      });
    }).on('error', (err) => {
      file.close();
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

async function main() {
  console.log('🚀 Iniciando actualización completa de catálogo, sinopsis y portadas...');

  // 1. Asegurar columna alt_text en book_images
  await db.query(`
    DO $$ BEGIN
      ALTER TABLE book_images ADD COLUMN IF NOT EXISTS alt_text VARCHAR(255);
    EXCEPTION WHEN duplicate_column THEN
      NULL;
    END $$;
  `);

  for (const item of BOOKS_DATA) {
    const filename = `cover-book-${item.id}.jpg`;
    const destPath = path.join(UPLOADS_DIR, filename);

    // Si tiene imagen IA generada, copiarla
    if (item.aiImage) {
      const srcPath = path.join(AI_DIR, item.aiImage);
      if (fs.existsSync(srcPath)) {
        fs.copyFileSync(srcPath, destPath);
        console.log(`  ✔ [IA] Portada asignada para Libro ${item.id}: "${item.title}"`);
      } else {
        console.warn(`  ⚠ Archivo IA no encontrado: ${srcPath}`);
      }
    } else if (item.downloadUrl) {
      // Descargar imagen temática
      try {
        await downloadFile(item.downloadUrl, destPath);
        console.log(`  ✔ [Arte] Portada descargada para Libro ${item.id}: "${item.title}"`);
      } catch (e) {
        console.warn(`  ⚠ Error descargando para Libro ${item.id} (${e.message}), manteniendo respaldo`);
      }
    }

    // 2. Actualizar título y descripción en tabla books
    await db.query(`
      UPDATE books
         SET title = $1,
             description = $2
       WHERE id = $3
    `, [item.title, item.description, item.id]);

    // 3. Actualizar tabla book_images
    await db.query('DELETE FROM book_images WHERE book_id = $1', [item.id]);
    await db.query(`
      INSERT INTO book_images (book_id, filename, mime_type, alt_text, is_primary)
      VALUES ($1, $2, 'image/jpeg', $3, true)
    `, [item.id, filename, `Portada de ${item.title}`]);
  }

  console.log('🎉 ¡Catálogo y portadas actualizados con éxito en PostgreSQL y en disco!');
  await db.pool.end();
  process.exit(0);
}

main().catch(err => {
  console.error('❌ Error en actualización:', err);
  process.exit(1);
});

