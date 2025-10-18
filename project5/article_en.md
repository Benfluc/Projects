# Understanding Sales Behavior through EDA

## Introduction

This text provides an explanation of the code, how it was built, and how it was executed. If you prefer, you can go straight to the section with the obtained results and management suggestions [here](results.md).

The dataset used in this study was obtained from Kaggle.com and can be viewed in the [code folder](https://github.com/Benfluc/Projects/tree/main/project5/codes).
The data contains 9,994 sales records from a store, including details such as purchase date, shipping date, product type, category, profit, and more.
The main goal of this study was to perform an Exploratory Data Analysis (EDA) to identify areas for improvement and potential opportunities for store managers.

## First Steps
We started by importing the libraries that would assist us throughout this project, loading the dataset, and adjusting the date columns.

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
All of this is essential for a solid analysis and to make our later work easier.

Next, we performed a thorough check to assess the dataset’s quality — another crucial step to ensure there are no missing, null, or duplicate values.

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
OUTPUT:

      Verificação de duplicatas:
      Duplicatas por Row ID: 0
      Duplicatas por Order ID + Product ID: 8


Next, we created a function called iqr_outlier_share, which calculates statistics based on the Interquartile Range (IQR) method to identify outliers in a numerical series.
The function computes the first and third quartiles (q1 and q3), the IQR itself, and the lower and upper bounds used to detect values outside the expected range.
It then returns a dictionary containing these metrics along with the percentage of outliers.
After that, the code applies this function to the “Sales” and “Profit” columns of the DataFrame, storing the results in a summary table.

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

Then, we calculated key performance indicators (KPIs) from the dataset, such as the number of orders, unique customers, and products, as well as the total sales and profits.
We also included metrics like the average values per order, the percentage of transactions with negative profit, and the average shipping delay in days.
All these indicators were gathered into a dictionary called kpis and later converted into a DataFrame (kpis_df) for easier visualization and analysis.

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

Here we have an extended part of the code where we group values using variables such as sales, profit, and delayed shipments.
In addition, we created several tables and plotted charts to make the data easier to visualize and interpret.

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
All generated tables and charts can be viewed [here](https://github.com/Benfluc/Projects/tree/main/project5/imgs)

Based on all this information, it was possible to extract valuable insights that highlight areas for improvement and growth opportunities for the company, such as increasing profitability and optimizing the logistics of order transportation, thereby reducing losses caused by delays.
You can check all of this in detail here: [results and recommendations](results.md)

