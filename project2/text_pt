# **Minimização de Custo Logístico**

## Sobre o Problema:
Uma empresa necessita distribuir seus produtos a diferentes destinos, utilizando centros de distribuição com capacidade limitada. 
Cada centro possui custo unitário de envio e cada destino tem uma demanda específica. 
O objetivo é minimizar o custo total de transporte respeitando a oferta disponível em cada centro e a demanda de cada destino.

Os custos, bem como a relação entre oferta e demanda é dada na tabela abaixo:


Origem/Destino  |  D1  |  D2  |   D3  |
----------------|------|------|-------|
CD1             |  4   |   6  |   8   |
CD2             |  2   |   4  |   5   |
CD3             |  3   |   1  |   7   |

*Custos unitários de transporte (R$/unidade)*

## Resolução:
O problema pode ser formulado através da atribuição de uma variável *(X_ij)* para cada Centro de Distribuição (CD) e Destino (D) tendo assim uma relação direta existente entre *i* e *j*. Transformando esses fluxos então em valores de *Xij*, temos: 

F.O.[min]: *4x11+ 6x12 + 8x13 + 2x21 + 4x22 + 5x23 + 3x31 + x32 + 7x33*

S. A.: 

        restrições de oferta:    
            x11 + x12 + x13 = 80
            x21 + x22 + x23 = 100
            x31 + x32 + x33 = 120
       
       restrições de demanda: 
            x11 + x21 + x31 = 90
            x12 + x22 + x32 = 70
            x13 + x23 + x33 = 140


### Método do Canto Noroeste 

O Método do Canto Noroeste (**Northwest Corner Method**) é uma técnica simples utilizada para encontrar uma solução inicial em problemas de transporte, que envolvem distribuir 
produtos de várias origens para diferentes destinos de forma a minimizar custos ou atender demandas. O nome “Canto Noroeste” vem do ponto de partida do método: sempre se inicia pela célula 
superior esquerda (canto noroeste) da tabela de transporte. A partir daí, aloca-se o máximo possível para essa célula, ajusta-se a oferta e a demanda correspondentes, e move-se para a célula seguinte à direita ou abaixo, 
repetindo o processo até que todas as demandas sejam atendidas. Este método é viável principalmente para problemas de transporte balanceados, onde a soma das ofertas é igual à soma das demandas. 
Ele é útil para gerar rapidamente uma solução inicial, que depois pode ser otimizada usando métodos como MODI (Modified Distribution Method) ou Stepping Stone para encontrar a solução de custo mínimo. 
Apesar de não garantir a solução ótima, é eficiente para obter uma base factível inicial, especialmente em problemas grandes, em que iniciar do zero seria mais trabalhoso.

Dada a função objetivo vista anteriormente, podemos transformá-la em uma matriz A.

**Código**:

### Criação da função para cálculo:

```python
# Importação da biblioteca Numpy
def northwest_corner(costs, supply, demand):
    # Gera solução inicial pelo método do canto noroeste.
    supply = supply.copy()
    demand = demand.copy()
    allocation = np.zeros_like(costs, dtype=int)
    
    i, j = 0, 0
    while i < 3 and j < 3:
        qty = min(supply[i], demand[j])
        allocation[i][j] = qty
        supply[i] -= qty
        demand[j] -= qty
        if supply[i] == 0 and demand[j] == 0:
            i += 1
            j += 1
        elif supply[i] == 0:
            i += 1
        else:
            j += 1
    return allocation
```
O que o código faz aqui é percorrer a matriz *allocation* a partir da posição 11 (linha 1, coluna 1) e preencher com o mínimo entre oferta e demanda.
Após isso a demanda ou oferta remanescente são atualizadas e passa-se para a próxima relação CD x D, até que todas as ofertas e demandas estejam satisfeitas.
Ao final, temos uma solução que atende as restrições, apesar de não ser a solução ótima.

### Em busca da solução ótima:
```python
def calculate_potentials(allocation, costs):
    # Calcula potenciais u,v e custos reduzidos delta.
    u = [None]*3
    v = [None]*3
    u[0] = 0
    basic = [(i,j) for i in range(3) for j in range(3) if allocation[i][j] > 0]
    
    changed = True
    while changed:
        changed = False
        for i,j in basic:
            if u[i] is not None and v[j] is None:
                v[j] = costs[i][j] - u[i]
                changed = True
            elif v[j] is not None and u[i] is None:
                u[i] = costs[i][j] - v[j]
                changed = True
                
    delta = np.zeros_like(costs, dtype=int)
    for i in range(3):
        for j in range(3):
            if (i,j) not in basic:
                delta[i][j] = costs[i][j] - (u[i] + v[j])
    return u, v, delta
```
Aqui começamos a busca pela solução ótima. Como trata-se de um problema balanceado (a oferta e demanda tem o mesmo valor '300') o número de básicas é dado por: *(m + n - 1)*. 
Substituindo temos: (3 + 3 - 1) = 5

