# Retail Banking Analytics in SQL

[English](README.md) · **Português**

Projeto de análise de dados de ponta a ponta, escrito quase inteiramente em **PostgreSQL**: parte dos extratos CSV
brutos de um banco de varejo, passa por um star schema testado e chega a quatro conjuntos de análises que respondem a
perguntas reais de negócio sobre **clientes, risco de crédito e prevenção à lavagem de dinheiro**.

O banco ("Liffey Bank") e todos os dados são fictícios. Um script Python com semente fixa gera 20.000 clientes,
1,4 milhão de transações e 5.900 empréstimos, e esconde neles, de propósito, os comportamentos que o SQL precisa
encontrar e os problemas de qualidade que precisa corrigir.

O código, os comentários e a documentação técnica estão em inglês.

## O que o projeto responde

| Módulo | Pergunta de negócio | SQL avançado utilizado |
|---|---|---|
| [01 Schema](sql/01_schema) | Como modelar os dados do banco? | Star schema, constraints, particionamento mensal criado com SQL dinâmico |
| [02 Staging](sql/02_staging) | Como extratos sujos viram tabelas confiáveis? | Deduplicação com `ROW_NUMBER`, conversão de tipos, tabela de rejeitados com o motivo, materialized view |
| [03 Qualidade de dados](sql/03_data_quality) | Os números são confiáveis? | 13 testes automatizados, reconciliação da carga linha a linha, interrupção do pipeline em caso de falha |
| [04 Clientes](sql/04_customer_analytics) | Quem tem valor, quem está saindo e o que ofertar? | Coortes, RFM com `NTILE`, gaps and islands, função SQL parametrizada com backtest, cesta de produtos com self-join |
| [05 Carteira de crédito](sql/05_credit_portfolio) | Quais empréstimos estão se deteriorando, e em que ritmo? | Fotografias mensais com `LATERAL`, curvas de safra, matriz de rolagem com `LEAD`, `ROLLUP`, médias móveis |
| [06 Prevenção à lavagem](sql/06_aml_detection) | Quais transações têm perfil de lavagem de dinheiro? | Sessionização, janelas temporais com `RANGE`, CTE recursiva sobre o grafo de transferências, precisão e recall |
| [07 Performance](sql/07_performance) | As decisões de modelagem compensam? | `EXPLAIN ANALYZE` antes e depois: índice composto, partition pruning, materialized view |

## Principais achados

A análise completa, com todas as tabelas, está em [docs/findings.md](docs/findings.md) (em inglês).

1. **Uma regra simples de atividade antecipa a saída de clientes.** Clientes cuja atividade caiu 60% ou mais tiveram
   probabilidade **4,9 vezes maior** de encerrar o relacionamento nos seis meses seguintes (14,7% contra 2,1% dos
   demais). A regra sinaliza 7% dos clientes e captura 34% das saídas.
2. **Metade do volume vem de um quinto dos clientes.** Os "Champions" do RFM são 20% dos clientes e 49% do volume
   movimentado. Outros 1.803 clientes de alto valor estão se afastando e respondem por 13% do volume.
3. **Dois pares de cross-sell se destacam.** Quem tem financiamento imobiliário tem seguro residencial em 61% dos
   casos (lift de 4,8), e previdência e fundo de investimento aparecem juntos 5,6 vezes mais que o acaso. Isso gera
   uma recomendação específica de produto para 3.244 clientes.
4. **A safra de 2023 é a mais fraca.** 11,7% dos empréstimos concedidos em 2023 atingiram mais de 90 dias de atraso em
   até 24 meses, contra 7,3% em 2021 e 8,6% em 2022. Com 61 a 90 dias de atraso, 57% dos contratos passam para a faixa
   acima de 90 dias no mês seguinte.
