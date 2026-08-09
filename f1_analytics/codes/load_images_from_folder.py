#!/usr/bin/env python3
"""
F1 Analytics — imagens das equipes a partir de arquivos locais.

Resolve o problema de hospedagem: em vez de depender de URLs de terceiros que
bloqueiam hotlink (Pinterest, sites oficiais) ou somem, você baixa as imagens
uma vez e o script as embute no banco como data URI base64. Funciona offline,
para sempre, sem servidor nenhum.

LIMITE DO POWER BI: uma imagem base64 precisa caber em 32.768 caracteres.
O script redimensiona e comprime automaticamente até caber, e avisa se não der.
Por isso logos funcionam bem; fotos grandes de carro nem sempre — para essas,
use a opção --github (veja no fim).

Estrutura esperada:

    imagens/
      logos/
        McLaren.png
        Ferrari.png
        Red Bull.png
        ...
      carros/
        McLaren.jpg
        Ferrari.jpg
        ...

O nome do arquivo deve ser IGUAL ao constructor_name do banco. Rode com
--listar para ver os nomes exatos que o banco espera.

Uso:
    pip install psycopg2-binary pillow
    python load_images_from_folder.py --listar
    python load_images_from_folder.py --pasta imagens
    python load_images_from_folder.py --pasta imagens --so-logos
"""

from __future__ import annotations

import argparse
import base64
import io
import os
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("Falta dependência. Rode:  pip install psycopg2-binary")

try:
    from PIL import Image
    TEM_PIL = True
except ImportError:
    TEM_PIL = False

DB = {
    "host":     os.getenv("PGHOST", "localhost"),
    "port":     int(os.getenv("PGPORT", 5433)),
    "dbname":   os.getenv("PGDATABASE", "f1"),
    "user":     os.getenv("PGUSER", "f1user"),
    "password": os.getenv("PGPASSWORD", "f1pass"),
}

LIMITE_PBI = 32768          # caracteres máximos que o Power BI aceita
EXTENSOES  = (".png", ".jpg", ".jpeg", ".webp")


def log(m: str = "") -> None:
    print(m, flush=True)


def para_data_uri(caminho: Path, largura_alvo: int) -> tuple[str | None, str]:
    """
    Converte a imagem em data URI base64, encolhendo até caber no limite do
    Power BI. Devolve (uri, mensagem).
    """
    if not TEM_PIL:
        # sem Pillow: tenta o arquivo como está
        dados = caminho.read_bytes()
        mime = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
        uri = f"data:{mime};base64," + base64.b64encode(dados).decode()
        if len(uri) > LIMITE_PBI:
            return None, f"{len(uri):,} chars — excede o limite; instale pillow para redimensionar"
        return uri, f"{len(uri):,} chars"

    img = Image.open(caminho)
    tem_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info

    for largura in (largura_alvo, 300, 240, 200, 160, 120, 96):
        if largura > img.width:
            continue
        copia = img.copy()
        proporcao = largura / copia.width
        copia = copia.resize((largura, max(1, int(copia.height * proporcao))),
                             Image.LANCZOS)

        buf = io.BytesIO()
        if tem_alpha:
            copia = copia.convert("RGBA")
            copia.save(buf, format="PNG", optimize=True)
            mime = "image/png"
        else:
            copia = copia.convert("RGB")
            copia.save(buf, format="JPEG", quality=82, optimize=True)
            mime = "image/jpeg"

        uri = f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()
        if len(uri) <= LIMITE_PBI:
            return uri, f"{largura}px, {len(uri):,} chars"

    return None, "não coube em 32.768 chars nem reduzida — use --github"


