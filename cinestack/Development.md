# CineStack: from a raw CSV to a full-stack movie catalog
![Screenshot of CineStack](https://raw.githubusercontent.com/Benfluc/benfluc.github.io/refs/heads/main/assets/img/cinestack.png)

CineStack is a movie catalog built end to end from a single messy CSV export: a normalized SQLite database, a REST API, 
and a React front end with search, filtering, and a dark UI. This is the story of how it was built, including the data problem that shaped every decision after it.

## The dataset and the core problem
The source was a TMDB-style export, [`movies.csv`](https://www.kaggle.com/datasets/harshshinde8/movies-csv), with roughly 770,000 rows and columns like `title`, `genres`, `credits` (cast), `production_companies`, `keywords`, and `recommendations` (a list of similar movie IDs). Several of those columns held multiple values per row, joined with a hyphen: `Action-Adventure-Fantasy`, or a full cast list like `Alexander Skarsgård-Nicole Kidman-Claes Bang-...`.

The naive fix is `split("-")`. It works fine for genres, because TMDB's genre list is a small, fixed vocabulary and none of the ~19 names contain a hyphen. 
It quietly breaks for anything else, because the same character that separates list items also shows up inside real names: actor surnames like Harper-Jones, studio names like Metro-Goldwyn-Mayer. 
Splitting on `-` turns one person into two fake ones. This wasn't theoretical — it showed up in the very first rows of the real file (two different actors named Harper-Jones in the same movie's cast list, both silently corrupted by a naive split).

![Names that would break when using '-' as split](https://github.com/Benfluc/Projects/blob/main/project10/imgs/affected_names.png)

That single observation drove the database design: don't force a fragile split on data that can't support it. Instead:
Genres — a closed, hyphen-safe vocabulary — became a proper normalized table with a many-to-many relationship to movies.
Recommendations — a list of numeric movie IDs, also hyphen-safe since digits never collide with the separator — became a proper self-referencing relationship table.
Cast, production companies, and keywords stayed as raw text columns on the movie itself, searched with full-text search instead of being forced into a broken relational shape. Substring search doesn't care whether a name was technically "split correctly" — it just needs the text to be there.

A companion Python script [`normalizar_coluna`](https://github.com/Benfluc/Projects/blob/main/project10/codes/normalizar_coluna.py) was also built to explore fixing the ambiguity properly: a heuristic that flags single-word fragments in a cast list as likely broken names, plus a script that re-fetches the correct cast from the TMDB API only for the flagged, suspicious rows — avoiding a full re-fetch of 770,000 movies.


## Building the database (SQLite, via DB Browser)
The schema was built with a single SQL script, written to be idempotent (safe to re-run from a clean slate), using a recursive CTE to split the delimited `genres` and `recommendations` columns into proper rows — the classic SQLite pattern for exploding a delimited string without any procedural code. A `FTS5` virtual table was added on top of `credits`, `production_companies`, and `keywords`, so a search like `credits:"Tom Hanks"` runs as an indexed lookup instead of a full scan over 770k rows.
Getting there took a few real debugging rounds, which turned out to be good lessons in their own right:
A `UNIQUE constraint failed` on `id` — traced back to genuinely duplicate rows in the source CSV (about 107,000 of them), not corruption. Confirmed with a simple `COUNT(*)` vs `COUNT(DISTINCT id)` check, then handled with `INSERT OR IGNORE`.
A `FOREIGN KEY constraint failed` that `INSERT OR IGNORE` did not fix — because SQLite's conflict resolution clauses don't cover foreign key violations, only `UNIQUE`/`PRIMARY KEY`/`NOT NULL`/`CHECK`. The real fix was pre-filtering rows against the parent table before inserting, not relying on a conflict clause to bail out after the fact.

- [Database normalization and ER table creation](https://github.com/Benfluc/Projects/blob/main/project10/codes/01_schema_e_normalizacao.sql)
- [Sample queries](https://github.com/Benfluc/Projects/blob/main/project10/codes/02_consultas_exemplo.sql)


## The backend: Express, and a native-dependency detour
The API is a small Express server exposing:
`GET /api/filmes` — search and filter by title, actor, production company, keyword, genre, release year range, and minimum rating, with pagination and sorting.
`GET /api/filmes/:id` — full movie detail, including genres and similar movies.
`GET /api/generos` — the genre list, to populate the front-end filter.

The first attempt used `better-sqlite3`, a native addon — which failed to install on Windows because it needed to compile from source without Visual Studio's C++ build tools present. Rather than asking for a multi-gigabyte toolchain install, the fix was to drop the native dependency entirely and use Node's own built-in `node:sqlite` module (stable enough, flag-free since Node 24), which has almost the same synchronous API. Zero native compilation, zero extra system dependencies.

All queries are parameterized, sort columns are validated against a whitelist instead of interpolated directly, and free-text search terms are escaped into literal FTS5 phrases so a search box can't be used to inject query syntax.

## The frontend: React, Tailwind, and a UX pass
The UI started as a single component with mock data to validate the design direction quickly, then was wired to the real API: debounced search across title, actor, year range, and minimum rating, genre filter chips (translated to Portuguese for display, while the underlying query still matches the English values stored in the database), a paginated results grid, and a detail modal — showing synopsis, cast, production companies, and similar movies fetched on click — instead of navigating to a separate page.

An early UX pass surfaced real usability gaps: cards weren't clickable, there was no page title, and searches like "movies with Tom Hanks" silently failed because the single search box only ever matched movie titles. The fix wasn't a smarter search box — it was exposing the filters the backend already supported (actor, year, rating) as their own fields, plus a hero section and a dark theme for the overall feel.

## Shipping it
The project ships as three folders — `backend`, `frontend`, `database` — with a `.gitignore` that excludes `node_modules`, real `.env` files, and, critically, the ~900MB SQLite database file itself (GitHub rejects anything over 100MB per file). The README documents how to rebuild the database from the source CSV instead of shipping the binary.

## What this project touches
Cleaning and modeling a large, imperfect real-world dataset; making a deliberate call not to over-normalize data that can't support it; SQL string processing without procedural code; debugging constraint and locking issues in SQLite; working around a native-dependency wall on Windows; building a small, parameterized, injection-safe REST API; and a React front end that evolved from a static mockup into a fully data-driven UI based on real usability feedback.

The final product of this project can be viewed [here](https://github.com/Benfluc/CineStack).