5. **As regras de prevenção à lavagem trocam cobertura por carga de trabalho.** As três regras encontram de 84% a 85%
   dos casos confirmados, com precisão de 90% a 100%. Reduzir o piso da regra de fracionamento de EUR 8.000 para
   EUR 7.000 eleva o recall para 95% ao custo de quatro alarmes falsos a mais; reduzir para EUR 6.000 multiplica os
   alarmes falsos por dezesseis.
6. **O desenho físico faz diferença.** Em 1,4 milhão de linhas, o índice composto reduz a consulta do histórico de uma
   conta de cerca de 30 ms para 0,1 ms, o partition pruning lê 747 páginas em vez de 16.932, e a materialized view de
   atividade mensal é mais de 20 vezes mais rápida que agregar a tabela fato.

## Como executar

Requisitos: Docker e Python 3.10 ou superior.

```bash
# 1. Gerar os dados (cerca de 10 segundos, 90 MB de CSV em data/raw)
pip install -r requirements.txt
python data_generation/generate_data.py

# 2. Subir o PostgreSQL 16
docker compose up -d

# 3. Construir tudo e imprimir os resultados (cerca de 1 minuto)
docker compose exec db psql -U bank -d retail_bank -f sql/run_all.sql

# 4. Opcional: os experimentos de performance
docker compose exec db psql -U bank -d retail_bank -f sql/07_performance/01_query_tuning.sql
```

Sem Docker, crie um banco em qualquer servidor PostgreSQL 14 ou superior e execute, a partir da raiz do projeto:

```bash
psql -d retail_bank -f sql/run_all.sql
```

O `sql/run_all.sql` pode ser executado quantas vezes for preciso: ele apaga e reconstrói todos os schemas. Use
`--scale 0.25` no passo 1 para uma base menor e mais rápida. Para explorar os resultados no Power BI ou no Tableau,
conecte em `localhost:5434` (banco `retail_bank`, usuário e senha `bank`) e carregue as views do schema `analytics`.

A saída esperada do passo 3 está em [docs/sample_output.txt](docs/sample_output.txt).

## Painel no Tableau

Você pode acessar a visualização no Tableau pelo [link](https://public.tableau.com/views/RetailBankingAnalyticsinSQL/AMLdetection)

O Tableau Public lê arquivos, e não bancos de dados. Por isso, o
[sql/09_export_for_tableau.sql](sql/09_export_for_tableau.sql) exporta os resultados em 14 arquivos CSV para
[tableau/data](tableau/data). Os arquivos estão no repositório, de modo que o painel pode ser refeito sem executar o
banco. Para gerá-los novamente:

```bash
docker compose exec db psql -U bank -d retail_bank -f sql/09_export_for_tableau.sql
```

## Limitações

- **Os dados são sintéticos.** Os padrões foram plantados pelo gerador; os achados mostram que o SQL os recupera
  corretamente, e não dizem nada sobre um banco real. Dados reais têm mais ruído, e a precisão das regras de prevenção
  à lavagem seria bem menor na prática.
- **Os "casos confirmados" de lavagem são rótulos simulados**, produzidos pelo gerador, e não por investigadores.
  Cerca de 15% dos casos plantados foram dificultados de propósito, para que as regras não acertem 100%.
- **Regras, não modelos.** A detecção de saída de clientes e de lavagem usa limiares transparentes. É uma linha de
  base contra a qual um modelo estatístico normalmente seria comparado.
- **Os tempos vêm de uma única máquina** (PostgreSQL 16, 2 núcleos) e variam em outros ambientes. O que importa é a
  mudança no plano de execução, não os milissegundos.
- **Testado em PostgreSQL 16.** O SQL usa recursos próprios do PostgreSQL (particionamento declarativo, `FILTER`,
  janelas `RANGE` com intervalos, `LATERAL`) e precisaria de ajustes em outros bancos.

## Autor

Lúcio Júnio Benfica Rosa · [Portfólio](https://benfluc.github.io/) · [GitHub](https://github.com/Benfluc)
