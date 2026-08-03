#!/usr/bin/env python3
"""
F1 Analytics — atualização de temporadas via API Jolpica.

O dataset do Kaggle parou em 2024 porque a API Ergast, que o alimentava, foi
desligada no fim daquele ano.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
    import requests
except ImportError:
    sys.exit("Faltam dependências. Rode:  pip install psycopg2-binary requests")

# ---------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------
DB = {
    "host":     os.getenv("PGHOST", "localhost"),
    "port":     int(os.getenv("PGPORT", 5433)),
    "dbname":   os.getenv("PGDATABASE", "f1"),
    "user":     os.getenv("PGUSER", "f1user"),
    "password": os.getenv("PGPASSWORD", "f1pass"),
}

API_BASE   = "https://api.jolpi.ca/ergast/f1"
PAGE_SIZE  = 100
THROTTLE_S = 0.30    # Jolpica permite ~4 req/s; 500 req/h sem autenticação
MAX_RETRY  = 4


def log(msg: str = "") -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------
# Camada de rede
# ---------------------------------------------------------------------
_session = requests.Session()
_session.headers["User-Agent"] = "f1-analytics-loader/1.0"


def fetch_json(path: str, limit: int = PAGE_SIZE, offset: int = 0) -> dict:
    """GET com throttle e retry exponencial. Isolada para facilitar testes."""
    url = f"{API_BASE}/{path}.json"
    params = {"limit": limit, "offset": offset}

    for attempt in range(MAX_RETRY):
        time.sleep(THROTTLE_S)
        try:
            r = _session.get(url, params=params, timeout=30)
            if r.status_code == 429:               # rate limit
                wait = 2 ** attempt * 5
                log(f"    rate limit; aguardando {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["MRData"]
        except requests.RequestException as e:
            if attempt == MAX_RETRY - 1:
                raise
            log(f"    erro de rede ({e}); tentativa {attempt + 2}/{MAX_RETRY}")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"falhou após {MAX_RETRY} tentativas: {url}")


def fetch_all(path: str, extract) -> list:
    """Percorre todas as páginas. `extract` recebe MRData e devolve a lista."""
    out, offset = [], 0
    while True:
        data = fetch_json(path, PAGE_SIZE, offset)
        chunk = extract(data)
        out.extend(chunk)
        total = int(data.get("total", 0))
        offset += PAGE_SIZE
        if offset >= total or not chunk:
            return out


# ---------------------------------------------------------------------
# Conversões
# ---------------------------------------------------------------------
def time_to_ms(t: str | None) -> int | None:
    """'1:26.572' | '26.572' | '1:34:50.616' -> milissegundos."""
    if not t or t.startswith("+"):
        return None
    try:
        parts = t.strip().split(":")
        if len(parts) == 1:
            return round(float(parts[0]) * 1000)
        if len(parts) == 2:
            return round(float(parts[0]) * 60000 + float(parts[1]) * 1000)
        if len(parts) == 3:
            return round(float(parts[0]) * 3600000 + float(parts[1]) * 60000
                         + float(parts[2]) * 1000)
    except ValueError:
        return None
    return None


def as_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def clean_time(t: str | None) -> str | None:
    """'04:00:00Z' -> '04:00:00'."""
    return t.rstrip("Z") if t else None


def position_int(position_text: str | None) -> int | None:
    """
    No Ergast/Jolpica, quem abandona recebe positionText 'R'/'D'/'W'/'N'/'F'/'E'
    mas ainda ocupa uma posição na ordem. A coluna `position` deve ficar NULL
    nesses casos, igual ao dataset original do Kaggle.
    """
    return int(position_text) if position_text and position_text.isdigit() else None


# ---------------------------------------------------------------------
# Cache de chaves: ref textual da API -> id numérico do banco
# ---------------------------------------------------------------------
class KeyMap:
    """
    A API identifica entidades por slug ('max_verstappen', 'red_bull',
    'albert_park'). O banco usa inteiros. Esta classe faz a ponte e cria
    entidades novas na sequência de IDs, sem nunca reciclar IDs antigos.
    """

    def __init__(self, conn, dry_run: bool = False):
        self.conn = conn
        self.dry_run = dry_run
        self.created = {"drivers": [], "constructors": [], "circuits": [], "status": []}
        self._load()

    def _load(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute('SELECT "driverRef", "driverId" FROM raw.drivers')
            self.drivers = dict(cur.fetchall())
            cur.execute('SELECT "constructorRef", "constructorId" FROM raw.constructors')
            self.constructors = dict(cur.fetchall())
            cur.execute('SELECT "circuitRef", "circuitId" FROM raw.circuits')
            self.circuits = dict(cur.fetchall())
            cur.execute('SELECT status, "statusId" FROM raw.status')
            self.status = dict(cur.fetchall())

    def _next_id(self, table: str, col: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute(f'SELECT COALESCE(MAX("{col}"), 0) + 1 FROM raw.{table}')
            return cur.fetchone()[0]

    def driver(self, d: dict) -> int:
        ref = d["driverId"]
        if ref in self.drivers:
            return self.drivers[ref]
        new_id = self._next_id("drivers", "driverId")
        if not self.dry_run:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO raw.drivers
                      ("driverId","driverRef",number,code,forename,surname,dob,nationality,url)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (new_id, ref, as_int(d.get("permanentNumber")), d.get("code"),
                      d.get("givenName"), d.get("familyName"), d.get("dateOfBirth"),
                      d.get("nationality"), d.get("url")))
        self.drivers[ref] = new_id
        self.created["drivers"].append(f'{d.get("givenName")} {d.get("familyName")}')
        return new_id

    def constructor(self, c: dict) -> int:
        ref = c["constructorId"]
        if ref in self.constructors:
            return self.constructors[ref]
        new_id = self._next_id("constructors", "constructorId")
        if not self.dry_run:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO raw.constructors
                      ("constructorId","constructorRef",name,nationality,url)
                    VALUES (%s,%s,%s,%s,%s)
                """, (new_id, ref, c.get("name"), c.get("nationality"), c.get("url")))
        self.constructors[ref] = new_id
        self.created["constructors"].append(c.get("name"))
        return new_id

    def circuit(self, c: dict) -> int:
        ref = c["circuitId"]
        if ref in self.circuits:
            return self.circuits[ref]
        new_id = self._next_id("circuits", "circuitId")
        loc = c.get("Location", {})
        if not self.dry_run:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO raw.circuits
                      ("circuitId","circuitRef",name,location,country,lat,lng,alt,url)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NULL,%s)
                """, (new_id, ref, c.get("circuitName"), loc.get("locality"),
                      loc.get("country"), loc.get("lat"), loc.get("long"), c.get("url")))
        self.circuits[ref] = new_id
        self.created["circuits"].append(c.get("circuitName"))
        return new_id

    def status_id(self, text: str | None) -> int:
        text = text or "Finished"
        if text in self.status:
            return self.status[text]
        new_id = self._next_id("status", "statusId")
        if not self.dry_run:
            with self.conn.cursor() as cur:
                cur.execute('INSERT INTO raw.status ("statusId",status) VALUES (%s,%s)',
                            (new_id, text))
        self.status[text] = new_id
        self.created["status"].append(text)
        return new_id


# ---------------------------------------------------------------------
# Sincronização
# ---------------------------------------------------------------------
def wipe_season(conn, year: int) -> None:
    """
    Apaga os FATOS da temporada, mas preserva as linhas de `races` (e portanto
    os raceId), para que relatórios salvos e IDs não mudem entre execuções.
    A ordem respeita as chaves estrangeiras.
    """
    with conn.cursor() as cur:
        sub = 'SELECT "raceId" FROM raw.races WHERE year = %s'
        for table in ("lap_times", "pit_stops", "qualifying", "sprint_results",
                      "results", "driver_standings", "constructor_standings",
                      "constructor_results"):
            cur.execute(f'DELETE FROM raw.{table} WHERE "raceId" IN ({sub})', (year,))


def sync_races(conn, km: KeyMap, year: int, dry: bool) -> dict[int, int]:
    """Insere/atualiza o calendário. Devolve {round: raceId}."""
    races = fetch_all(f"{year}/races",
                      lambda d: d["RaceTable"]["Races"])
    log(f"  calendário: {len(races)} corridas")

    with conn.cursor() as cur:
        cur.execute("INSERT INTO raw.seasons (year,url) VALUES (%s,%s) "
                    "ON CONFLICT (year) DO NOTHING",
                    (year, f"https://en.wikipedia.org/wiki/{year}_Formula_One_World_Championship"))

    mapping: dict[int, int] = {}
    for r in races:
        rnd = int(r["round"])
        circuit_id = km.circuit(r["Circuit"])

        with conn.cursor() as cur:
            cur.execute('SELECT "raceId" FROM raw.races WHERE year=%s AND round=%s',
                        (year, rnd))
            row = cur.fetchone()
            if row:
                race_id = row[0]
            else:
                cur.execute('SELECT COALESCE(MAX("raceId"),0)+1 FROM raw.races')
                race_id = cur.fetchone()[0]

            fp1 = r.get("FirstPractice", {});  fp2 = r.get("SecondPractice", {})
            fp3 = r.get("ThirdPractice", {});  qua = r.get("Qualifying", {})
            spr = r.get("Sprint", {})
            values = (race_id, year, rnd, circuit_id, r["raceName"], r["date"],
                      clean_time(r.get("time")), r.get("url"),
                      fp1.get("date"), clean_time(fp1.get("time")),
                      fp2.get("date"), clean_time(fp2.get("time")),
                      fp3.get("date"), clean_time(fp3.get("time")),
                      qua.get("date"), clean_time(qua.get("time")),
                      spr.get("date"), clean_time(spr.get("time")))
            if not dry:
                cur.execute("""
                    INSERT INTO raw.races ("raceId",year,round,"circuitId",name,date,time,url,
                        fp1_date,fp1_time,fp2_date,fp2_time,fp3_date,fp3_time,
                        quali_date,quali_time,sprint_date,sprint_time)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT ("raceId") DO UPDATE SET
                        name=EXCLUDED.name, date=EXCLUDED.date, time=EXCLUDED.time,
                        "circuitId"=EXCLUDED."circuitId",
                        sprint_date=EXCLUDED.sprint_date, sprint_time=EXCLUDED.sprint_time,
                        quali_date=EXCLUDED.quali_date, quali_time=EXCLUDED.quali_time
                """, values)
        mapping[rnd] = race_id
    return mapping


def sync_results(conn, km: KeyMap, year: int, rnd: int, race_id: int, dry: bool) -> int:
    races = fetch_all(f"{year}/{rnd}/results",
                      lambda d: d["RaceTable"]["Races"][0]["Results"]
                      if d["RaceTable"]["Races"] else [])
    if not races or dry:
        return len(races)

    rows, team_points = [], {}
    with conn.cursor() as cur:
        cur.execute('SELECT COALESCE(MAX("resultId"),0)+1 FROM raw.results')
        next_id = cur.fetchone()[0]

    for order, res in enumerate(races, start=1):
        driver_id = km.driver(res["Driver"])
        ctor_id   = km.constructor(res["Constructor"])
        status_id = km.status_id(res.get("status"))
        fl        = res.get("FastestLap", {})
        tm        = res.get("Time", {})
        pts       = float(res.get("points", 0))
        team_points[ctor_id] = team_points.get(ctor_id, 0) + pts

        rows.append((
            next_id, race_id, driver_id, ctor_id, as_int(res.get("number")),
            as_int(res.get("grid")) or 0,
            position_int(res.get("positionText")),
            res.get("positionText"), order, pts,
            as_int(res.get("laps")) or 0,
            tm.get("time"), as_int(tm.get("millis")),
            as_int(fl.get("lap")), as_int(fl.get("rank")),
            (fl.get("Time") or {}).get("time"),
            (fl.get("AverageSpeed") or {}).get("speed"),
            status_id,
        ))
        next_id += 1

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.results ("resultId","raceId","driverId","constructorId",number,
                grid,position,"positionText","positionOrder",points,laps,time,milliseconds,
                "fastestLap",rank,"fastestLapTime","fastestLapSpeed","statusId")
            VALUES %s
        """, rows)

        # constructor_results não tem endpoint próprio: derivamos somando os pontos
        cur.execute('SELECT COALESCE(MAX("constructorResultsId"),0)+1 FROM raw.constructor_results')
        cr_id = cur.fetchone()[0]
        cr_rows = []
        for ctor_id, pts in team_points.items():
            cr_rows.append((cr_id, race_id, ctor_id, pts, None))
            cr_id += 1
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.constructor_results
              ("constructorResultsId","raceId","constructorId",points,status)
            VALUES %s
        """, cr_rows)

    return len(rows)


def sync_qualifying(conn, km: KeyMap, year: int, rnd: int, race_id: int, dry: bool) -> int:
    quali = fetch_all(f"{year}/{rnd}/qualifying",
                      lambda d: d["RaceTable"]["Races"][0]["QualifyingResults"]
                      if d["RaceTable"]["Races"] else [])
    if not quali or dry:
        return len(quali)

    with conn.cursor() as cur:
        cur.execute('SELECT COALESCE(MAX("qualifyId"),0)+1 FROM raw.qualifying')
        next_id = cur.fetchone()[0]

    rows = []
    for q in quali:
        rows.append((next_id, race_id, km.driver(q["Driver"]),
                     km.constructor(q["Constructor"]), as_int(q.get("number")),
                     as_int(q.get("position")), q.get("Q1"), q.get("Q2"), q.get("Q3")))
        next_id += 1

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.qualifying ("qualifyId","raceId","driverId","constructorId",
                number,position,q1,q2,q3)
            VALUES %s
        """, rows)
    return len(rows)


