# Metodologia e Resultados

Para acessar o código e datasets usadados nesse projeto clique [aqui](https://github.com/Benfluc/Projects/tree/main/project9/codes)

## 1. O Problema e o Objetivo
Neste projeto, desenvolveu-se um sistema de pontuação de crédito (Credit Scoring) utilizando o dataset 'Give Me Some Credit'. O objetivo central foi prever a probabilidade de um cliente enfrentar 
dificuldades financeiras nos próximos dois anos. É um problema clássico de classificação binária, mas com um desafio crítico: os dados são altamente desbalanceados, com pouquíssimos exemplos de inadimplência real.

## 2. A Escolha da Arquitetura: Neuro-Fuzzy (ANFIS)
Em vez de seguir o caminho comum com Random Forest ou XGBoost, implementamos uma rede Neuro-Fuzzy (baseada em ANFIS) usando PyTorch. Essa abordagem foi escolhida por dois motivos principais: 
- Interpretabilidade (XAI): Diferente de uma 'caixa-preta', o modelo Fuzzy utiliza funções de pertinência (Gaussianas) que mapeiam variáveis contínuas em conceitos lógicos. Isso é fundamental no setor bancário para conformidade e explicação de decisões.
- Aprendizado Adaptativo: A rede neural ajusta automaticamente os parâmetros das regras lógicas, unindo o rigor da lógica fuzzy com o poder de otimização do Gradient Descent.

## 3. Engenharia de Dados e Variáveis
Pré-processamento focado em robustez: 
- Tratamento de Nulos: Imputação baseada na mediana para renda mensal, evitando que outliers distorçam o modelo.
- Feature Engineering: Consolidei o histórico de atrasos (30, 60 e 90 dias) em uma única métrica de TotalLate, simplificando a dimensionalidade e aumentando o sinal preditivo.
- Escalonamento Min-Max: Essencial para que as funções de pertinência fuzzy operem corretamente no intervalo $[0, 1]$.

## 4. Estratégia de Treinamento e Solução do Desbalanceamento
Um ponto alto do projeto foi lidar com o viés dos dados. Notei inicialmente que o modelo tendia a prever a média para todos. Corrigi isso com: 
- Cost-Sensitive Learning: Utilizei a função de perda BCEWithLogitsLoss com um pos_weight de 15.0. Isso deu mais peso aos erros cometidos na classe minoritária (inadimplentes), forçando o modelo a aprender os padrões de risco.
- Inicialização Inteligente: Inicializei os centros das funções fuzzy (mu) de forma distribuída linearmente, o que acelerou a convergência e evitou que o modelo ficasse preso em mínimos locais.

## 5. Resultados
Para cada proponente de crédito, o modelo estimou uma probabilidade de inadimplência em um intervalo contínuo de 0 a 1, onde o valor máximo representa o grau mais elevado de risco de descumprimento das obrigações financeiras.

O diferencial da arquitetura Neuro-Fuzzy reside na sua natureza interpretável. Ao contrário de modelos "caixa-preta" como LSTM (Long Short-Term Memory) ou XGBoost, a lógica fuzzy permite auditar os critérios de classificação por meio da análise das funções de pertinência e regras de inferência. Para quantificar a influência dos atributos no veredito da rede, aplicou-se o coeficiente de correlação de Spearman, que identificou os principais drivers de risco do modelo:

![](https://github.com/Benfluc/Projects/blob/main/project9/imgs/mapa_corr.png)

 - Idade: Apresentou uma correlação inversa significativa, indicando que a maturidade demográfica está associada a perfis de menor risco.

 - Rendimentos Mensais: Demonstrou que a capacidade de geração de renda atua como um fator mitigador da probabilidade de default.

 - Tempo Total de Atraso: Identificado como o principal indicador comportamental, onde o histórico de impontualidade eleva diretamente o score de risco.

Os resultados gerados pela rede Neuro-Fuzzy convergem com o cenário macroeconômico brasileiro. 
A tendência de maior vulnerabilidade financeira em faixas etárias mais jovens, capturada pelo modelo, é corroborada pelo [Mapa de Inadimplência do Brasil - Março/2026](https://www.serasa.com.br/limpa-nome-online/blog/mapa-da-inadimplencia-e-renogociacao-de-dividas-no-brasil/) 

Abaixo, detalhamos o risco médio segregado por categorias, demonstrando a consistência estatística do modelo:

### Risco Médio por Faixa Etária:        
----------------------------------------
|Age_Group                 | Risk     |
|--------------------------|----------|
|Jovem (até 30 anos)       | 0.650497 |
|Adulto (31 a 45 anos)     | 0.608300 |
|Meia-Idade (46 a 60 anos) | 0.480834 |
|Sênior (+ 60 anos)        | 0.349829 |

Além do fator demográfico, a rede demonstrou uma sensibilidade refinada ao comportamento financeiro ativo, como observado na relação entre a Utilização de Linhas de Crédito Desprotegidas e a Probabilidade Fuzzy.

![](https://github.com/Benfluc/Projects/blob/main/project9/imgs/graph_credit_risk.png)

O gráfico de dispersão revela que o modelo não aplica uma penalização binária, mas sim uma gradação de risco. É perceptível uma densidade acentuada de perfis com risco elevado à medida que a utilização atinge o limiar de 1.0 (100% do limite utilizado). Esse comportamento evidencia a capacidade do sistema Neuro-Fuzzy de mapear zonas de incerteza: enquanto usuários com baixa utilização apresentam uma dispersão maior de risco (influenciada por outras variáveis como atrasos históricos), o esgotamento das linhas de crédito atua como um gatilho de alerta imediato para a rede, elevando a base da probabilidade de inadimplência.

Em suma, a modelagem proposta não apenas identifica quem são os inadimplentes, mas oferece uma explicação visual e matemática de como o comportamento de consumo impacta a saúde financeira do proponente, tornando o processo de decisão de crédito mais transparente e auditável.






