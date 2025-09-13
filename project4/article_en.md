# Building an Intelligent Purchase Recommendation System Based on Other Customers' Choices

This project is based on a dataset of sales from an electronics store available on Kaggle.
The dataset is used purely for educational purposes and can be accessed [here](https://www.kaggle.com/datasets/vincentcornlius/sales-orders/data)


The dataset covers all transactions made between January 22 and December 21, 2019, providing a complete overview of customer purchasing behavior throughout the year.

## Introduction
### Dataset Features

- **Size:** 185,950 purchase records.
- **Integrity:** no empty rows, duplicates, or missing values.
- **Period covered:** from 01/22/2019 to 12/21/2019.
- **Distinct customers:** 140,787 (identified based on delivery addresses).
- **Total sales:** 185,949 valid transactions.
- **Grouping:** sales and customers (based on addresses) were organized in a dictionary to facilitate analysis and recommendations.

### Dataset Columns
- **Order Date** – Order date.
- **Order ID** – Unique order identifier.
- **Product** – Name of the sold product.
- **Product_ean** – Product EAN code.
- **catégorie** – Product category.
- **Purchase Address** – Delivery address.
- **Quantity Ordered** – Quantity of units purchased.
- **Price Each** – Sale unit price.
- **Cost price** – Cost price.
- **turnover** – Revenue from the sale.
- **margin** – Profit margin obtained.

### Project Objective

The main objective is to develop a product recommendation system in the style of “customers who bought this also bought”.
The idea is to analyze customers' purchasing habits and identify product co-occurrence patterns, allowing suggestions of items that are often bought together.

### Importance of a Recommendation System

- **Customer experience:** increases satisfaction by offering personalized and relevant suggestions.
- **Sales increase:** encourages additional purchases (cross-selling), raising the average ticket.
- **Strategic decision-making:** provides insights for inventory planning, promotions, and targeted marketing.

This project demonstrates how historical sales data, when properly processed and analyzed, can be transformed into a powerful tool to drive business results and create a competitive advantage.

## Data Analysis and Preprocessing
```python
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
import seaborn as sns
import matplotlib.pyplot as plt

df = pd.read_csv('sales_data.csv')

df['Purchase Address'] = df['Purchase Address'].str.strip()  # remove espaços
df['Purchase Address'] = df['Purchase Address'].str.upper()  # uniformiza maiúsculas

clientes_dict = {}
for cid, endereco in enumerate(df['Purchase Address'].unique(), start=1):
    produtos_cliente = df.loc[df['Purchase Address'] == endereco, 'Product'].unique().tolist()
    clientes_dict[cid] = produtos_cliente
    print(f'Cliente {cid} gerado')
```
In the first step of the code, the necessary libraries are imported, and delivery addresses are standardized by removing whitespace and converting all characters to uppercase.
This normalization prevents minor formatting differences — such as “A Street, 123” vs. “a street, 123 ” — from generating distinct IDs for the same customer.

It is important to note that grouping customers solely by delivery address can introduce limitations.
A single customer may have more than one address (residential and commercial), or different customers may share the same delivery location.
Still, this method realistically reflects the scenario of many companies without strict data management, reproducing common real-world challenges in sales analysis.

Next, the *for* loop iterates over the unique addresses in the dataset.
For each address, a numerical ID is generated and associated with the list of purchased products, using *unique()* to ensure no item is duplicated within the same list.
The final result is a dictionary *(clientes_dict)*, where each key represents a customer (or address) and each value corresponds to the set of purchased products.

## Creating the Matrix and Purchase Correlation

```python
mlb = MultiLabelBinarizer()
matriz = pd.DataFrame(
    mlb.fit_transform(list(clientes_dict.values())),
    index=clientes_dict.keys(),
    columns=mlb.classes_
)
print(matriz.head())

coocorrencia = matriz.T.dot(matriz)
relacao = coocorrencia / coocorrencia.to_numpy().max()
top_produtos = matriz.sum().sort_values(ascending=False).head(20).index
```

We move on to the customer purchase data process to transform qualitative information into a form that can be analyzed mathematically.
First, the code uses MultiLabelBinarizer to convert the clientes_dict dictionary, which links each customer to the products they bought, into a binary matrix.
In this matrix, each row represents a customer, and each column represents a product, with values of 1 indicating that the customer purchased the product and 0 otherwise.

Then, the code calculates a product co-occurrence matrix by multiplying the transposed matrix by the original matrix *(matriz.T.dot(matriz))*, so that each cell indicates how many customers bought that product pair together.
This matrix is then normalized by dividing each value by the maximum value found, creating the relacao matrix, which shows the relative strength of co-occurrence between products.
Finally, the code identifies the 20 most purchased products by summing the values of each column in the binary matrix and selecting the highest sums, providing a quick view of the most popular items among customers.

## Visualization and Recommendation System

```python
plt.figure(figsize=(12,10))
sns.heatmap(
    coocorrencia.loc[top_produtos, top_produtos],
    annot=True, fmt="d", cmap="YlOrRd"
)

plt.xticks(rotation=90)
plt.yticks(rotation=0)
plt.title("Clientes que compraram os dois produtos juntos")
plt.tight_layout()
plt.show()
```
With the co-occurrence matrix built, we visualize it through a plot:

**Output:**
![Correlation Graph of Sales](https://github.com/Benfluc/Projects/blob/main/project4/imgs/grafico_correla%C3%A7%C3%A3o_compras.png)

Finally, we identify the target product, in this example, the '20in Monitor'. The code traverses the corresponding row (excluding the product itself) and returns the three largest values found there.
The advantage of this system is that it is easily adjustable, serving as an effective tool for purchase recommendations based on the purchase history of other customers.

```pyhton
produto = "20in Monitor"
linha = coocorrencia.loc[produto].drop(produto)
top3 = linha.nlargest(3)

print(produto)
print(top3)
```

**Output:**

    20in Monitor
    Lightning Charging Cable    235
    USB-C Charging Cable        232
    AAA Batteries (4-pack)      196
    Name: 20in Monitor, dtype: int64

## Conclusion

The project demonstrated how historical sales data can be transformed into a practical and intelligent product recommendation tool.
Through preprocessing and the creation of a binary matrix of customers versus products, it was possible to identify co-occurrence patterns, highlighting which products are often bought together.
The analysis allowed not only to identify the most popular items but also to generate personalized recommendations automatically based on collective customer behavior.

In addition to illustrating the usefulness of simple data analysis techniques, the project shows how recommendation systems can add real value to a business, improving customer experience and boosting sales through strategic suggestions.
The approach used, although educational, reflects challenges and solutions applicable to real commercial scenarios, serving as a foundation for more advanced implementations, such as real-time recommendations or integration with e-commerce platforms.

