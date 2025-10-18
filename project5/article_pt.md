# Compreendendo o Comportamento de Vendas através da AED

## Introdução
Esse texto traz a explicação do código e de como foi feito e executado. Caso você queira, você pode checar logo a parte de resultados obtidos e sugestões aos gestores [aqui](results_pt.md).

O dataset usado nesse estudo foi adquirido no site Kaggle.com e pode ser visualizado na [pasta de códigos](https://github.com/Benfluc/Projects/tree/main/project5/codes).
Os dados correspondem a 9994 iformações de vendas de uma loja, com informações como a data da compra, data do envio, tipo de produto, categoria, lucro, etc.
O objetivo desse estudo foi realizar uma análise exploratória de dados (EDA) afim de identificar pontos de melhoria e oportunidades para os gestores da loja.

## Primeiros Passos
Começamos importando as bibliotecas que irão nos ajudar ao longo desse trabalho, abrindo o arquivo e ajustanto as colunas de data.

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

df = pd.read_csv("Superstore.csv", encoding="ISO-8859-1")
df.columns = df.columns.str.strip()

for col in ["Order Date", "Ship Date"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")

df["Order Year"] = df["Order Date"].dt.year
df["Order Month"] = df["Order Date"].dt.to_period("M").astype(str)
df["Order DayOfWeek"] = df["Order Date"].dt.day_name()
df["Ship Delay (days)"] = (df["Ship Date"] - df["Order Date"]).dt.days
df["Profit Margin"] = np.where(df["Sales"] != 0, df["Profit"] / df["Sales"], np.nan)
  
```
Tudo isso é fundamental para uma boa análise e para facilitar nosso posterior trabalho.

Então, realizamos uma varredura para checar a qualidade do dataset. Esse é outro ponto importante para garantirmos que não hajam valores faltantes, nulos ou duplicados.
```python
data_quality = pd.DataFrame({
    "non_null": df.notnull().sum(),
    "%_non_null": (df.notnull().sum()/len(df))*100,
    "dtype": df.dtypes.astype(str)
}).reset_index().rename(columns={"index":"column"})

print("Verificação de duplicatas:")
print("Duplicatas por Row ID:", df["Row ID"].duplicated().sum())
print("Duplicatas por Order ID + Product ID:", df.duplicated(subset=["Order ID", "Product ID"]).sum())
```
SAÍDA:

      Verificação de duplicatas:
      Duplicatas por Row ID: 0
      Duplicatas por Order ID + Product ID: 8


Agora criamos uma função chamada 'iqr_outlier_share' que calcula estatísticas baseadas no método do intervalo interquartil (IQR) para identificar outliers (valores atípicos) em uma série numérica. A função calcula o primeiro e o terceiro quartis (q1, q3), o IQR, e os limites inferior e superior para detectar valores fora do intervalo esperado. A função retorna um dicionário com essas informações e a porcentagem de outliers. 
Depois, o código aplica essa função às colunas "Sales" e "Profit" do DataFrame, armazenando os resultados em uma tabela.

```python
def iqr_outlier_share(series):
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower = q1 - 1.5*iqr
    upper = q3 + 1.5*iqr
    mask = (series < lower) | (series > upper)
    return {
        "q1": q1, "q3": q3, "iqr": iqr,
        "lower": lower, "upper": upper,
        "outliers_count": int(mask.sum()),
        "outliers_%": 100*mask.mean()
    }

outlier_sales = iqr_outlier_share(df["Sales"])
outlier_profit = iqr_outlier_share(df["Profit"])
outlier_table = pd.DataFrame([
    {"metric":"Sales", **outlier_sales},
    {"metric":"Profit", **outlier_profit},
])
```


Depois calculamos indicadores de desempenho (KPIs) do conjunto de dados, como número de pedidos, clientes e produtos únicos, soma total de vendas e lucros, valores médios por pedido, percentual de transações com lucro negativo e atraso médio de envio em dias. 
Esses indicadores são reunidos em um dicionário chamado kpis e depois convertidos em um DataFrame (kpis_df) para fácil visualização e análise.

```pyhton
kpis = {
    "Orders": df["Order ID"].nunique(),
    "Customers": df["Customer ID"].nunique(),
    "Products": df["Product ID"].nunique(),
    "Total Sales": df["Sales"].sum(),
    "Total Profit": df["Profit"].sum(),
    "Avg Order Value": df.groupby("Order ID")["Sales"].sum().mean(),
    "Avg Profit per Order": df.groupby("Order ID")["Profit"].sum().mean(),
    "Negative Profit Rows (%)": 100*(df["Profit"] < 0).mean(),
    "Avg Ship Delay (days)": df["Ship Delay (days)"].mean()
}
kpis_df = pd.DataFrame(list(kpis.items()), columns=["KPI","Value"])
```

Aqui temos uma parte extensa do código onde fazemos o grupamento de valores usando algumas variáveis como: vendas, lucro, envios de pedidos atrasados, etc. Além disso, criamos algumas tabelas e plotamos gráficos que ajudam na visualização.
```python
cat = df.groupby("Category").agg(Sales=("Sales","sum"),
                                 Profit=("Profit","sum"),
                                 Orders=("Order ID","nunique")).reset_index()

subcat = df.groupby(["Category","Sub-Category"]).agg(
    Sales=("Sales","sum"), Profit=("Profit","sum")
).reset_index().sort_values("Sales", ascending=False)

region = df.groupby("Region").agg(Sales=("Sales","sum"),
                                  Profit=("Profit","sum")).reset_index()

state_top = df.groupby("State").agg(Sales=("Sales","sum"),
                                    Profit=("Profit","sum")).reset_index().sort_values("Sales", ascending=False).head(15)

segment = df.groupby("Segment").agg(Sales=("Sales","sum"),
                                    Profit=("Profit","sum")).reset_index()

shipmode = df.groupby("Ship Mode").agg(Sales=("Sales","sum"),
                                       Profit=("Profit","sum"),
                                       Delay=("Ship Delay (days)","mean")).reset_index()

# Produtos mais e menos lucrativos
product_profit = df.groupby(["Product ID","Product Name"]).agg(Sales=("Sales","sum"), Profit=("Profit","sum")).reset_index()
top_profitable = product_profit.sort_values("Profit", ascending=False).head(15)
worst_profitable = product_profit.sort_values("Profit").head(15)

# Subcategorias com maior taxa de prejuízo
neg_profit_rate = df.assign(neg=(df["Profit"]<0)).groupby(["Category","Sub-Category"]).agg(
    Sales=("Sales","sum"),
    Profit=("Profit","sum"),
    NegRate=("neg","mean")
).reset_index().sort_values("NegRate", ascending=False)

# Série temporal mensal
monthly = df.set_index("Order Date").groupby(pd.Grouper(freq="M")).agg(
    Sales=("Sales","sum"), Profit=("Profit","sum")
).reset_index()

# Correlação
corr = df.select_dtypes(include=[np.number])[["Sales","Quantity","Discount","Profit","Ship Delay (days)","Profit Margin"]].corr()

def save_plot(fig, name):
    path = os.path.join("plots", name)
    os.makedirs("plots", exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

# Distribuições
fig = plt.figure(figsize=(8,5))
plt.hist(df["Sales"], bins=50)
plt.title("Sales Distribution")
plt.xlabel("Sales"); plt.ylabel("Frequência")
save_plot(fig, "sales_distribution.png")

fig = plt.figure(figsize=(8,5))
plt.hist(df["Profit"], bins=50)
plt.title("Profit Distribution")
plt.xlabel("Profit"); plt.ylabel("Frequência")
save_plot(fig, "profit_distribution.png")

# Vendas e Lucro por Categoria
fig = plt.figure(figsize=(8,5))
plt.bar(cat["Category"], cat["Sales"])
plt.title("Sales by Category"); plt.ylabel("Sales")
save_plot(fig, "sales_by_category.png")

fig = plt.figure(figsize=(8,5))
plt.bar(cat["Category"], cat["Profit"])
plt.title("Profit by Category"); plt.ylabel("Profit")
save_plot(fig, "profit_by_category.png")

# Série Temporal
fig = plt.figure(figsize=(10,5))
plt.plot(monthly["Order Date"], monthly["Sales"])
plt.title("Monthly Sales"); plt.ylabel("Sales")
save_plot(fig, "monthly_sales.png")

fig = plt.figure(figsize=(10,5))
plt.plot(monthly["Order Date"], monthly["Profit"])
plt.title("Monthly Profit"); plt.ylabel("Profit")
save_plot(fig, "monthly_profit.png")

# Correlação
fig = plt.figure(figsize=(6,5))
plt.imshow(corr, aspect='auto')
plt.xticks(range(corr.shape[1]), corr.columns, rotation=45, ha='right')
plt.yticks(range(corr.shape[0]), corr.index)
plt.title("Correlation Matrix")
for i in range(corr.shape[0]):
    for j in range(corr.shape[1]):
        plt.text(j, i, f"{corr.iloc[i,j]:.2f}", ha="center", va="center")
save_plot(fig, "correlation_matrix.png")
```
Todas as tabelas e gráficos gerados podem ser visualizados [aqui](https://github.com/Benfluc/Projects/tree/main/project5/imgs)

Com base em todas essas informações, foi possível extrair insights valiosos que revelam pontos de melhoria e oportunidades de crescimento para a empresa, como o aumento do lucro e a otimização da logística 
de transporte de pedidos, reduzindo prejuízos causados por atrasos. Você pode checar tudo isso aqui [resultados e recomendações](results_pt.md).

