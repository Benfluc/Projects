# Exploratory Analysis of Workplace Accidents in Brazil (2023–2024): Patterns, Trends, and Risk Factors

This study conducts an exploratory data analysis (EDA) on workplace accidents in Brazil for the years 2023 and 2024, using official government data.  
Statistical and visualization techniques were applied to identify the main causative agents, most affected occupations, municipalities with the highest occurrence, and the demographic profile of the victims.

**SUMMARY:**
- Introduction
- Data Cleaning and Preprocessing
- General Descriptive Statistics
- Key Occurrences
- Worker Demographic Profile
- General Conclusions and Insights

## **1. INTRODUCTION**

Workplace accidents are a significant problem in Brazil, affecting workers' health and generating substantial economic and social impacts.  
Analyzing official data on these events allows us to identify patterns, the most vulnerable sectors, and risk factors, providing important insights for prevention.  
The data were obtained from the Brazilian Government Open Data Portal and are organized monthly, covering the last two years.  
The data used in this study are public and can be accessed at this [link](https://dados.gov.br/dados/conjuntos-dados/comunicacoes-de-acidente-de-trabalho-cat-plano-de-dados-abertos-jun-2023-a-jun-2025).

## **2. DATA CLEANING AND PREPROCESSING**

Initially, the monthly files were consolidated into a single dataset, providing an integrated view of the period from 2023 to 2024.  
Next, duplicate or irrelevant columns for the study's objectives were removed, reducing redundancy and informational noise.

Missing and inconsistent values were identified and treated differently: in categorical variables, they were replaced with labels such as "Unknown," while in numerical or date variables, imputation with the most frequent values (mode) or conversion to appropriate null values was applied. Records with invalid codes, such as “000000-Ignored” or “Zeroed,” were also eliminated.

Additionally, column names were standardized, replacing spaces, special characters, and confusing abbreviations with uniform identifiers. Date variables, such as Accident Date and Birth Date, were converted to the proper temporal format, allowing the creation of new attributes, such as age in years at the time of the accident. Finally, the fatality indicator was normalized, ensuring its consistency as a boolean variable.

This cleaning process resulted in a more organized, standardized, and consistent dataset, providing suitable conditions for subsequent exploratory analyses.

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
    for year, month in product((2023, 2024), range(1, 13))]

dfs = [pd.read_csv(file, sep=";", encoding="latin1", low_memory=False) for file in file_paths]

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

## **3. GENERAL DESCRIPTIVE STATISTICS**

After the cleaning stage, it was possible to calculate general indicators for the dataset. The analyzed period included over **620 thousand workplace accident records**, distributed across more than **3 thousand municipalities.**  
More than **4,500 distinct occupations (CBO)** and approximately **950 economic activities (CNAE)** were identified. Around **2,300 records indicated a fatality.**

The demographic analysis shows an average worker age of approximately 38 years, with a range from 7 to 125 years, predominantly between 28 and 46 years. These figures provide an initial view of the accident profile and the most affected population, serving as a basis for more detailed analyses.

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

**Output:**

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

    ## **4. KEY OCCURRENCES**

The occurrence analysis allowed us to identify the most frequent elements associated with workplace accidents. Among them, the causative agents stand out, highlighting the main risk factors in the work environment; the municipalities with the highest number of records, which concentrate the largest volume of notifications; as well as the most affected occupations (CBO) and economic sectors (CNAE).

The relationship between the agents involved in fatal accidents was also analyzed, providing a differentiated view of the most severe events. These results help to understand where risks are most recurrent and assist in defining targeted preventive measures.

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
**Output:**

![Top Causadores de Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_agentes.png)

![Municípios com mais Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_municipios.png)

![Agentes Acidentes Fatais](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_agentes_fatais.png)

![CBO com mais Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_cbos.png)