def sync_sprint(conn, km: KeyMap, year: int, rnd: int, race_id: int, dry: bool) -> int:
    sprint = fetch_all(f"{year}/{rnd}/sprint",
                       lambda d: d["RaceTable"]["Races"][0]["SprintResults"]
                       if d["RaceTable"]["Races"] else [])
    if not sprint or dry:
        return len(sprint)

    with conn.cursor() as cur:
        cur.execute('SELECT COALESCE(MAX("resultId"),0)+1 FROM raw.sprint_results')
        next_id = cur.fetchone()[0]

    rows = []
    for order, s in enumerate(sprint, start=1):
        fl = s.get("FastestLap", {});  tm = s.get("Time", {})
        rows.append((next_id, race_id, km.driver(s["Driver"]),
                     km.constructor(s["Constructor"]), as_int(s.get("number")),
                     as_int(s.get("grid")) or 0, position_int(s.get("positionText")),
                     s.get("positionText"), order, float(s.get("points", 0)),
                     as_int(s.get("laps")) or 0, tm.get("time"), as_int(tm.get("millis")),
                     as_int(fl.get("lap")), (fl.get("Time") or {}).get("time"),
                     km.status_id(s.get("status"))))
        next_id += 1

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.sprint_results ("resultId","raceId","driverId","constructorId",
                number,grid,position,"positionText","positionOrder",points,laps,time,
                milliseconds,"fastestLap","fastestLapTime","statusId")
            VALUES %s
        """, rows)
    return len(rows)


def sync_pitstops(conn, km: KeyMap, year: int, rnd: int, race_id: int, dry: bool) -> int:
    stops = fetch_all(f"{year}/{rnd}/pitstops",
                      lambda d: d["RaceTable"]["Races"][0]["PitStops"]
                      if d["RaceTable"]["Races"] else [])
    if not stops or dry:
        return len(stops)

    seen, rows = set(), []
    for p in stops:
        driver_id = km.drivers.get(p["driverId"])
        if driver_id is None:          # piloto que não pontuou ainda não mapeado
            continue
        key = (race_id, driver_id, int(p["stop"]))
        if key in seen:
            continue
        seen.add(key)
        rows.append((race_id, driver_id, int(p["stop"]), int(p["lap"]),
                     p["time"], p.get("duration"), time_to_ms(p.get("duration"))))

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.pit_stops ("raceId","driverId",stop,lap,time,duration,milliseconds)
            VALUES %s
        """, rows)
    return len(rows)


