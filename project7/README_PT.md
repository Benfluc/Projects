## 1. Contexto do Projeto

Este projeto simula uma operação de atendimento multicanal de médio a grande porte, responsável por atividades de suporte, cobrança e vendas, operando com alto volume de interações diárias e metas claras de desempenho operacional e comercial.

A operação atua por diferentes canais de contato (voz, chat, WhatsApp e e-mail) e é composta por operadores, supervisores e gestores que dependem de informações confiáveis para tomada de decisão em tempo hábil.

## 2. Objetivo da Solução de BI

O objetivo deste projeto é desenvolver uma plataforma de Business Intelligence capaz de integrar dados operacionais de múltiplas fontes, garantir qualidade e rastreabilidade das informações e disponibilizar indicadores estratégicos e operacionais para apoio à gestão.

A solução busca:

 - Monitorar o cumprimento de SLA operacional
 - Avaliar produtividade individual e por equipe
 - Acompanhar resultados de campanhas e conversão
 - Identificar gargalos de fila e abandono
 - Apoiar decisões táticas e estratégicas da liderança

## 3. Stakeholders e Necessidades de Informação

| Stakeholder           | Necessidade |
|-----------------------|-------------|
| Diretoria             | Visão consolidada, tendências e resultados   |
| Gerência Operacional  | SLA, produtividade, eficiência por canal     |
| Supervisores          | Ranking de operadores, acompanhamento diário |
| Time de BI/Dados      | Consistência, rastreabilidade e governança |


## 4. Perguntas de Negócio

As principais perguntas que a solução de BI deve responder são:

- O SLA está sendo cumprido por canal e por período?
- Quais operadores apresentam maior produtividade?
- Quais campanhas geram maior taxa de conversão?
- Em quais horários ocorre maior taxa de abandono?
- Onde estão os principais gargalos da operação?

## 5. Indicadores Definidos

| Pergunta de Negócio   | Indicador            |  Conceito                                          |
|-----------------------|----------------------|----------------------------------------------------|
| Cumprimento de SLA    | % SLA                | Atendimento dentro do prazo/total                  |
| Produtividade         | Atendimento por hora | Total de atendimentos / horas trabalhadas          |
| Conversão             | Taxa de conversão    | Fechamentos / contatos realizados                  |
| Abandono              | Taxa de abandono     | Atendimentos abandonados / tentativas              |
| Eficiência            | TMA                  | Tempo médio de atendimento                         |

## 6. Regras de Negócio

- SLA: atendimento iniciado dentro do tempo máximo definido por canal
- Atendimento abandonado: cliente encerra contato antes de atendimento efetivo
- Conversão: atendimento finalizado com valor financeiro positivo
- Produtividade: considera apenas atendimentos finalizados
- TMA: calculado com base no tempo total de atendimento

Estas regras são aplicadas de forma consistente nos processos de ETL, consultas SQL e dashboards.

## 7. Granularidade e Atualização dos Dados

- Granularidade mínima: 1 registro por atendimento
- Datas registradas em formato timestamp
- Atualização dos dados: processo diário automatizado
- Indicadores analisados por hora, dia e mês

## 8. Resultado Esperado

Ao final do projeto, a solução permitirá visibilidade completa da operação, com dados confiáveis, indicadores claros e 
dashboards orientados à tomada de decisão, simulando um ambiente corporativo real de BI e Analytics.
