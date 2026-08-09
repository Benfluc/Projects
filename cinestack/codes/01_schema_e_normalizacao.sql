
-- Tabela principal de filmes.
-- production_companies, credits e keywords ficam como texto puro
-- de proposito: sao buscados por LIKE (substring), entao nao
-- precisam ser quebrados em tabelas separadas.
CREATE TABLE filmes (
    id                    INTEGER PRIMARY KEY,
    title                 TEXT NOT NULL,
    original_language     TEXT,
    overview              TEXT,
    release_date          TEXT,
    budget                REAL,
    revenue               REAL,
    runtime               REAL,
    status                TEXT,
    tagline               TEXT,
    vote_average          REAL,
    vote_count            REAL,
    popularity            REAL,
    poster_path           TEXT,
    backdrop_path         TEXT,
    production_companies  TEXT,
    credits               TEXT,
    keywords              TEXT
);

-- OR IGNORE: se movies_raw tiver ids duplicados (linhas repetidas no
-- CSV de origem, ou import feito duas vezes), a segunda ocorrencia do
-- mesmo id e descartada silenciosamente em vez de travar o script.
INSERT OR IGNORE INTO filmes (
    id, title, original_language, overview, release_date, budget, revenue,
    runtime, status, tagline, vote_average, vote_count, popularity,
    poster_path, backdrop_path, production_companies, credits, keywords
)
SELECT
    CAST(id AS INTEGER),
    title,
    original_language,
    overview,
    release_date,
    CAST(NULLIF(budget, '') AS REAL),
    CAST(NULLIF(revenue, '') AS REAL),
    CAST(NULLIF(runtime, '') AS REAL),
    status,
    tagline,
    CAST(NULLIF(vote_average, '') AS REAL),
    CAST(NULLIF(vote_count, '') AS REAL),
    CAST(NULLIF(popularity, '') AS REAL),
    poster_path,
    backdrop_path,
    production_companies,
    credits,
    keywords
FROM movies_raw;

-- Generos: vocabulario fechado (Action, Comedy, Drama, etc)
CREATE TABLE generos (
    id    INTEGER PRIMARY KEY,
    nome  TEXT UNIQUE NOT NULL
);

INSERT INTO generos (nome)
WITH RECURSIVE split(id, rest, valor) AS (
    SELECT id, genres || '-', NULL
    FROM movies_raw
    WHERE genres IS NOT NULL AND genres <> ''
    UNION ALL
    SELECT id,
           substr(rest, instr(rest, '-') + 1),
           substr(rest, 1, instr(rest, '-') - 1)
    FROM split
    WHERE rest <> ''
)
SELECT DISTINCT trim(valor)
FROM split
WHERE valor IS NOT NULL AND trim(valor) <> ''
ORDER BY 1;

CREATE TABLE filme_genero (
    filme_id   INTEGER NOT NULL REFERENCES filmes(id),
    genero_id  INTEGER NOT NULL REFERENCES generos(id),
    PRIMARY KEY (filme_id, genero_id)
);

-- Algumas linhas de movies_raw tem o id corrompido (colunas
-- desalinhadas por causa de virgula/aspas em overview ou tagline) e
-- por isso nao existem em "filmes". No SQLite, OR IGNORE NAO cobre
-- violacao de FOREIGN KEY (so cobre UNIQUE/PRIMARY KEY/NOT NULL/
-- CHECK) -- entao filtramos essas linhas aqui no proprio WHERE, antes
-- de tentar inserir, em vez de depender do OR IGNORE.
INSERT OR IGNORE INTO filme_genero (filme_id, genero_id)
WITH RECURSIVE split(id, rest, valor) AS (
    SELECT CAST(id AS INTEGER), genres || '-', NULL
    FROM movies_raw
    WHERE genres IS NOT NULL AND genres <> ''
      AND CAST(id AS INTEGER) IN (SELECT id FROM filmes)
    UNION ALL
    SELECT id,
           substr(rest, instr(rest, '-') + 1),
           substr(rest, 1, instr(rest, '-') - 1)
    FROM split
    WHERE rest <> ''
)
SELECT DISTINCT s.id, g.id
FROM split s
JOIN generos g ON g.nome = trim(s.valor)
WHERE s.valor IS NOT NULL AND trim(s.valor) <> '';

-- Filmes semelhantes: "recommendations" e uma lista de IDs
-- (numeros), entao o hifen como separador e 100% seguro aqui.
CREATE TABLE filme_similar (
    filme_id              INTEGER NOT NULL REFERENCES filmes(id),
    filme_recomendado_id  INTEGER NOT NULL,
    PRIMARY KEY (filme_id, filme_recomendado_id)
);

-- Mesmo motivo de filme_genero: pre-filtramos pelo id existir em
-- "filmes" (OR IGNORE nao protege contra FOREIGN KEY no SQLite).
-- filme_recomendado_id nao tem FK (o filme recomendado pode nao
-- estar neste CSV), entao esse lado nao precisa de filtro.
INSERT OR IGNORE INTO filme_similar (filme_id, filme_recomendado_id)
WITH RECURSIVE split(id, rest, valor) AS (
    SELECT CAST(id AS INTEGER), recommendations || '-', NULL
    FROM movies_raw
    WHERE recommendations IS NOT NULL AND recommendations <> ''
      AND CAST(id AS INTEGER) IN (SELECT id FROM filmes)
    UNION ALL
    SELECT id,
           substr(rest, instr(rest, '-') + 1),
           substr(rest, 1, instr(rest, '-') - 1)
    FROM split
    WHERE rest <> ''
)
SELECT DISTINCT id, CAST(trim(valor) AS INTEGER)
FROM split
WHERE valor IS NOT NULL AND trim(valor) <> '';

-- Indices para as consultas mais comuns.
CREATE INDEX idx_filmes_release_date ON filmes(release_date);
CREATE INDEX idx_filmes_vote_average ON filmes(vote_average);
CREATE INDEX idx_filme_genero_genero ON filme_genero(genero_id);
CREATE INDEX idx_filme_similar_filme ON filme_similar(filme_id);

-- Indice de texto completo para
-- busca rapida em ator/produtora/palavra-chave. Sem isso, um
-- LIKE '%Tom Hanks%' em 769 mil linhas faz varredura completa
-- da tabela toda vez -- funciona, mas fica lento.
CREATE VIRTUAL TABLE filmes_fts USING fts5(
    credits, production_companies, keywords,
    content='filmes', content_rowid='id'
);

INSERT INTO filmes_fts (rowid, credits, production_companies, keywords)
SELECT id, credits, production_companies, keywords FROM filmes;