![CNAE com mais Acidentes](https://github.com/Benfluc/Projects/blob/main/project3/imgs/top10_cnaes.png)

Next, we analyzed the accidents comparatively on a monthly basis.

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
**Output:**
![Acidentes por Mês](https://github.com/Benfluc/Projects/blob/main/project3/imgs/acidentes_por_mes.png)

## 5. DEMOGRAPHIC PROFILE

The demographic analysis of the records shows the distribution of accidents according to workers' sex and age.  
A difference in frequency between men and women is observed, reflecting the higher male participation in higher-risk activities.  
Regarding age, the average age of injured workers is approximately 38 years, with the highest concentration between 28 and 46 years.  
The relationship between age and event severity was also evaluated, considering cases with recorded fatalities.

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
**Output:**
![Acidentes por Sexo](https://github.com/Benfluc/Projects/blob/main/project3/imgs/Acidentes%20por%20Sexo.png)
![Acidentes por Idade](https://github.com/Benfluc/Projects/blob/main/project3/imgs/Acidentes%20por%20idade.png)
![Idade vs. Óbito](https://github.com/Benfluc/Projects/blob/main/project3/imgs/Idade%20vs%20%C3%93bito.png)

## **6. GENERAL CONCLUSIONS AND INSIGHTS**

Between January 2023 and December 2024, totaling 24 months, **620,545 workplace accidents** were recorded, of which **2,362 (0.38%) resulted in fatalities**.

Analyzing the distribution by sex, a predominance of accidents involving men is observed, with **413,785 occurrences (66.68%)**, while women accounted for **204,315 cases (32.93%)**.  
This difference indicates that men experienced approximately **102.5% more accidents than women**. Another **2,430 cases (0.39%)** did not report sex, and **15 cases (0.002%)** were classified as indeterminate. This disparity is also reflected in fatal accidents: **2,133 deaths (90.30%)** occurred among men, compared to **222 (9.40%)** among women, with 7 cases missing information.

Regarding the causes of accidents, the main contributors are:

- Motorcycle traffic accidents: 35,515 cases (5.72%)
- Traffic accidents with other vehicles: 25,624 cases (4.13%)
- Impacts against objects: 24,251 cases (3.91%)
- Falls on streets and roads: 24,236 cases (3.91%)
- Falls on floor/surface: 22,538 cases (3.63%)

For fatal accidents, road vehicles lead with **479 deaths (20.28%)**, followed by unidentified or unclassified vehicles (**254 deaths, 10.75%**), motorcycles and scooters (**225 deaths, 9.53%**), impacts against objects (**185 deaths, 7.83%**), and falls on streets and roads (**137 deaths, 5.80%**).

Analyzing economic sectors:

- Retail trade: 50,710 accidents (8.17%)
- Service activities: 43,150 accidents (6.95%)
- Wholesale trade: 21,138 accidents (3.41%)
- Road transport: 20,773 accidents (3.35%)
- Manufacturing: 17,878 accidents (2.88%)

For fatal accidents, **road transport** leads with **360 deaths (15.24%)**, followed by retail trade (**154 deaths, 6.52%**), wholesale trade (**104 deaths, 4.40%**), manufacturing (**65 deaths, 2.75%**), and building construction (**57 deaths, 2.41%**).

In terms of geography, **São Paulo** records the highest number of accidents (**79,700 cases, 12.84%**) and fatalities (**192 deaths, 8.13%**), followed by **Rio de Janeiro** (24,546 accidents, 3.96%; 78 deaths, 3.30%), **Curitiba** (15,894 accidents, 2.56%; 55 deaths, 2.33%), **Belo Horizonte** (13,959 accidents, 2.25%; 51 deaths, 2.16%), and **Brasília** (13,505 accidents, 2.18%; 38 deaths, 1.61%).

Regarding occupations, the "unknown" category accounts for the highest number of accidents (**114,712 cases, 18.48%**). Excluding this category, the most affected occupations were:

- Production line feeders: 75,963 accidents (12.24%)
- Nursing technicians: 62,866 accidents (10.13%)
- Truck drivers: 28,311 accidents (4.56%)
- Construction laborers: 23,260 accidents (3.75%)
- Retail salespersons: 18,212 accidents (2.93%)

In fatal accidents, **truck drivers** lead with **802 deaths (33.94%)**, followed by "unknown" (**348 deaths, 14.73%**), production line feeders (**159 deaths, 6.73%**), construction laborers (**118 deaths, 5.00%**), security guards (**90 deaths, 3.81%**), and motorcyclists (**87 deaths, 3.68%**).

In summary, the data show a significant prevalence of accidents among men, especially in sectors related to road transport and trade. Vehicles, particularly motorcycles and road vehicles, are the main causative agents of accidents, including fatal ones. Economically important municipalities, such as São Paulo and Rio de Janeiro, concentrate the highest numbers of occurrences.  
The high proportion of accidents with unidentified occupations highlights the need to improve data quality to support public policies for workplace safety and prevention.




