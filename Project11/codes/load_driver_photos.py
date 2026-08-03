#!/usr/bin/env python3
"""
F1 Analytics — fotos dos pilotos.

Monta a tabela raw.driver_photos (driverId + URL da imagem) e injeta a coluna
photo_url na view mart.dim_driver, para o Power BI exibir a foto sem precisar de
tabela extra nem relacionamento novo.

De onde vêm as imagens: o seu banco já guarda a URL da Wikipedia de cada piloto
em raw.drivers.url. O script extrai o título do artigo dali e pergunta à API da
Wikipedia qual é a imagem principal da página. Nada é inventado nem chutado.

Uso:
    pip install requests
    python load_driver_photos.py                      # pilotos de 2026
    python load_driver_photos.py --seasons 2025 2026
    python load_driver_photos.py --all                # todos os pilotos do banco
    python load_driver_photos.py --export-csv         # exporta para revisar/editar
    python load_driver_photos.py --import-csv fotos.csv   # importa CSV editado
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from urllib.parse import unquote

try:
    import psycopg2
    import psycopg2.extras
    import requests
except ImportError:
    sys.exit("Faltam dependências. Rode:  pip install psycopg2-binary requests")

DB = {
    "host":     os.getenv("PGHOST", "localhost"),
    "port":     int(os.getenv("PGPORT", 5433)),
    "dbname":   os.getenv("PGDATABASE", "f1"),
    "user":     os.getenv("PGUSER", "f1user"),
    "password": os.getenv("PGPASSWORD", "f1pass"),
}

WIKI_API   = "https://en.wikipedia.org/w/api.php"
THUMB_SIZE = 500          # px de largura; suficiente para cartão e tabela
BATCH      = 20           # títulos por requisição (a API aceita até 50)
CSV_PATH   = "driver_photos.csv"

_session = requests.Session()
# A Wikipedia exige um User-Agent identificável, senão devolve 403.
_session.headers["User-Agent"] = "f1-analytics-dashboard/1.0 (uso pessoal; contato via github)"


def log(m: str = "") -> None:
    print(m, flush=True)


# ---------------------------------------------------------------------
def wiki_title(url: str | None) -> str | None:
    """'http://en.wikipedia.org/wiki/Lewis_Hamilton' -> 'Lewis Hamilton'"""
    if not url:
        return None
    m = re.search(r"/wiki/([^?#]+)", url)
    return unquote(m.group(1)).replace("_", " ") if m else None


def buscar_imagens(titulos: list[str]) -> dict[str, str]:
    """Pergunta à API da Wikipedia a imagem principal de cada artigo."""
    achadas: dict[str, str] = {}

    for i in range(0, len(titulos), BATCH):
        lote = titulos[i:i + BATCH]
        params = {
            "action": "query",
            "titles": "|".join(lote),
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": THUMB_SIZE,
            "pilimit": "max",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
        try:
            r = _session.get(WIKI_API, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log(f"  erro no lote {i // BATCH + 1}: {e}")
            continue

        # A API transforma o título em duas etapas encadeadas:
        #   pedido --normalized--> normalizado --redirects--> página final
        # Para devolver na chave que o chamador conhece, desfazemos na ordem
        # inversa. Tratar os dois mapas como um só sobrescreveria o primeiro.
        q = data.get("query", {})
        norm  = {i["to"]: i["from"] for i in q.get("normalized", [])}
        redir = {i["to"]: i["from"] for i in q.get("redirects", [])}

        def titulo_pedido(final: str) -> str:
            passo = redir.get(final, final)
            return norm.get(passo, passo)

        for page in q.get("pages", []):
            titulo_final = page.get("title")
            thumb = (page.get("thumbnail") or {}).get("source")
            if not thumb:                     # artigo sem imagem, ou inexistente
                continue
            achadas[titulo_final] = thumb
            pedido = titulo_pedido(titulo_final)
            if pedido != titulo_final:
                achadas[pedido] = thumb

        log(f"  lote {i // BATCH + 1}: {len(lote)} títulos consultados")
        time.sleep(0.5)      # cortesia com a API

    return achadas


# ---------------------------------------------------------------------
def garantir_tabela(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.driver_photos (
                "driverId"  INTEGER PRIMARY KEY REFERENCES raw.drivers("driverId"),
                driver_ref  VARCHAR(60) NOT NULL,
                photo_url   TEXT,
                source      VARCHAR(30) DEFAULT 'wikipedia',
                updated_at  TIMESTAMP   DEFAULT NOW()
            )
        """)
        cur.execute("COMMENT ON TABLE raw.driver_photos IS "
                    "'URL da foto de cada piloto. Alimentada por load_driver_photos.py'")
    conn.commit()


def pilotos_alvo(conn, seasons: list[int] | None) -> list[tuple]:
    """Pilotos que efetivamente correram nas temporadas pedidas."""
    with conn.cursor() as cur:
        if seasons is None:
            cur.execute("""
                SELECT d."driverId", d."driverRef",
                       d.forename || ' ' || d.surname AS nome, d.url
                FROM raw.drivers d ORDER BY d."driverId"
            """)
        else:
            cur.execute("""
                SELECT DISTINCT d."driverId", d."driverRef",
                       d.forename || ' ' || d.surname AS nome, d.url
                FROM raw.drivers d
                JOIN raw.results r ON r."driverId" = d."driverId"
                JOIN raw.races  ra ON ra."raceId"  = r."raceId"
                WHERE ra.year = ANY(%s)
                ORDER BY 3
            """, (seasons,))
        return cur.fetchall()


