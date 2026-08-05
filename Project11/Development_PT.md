# Desenvolvimento da Plataforma de Análise da Fórmula 1

![Kimi Antonelli Standings](https://raw.githubusercontent.com/Benfluc/Projects/refs/heads/main/Project11/imgs/kimi_relat.png)

## Overview

A F1 Analytics Platform foi desenvolvida como uma solução completa de **Business Intelligence** para análise de dados da Fórmula 1, combinando Data Engineering, modelagem de banco de dados, integração com APIs, processamento de imagens e visualização interativa com Power BI.

O principal objetivo foi construir um ambiente analítico capaz de explorar dados históricos e atuais da Fórmula 1, incluindo pilotos, equipes, circuitos, corridas, resultados de classificação, standings e indicadores de desempenho.

A arquitetura do projeto foi desenvolvida seguindo um moderno **analytics pipeline**:

```text
Python
    │
    ├── ETL Processes
    ├── Jolpica API Integration
    ├── Wikipedia Image Extraction
    ├── Image Processing
    │
    ▼
PostgreSQL
    │
    ├── raw layer
    ├── mart layer
    ├── analytical views
    │
    ▼
Power BI
    │
    ├── Star Schema
    ├── DAX Measures
    ├── KPIs
    ├── Dashboards
    │
    ▼
Business Intelligence
```

## Aquisição de Dados e Pipeline

### Dataset Inicial: Kaggle

O projeto começou utilizando um dataset de Fórmula 1 disponível no [Kaggle](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020). Esse conjunto de dados continha informações históricas sobre corridas, pilotos, construtores, circuitos, sessões de classificação e campeonatos. Entretanto, o dataset possuía uma limitação: estava atualizado apenas até a temporada de 2024. Isso ocorreu porque sua fonte original, a Ergast Formula 1 API, foi descontinuada ao final de 2024. Como o dataset do Kaggle dependia da Ergast, as novas temporadas da Fórmula 1 deixaram de ser incorporadas.

Para superar essa limitação, o projeto foi expandido com a **Jolpica API**.

### Integração com a Jolpica API

A Jolpica foi escolhida porque mantém exatamente a mesma estrutura de resposta anteriormente fornecida pela Ergast, permitindo que o projeto continuasse utilizando o dataset existente sem a necessidade de redesenhar todo o processo de ETL.

Foi desenvolvido um **pipeline** em Python para obter novas temporadas diretamente da API.

O processo de ingestão foi projetado com duas características importantes.

#### **Incremental Processing**

O pipeline atualiza apenas as temporadas solicitadas pelo usuário, em vez de reconstruir todo o banco de dados.

Exemplo:

```text
python update_f1.py --seasons 2025 2026
```

Isso permite que novos campeonatos sejam adicionados conforme a Fórmula 1 evolui.

#### **Idempotent Loading**

O processo de ETL pode ser executado múltiplas vezes sem gerar registros duplicados.

O processo:

- Remove os dados das temporadas selecionadas.
- Recarrega as informações atualizadas.
- Preserva os identificadores existentes.
- Cria novos IDs sequencialmente para novos pilotos, equipes e circuitos.

Essa abordagem garante a consistência dos dados e simplifica futuras manutenções.

## Infraestrutura do Banco de Dados

A camada de dados do projeto foi construída sobre o PostgreSQL para fornecer um ambiente robusto e escalável para armazenar tanto dados brutos quanto dados analíticos.

Para tornar a configuração do banco de dados totalmente automatizada e reproduzível, foi desenvolvido um conjunto de scripts em Python ([Load Data Script](./codes/load_data.py) e [Update Seasons Script](codes/update_seasons.py)) responsável por criar toda a estrutura do banco, carregar o dataset original do Kaggle, validar a integridade dos dados e gerar as **analytical views** consumidas pelo Power BI.

O pipeline de ETL cria automaticamente os schemas necessários, importa os arquivos CSV respeitando as dependências de **foreign keys**, executa rotinas de validação e prepara o banco para consultas analíticas.

O banco segue uma arquitetura em camadas composta por uma **raw layer**, responsável por armazenar os dados originais com mínima transformação, e uma **mart layer**, onde são criados os modelos dimensionais e as **analytical views** utilizadas para otimizar relatórios e workloads de Business Intelligence.

Essa separação preserva a integridade dos dados de origem enquanto fornece uma estrutura limpa e eficiente para análise.

Para simplificar o deployment e garantir que o projeto possa ser reproduzido de forma consistente em diferentes ambientes, o PostgreSQL é executado dentro de um container Docker.

Essa abordagem elimina a necessidade de configuração manual do banco de dados, permitindo que toda a infraestrutura seja recriada com um único comando.

Ao combinar Docker, PostgreSQL e automação em Python, a plataforma fornece um ambiente de dados portátil e de fácil manutenção, que pode ser atualizado, compartilhado ou implantado em diferentes máquinas preservando a mesma estrutura de banco de dados e as mesmas capacidades analíticas.

## Imagens

Um dos desafios em projetos de **Business Intelligence** é o gerenciamento de imagens externas, especialmente quando sites bloqueiam a incorporação direta ou removem suas URLs.

Para resolver esse problema, foi desenvolvido um **pipeline** local de ingestão de imagens.

A solução realiza o download das imagens apenas uma vez e as armazena diretamente no PostgreSQL como strings no formato **Base64 Data URI**. ([load_driver_photos.py](Project11/codes/load_driver_photos.py))

```text
Wikipedia / Local Files
          │
          ▼
Python Image Processor
          │
          ▼
PostgreSQL
          │
          ▼
Power BI
```

Para construtores e carros, foi criado um repositório local de imagens:

```text
images/

├── logos/
│
├── Ferrari.png
├── McLaren.png
├── Red Bull.png
│
└── cars/
    │
    ├── Ferrari.jpg
    ├── McLaren.jpg
    └── Red Bull.jpg
```

Essa abordagem elimina a dependência de hospedagem externa.

As imagens funcionam completamente offline.

Durante o desenvolvimento, uma limitação do Power BI foi levada em consideração: imagens em Base64 devem permanecer abaixo de **32.768 caracteres**.

Por isso, o pipeline otimiza automaticamente as imagens até que elas atendam a essa restrição do Power BI. ([load_images_from_folder.py](Project11/codes/load_images_from_folder.py))

Essa abordagem funciona especialmente bem para:

- Team logos.
- Small icons.

Para imagens maiores, como fotos dos carros, a hospedagem no GitHub pode ser utilizada como alternativa.

## Modelo de Dados do Power BI

A camada de visualização foi desenvolvida utilizando Power BI.

O banco de dados foi modelado seguindo a abordagem **Star Schema**.

![Star Schema](https://github.com/Benfluc/Projects/blob/main/Project11/imgs/star_schema.png)

O modelo separa:

**Dimensions**

Entidades descritivas:

- Drivers
- Constructors
- Circuits
- Races
- Dates

**Facts**

Dados numéricos de desempenho:

- Points
- Positions
- Lap times
- Qualifying results
- Race results

## DAX Measures and KPIs

Diversas medidas analíticas foram desenvolvidas utilizando DAX.

Exemplos:

- Total wins.
- Pole positions.
- Championship points.
- Average finishing position.
- Driver performance evolution.
- Constructor comparison.
- Season rankings.

O objetivo não foi apenas apresentar os dados, mas criar indicadores de desempenho relevantes para a análise da Fórmula 1.

**DAX Measures**

- [Analytics Measures](Project11/codes/dax_measures.dax)
- [Projection Measures](Project11/codes/dax_medidas_extras.dax)

## Conclusão

![Mercedes Analytics](https://github.com/Benfluc/Projects/blob/main/Project11/imgs/mercedes_relat.png)
![McLaren Analytics](https://github.com/Benfluc/Projects/blob/main/Project11/imgs/mclaren_relat.png)

A F1 Analytics Platform demonstra como técnicas modernas de **Data Engineering** e **Business Intelligence** podem ser integradas em uma solução analítica completa. Ao combinar pipelines automatizados de ETL, integração com APIs, PostgreSQL, Docker, processamento de imagens, modelagem dimensional e dashboards interativos no Power BI, o projeto fornece um ambiente escalável, portátil e de fácil manutenção para análise de dados da Fórmula 1.

Mais do que o desenvolvimento de dashboards, este projeto representa a implementação de um **end-to-end data pipeline**, abrangendo todas as etapas do ciclo de vida dos dados: aquisição, armazenamento, transformação, modelagem e visualização. Sua arquitetura foi projetada para ser modular e extensível, permitindo a atualização incremental de novas temporadas, a automação do processo de ingestão e a reprodução consistente da infraestrutura em diferentes ambientes.

Com a evolução contínua da Fórmula 1, a plataforma poderá incorporar novas funcionalidades, métricas e recursos analíticos, tornando-se uma solução cada vez mais completa para exploração de dados históricos e atuais do esporte. Além de servir como ferramenta de análise, o projeto também demonstra a aplicação prática de conceitos de **Data Engineering**, **Data Modeling**, **ETL**, **Business Intelligence** e desenvolvimento de soluções analíticas modernas.