def sync_laps(conn, km: KeyMap, year: int, rnd: int, race_id: int, dry: bool) -> int:
    laps = fetch_all(f"{year}/{rnd}/laps",
                     lambda d: d["RaceTable"]["Races"][0]["Laps"]
                     if d["RaceTable"]["Races"] else [])
    if not laps or dry:
        return sum(len(l.get("Timings", [])) for l in laps)

    seen, rows = set(), []
    for lap in laps:
        n = int(lap["number"])
        for t in lap.get("Timings", []):
            driver_id = km.drivers.get(t["driverId"])
            if driver_id is None:
                continue
            key = (race_id, driver_id, n)
            if key in seen:
                continue
            seen.add(key)
            rows.append((race_id, driver_id, n, as_int(t.get("position")),
                         t.get("time"), time_to_ms(t.get("time"))))

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.lap_times ("raceId","driverId",lap,position,time,milliseconds)
            VALUES %s
        """, rows, page_size=500)
    return len(rows)


def sync_standings(conn, km: KeyMap, year: int, rnd: int, race_id: int, dry: bool) -> tuple[int, int]:
    drv = fetch_all(f"{year}/{rnd}/driverstandings",
                    lambda d: (d["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
                               if d["StandingsTable"]["StandingsLists"] else []))
    ctr = fetch_all(f"{year}/{rnd}/constructorstandings",
                    lambda d: (d["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]
                               if d["StandingsTable"]["StandingsLists"] else []))
    if dry:
        return len(drv), len(ctr)

    with conn.cursor() as cur:
        cur.execute('SELECT COALESCE(MAX("driverStandingsId"),0)+1 FROM raw.driver_standings')
        ds_id = cur.fetchone()[0]
        rows = []
        for s in drv:
            rows.append((ds_id, race_id, km.driver(s["Driver"]), float(s["points"]),
                         position_int(s.get("positionText")), s.get("positionText"),
                         int(s.get("wins", 0))))
            ds_id += 1
        if rows:
            psycopg2.extras.execute_values(cur, """
                INSERT INTO raw.driver_standings ("driverStandingsId","raceId","driverId",
                    points,position,"positionText",wins)
                VALUES %s
            """, rows)

        cur.execute('SELECT COALESCE(MAX("constructorStandingsId"),0)+1 FROM raw.constructor_standings')
        cs_id = cur.fetchone()[0]
        rows2 = []
        for s in ctr:
            rows2.append((cs_id, race_id, km.constructor(s["Constructor"]),
                          float(s["points"]), position_int(s.get("positionText")),
                          s.get("positionText"), int(s.get("wins", 0))))
            cs_id += 1
        if rows2:
            psycopg2.extras.execute_values(cur, """
                INSERT INTO raw.constructor_standings ("constructorStandingsId","raceId",
                    "constructorId",points,position,"positionText",wins)
                VALUES %s
            """, rows2)
    return len(drv), len(ctr)


def refresh_dim_date(conn) -> None:
    """
    mart.dim_date é uma TABELA materializada, não uma view: ela não se atualiza
    sozinha quando chegam temporadas novas. Sem isso, a relação de data no Power
    BI fica sem correspondência para 2025+ e as medidas de time intelligence
    param de funcionar. Estende até 31/12 do ano da última corrida.
    """
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS mart.dim_date CASCADE")
        cur.execute("""
            CREATE TABLE mart.dim_date AS
            WITH bounds AS (
                SELECT MIN(date) AS d0,
                       MAKE_DATE(MAX(EXTRACT(YEAR FROM date))::INT, 12, 31) AS d1
                FROM raw.races
            ), dias AS (
                SELECT (b.d0 + n) AS d
                FROM bounds b, generate_series(0, (SELECT d1 - d0 FROM bounds)) AS n
            )
            SELECT d                              AS date,
                   EXTRACT(YEAR    FROM d)::INT   AS year,
                   EXTRACT(QUARTER FROM d)::INT   AS quarter,
                   EXTRACT(MONTH   FROM d)::INT   AS month_number,
                   TO_CHAR(d, 'TMMonth')          AS month_name,
                   TO_CHAR(d, 'YYYY-MM')          AS year_month,
                   EXTRACT(DAY     FROM d)::INT   AS day_of_month,
                   EXTRACT(ISODOW  FROM d)::INT   AS weekday_number,
                   TO_CHAR(d, 'TMDay')            AS weekday_name,
                   (EXTRACT(ISODOW FROM d) >= 6)  AS is_weekend
            FROM dias
        """)
        cur.execute("ALTER TABLE mart.dim_date ADD PRIMARY KEY (date)")


# ---------------------------------------------------------------------
def sync_season(conn, km: KeyMap, year: int, with_laps: bool, dry: bool) -> None:
    log(f"\n{'=' * 60}\nTEMPORADA {year}\n{'=' * 60}")

    if not dry:
        wipe_season(conn, year)
        conn.commit()

    schedule = sync_races(conn, km, year, dry)
    conn.commit()

    today = datetime.now().date()
    with conn.cursor() as cur:
        cur.execute("SELECT round, date FROM raw.races WHERE year=%s ORDER BY round", (year,))
        dates = dict(cur.fetchall())

    totals = {"results": 0, "quali": 0, "sprint": 0, "pits": 0, "laps": 0, "stand": 0}

    for rnd in sorted(schedule):
        if dates.get(rnd) and dates[rnd] > today:
            log(f"  R{rnd:02d} — ainda não disputada, pulando")
            continue

        race_id = schedule[rnd]
        n_res = sync_results(conn, km, year, rnd, race_id, dry)
        if n_res == 0:
            log(f"  R{rnd:02d} — sem resultados publicados ainda")
            conn.commit()
            continue

        n_q  = sync_qualifying(conn, km, year, rnd, race_id, dry)
        n_s  = sync_sprint(conn, km, year, rnd, race_id, dry)
        n_p  = sync_pitstops(conn, km, year, rnd, race_id, dry)
        n_l  = sync_laps(conn, km, year, rnd, race_id, dry) if with_laps else 0
        d, c = sync_standings(conn, km, year, rnd, race_id, dry)
        conn.commit()

        totals["results"] += n_res; totals["quali"] += n_q; totals["sprint"] += n_s
        totals["pits"] += n_p;      totals["laps"] += n_l;  totals["stand"] += d + c

        log(f"  R{rnd:02d} — {n_res} resultados, {n_q} quali, "
            f"{n_s} sprint, {n_p} pits, {n_l} voltas")

    log(f"\n  Totais de {year}: {totals}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", type=int, required=True)
    ap.add_argument("--no-laps", action="store_true",
                    help="pula lap_times (muito mais rápido; ~15x menos requisições)")
    ap.add_argument("--dry-run", action="store_true",
                    help="consulta a API mas não grava nada")
    args = ap.parse_args()

    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    log(f"Conectado em {DB['host']}:{DB['port']}/{DB['dbname']}")
    if args.dry_run:
        log(">>> DRY RUN: nada será gravado <<<")

    km = KeyMap(conn, dry_run=args.dry_run)

    for year in args.seasons:
        sync_season(conn, km, year, not args.no_laps, args.dry_run)

    if not args.dry_run:
        log("\nRegenerando mart.dim_date ...")
        refresh_dim_date(conn)
        conn.commit()
        old = conn.isolation_level
        conn.set_isolation_level(0)
        with conn.cursor() as cur:
            cur.execute("VACUUM ANALYZE;")
        conn.set_isolation_level(old)

    log("\n" + "=" * 60)
    for kind, items in km.created.items():
        if items:
            log(f"Novos {kind} ({len(items)}): {', '.join(map(str, items))}")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.year, COUNT(DISTINCT r."raceId") AS corridas, COUNT(res.*) AS resultados
            FROM raw.races r LEFT JOIN raw.results res ON res."raceId" = r."raceId"
            WHERE r.year >= %s GROUP BY r.year ORDER BY r.year
        """, (min(args.seasons),))
        log("\nano  | corridas | resultados")
        for y, c, n in cur.fetchall():
            log(f"{y} | {c:>8} | {n:>10}")

    conn.close()
    log("\nPronto. Atualize o dataset no Power BI.")


if __name__ == "__main__":
    main()
