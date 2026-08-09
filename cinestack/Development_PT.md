# CineStack: de um CSV bruto a um catálogo de filmes full-stack
![Screenshot da tela inicial do CineStack](https://raw.githubusercontent.com/Benfluc/benfluc.github.io/refs/heads/main/assets/img/cinestack.png)

CineStack é um catálogo de filmes construído do zero a partir de um único CSV bagunçado: um banco SQLite normalizado, uma API REST e um front-end em React com busca, filtros e tema escuro. Esta é a história de como ele foi construído, incluindo o problema de dados que moldou praticamente toda decisão técnica depois dele.

## O dataset e o problema central
A fonte era um export no formato TMDB, [`movies.csv`](https://www.kaggle.com/datasets/harshshinde8/movies-csv), com cerca de 770 mil linhas e colunas como `title`, `genres`, `credits` (elenco), `production_companies`, `keywords` e `recommendations` (uma lista de IDs de filmes semelhantes). Várias dessas colunas guardavam múltiplos valores por linha, unidos por hífen: `Action-Adventure-Fantasy`, ou uma lista de elenco inteira como `Alexander Skarsgård-Nicole Kidman-Claes Bang-...`.

A solução ingênua é `split("-")`. Ela funciona bem para gêneros, porque a lista de gêneros do TMDB é um vocabulário pequeno e fechado, e nenhum dos ~19 nomes tem hífen. Mas ela quebra silenciosamente em qualquer outra coluna, porque o mesmo caractere que separa itens da lista também aparece dentro de nomes reais: sobrenomes de ator como Harper-Jones, nomes de estúdio como Metro-Goldwyn-Mayer. Fazer o split por `-` transforma uma pessoa em duas pessoas falsas. Isso não era teórico — apareceu já nas primeiras linhas do arquivo real (dois atores diferentes de sobrenome Harper-Jones no elenco do mesmo filme, os dois corrompidos silenciosamente por um split ingênuo).

![Nomes que 'quebrariam' usando '-' como split](https://github.com/Benfluc/Projects/blob/main/project10/imgs/affected_names.png)

Essa única observação guiou o design do banco: não forçar um split frágil em dados que não suportam isso. Em vez disso:
Gêneros — um vocabulário fechado e seguro contra hífen — viraram uma tabela normalizada de verdade, com relação muitos-para-muitos com os filmes.
Recomendações — uma lista de IDs numéricos de filme, também segura contra hífen já que dígito nunca colide com o separador — virou uma tabela de relacionamento auto-referenciada de verdade.
Elenco, produtoras e palavras-chave continuaram como colunas de texto puro no próprio filme, buscadas com full-text search em vez de forçadas num formato relacional quebrado. Busca por substring não se importa se um nome foi "separado corretamente" — só precisa que o texto esteja lá.

Um script Python complementar [`normalizar_coluna`](https://github.com/Benfluc/Projects/blob/main/project10/codes/normalizar_coluna.py) também foi construído pra explorar uma correção de verdade da ambiguidade: uma heurística que sinaliza fragmentos de uma palavra só numa lista de elenco como prováveis nomes quebrados, mais um script que busca o elenco correto na API do TMDB só para as linhas sinalizadas como suspeitas — evitando ter que rebuscar 770 mil filmes inteiros.

## Construindo o banco (SQLite, via DB Browser)

O schema foi construído com um único script SQL, escrito para ser idempotente (seguro de rodar de novo do zero), usando uma CTE recursiva para quebrar as colunas delimitadas `genres` e `recommendations` em linhas de verdade — o padrão clássico do SQLite pra explodir uma string delimitada sem nenhum código procedural. Uma tabela virtual `FTS5` foi criada sobre `credits`, `production_companies` e `keywords`, então uma busca como `credits:"Tom Hanks"` roda como uma consulta indexada em vez de uma varredura completa em 770 mil linhas.
Chegar lá exigiu algumas rodadas reais de depuração, que acabaram sendo boas lições por si só:
Um `UNIQUE constraint failed` no `id` — rastreado até linhas genuinamente duplicadas no CSV de origem (cerca de 107 mil delas), não corrupção. Confirmado com uma checagem simples de `COUNT(*)` vs `COUNT(DISTINCT id)`, depois resolvido com `INSERT OR IGNORE`.
Um `FOREIGN KEY constraint failed` que o `INSERT OR IGNORE` não resolveu — porque as cláusulas de resolução de conflito do SQLite não cobrem violação de chave estrangeira, só `UNIQUE`/`PRIMARY KEY`/`NOT NULL`/`CHECK`. A correção de verdade foi pré-filtrar as linhas contra a tabela pai antes de inserir, em vez de depender de uma cláusula de conflito pra abortar depois do fato.
Um erro de `database is locked` em tempo de execução — causado pelo DB Browser mantendo o arquivo aberto com um lock pendente enquanto a API tentava ler ao mesmo tempo.

- [Normalização do Banco de Dados e criação das Tabelas Entidade-Relacionamento](https://github.com/Benfluc/Projects/blob/main/project10/codes/01_schema_e_normalizacao.sql)
- [Consultas de exemplo](https://github.com/Benfluc/Projects/blob/main/project10/codes/02_consultas_exemplo.sql)


## O backend: Express, e um desvio por dependência nativa
A API é um servidor Express pequeno, expondo:
`GET /api/filmes` — busca e filtro por título, ator, produtora, palavra-chave, gênero, intervalo de ano de lançamento e nota mínima, com paginação e ordenação.
`GET /api/filmes/:id` — detalhe completo do filme, incluindo gêneros e filmes semelhantes.
`GET /api/generos` — a lista de gêneros, pra popular o filtro do front-end.
A primeira tentativa usou `better-sqlite3`, um módulo nativo — que falhou ao instalar no Windows porque precisava compilar a partir do código-fonte sem as ferramentas de build C++ do Visual Studio instaladas. Em vez de pedir a instalação de uma toolchain de vários gigabytes, a correção foi abandonar a dependência nativa por completo e usar o módulo `node:sqlite`, embutido no próprio Node (estável o suficiente, sem flag desde o Node 24), que tem uma API síncrona quase idêntica. Zero compilação nativa, zero dependência extra de sistema.
Todas as consultas são parametrizadas, as colunas de ordenação são validadas contra uma lista branca em vez de interpoladas diretamente, e os termos de busca livre são escapados como frases literais do FTS5 pra que um campo de busca não possa ser usado pra injetar sintaxe de query.


## O front-end: React, Tailwind e uma passada de UX
A interface começou como um componente único com dados fictícios, pra validar a direção do design rapidamente, e depois foi conectada à API de verdade: busca com debounce em título, ator, intervalo de ano e nota mínima, chips de filtro de gênero (traduzidos pra português na exibição, enquanto a consulta por baixo continua batendo com os valores em inglês guardados no banco), grade de resultados paginada, e um modal de detalhe — mostrando sinopse, elenco, produtoras e filmes semelhantes buscados no clique — em vez de navegar pra uma página separada.
Uma primeira passada de UX revelou lacunas reais de usabilidade: os cards não eram clicáveis, não tinha título de página, e buscas como "filmes com Tom Hanks" falhavam silenciosamente porque o único campo de busca só batia com o título do filme. A correção não foi um campo de busca mais "inteligente" — foi expor os filtros que o backend já suportava (ator, ano, nota) como campos próprios, além de uma seção inicial (hero) e um tema escuro pra sensação geral do site.

## Publicando
O projeto é entregue em três pastas — `backend`, `frontend`, `database` — com um `.gitignore` que exclui `node_modules`, os arquivos `.env` reais e, principalmente, o arquivo do banco SQLite de quase 900MB (o GitHub recusa qualquer arquivo acima de 100MB). O README documenta como reconstruir o banco a partir do CSV de origem em vez de versionar o binário.

## O que esse projeto envolve
Limpeza e modelagem de um dataset real, grande e imperfeito; a decisão deliberada de não normalizar demais dados que não suportam isso; processamento de string em SQL sem código procedural; depuração de problemas de constraint e lock no SQLite; contornar um bloqueio de dependência nativa no Windows; construção de uma API REST pequena, parametrizada e segura contra injeção; e um front-end em React que evoluiu de um mockup estático pra uma interface totalmente orientada a dados, guiada por feedback real de usabilidade.

O produto final desse projeto pode ser visto [aqui](https://github.com/Benfluc/CineStack).
