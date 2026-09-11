# Diseño ER — 3FN (Librería en línea)

```
 ┌──────────────┐        ┌──────────────────┐        ┌──────────────┐
 │   authors    │        │   book_authors    │        │    genres    │
 │──────────────│        │───────────────────│        │──────────────│
 │ id PK        │◄──────┤ book_id  FK        │        │ id PK        │
 │ name UNIQUE  │        │ author_id FK       │        │ name UNIQUE  │
 └──────────────┘        └─────────┬──────────┘        └──────┬───────┘
                                    │                           │
                                    ▼                           │
                          ┌──────────────────┐                  │
                          │      books        │                 │
                          │───────────────────│                 │
                          │ id PK              │                 │
                          │ isbn UNIQUE         │                │
                          │ title               │                │
                          │ publication_year    │                │
                          │ price               │                │
                          │ stock               │                │
                          │ format_id   FK ─────┼──► formats(id) │
                          │ category_id FK ─────┼──► categories(id)
                          │ description         │                │
                          │ created_at/updated_at│               │
                          └─────────┬───────────┘                │
                                    │                             │
                     ┌──────────────┼───────────────┐             │
                     ▼              ▼               ▼             │
          ┌──────────────────┐ ┌────────────────┐ ┌───────────────┴──┐
          │  book_concepts    │ │  book_images    │ │   book_genres     │
          │───────────────────│ │─────────────────│ │───────────────────│
          │ id PK             │ │ id PK           │ │ book_id  FK       │
          │ book_id FK        │ │ book_id FK      │ │ genre_id FK       │
          │ name              │ │ filename        │ └───────────────────┘
          │ definition        │ │ mime_type       │
          │ UNIQUE(book_id,   │ │ is_primary      │
          │        name)      │ │ uploaded_at     │
          └───────────────────┘ └─────────────────┘

 ┌──────────────┐          ┌──────────────┐
 │    users      │          │    formats    │   ┌──────────────┐
 │──────────────│          │──────────────│   │  categories   │
 │ id PK         │          │ id PK        │   │──────────────│
 │ username UNIQUE│         │ name UNIQUE  │   │ id PK        │
 │ email UNIQUE   │         └──────────────┘   │ name UNIQUE  │
 │ password_hash  │                            └──────────────┘
 │ role (user|admin)
 │ created_at
 │ -- índice único parcial: máximo 1 fila con role='admin'
 └───────────────┘
```

## Por qué autores, géneros, conceptos e imágenes NO son listas dentro de `books`

Si `books` tuviera columnas como `autores = "Autor A, Autor B"` o un
array de imágenes:

1. **Viola 1FN** (valores no atómicos) si se guardan como texto separado
   por comas.
2. **Redundancia y anomalías de actualización:** cambiar el nombre de un
   autor obligaría a actualizar cada libro donde aparece.
3. **Imposible indexar o consultar eficientemente** "todos los libros de
   un autor" sin `LIKE '%...%'` sobre texto libre.
4. **Dependencias multivaluadas independientes:** "un libro tiene varios
   autores" y "un libro tiene varios géneros" son hechos independientes
   entre sí; mezclarlos en una sola tabla ancha generaría filas
   redundantes (el problema clásico que 4FN resuelve separándolos en
   tablas puente independientes: `book_authors` y `book_genres`).
5. **Conceptos son un caso especial:** el mismo nombre de concepto
   puede tener **definiciones distintas** en libros distintos, por lo
   que la definición depende del par `(book_id, name)` y no puede vivir
   en un catálogo compartido de conceptos: se modela como tabla propia
   (`book_concepts`) referenciando a `books`.

## Reglas de negocio protegidas en el esquema

- `UNIQUE (books.isbn)` — no puede haber dos libros con el mismo ISBN.
- `UNIQUE ((role)) WHERE role = 'admin'` — máximo un administrador.
- `CHECK (price >= 0)`, `CHECK (stock >= 0)`,
  `CHECK (publication_year BETWEEN 1450 AND 2100)`.
- `CHECK (mime_type IN ('image/jpeg','image/png','image/webp'))`.
- `ON DELETE CASCADE` en las tablas hijas de `books` (autores/géneros/
  conceptos/imágenes desaparecen si se borra el libro, evitando huérfanos).