def gravar(conn, linhas: list[tuple]) -> None:
    with conn.cursor() as cur:
        # updated_at fica de fora do INSERT: o DEFAULT NOW() da tabela preenche
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.driver_photos ("driverId", driver_ref, photo_url, source)
            VALUES %s
            ON CONFLICT ("driverId") DO UPDATE
              SET photo_url  = EXCLUDED.photo_url,
                  source     = EXCLUDED.source,
                  updated_at = NOW()
        """, linhas)
    conn.commit()


def atualizar_view(conn) -> None:
    """
    Recria mart.dim_driver com photo_url. LEFT JOIN: piloto sem foto continua
    aparecendo normalmente, só com a coluna nula.

    photo_url entra como ÚLTIMA coluna de propósito: CREATE OR REPLACE VIEW só
    aceita colunas novas no fim da lista. Inserir no meio dispara
    "cannot change name of view column".
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE OR REPLACE VIEW mart.dim_driver AS
            SELECT
                d."driverId"                   AS driver_id,
                d.forename || ' ' || d.surname AS driver_name,
                d.surname                      AS driver_surname,
                d.code                         AS driver_code,
                d.number                       AS driver_number,
                d.nationality,
                d.dob                          AS birth_date,
                EXTRACT(YEAR FROM d.dob)::INT  AS birth_year,
                d.url,
                (SELECT MIN(r.year) FROM raw.results res JOIN raw.races r ON r."raceId" = res."raceId"
                  WHERE res."driverId" = d."driverId") AS first_season,
                (SELECT MAX(r.year) FROM raw.results res JOIN raw.races r ON r."raceId" = res."raceId"
                  WHERE res."driverId" = d."driverId") AS last_season,
                p.photo_url
            FROM raw.drivers d
            LEFT JOIN raw.driver_photos p ON p."driverId" = d."driverId"
        """)
    conn.commit()


# ---------------------------------------------------------------------
def exportar_csv(conn, seasons) -> None:
    alvo = pilotos_alvo(conn, seasons)
    with conn.cursor() as cur:
        cur.execute("SELECT \"driverId\", photo_url FROM raw.driver_photos")
        atuais = dict(cur.fetchall())

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["driverId", "driver_ref", "driver_name", "photo_url"])
        for did, ref, nome, _ in alvo:
            w.writerow([did, ref, nome, atuais.get(did, "")])
    log(f"Exportado: {CSV_PATH} ({len(alvo)} pilotos)")
    log("Edite a coluna photo_url e rode:  python load_driver_photos.py --import-csv " + CSV_PATH)


def importar_csv(conn, caminho: str) -> None:
    linhas = []
    with open(caminho, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            url = (row.get("photo_url") or "").strip()
            if url:
                linhas.append((int(row["driverId"]), row["driver_ref"], url, "manual"))
    if not linhas:
        sys.exit("Nenhuma linha com photo_url preenchida no CSV.")
    garantir_tabela(conn)
    gravar(conn, linhas)
    atualizar_view(conn)
    log(f"Importadas {len(linhas)} fotos do CSV.")


# ---------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", type=int, default=[2026])
    ap.add_argument("--all", action="store_true", help="todos os pilotos do banco")
    ap.add_argument("--export-csv", action="store_true")
    ap.add_argument("--import-csv", metavar="ARQUIVO")
    args = ap.parse_args()

    conn = psycopg2.connect(**DB)
    log(f"Conectado em {DB['host']}:{DB['port']}/{DB['dbname']}\n")

    if args.import_csv:
        importar_csv(conn, args.import_csv)
        conn.close()
        return

    garantir_tabela(conn)
    seasons = None if args.all else args.seasons

    if args.export_csv:
        exportar_csv(conn, seasons)
        conn.close()
        return

    alvo = pilotos_alvo(conn, seasons)
    log(f"{len(alvo)} pilotos em {'todas as temporadas' if seasons is None else seasons}")

    # titulo do artigo -> lista de pilotos (dois pilotos podem apontar para o mesmo artigo)
    por_titulo: dict[str, list] = {}
    sem_url = []
    for did, ref, nome, url in alvo:
        t = wiki_title(url)
        if t:
            por_titulo.setdefault(t, []).append((did, ref, nome))
        else:
            sem_url.append(nome)

    if sem_url:
        log(f"  {len(sem_url)} sem URL da Wikipedia: {', '.join(sem_url[:6])}")

    log(f"\nConsultando a Wikipedia ({len(por_titulo)} artigos)...")
    imagens = buscar_imagens(sorted(por_titulo))

    linhas, faltando = [], []
    for titulo, pilotos in por_titulo.items():
        url_img = imagens.get(titulo)
        for did, ref, nome in pilotos:
            if url_img:
                linhas.append((did, ref, url_img, "wikipedia"))
            else:
                faltando.append(nome)

    if linhas:
        gravar(conn, linhas)
    atualizar_view(conn)

    log(f"\n{len(linhas)} fotos gravadas em raw.driver_photos")
    if faltando:
        log(f"{len(faltando)} sem imagem no artigo: {', '.join(faltando)}")
        log("Para preencher à mão:  python load_driver_photos.py --export-csv")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.forename || ' ' || d.surname, LEFT(p.photo_url, 70)
            FROM raw.driver_photos p JOIN raw.drivers d ON d."driverId" = p."driverId"
            ORDER BY 1 LIMIT 5
        """)
        log("\nAmostra:")
        for nome, url in cur.fetchall():
            log(f"  {nome:<26} {url}...")

    conn.close()
    log("\nPronto. No Power BI: Atualizar -> selecione dim_driver[photo_url] ->")
    log("Ferramentas de Coluna -> Categoria de Dados -> URL da Imagem")


if __name__ == "__main__":
    main()
