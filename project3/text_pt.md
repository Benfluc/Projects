# Análise Exploratória de Dados: Um estudo sobre os acidentes de trabalho no Brasil

Este projeto realiza uma análise exploratória de dados (EDA) sobre acidentes de trabalho no Brasil, utilizando bases de dados oficiais para identificar padrões, tendências e fatores de risco associados a incidentes ocupacionais.
O estudo aplica análise estatística, visualização de dados e técnicas descritivas para compreender a distribuição dos acidentes entre setores, regiões e períodos de tempo.
Ele demonstra habilidades práticas em análise de dados, programação em Python e uso de bibliotecas como Pandas, Matplotlib e Seaborn.

## **Sobre os dados**

Os dados foram obtidos através do Portal de Dados Abertos do governo do Brasil e estão separados mensalmente abrangendo o período dos últimos dois anos.
Os dados nesse estudo são públicos e podem ser acessados nesse [link](https://dados.gov.br/dados/conjuntos-dados/comunicacoes-de-acidente-de-trabalho-cat-plano-de-dados-abertos-jun-2023-a-jun-2025).

## **Limpeza e tratamento dos dados**

Começamos importando as bibliotecas necessárias que serão usadas ao longo do projeto e depois organizando o caminho dos datasets baixados e abrindo o arquivo.

```python
import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import missingno as msno
from datetime import datetime
from itertools import product

file_paths = [
    f"Datasets/D.SDA.PDA.005.CAT.{year}{month:02}.csv"
    for year in (2023, 2024)
    for month in range(1, 13)]

file_paths = [
    f"Datasets/D.SDA.PDA.005.CAT.{year}{month:02}.csv"
    for year, month in product((2023, 2024), range(1, 13))]

dfs = [pd.read_csv(file, sep=";", encoding="latin1", low_memory=False) for file in file_paths]
```

Agora fazemos a concatenação dos *datasets* e verificamos suas principais informações:

```python
df_consolidado = pd.concat(dfs, ignore_index=True)
df_consolidado.shape #verifica o tamanho do dataset
df_consolidado.columns #mostra as colunas presentes e seus nomes
df_consolidado.info #informações sobre valores ausentes e vazios
```

Percebemos a presença de algumas colunas duplicadas, mal escritas e também desnecessárias para o nosso objetivo final. Além disso,
o *dataset* contém valores ausentes ou zerados. Vamos excluir essas colunas e limpar esses dados para facilitar a análise.

```python

cols_to_drop = [
    "Emitente CAT", "Espécie do benefício", "Filiação Segurado",
    "Data Acidente.1", "Data Despacho Benefício", "Data Acidente.2",
    "Data Emissão CAT", "CNPJ/CEI Empregador", "Tipo de Empregador",
    "Natureza da Lesão", "Origem de Cadastramento CAT", "Parte Corpo Atingida",
    "CID-10.1", "Data Afastamento", "CNAE2.0 Empregador", "Tipo do Acidente",
    "Data Afastamento", "UF Munic. Empregador"]

df_consolidado.drop(columns=cols_to_drop, inplace=True, errors="ignore")
df_clean = df_consolidado.dropna(thresh=10)  #Remoção das linhas com mais de 10 valores ausentes

#Preenche valores ausentes em colunas categóricas com 'Desconhecido'
cat_cols = df_clean.select_dtypes(include=['object']).columns
for col in cat_cols:
    df_clean[col] = df_clean[col].fillna("Desconhecido") 

#Remove valores inválidos como "{ñ class}", "000000-Ignorado", "Zerado"
valores_invalidos = ["{ñ class}", "000000-Ignorado", "Zerado"]
for col in cat_cols:
    df_clean[col] = df_clean[col].astype(str).str.strip().str.lower()  

valores_invalidos = [v.lower() for v in valores_invalidos]

for col in cat_cols:
    df_clean = df_clean[~df_clean[col].isin(valores_invalidos)]

#Converte 'Data Acidente' para formato de data e preencher datas ausentes com a data mais comum
df_clean["Data Acidente"] = pd.to_datetime(df_clean["Data Acidente"], errors='coerce')
df_clean["Data Acidente"] = df_clean["Data Acidente"].fillna(df_clean["Data Acidente"].mode()[0])
df_clean["Data Nascimento"] = pd.to_datetime(df_clean["Data Nascimento"], errors='coerce')
```
Por fim, vamos apenas corrigir os nomes das colunas para remover espaços extras, abreviações confusas, e caracteres inválidos.

```python
df_clean.rename(columns={
    "Unnamed: 0": "ID",
    "Agente  Causador": "Agente_Causador",
    "Acidente": "Tipo_Acidente",
    "Data Acidente": "Data_Acidente",
    "CBO": "CBO",
    "CID-10": "CID10",
    "CNAE2.0 Empregador.1": "CNAE_Empregador",
    "Indica Ãbito Acidente": "Indica_Obito",
    "Munic Empr": "Municipio_Empregador",
    "Sexo": "Sexo",
    "UF": "UF",
    "Munic.  Acidente": "Municipio_Acidente",
    "Data Nascimento": "Data_Nascimento",
    "CBO.1": "CBO_Detalhado",
    "Data  Afastamento": "Data_Afastamento"
}, inplace=True)

def normalize_columns(cols):
    """Normaliza nomes das colunas para facilitar acesso."""
    clean = []
    for c in cols:
        s = str(c).strip().lower()
        s = re.sub(r"[^\w]+", "_", s)  # substitui espaços/pontos/virgulas por underscore
        s = re.sub(r"_+", "_", s).strip("_")
        clean.append(s)
    return clean

def find_col(df, keywords):
    """
    Acha primeira coluna do df que contenha qualquer substring em keywords.
    keywords pode ser lista de strings.
    Retorna None se não encontrado.
    """
    cols = df.columns
    for kw in keywords:
        for c in cols:
            if kw in c:
                return c
    return None

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)
df.columns = normalize_columns(df.columns)
```
Vamos converter as demais datas presentes no dataset, além de criar uma nova coluna chamada "idade_anos".

```python
# Datas
def to_datetime_safe(s):
    try:
        return pd.to_datetime(s, dayfirst=False, errors="coerce")
    except:
        return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")

if col_data_acidente:
    df["data_acidente_parsed"] = to_datetime_safe(df[col_data_acidente])
else:
    df["data_acidente_parsed"] = pd.NaT

if col_data_nasc:
    df["data_nascimento_parsed"] = to_datetime_safe(df[col_data_nasc])
else:
    df["data_nascimento_parsed"] = pd.NaT

# Idade aproximada em anos (quando data de nascimento válida)
ref_date = pd.Timestamp.now()
df["idade_anos"] = np.floor((ref_date - df["data_nascimento_parsed"]).dt.days / 365.25)
df.loc[df["idade_anos"] < 0, "idade_anos"] = np.nan

# Normaliza indicador óbito para string lower
if col_indica_obito:
    df["obito_flag"] = df[col_indica_obito].astype(str).str.lower().str.contains("sim|s|1|true", na=False)
else:
    df["obito_flag"] = False

# Substitui strings 'desconhecido' ou 'nan' por NaN
df = df.replace({"desconhecido": np.nan, "nan": np.nan, "none": np.nan})
```

Agora vamos elencar as estastícas descritivas gerais como total de registros (após limpeza); como também quantidade de municípios presentes, CBO (Cód. Brasileiro de Ocupação) e CNAE (Classificação Nacional de Atividades Econômicas) que estão presentes.

```python
# Números gerais
total_acidentes = len(df)
n_mun = df[col_municipio].nunique() if col_municipio else None
n_cbos = df[col_cbo].nunique() if col_cbo else None
n_cnaes = df[col_cnae].nunique() if col_cnae else None
n_obitos = df["obito_flag"].sum()

print(f"\nTotal de registros: {total_acidentes}")
print(f"Registros com óbito flag = True: {n_obitos}")
print(f"Nº municípios distintos (col detectada): {n_mun}")
print(f"Nº CBO distintos (col detectada): {n_cbos}")
print(f"Nº CNAE distintos (col detectada): {n_cnaes}")

desc_num = df[["idade_anos"]].describe()
print("\nDescrição numérica (idade):\n", desc_num)
```

**Saída:**

    Total de registros: 620545
    Registros com óbito flag = True: 2362
    Nº municípios distintos (col detectada): 3052
    Nº CBO distintos (col detectada): 4525
    Nº CNAE distintos (col detectada): 949
    
    Descrição numérica (idade):
               idade_anos
    count  619430.000000
    mean       37.651961
    std        11.652246
    min         7.000000
    25%        28.000000
    50%        36.000000
    75%        46.000000
    max       125.000000

Agora criamos duas funções para facilitar a criação dos gráficos e visualização dos dados.

```python
def topn_counts(df, col, n=10):
    if col is None:
        return pd.Series([], dtype=int)
    s = df[col].fillna("<<NA>>").value_counts().head(n)
    return s

def plot_topn(series, title, xlabel=None, filename=None, rotate=45):
    if series.empty:
        print(f"Aviso: serie vazia para {title}")
        return
    plt.figure(figsize=(10,6))
    sns.barplot(x=series.values, y=series.index, orient="h")
    plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    plt.tight_layout()
    if filename:
        plt.savefig(filename, bbox_inches="tight")
        print("Salvo:", filename)
    plt.show()
    plt.close()

ensure_dir("figs/top10")

top_agentes = topn_counts(df, col_agente, 10)
plot_topn(top_agentes, "Top 10 - Agentes Causadores de Acidentes", "Número de acidentes", "figs/top10/top10_agentes.png")

top_municipios = topn_counts(df, col_municipio, 10)
plot_topn(top_municipios, "Top 10 - Municípios com Mais Acidentes", "Número de acidentes", "figs/top10/top10_municipios.png")

# Agentes em acidentes fatais
top_agentes_fatais = topn_counts(df[df["obito_flag"]==True], col_agente, 10)
plot_topn(top_agentes_fatais, "Top 10 - Agentes em Acidentes Fatais", "Número de acidentes fatais", "figs/top10/top10_agentes_fatais.png")

top_cbos = topn_counts(df, col_cbo, 10)
plot_topn(top_cbos, "Top 10 - CBO com Mais Acidentes", "Número de acidentes", "figs/top10/top10_cbos.png")

top_cnaes = topn_counts(df, col_cnae, 10)
plot_topn(top_cnaes, "Top 10 - CNAE com Mais Acidentes", "Número de acidentes", "figs/top10/top10_cnaes.png")
```
**Saída:**

![Top Causadores de Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_agentes.png)

![Municípios com mais Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_municipios.png)

![Agentes Acidentes Fatais](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_agentes_fatais.png)

![CBO com mais Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_cbos.png)

![CNAE com mais Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_cnaes.png)

Agora vamos analisar os acidentes comparativamente por mês.

```python
if "data_acidente_parsed" in df.columns and not df["data_acidente_parsed"].isna().all():
    ts = df.set_index("data_acidente_parsed").resample("M").size()
    plt.figure(figsize=(12,5))
    ts.plot()
    plt.title("Série temporal: acidentes por mês")
    plt.ylabel("Número de acidentes")
    plt.xlabel("Mês")
    plt.tight_layout()
    plt.savefig("figs/acidentes_por_mes.png", bbox_inches="tight")
    plt.show()
    plt.close()

    # comparação ano a ano (se houver múltiplos anos)
    df["ano"] = df["data_acidente_parsed"].dt.year
    if df["ano"].nunique() > 1:
        pivot = df.groupby([df["data_acidente_parsed"].dt.to_period("M"), "ano"]).size().unstack(fill_value=0)
        pivot.index = pivot.index.to_timestamp()
        pivot.plot(figsize=(12,5))
        plt.title("Comparação mensal por ano")
        plt.ylabel("Nº acidentes")
        plt.xlabel("Mês")
        plt.tight_layout()
        plt.savefig("figs/comparacao_mensal_por_ano.png", bbox_inches="tight")
        plt.show()
        plt.close()
```
**Saída:**
![Acidentes por Mês](https://github.com/Benfluc/Projects/blob/main/project3/imgs/acidentes_por_mes.png)

Plotando a distribuição por idade e por sexo
```python
#Distribuição de idade e sexo

ensure_dir("figs/demografia")
if col_sexo:
    plt.figure(figsize=(6,4))
    sns.countplot(data=df, x=col_sexo, order=df[col_sexo].value_counts().index)
    plt.title("Distribuição por sexo")
    plt.xlabel("Sexo")
    plt.tight_layout()
    plt.savefig("figs/demografia/sexo_dist.png", bbox_inches="tight")
    plt.show()
    plt.close()

if "idade_anos" in df.columns:
    plt.figure(figsize=(8,4))
    sns.histplot(df["idade_anos"].dropna(), kde=False, bins=25)
    plt.title("Distribuição de Idade (anos)")
    plt.xlabel("Idade (anos)")
    plt.tight_layout()
    plt.savefig("figs/demografia/idade_hist.png", bbox_inches="tight")
    plt.show()
    plt.close()

# Boxplot idade por óbito_flag
if "idade_anos" in df.columns:
    plt.figure(figsize=(8,4))
    sns.boxplot(x="obito_flag", y="idade_anos", data=df)
    plt.title("Idade vs óbito (boxplot)")
    plt.xlabel("Óbito")
    plt.ylabel("Idade (anos)")
    plt.tight_layout()
    plt.savefig("figs/demografia/idade_vs_obito_box.png", bbox_inches="tight")
    plt.show()
    plt.close()
```
