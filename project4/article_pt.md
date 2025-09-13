# Construção de um Sistema Inteligente de Recomendação de Compras Baseado nas Escolhas de Outros Clientes

Este projeto tem como base um **dataset de vendas de uma loja de eletrônicos** disponível no Kaggle.
O uso do dataset tem cárater meramente educativo e você pode acessá-lo clicando [aqui](https://www.kaggle.com/datasets/vincentcornlius/sales-orders/data)

O conjunto de dados abrange **todas as transações realizadas entre 22 de janeiro e 21 de dezembro de 2019**, oferecendo um panorama completo do comportamento de compra dos clientes ao longo do ano.

## Introdução
### Características do Dataset

- **Tamanho**: 185.950 registros de compras.  
- **Integridade**: não há linhas vazias, duplicadas ou valores faltantes.  
- **Período coberto**: de 22/01/2019 a 21/12/2019.  
- **Clientes distintos**: 140.787 (identificados a partir dos endereços de entrega).  
- **Total de vendas**: 185.949 transações válidas.  
- **Agrupamento**: vendas e clientes (baseados nos endereços) foram organizados em um dicionário para facilitar análises e recomendações.

#### Colunas do Dataset
- **Order Date** – Data do pedido.  
- **Order ID** – Identificador único do pedido.  
- **Product** – Nome do produto vendido.  
- **Product_ean** – Código EAN do produto.  
- **catégorie** – Categoria do produto.  
- **Purchase Address** – Endereço de entrega.  
- **Quantity Ordered** – Quantidade de unidades adquiridas.  
- **Price Each** – Preço unitário de venda.  
- **Cost price** – Preço de custo.  
- **turnover** – Faturamento da venda.  
- **margin** – Margem de lucro obtida.

### Objetivo do Projeto

O principal objetivo é **desenvolver um sistema de recomendação de produtos** no estilo *“quem comprou isso também comprou”*.  
A ideia é analisar os hábitos de compra dos clientes e identificar padrões de coocorrência de produtos, permitindo sugerir itens que costumam ser adquiridos em conjunto.

### Importância de um Sistema de Recomendação

- **Experiência do cliente**: aumenta a satisfação ao oferecer sugestões personalizadas e relevantes.  
- **Aumento de vendas**: incentiva compras adicionais (*cross-selling*), elevando o ticket médio.  
- **Tomada de decisão estratégica**: fornece insights para planejamento de estoque, promoções e marketing direcionado.  

Este projeto demonstra como **dados históricos de vendas**, quando bem tratados e analisados, podem ser transformados em uma poderosa ferramenta para impulsionar resultados de negócio e criar vantagem competitiva.

## Análise e Pré-processamento de Dados

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


Na primeira etapa do código, são importadas as bibliotecas necessárias e executada uma padronização dos endereços de entrega, removendo espaços em branco e convertendo todos os caracteres para maiúsculas.
Essa normalização evita que pequenas divergências de formatação — como “Rua A, 123” vs. “rua a, 123 ” — gerem identificações distintas para o mesmo cliente.

É importante destacar que agrupar clientes apenas pelo endereço de entrega pode introduzir limitações.
Um mesmo cliente, por exemplo, pode possuir mais de um endereço (residencial e comercial), ou diferentes clientes podem compartilhar um mesmo local de entrega.
Ainda assim, esse método reflete de forma realista o cenário de muitas empresas que não possuem uma gestão de dados rigorosa, reproduzindo desafios comuns na vida real de análise de vendas.

Em seguida, o laço *for* percorre os endereços únicos do dataset.
Para cada endereço, é gerado um ID numérico e associado a ele a lista de produtos adquiridos, utilizando *unique()* para garantir que não haja duplicação de itens dentro da mesma lista.
O resultado final é um dicionário (clientes_dict), onde cada chave representa um cliente (ou endereço) e cada valor corresponde ao conjunto de produtos comprados.

## Criação da Matriz e Correlação de Compras

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

Partimos para o processo dos dados de compras de clientes para transformar informações qualitativas em uma forma quantitativa que pode ser analisada matematicamente. 
Primeiro, o código usa o *MultiLabelBinarizer* para converter o dicionário clientes_dict, que relaciona cada cliente aos produtos que comprou, em uma matriz binária. 
Nessa matriz, cada linha representa um cliente e cada coluna representa um produto, com valores 1 indicando que o cliente comprou aquele produto e 0 caso contrário.

Depois, o código calcula uma matriz de coocorrência de produtos, multiplicando a matriz transposta pela matriz original *(matriz.T.dot(matriz))*, de modo que cada célula 
indique quantos clientes compraram aquele par de produtos juntos. Essa matriz é então normalizada dividindo cada valor pelo valor máximo encontrado, gerando a matriz relacao, 
que indica a força relativa da coocorrência entre produtos. Por fim, o código identifica os 20 produtos mais comprados somando os valores de cada coluna na matriz binária e selecionando 
aqueles com maior soma, fornecendo uma visão rápida dos itens mais populares entre os clientes.

## Gráfico e Sistema de Recomendação

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
Com a matriz de coocorrência construida, visualizamos através de um gráfico:

**Saída:**
![Gráfico de Correlação de Compras](https://github.com/Benfluc/Projects/blob/main/project4/imgs/grafico_correla%C3%A7%C3%A3o_compras.png)


produto = "20in Monitor"

```pyhton
linha = coocorrencia.loc[produto].drop(produto)
top3 = linha.nlargest(3)

print(produto)
print(top3)
```

Por fim, identificamos o produto que queremos, nesse exemplo o '20in Monitor'. O código percorre a linha correspondente (excluindo o próprio produto) e retorna os três maiores valores encontrados ali.
A vantagem desse sistema é que ele é facilmente ajustável, sendo uma ótima ferramenta de recomendação de compras baseada em histórico de compras de outros clientes.

**Saída:**

    20in Monitor
    Lightning Charging Cable    235
    USB-C Charging Cable        232
    AAA Batteries (4-pack)      196
    Name: 20in Monitor, dtype: int64

## Conclusão

O projeto demonstrou como dados de vendas históricas podem ser transformados em uma ferramenta prática e inteligente para recomendação de produtos. 
A partir do pré-processamento e da criação de uma matriz binária de clientes versus produtos, foi possível identificar padrões de coocorrência, evidenciando quais produtos costumam ser adquiridos em conjunto. 
A análise permitiu não apenas destacar os itens mais populares, mas também gerar recomendações personalizadas de forma automática, com base no comportamento coletivo dos clientes.

Além de ilustrar a utilidade de técnicas simples de análise de dados, o projeto mostra como sistemas de recomendação podem agregar valor real ao negócio, melhorando a experiência do cliente 
e potencializando vendas por meio de sugestões estratégicas. A abordagem utilizada, embora educativa, reflete desafios e soluções aplicáveis a cenários 
comerciais reais, servindo como base para implementações mais avançadas, como recomendações em tempo real ou integração com plataformas de e-commerce.


