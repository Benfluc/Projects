# Análise Exploratória de Acidentes de Trabalho no Brasil (2023–2024): Padrões, Tendências e Fatores de Risco

Este estudo realiza uma análise exploratória de dados (EDA) sobre acidentes de trabalho no Brasil nos anos de 2023 e 2024, utilizando dados oficiais do governo. 
Foram aplicadas técnicas estatísticas e de visualização para identificar os principais agentes causadores, ocupações mais afetadas, municípios de maior ocorrência e perfil demográfico das vítimas.

SUMÁRIO:
- Introdução
- Limpeza e tratamento dos dados
- Estatísticas descritivas gerais
- Principais recorrências
- Perfil demográfico dos trabalhadores
- Conclusões gerais e insights


## **1. INTRODUÇÃO**

Os acidentes de trabalho constituem um problema relevante no Brasil, afetando a saúde dos trabalhadores e gerando impactos econômicos e sociais significativos. A análise de dados oficiais sobre esses eventos permite identificar padrões, setores mais vulneráveis e fatores de risco, fornecendo subsídios importantes para a prevenção.
Os dados foram obtidos através do Portal de Dados Abertos do governo do Brasil e estão separados mensalmente abrangendo o período dos últimos dois anos.
Os dados nesse estudo são públicos e podem ser acessados nesse [link](https://dados.gov.br/dados/conjuntos-dados/comunicacoes-de-acidente-de-trabalho-cat-plano-de-dados-abertos-jun-2023-a-jun-2025).

## **2. LIMPEZA E TRATAMENTO DOS DADOS**

Inicialmente, os arquivos mensais foram consolidados em um único dataset, permitindo uma visão integrada do período de 2023 a 2024. Em seguida, foram removidas colunas duplicadas ou irrelevantes para os objetivos do estudo, reduzindo a redundância e o ruído informacional.

Foram identificados valores ausentes e inconsistentes, que foram tratados de forma diferenciada: nas variáveis categóricas, substituiu-se por rótulos como “Desconhecido”, enquanto nas variáveis numéricas ou de data aplicou-se imputação com valores mais frequentes (mode) ou conversão para valores nulos apropriados. Também foram eliminados registros com códigos inválidos, como “000000-Ignorado” ou “Zerado”.

Adicionalmente, realizou-se a padronização dos nomes das colunas, substituindo espaços, caracteres especiais e abreviações confusas por identificadores uniformes. As variáveis de data, como Data de Acidente e Data de Nascimento, foram convertidas para o formato temporal adequado, permitindo a criação de novos atributos, como a idade em anos no momento do acidente. Por fim, normalizou-se o indicador de óbito, garantindo sua consistência como variável booleana.

Esse processo de limpeza resultou em uma base de dados mais organizada, padronizada e livre de inconsistências, fornecendo condições adequadas para a realização das análises exploratórias subsequentes.
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

```python
df_consolidado = pd.concat(dfs, ignore_index=True)
df_consolidado.shape #verifica o tamanho do dataset
df_consolidado.columns #mostra as colunas presentes e seus nomes
df_consolidado.info #informações sobre valores ausentes e vazios
```

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

## **3. ESTATÍSTICAS DESCRITIVAS GERAIS**
Após a etapa de limpeza, foi possível calcular indicadores gerais do conjunto de dados. O período analisado contou com mais de **620 mil registros de acidentes de trabalho**, distribuídos em mais de **3 mil municípios.** 
Foram identificados mais de **4,5 mil ocupações distintas (CBO)** e cerca de **950 atividades econômicas (CNAE)**. Aproximadamente **2,3 mil registros indicaram ocorrência de óbito**.

A análise demográfica mostra idade média dos trabalhadores em torno de 38 anos, com distribuição variando de 7 a 125 anos, predominando faixas entre 28 e 46 anos. Esses números fornecem uma visão inicial do perfil dos acidentes e da população mais afetada, servindo de base para análises mais detalhadas.

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

## **4. PRINCIPAIS RECORRÊNCIAS**
A análise das ocorrências permitiu identificar os elementos mais frequentes associados aos acidentes de trabalho. Entre eles destacam-se os agentes causadores, que evidenciam os principais fatores de risco no ambiente laboral; os municípios com maior número de registros, que concentram maior volume de notificações; além das ocupações (CBO) e setores econômicos (CNAE) mais afetados.

Também foi analisada a relação entre os agentes presentes em acidentes fatais, oferecendo uma visão diferenciada sobre os eventos de maior gravidade. Esses resultados permitem compreender onde os riscos são mais recorrentes e auxiliam na definição de medidas preventivas direcionadas.

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

Em seguida analisamos os acidentes comparativamente por mês.

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

## 5. PERFIL DEMOGRÁFICO

A análise demográfica dos registros mostra a distribuição dos acidentes segundo sexo e idade dos trabalhadores. 
Observa-se diferença na frequência entre homens e mulheres, refletindo a maior participação masculina em atividades de maior risco.
Em relação à idade, a média dos trabalhadores acidentados é de aproximadamente 38 anos, com maior concentração entre 28 e 46 anos. 
Também foi avaliada a relação entre idade e gravidade dos eventos, considerando os casos com registro de óbito.

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
**Saída:**
![Acidentes por Sexo](https://github.com/Benfluc/Projects/blob/main/project3/imgs/Acidentes%20por%20Sexo.png)
![Acidentes por Idade](https://github.com/Benfluc/Projects/blob/main/project3/imgs/Acidentes%20por%20idade.png)
![Idade vs. Óbito](https://github.com/Benfluc/Projects/blob/main/project3/imgs/Idade%20vs%20%C3%93bito.png)

## **6. CONCLUSÕES GERAIS E INSIGHTS**

Entre janeiro de 2023 e dezembro de 2024, totalizando 24 meses, foram registrados 620.545 acidentes de trabalho, dos quais 2.362 (0,38%) resultaram em óbitos.

Ao analisar a distribuição por sexo, observa-se uma predominância de acidentes envolvendo homens, com 413.785 ocorrências (66,68%), enquanto as mulheres registraram 204.315 casos (32,93%). 
Essa diferença indica que os homens tiveram aproximadamente 102,5% mais acidentes do que as mulheres. Outros 2.430 casos (0,39%) não informaram o sexo e 15 (0,002%) foram classificados como indeterminados. A disparidade também se reflete nos acidentes fatais: 2.133 óbitos (90,30%) ocorreram entre homens, contra 222 (9,40%) entre mulheres, com 7 casos sem informação.

Quanto às causas dos acidentes, destacam-se:

- Acidentes de trânsito com motocicletas: 35.515 casos (5,72%)
- Acidentes de trânsito com outros veículos: 25.624 casos (4,13%)
- Impactos contra objetos: 24.251 casos (3,91%)
- Quedas em ruas e estradas: 24.236 casos (3,91%)
- Quedas em chão/superfície útil: 22.538 casos (3,63%)

Nos acidentes fatais, veículos rodoviários lideram com 479 mortes (20,28%), seguidos por veículos não identificados ou classificados (254 óbitos, 10,75%), motocicletas e motonetas (225 óbitos, 9,53%), impactos contra objetos (185 óbitos, 7,83%) e quedas em ruas e estradas (137 óbitos, 5,80%).

Analisando os setores econômicos:

- Comércio varejista: 50.710 acidentes (8,17%)
- Atividades de atendimento: 43.150 acidentes (6,95%)
- Comércio atacadista: 21.138 acidentes (3,41%)
- Transporte rodoviário: 20.773 acidentes (3,35%)
- Fabricação de produtos: 17.878 acidentes (2,88%)

No caso de acidentes fatais, o transporte rodoviário lidera com 360 óbitos (15,24%), seguido por comércio varejista (154 óbitos, 6,52%), comércio atacadista (104 óbitos, 4,40%), fabricação de produtos (65 óbitos, 2,75%) e construção de edifícios (57 óbitos, 2,41%).

Em termos geográficos, São Paulo registra o maior número de acidentes (79.700 casos, 12,84%) e óbitos (192 mortes, 8,13%), seguido pelo Rio de Janeiro (24.546 acidentes, 3,96%; 78 óbitos, 3,30%), Curitiba (15.894 acidentes, 2,56%; 55 óbitos, 2,33%), Belo Horizonte (13.959 acidentes, 2,25%; 51 óbitos, 2,16%) e Brasília (13.505 acidentes, 2,18%; 38 óbitos, 1,61%).

Quanto às ocupações, a categoria “desconhecido” concentra o maior número de acidentes (114.712 casos, 18,48%). Excluindo esta categoria, as ocupações mais afetadas foram:


- Alimentadores de linha de produção: 75.963 acidentes (12,24%)
- Técnicos de enfermagem: 62.866 acidentes (10,13%)
- Motoristas de caminhão: 28.311 acidentes (4,56%)
- Serventes de obras: 23.260 acidentes (3,75%)
- Vendedores do comércio varejista: 18.212 acidentes (2,93%)

Nos acidentes fatais, os motoristas de caminhão lideram com 802 óbitos (33,94%), seguidos por “desconhecido” (348 óbitos, 14,73%), alimentadores de linha de produção (159 óbitos, 6,73%), serventes de obras (118 óbitos, 5,00%), vigilantes (90 óbitos, 3,81%) e motociclistas (87 óbitos, 3,68%).

Em resumo, os dados mostram uma prevalência significativa de acidentes entre homens, especialmente em setores ligados ao transporte rodoviário e comércio. Veículos, sobretudo motocicletas e veículos rodoviários, são os principais agentes causadores de acidentes, incluindo os fatais. Municípios economicamente importantes, como São Paulo e Rio de Janeiro, concentram os maiores números de ocorrências. A alta proporção de acidentes sem identificação clara da ocupação reforça a necessidade de aprimorar a qualidade dos dados para apoiar políticas públicas de prevenção e segurança no trabalho.