def nomes_do_banco(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT c.name
            FROM raw.constructors c
            JOIN raw.results r  ON r."constructorId" = c."constructorId"
            JOIN raw.races  ra  ON ra."raceId" = r."raceId"
            WHERE ra.year >= 2025
            ORDER BY 1
        """)
        return [r[0] for r in cur.fetchall()]


def achar_arquivo(pasta: Path, nome: str) -> Path | None:
    if not pasta.is_dir():
        return None
    for ext in EXTENSOES:
        p = pasta / f"{nome}{ext}"
        if p.exists():
            return p
    # tolera diferenças de caixa e espaços
    alvo = nome.lower().replace(" ", "")
    for p in pasta.iterdir():
        if p.suffix.lower() in EXTENSOES and p.stem.lower().replace(" ", "") == alvo:
            return p
    return None


def gravar(conn, linhas: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.constructor_images (
                constructor_name VARCHAR(120) PRIMARY KEY,
                logo_url         TEXT,
                car_url          TEXT,
                wiki_team_title  VARCHAR(160),
                wiki_car_title   VARCHAR(160),
                source           VARCHAR(30) DEFAULT 'wikipedia',
                updated_at       TIMESTAMP   DEFAULT NOW()
            )
        """)
        psycopg2.extras.execute_values(cur, """
            INSERT INTO raw.constructor_images (constructor_name, logo_url, car_url, source)
            VALUES %s
            ON CONFLICT (constructor_name) DO UPDATE
              SET logo_url   = COALESCE(EXCLUDED.logo_url, raw.constructor_images.logo_url),
                  car_url    = COALESCE(EXCLUDED.car_url,  raw.constructor_images.car_url),
                  source     = 'arquivo local',
                  updated_at = NOW()
        """, linhas)
        cur.execute("""
            CREATE OR REPLACE VIEW mart.dim_constructor AS
            SELECT
                c."constructorId"  AS constructor_id,
                c.name             AS constructor_name,
                c.nationality,
                c.url,
                (SELECT MIN(r.year) FROM raw.results res JOIN raw.races r ON r."raceId" = res."raceId"
                  WHERE res."constructorId" = c."constructorId") AS first_season,
                (SELECT MAX(r.year) FROM raw.results res JOIN raw.races r ON r."raceId" = res."raceId"
                  WHERE res."constructorId" = c."constructorId") AS last_season,
                COALESCE(col.team_color,   '#7A7A88') AS team_color,
                COALESCE(col.accent_color, '#FFFFFF') AS accent_color,
                img.logo_url,
                img.car_url
            FROM raw.constructors c
            LEFT JOIN raw.constructor_colors col ON col.constructor_name = c.name
            LEFT JOIN raw.constructor_images img ON img.constructor_name = c.name
        """)
    conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="imagens")
    ap.add_argument("--listar", action="store_true",
                    help="mostra os nomes de arquivo que o banco espera")
    ap.add_argument("--so-logos", action="store_true")
    ap.add_argument("--so-carros", action="store_true")
    args = ap.parse_args()

    conn = psycopg2.connect(**DB)
    equipes = nomes_do_banco(conn)

    if args.listar:
        log(f"O banco tem {len(equipes)} equipes ativas. Nomeie os arquivos assim:\n")
        log(f"{args.pasta}/logos/")
        for e in equipes:
            log(f"  {e}.png")
        log(f"\n{args.pasta}/carros/")
        for e in equipes:
            log(f"  {e}.jpg")
        log("\nMaiúsculas e espaços são tolerados; a extensão pode ser png, jpg ou webp.")
        conn.close()
        return

    if not TEM_PIL:
        log("AVISO: pillow não instalado. Sem ele não dá para redimensionar, e")
        log("       imagens grandes vão ser rejeitadas. Instale com: pip install pillow\n")

    base = Path(args.pasta)
    if not base.is_dir():
        sys.exit(f"Pasta não encontrada: {base.resolve()}\n"
                 f"Crie {base}/logos e {base}/carros, ou informe --pasta")

    linhas, faltando = [], []
    log(f"{len(equipes)} equipes ativas no banco\n")

    for nome in equipes:
        logo_uri = car_uri = None

        if not args.so_carros:
            p = achar_arquivo(base / "logos", nome)
            if p:
                logo_uri, msg = para_data_uri(p, 240)
                log(f"  logo  {nome:<20} {'ok  ' if logo_uri else 'FALHA'} {msg}")
            else:
                faltando.append(f"logo de {nome}")

        if not args.so_logos:
            p = achar_arquivo(base / "carros", nome)
            if p:
                car_uri, msg = para_data_uri(p, 480)
                log(f"  carro {nome:<20} {'ok  ' if car_uri else 'FALHA'} {msg}")
            else:
                faltando.append(f"carro de {nome}")

        if logo_uri or car_uri:
            linhas.append((nome, logo_uri, car_uri, "arquivo local"))

    if not linhas:
        sys.exit("\nNenhuma imagem encontrada. Rode --listar para ver os nomes esperados.")

    gravar(conn, linhas)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(logo_url), COUNT(car_url) FROM raw.constructor_images")
        n_logo, n_carro = cur.fetchone()

    log(f"\nGravado: {n_logo} logos, {n_carro} carros")
    if faltando:
        log(f"Faltando ({len(faltando)}): {', '.join(faltando[:8])}"
            + (" ..." if len(faltando) > 8 else ""))

    conn.close()
    log("\nNo Power BI: Atualizar -> marque dim_constructor[logo_url] e [car_url]")
    log("como Categoria de Dados -> URL da Imagem.")


if __name__ == "__main__":
    main()
