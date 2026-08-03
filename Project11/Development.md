# Development of the F1 Analytics Platform

![Kimi Antonelli Standings](https://raw.githubusercontent.com/Benfluc/Projects/refs/heads/main/Project11/imgs/kimi_relat.png)

## Overview

The F1 Analytics Platform was developed as a complete Business Intelligence solution for Formula 1 data analysis, combining data engineering, database modeling, API integration, image processing, and interactive visualization with Power BI.

The main objective was to build an analytical environment capable of exploring historical and current Formula 1 data, including drivers, teams, circuits, races, qualifying results, standings, and performance indicators.

The project architecture was designed following a modern analytics pipeline:

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

## Data Acquisition and Pipeline Design
### Initial Dataset: Kaggle

The project started using a Formula 1 dataset available on [Kaggle](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020). This dataset contained historical information about races, drivers, constructors, circuits, qualifying sessions, and championships. However, the dataset had a limitation: it was only updated until the 2024 season. The reason was that the original data source, the Ergast Formula 1 API, was discontinued at the end of 2024. Since the Kaggle dataset depended on Ergast, new Formula 1 seasons were no longer being incorporated.

To solve this limitation, the project was extended with the Jolpica API.

### API Integration with Jolpica

Jolpica was selected because it maintains the same response structure previously provided by Ergast, allowing the project to continue from the existing dataset without redesigning the entire ETL process.

A Python pipeline was developed to retrieve new seasons directly from the API. 
The ingestion process was designed with two important characteristics:

#### **Incremental Processing**

The pipeline only updates the seasons requested by the user instead of rebuilding the entire database.

Example:

python update_f1.py --seasons 2025 2026

This allows new championships to be added as Formula 1 progresses.

#### **Idempotent Loading**

The ETL process can be executed multiple times without generating duplicated records.

The process:

- Removes data from the selected seasons.
- Reloads the updated information.
- Preserves existing identifiers.
- Creates new IDs sequentially for new drivers, teams, and circuits.

This guarantees data consistency and simplifies future maintenance.

## Project Status

🚧 **Under Construction**

This project is continuously evolving. New features, improvements, and additional analyses will be added in future updates.
