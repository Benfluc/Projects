-- ============================================================
-- Exemplos de consultas ao Banco de Dados
-- ============================================================

-- 1) Todos os filmes com Tom Hanks
SELECT f.title, f.release_date, f.vote_average
FROM filmes f
JOIN filmes_fts ON filmes_fts.rowid = f.id
WHERE filmes_fts MATCH '"Tom Hanks"'
ORDER BY f.release_date;

-- 2) Filmes de ficcao cientifica produzidos pela Warner
SELECT DISTINCT f.title, f.release_date, f.vote_average, f.production_companies
FROM filmes f
JOIN filme_genero fg ON fg.filme_id = f.id
JOIN generos g ON g.id = fg.genero_id
WHERE g.nome = 'Science Fiction'
  AND f.production_companies LIKE '%Warner%'
ORDER BY f.vote_average DESC;

-- 3) Filmes lancados entre 2010 e 2020 com nota acima de 8
-- (release_date esta em formato ISO "AAAA-MM-DD", entao a
-- comparacao de texto funciona como comparacao de data)
SELECT title, release_date, vote_average
FROM filmes
WHERE release_date BETWEEN '2010-01-01' AND '2020-12-31'
  AND vote_average > 8
ORDER BY vote_average DESC;

-- 4) Filmes semelhantes a um filme especifico
-- (troque 634649 pelo id do filme que voce quiser, ex.: Spider-Man: No Way Home)
SELECT r.title, r.vote_average, r.release_date
FROM filme_similar fs
JOIN filmes r ON r.id = fs.filme_recomendado_id
WHERE fs.filme_id = 634649;

-- 5) Filmes com a palavra-chave "time travel"
SELECT f.title, f.release_date
FROM filmes f
JOIN filmes_fts ON filmes_fts.rowid = f.id
WHERE filmes_fts MATCH 'keywords:"time travel"'
ORDER BY f.release_date;
