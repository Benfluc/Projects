#!/usr/bin/env python3
"""
F1 Analytics - Carga do dataset Kaggle no PostgreSQL.

Faz tudo em uma tacada:
  1. cria os schemas raw/mart (01_schema.sql)
  2. carrega os 14 CSVs via COPY, na ordem correta de chaves estrangeiras
  3. cria as views do mart (02_views.sql)
  4. roda ANALYZE e valida contagens e integridade

Uso:
    pip install psycopg2-binary
    python load_data.py
    python load_data.py --skip-schema     # só recarrega os dados
    python load_data.py --only-validate   # só confere o que já está no banco
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from pathlib import Path

try:
    import psycopg2
except ImportError:
    sys.exit("Falta a dependência. Rode:  pip install psycopg2-binary")

# ---------------------------------------------------------------------
# Conexão (bate com o docker-compose.yml)
# ---------------------------------------------------------------------
DB = {
    "host":     os.getenv("PGHOST", "localhost"),
    "port":     int(os.getenv("PGPORT", 5433)),
    "dbname":   os.getenv("PGDATABASE", "f1"),
    "user":     os.getenv("PGUSER", "f1user"),
    "password": os.getenv("PGPASSWORD", "f1pass"),
}

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR  = BASE_DIR / "sql"

# ---------------------------------------------------------------------
# Ordem de carga: pais antes de filhos, senão a FK barra
# (arquivo_csv, tabela_destino)
# ---------------------------------------------------------------------
LOAD_ORDER = [
    ("seasons.csv",               "raw.seasons"),
    ("status.csv",                "raw.status"),
    ("circuits.csv",              "raw.circuits"),
    ("constructors.csv",          "raw.constructors"),
    ("drivers.csv",               "raw.drivers"),
    ("races.csv",                 "raw.races"),
    ("results.csv",               "raw.results"),
    ("sprint_results.csv",        "raw.sprint_results"),
    ("qualifying.csv",            "raw.qualifying"),
    ("pit_stops.csv",             "raw.pit_stops"),
    ("lap_times.csv",             "raw.lap_times"),
    ("constructor_results.csv",   "raw.constructor_results"),
    ("constructor_standings.csv", "raw.constructor_standings"),
    ("driver_standings.csv",      "raw.driver_standings"),
]

# Colunas de data/hora que vêm vazias ou como "\N" e precisam virar NULL de verdade.
# O COPY do Postgres já trata \N, mas o Kaggle às vezes traz "" em campos de tempo.
NULLABLE_BLANKS = {"", "\\N", "\\n", "N", "null", "NULL"}


def log(msg: str) -> None:
    print(msg, flush=True)


def connect():
    try:
        return psycopg2.connect(**DB)
    except psycopg2.OperationalError as e:
        sys.exit(
            f"Não consegui conectar em {DB['host']}:{DB['port']}.\n"
            f"O container está de pé? Rode:  docker compose up -d\n\n{e}"
        )


def run_sql_file(conn, path: Path) -> None:
    log(f"  executando {path.name} ...")
    with conn.cursor() as cur:
        cur.execute(path.read_text(encoding="utf-8"))
    conn.commit()


def clean_csv(path: Path) -> tuple[io.StringIO, list[str], int]:
    """
    Lê o CSV e normaliza os marcadores de nulo do Kaggle ('\\N', '') para \\N,
    que é o NULL padrão do COPY TEXT. Devolve um buffer TAB-separated.
    Usar TSV evita conflito com as vírgulas dentro de nomes ("Brawn GP, Ltd").
    """
    buf = io.StringIO()
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = 0
        for row in reader:
            out = []
            for value in row:
                v = value.strip()
                if v in NULLABLE_BLANKS:
                    out.append("\\N")
                else:
                    # escapa os caracteres especiais do formato TEXT do COPY
                    out.append(
                        v.replace("\\", "\\\\")
                         .replace("\t", "\\t")
                         .replace("\n", "\\n")
                         .replace("\r", "")
                    )
            buf.write("\t".join(out) + "\n")
            rows += 1
    buf.seek(0)
    return buf, header, rows


def load_table(conn, csv_name: str, table: str) -> int:
    path = DATA_DIR / csv_name
    if not path.exists():
        sys.exit(f"Arquivo não encontrado: {path}\nColoque os 14 CSVs em ./data/")

    buf, header, rows = clean_csv(path)
    cols = ", ".join(f'"{c.strip()}"' for c in header)

    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {table} CASCADE;")
        cur.copy_expert(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
    conn.commit()

    log(f"  {table:<34} {rows:>7,} linhas  ({time.time() - t0:.1f}s)")
    return rows


def validate(conn) -> bool:
    log("\n=== VALIDAÇÃO ===")
    ok = True

    checks = [
        ("Corridas por década", """
            SELECT (year/10*10) || 's' AS decada, COUNT(*) AS corridas
            FROM raw.races GROUP BY 1 ORDER BY 1
        """),
        ("Cobertura temporal", """
            SELECT MIN(year) AS primeira, MAX(year) AS ultima,
                   COUNT(DISTINCT year) AS temporadas, COUNT(*) AS corridas
            FROM raw.races
        """),
        ("Top 5 vitórias (sanidade: Hamilton/Schumacher no topo)", """
            SELECT d.forename || ' ' || d.surname AS piloto, COUNT(*) AS vitorias
            FROM raw.results r JOIN raw.drivers d ON d."driverId" = r."driverId"
            WHERE r."positionOrder" = 1
            GROUP BY 1 ORDER BY 2 DESC LIMIT 5
        """),
        ("Órfãos (deve ser tudo zero)", """
            SELECT
              (SELECT COUNT(*) FROM raw.results  x LEFT JOIN raw.races  y ON y."raceId"=x."raceId"   WHERE y."raceId"   IS NULL) AS results_sem_corrida,
              (SELECT COUNT(*) FROM raw.lap_times x LEFT JOIN raw.races y ON y."raceId"=x."raceId"   WHERE y."raceId"   IS NULL) AS voltas_sem_corrida,
              (SELECT COUNT(*) FROM raw.results  x LEFT JOIN raw.drivers y ON y."driverId"=x."driverId" WHERE y."driverId" IS NULL) AS results_sem_piloto
        """),
        ("Nulos esperados (não é erro, é a era clássica)", """
            SELECT
              (SELECT COUNT(*) FROM raw.drivers WHERE code IS NULL)      AS pilotos_sem_code,
              (SELECT COUNT(*) FROM raw.results WHERE position IS NULL)  AS resultados_sem_posicao,
              (SELECT COUNT(*) FROM raw.races   WHERE sprint_date IS NULL) AS corridas_sem_sprint
        """),
    ]

    with conn.cursor() as cur:
        for title, sql in checks:
            cur.execute(sql)
            headers = [d[0] for d in cur.description]
            rows = cur.fetchall()
            log(f"\n{title}")
            log("  " + " | ".join(h.ljust(22) for h in headers))
            for row in rows:
                log("  " + " | ".join(str(v).ljust(22) for v in row))
            if "Órfãos" in title and any(v for v in rows[0]):
                ok = False
                log("  !! integridade referencial quebrada")

        # As views do mart respondem?
        cur.execute("""
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'mart' ORDER BY table_name
        """)
        views = [r[0] for r in cur.fetchall()]
        log(f"\nViews do mart criadas ({len(views)}): {', '.join(views)}")

        for v in views:
            try:
                cur.execute(f"SELECT COUNT(*) FROM mart.{v}")
                log(f"  mart.{v:<32} {cur.fetchone()[0]:>8,} linhas")
            except Exception as e:
                ok = False
                log(f"  mart.{v:<32} ERRO: {e}")
                conn.rollback()

    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-schema",  action="store_true", help="não recria as tabelas")
    ap.add_argument("--only-validate", action="store_true", help="só roda a validação")
    args = ap.parse_args()

    conn = connect()
    conn.autocommit = False
    log(f"Conectado em {DB['host']}:{DB['port']}/{DB['dbname']}\n")

    if args.only_validate:
        validate(conn)
        conn.close()
        return

    if not args.skip_schema:
        log("=== 1/4 SCHEMA ===")
        run_sql_file(conn, SQL_DIR / "01_schema.sql")

    log("\n=== 2/4 CARGA DOS CSVs ===")
    t0 = time.time()
    total = sum(load_table(conn, csv_name, table) for csv_name, table in LOAD_ORDER)
    log(f"  total: {total:,} linhas em {time.time() - t0:.1f}s")

    log("\n=== 3/4 VIEWS DO MART ===")
    run_sql_file(conn, SQL_DIR / "02_views.sql")

    log("\n=== 4/4 ANALYZE ===")
    old_isolation = conn.isolation_level
    conn.set_isolation_level(0)   # VACUUM/ANALYZE não roda dentro de transação
    with conn.cursor() as cur:
        cur.execute("VACUUM ANALYZE;")
    conn.set_isolation_level(old_isolation)
    log("  estatísticas do planner atualizadas")

    ok = validate(conn)
    conn.close()

    log("\n" + ("PRONTO. Banco carregado." if ok else "Carregado COM AVISOS - revise acima."))
    log("Power BI -> Obter Dados -> PostgreSQL -> localhost:5433 / f1  (schema: mart)")


if __name__ == "__main__":
    main()
