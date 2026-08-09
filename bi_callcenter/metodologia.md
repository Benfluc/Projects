# Metodologia

## Objetivo

O projeto foi desenvolvido para analisar o desempenho operacional de uma equipe de atendimento, integrando métricas tradicionais com técnicas de inteligência artificial para gerar insights estratégicos e apoiar decisões gerenciais. 
Para isso, adotou-se uma abordagem baseada em dados sintéticos, construídos em Python, cuidadosamente modelados para refletir características reais de um call center, como variação de conversões entre campanhas e operadores, 
número elevado de ligações não atendidas e distribuição heterogênea de atendimentos.


## Geração e Tratamento de Dados

Os dados foram gerados sinteticamente utilizando scripts em Python, garantindo que padrões típicos de operação fossem preservados, como diferenças de desempenho entre operadores e entre campanhas, tempos médios de atendimento variados 
e valores recuperados realistas. Após a geração, os dados passaram por limpeza, padronização e validação, assegurando consistência, ausência de duplicidades e plausibilidade estatística dos indicadores.
Tomou-se cuidado para que os dados refletissem o mais próximo possível as peculiaridades de um atendimento de call center.

## Construção de Indicadores e Score de Desempenho

Para facilitar a avaliação comparativa e reduzir vieses decorrentes da análise isolada de métricas, foi desenvolvido um score de desempenho. 
O score consolidou diversas variáveis ponderadas de acordo com sua relevância para resultados comerciais: taxa de conversão, taxa de abandono, tempo médio de atendimento, número de atendimentos, contratos fechados e valores recuperados. 
Técnicas de inteligência artificial foram aplicadas para calibrar os pesos das métricas, garantindo que o score refletisse de forma equilibrada a performance global de cada operador.

O cálculo do score é realizado da seguinte forma:

$$
\text{Score Operador} = 0.40 \times [\text{Conversão Norm}] + 0.30 \times [\text{Abandono Norm}] + 0.20 \times [\text{Tempo Norm}] + 0.10 \times \frac{[\text{Atendimentos}]}{[\text{Max Atendimentos Operador}]}
$$

Os componentes do score são descritos a seguir:

Conversão Norm (40%): Representa a taxa de conversão do operador, normalizada entre 0 e 1. Esta métrica indica a efetividade do operador em fechar contratos ou gerar resultados comerciais a partir dos atendimentos realizados. Foi atribuída a maior ponderação no score devido à sua relevância direta para o sucesso da operação.

Abandono Norm (30%): Refere-se à taxa de abandono, normalizada de forma que valores mais baixos indiquem melhor desempenho. Esse indicador mede a capacidade do operador em manter os atendimentos até a conclusão, refletindo a qualidade e o engajamento no atendimento.

Tempo Norm (20%): Corresponde ao tempo médio de atendimento do operador, normalizado para que valores adequados ao perfil de atendimento do call center sejam considerados positivos. Esse componente captura a eficiência e a capacidade do operador em conduzir atendimentos de maneira equilibrada, garantindo qualidade e conversão.

Atendimentos (10%): Representa a quantidade de atendimentos realizados pelo operador, normalizada em relação ao máximo registrado na operação. Esse fator incorpora a produtividade individual, considerando que operadores que realizam mais atendimentos têm maior exposição a oportunidades de conversão.

A combinação ponderada desses quatro elementos permite uma avaliação multidimensional do desempenho, equilibrando produtividade, qualidade do atendimento e resultados comerciais. Dessa forma, o Score Operador fornece à gestão um indicador único, objetivo e comparável, capaz de identificar tanto os melhores quanto os piores desempenhos de forma consistente, evitando interpretações enviesadas derivadas da análise isolada de métricas individuais.

## Visualização e Insights

Os resultados foram apresentados em dashboards interativos no Power BI, com rankings dos melhores e piores operadores, métricas consolidadas e comparações entre campanhas e períodos do mês. A interface permitiu análises detalhadas individuais e coletivas, além de gerar insights estratégicos, como a correlação entre tempo médio de atendimento e taxa de conversão, e a importância do volume de atendimentos para o desempenho comercial.

## Validação e Aplicação

Embora os dados fossem sintéticos, foram projetados para refletir de forma fiel o comportamento de um call center real, permitindo validação conceitual da metodologia. O modelo consolidado passou a ser utilizado como ferramenta de apoio à gestão, oferecendo uma visão global da operação e subsidiando decisões sobre alocação de recursos, estratégias de campanha e treinamentos de operadores.