Para cada Delta(*Xij*),  *Cij* - (*ui* + *vj*), sendo 
 - *Cij* = Custo unitário da célula *ij*;
 - *ui* = Potencial associado a linha *CDi*
 - *vj* = Potencial associado a coluna (Destino *j*)

As variáveis básicas achadas no método anterior foram: (1,1), (2,1), (2,2), (2,3), (3,3) e assumimos *u1* = 0

```python
def find_loop(allocation, start):
    # Encontra loop fechado em 3x3 para célula inicial start (i,j).
    i0,j0 = start
    basic = [(i,j) for i in range(3) for j in range(3) if allocation[i][j] > 0]
    basic.append((i0,j0))
    
    # Para 3x3, tentamos percorrer linhas e colunas alternadas
    # Geramos todas combinações possíveis simples (como L)
    for i1,j1 in basic:
        if i1 != i0 and j1 != j0 and (i1,j0) in basic and (i0,j1) in basic:
            return [(i0,j0),(i0,j1),(i1,j1),(i1,j0)]
    return None

def modi_3x3(costs, supply, demand):
    allocation = northwest_corner(costs, supply, demand)
    
    while True:
        u, v, delta = calculate_potentials(allocation, costs)
        if np.all(delta >= 0):
            break  # ótimo
        # seleciona célula com delta mínimo
        i,j = np.unravel_index(np.argmin(delta), delta.shape)
        loop = find_loop(allocation, (i,j))
        if loop is None:
            raise Exception("Não foi possível encontrar loop para melhoria")
        
        plus = loop[0::2]
        minus = loop[1::2]
        theta = min([allocation[x,y] for x,y in minus])
        
        for x,y in plus:
            allocation[x][y] += theta
        for x,y in minus:
            allocation[x][y] -= theta

    total_cost = np.sum(allocation * costs)
    u, v, delta = calculate_potentials(allocation, costs)
    return allocation, total_cost, u, v, delta
```
Na última parte do código criamos uma função que encontra o loop alternando os sinais de substituição da célula básica.
A princípio, após calcularmos os custos reduzidos das não básicas procuramos por todos os Custos(*Cij*) = 0 para obtermos a solução ótima. 
Valores < 0 representam bons ganhos na minimização do custo e dessa forma são inseridos até que a solução ótima seja encontrada, ou seja todos os custos sejam iguais a zero.

### Aplicando ao nosso exemplo real:
```python
# Matriz de custo
osts = np.array([
    [4, 6, 8],
    [2, 4, 5],
    [3, 1, 7]
])
supply = [80, 100, 120]
demand = [90, 70, 140]

alloc, cost, u, v, delta = modi_3x3(costs, supply, demand)

print("Matriz Ótima:\n", alloc)
print("Custo Total Ótimo:", cost)
print("Potenciais u:", u)
print("Potenciais v:", v)
print("Custos Reduzidos (Delta):\n", delta)
```
Por fim, simplesmente informamos a matriz, construida através da relação dos custos unitários entre os centros de distribuição e destinos e as restrições de oferta e demanda.
Com isso podemos chamar as funções criadas e ter a solução ótima do problema, bem como a matriz ótima e outras informações.

Saída:
 
      Matriz Ótima:[80, 0, 0], [0, 0, 100], [10, 70, 40]
      Custo Total Ótimo: 1200
      Potenciais u: [0, np.int64(-3), np.int64(-1)]
      Potenciais v: [np.int64(4), np.int64(2), np.int64(8)]
      Custos Reduzidos (Delta):[0 4 0], [1 5 0], [0 0 0]]

### Considerações finais:
Este código funciona para matrizes 3x3 e assume que sempre existe um loop simples em L para ajuste.
Para matrizes maiores ou loops complexos, seria necessário implementar um algoritmo de detecção de loop completo. Porém ainda assim essas funções são um bom ponto de partida para solução do problema e otimização de transportes.
Caso tenha interesse também o link abaixo traz uma versão completa com todo o cálculo explicado e discussão sobre viabilidade da implementação dessa solução.
