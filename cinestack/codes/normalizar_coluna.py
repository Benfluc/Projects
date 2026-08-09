import pandas as pd


def normalizar_coluna(df, coluna, nome_id, correcoes=None):
    """
    Normaliza uma coluna cujos valores estão concatenados com "-".

    ATENÇÃO (limitação dos dados, não do código): o "-" é usado tanto como
    separador entre itens quanto, às vezes, dentro do próprio nome
    (ex.: "James Harper-Jones" em credits, "Metro-Goldwyn-Mayer" em
    production_companies). Como o mesmo caractere tem os dois papéis, não
    existe forma de split() distinguir os dois casos com 100% de certeza —
    nomes com hífen interno serão fragmentados em itens separados, A MENOS
    que o filme esteja em `correcoes` (ver abaixo).

    Parâmetros
    ----------
    df : DataFrame
        Precisa conter uma coluna "id" (chave do filme).
    coluna : str
        Nome da coluna a normalizar (genres, credits, production_companies...).
    nome_id : str
        Nome da chave estrangeira na tabela de relacionamento.
        Ex.: genero_id, ator_id, produtora_id.
    correcoes : dict[str, list[str]], opcional
        Mapeamento id do filme (como string) -> lista de itens já corretos,
        vindos por exemplo da API do TMDB (ver tmdb_fetch_correcoes.py).
        Para os filmes presentes aqui, a lista é usada no lugar do split
        ingênuo por "-", contornando o problema de nomes com hífen interno.
        Filmes fora desse dicionário continuam usando o split normal.

    Retorna
    -------
    tabela : DataFrame
        Colunas: id, nome.
    relacionamento : DataFrame
        Colunas: filme_id, <nome_id>. Sempre tem essas duas colunas,
        mesmo quando não há nenhuma relação (coluna inteira vazia).
    """
    if "id" not in df.columns:
        raise ValueError('df precisa ter uma coluna "id".')
    if coluna not in df.columns:
        raise ValueError(f'Coluna "{coluna}" não existe no DataFrame.')

    correcoes = correcoes or {}

    def processar_linha(id_filme, texto):
        chave_correcao = str(id_filme)
        if chave_correcao in correcoes:
            brutos = correcoes[chave_correcao]
        elif pd.isna(texto):
            return None
        else:
            brutos = texto.split("-")

        limpo = sorted({p.strip() for p in brutos if p and p.strip()})
        return limpo if limpo else None

    # Loop em Python (não totalmente vetorizado) porque cada linha pode vir
    # do split ingênuo OU de `correcoes`, dependendo do id — um dict lookup
    # por linha não dá pra expressar com operações vetorizadas do pandas
    # de forma direta. Para os ~770 mil filmes do dataset isso ainda roda
    # em poucos segundos; não é o gargalo real do pipeline.
    itens = pd.Series(
        [processar_linha(i, t) for i, t in zip(df["id"], df[coluna])],
        index=df.index,
    ).dropna()

    # --- tabela de dimensão ---
    valores = sorted({item for lista in itens for item in lista})
    tabela = pd.DataFrame({"nome": valores})
    tabela.insert(0, "id", range(1, len(tabela) + 1))
    mapa = dict(zip(tabela["nome"], tabela["id"]))

    # --- tabela de relacionamento (vetorizado, sem iterrows) ---
    relacionamento = itens.explode()
    relacionamento = pd.DataFrame({
        "filme_id": df.loc[relacionamento.index, "id"].to_numpy(),
        nome_id: relacionamento.map(mapa).to_numpy(),
    })

    if relacionamento.empty:
        relacionamento = pd.DataFrame(columns=["filme_id", nome_id])

    return tabela, relacionamento
