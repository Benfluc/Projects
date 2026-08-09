# Development of the F1 Analytics Platform

![Kimi Antonelli Standings](https://raw.githubusercontent.com/Benfluc/Projects/refs/heads/main/f1_analytics/imgs/kimi_relat.png)

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

```text
python update_f1.py --seasons 2025 2026
```

This allows new championships to be added as Formula 1 progresses.

#### **Idempotent Loading**

The ETL process can be executed multiple times without generating duplicated records.

The process:

- Removes data from the selected seasons.
- Reloads the updated information.
- Preserves existing identifiers.
- Creates new IDs sequentially for new drivers, teams, and circuits.

This guarantees data consistency and simplifies future maintenance.

## Database Infrastructure

The project’s data layer was built on PostgreSQL 
to provide a robust and scalable environment 
for storing both raw and analytical data. 

To make the database setup fully automated 
and reproducible, a collection of Python 
scripts ( [Load Data Script](codes/load_data.py)
[Update Seasons Script](codes/update_seasons.py)) was developed to create the database 
structure, load the original Kaggle dataset, 
validate data integrity, and generate the 
analytical views consumed by Power BI. 

The ETL pipeline automatically creates 
the required schemas, imports the CSV 
files while respecting foreign key 
dependencies, executes validation routines, 
and prepares the database for analytical 
queries.

The database follows a layered 
architecture composed of a raw layer, 
which stores the original data with 
minimal transformation, and a mart layer, 
where dimensional models and analytical 
views are created to optimize reporting 
and business intelligence workloads. 

This separation preserves the integrity 
of the source data while providing a 
clean and efficient structure for analysis.

To simplify deployment and ensure that 
the project can be reproduced consistently 
across different environments, 
PostgreSQL runs inside a Docker container. 
This approach removes the need for manual 
database configuration, allowing the 
entire infrastructure to be recreated 
with a single command. 

By combining Docker, PostgreSQL, and Python 
automation, the platform provides a 
portable and maintainable data environment 
that can be easily updated, shared, 
or deployed on different machines 
while preserving the same database 
structure and analytical capabilities.

## Images 

A challenge in BI projects is handling 
external images, especially when websites
block direct embedding or remove URLs.

To solve this, a local image ingestion 
pipeline was created.

The solution downloads images once and 
stores them directly inside PostgreSQL as 
Base64 Data URI strings. ([load_driver_photos.py](codes/load_driver_photos.py))

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

For constructors and cars, a local 
image repository was created:

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
This approach eliminates dependency 
on external hosting.

The images work completely offline.
A Power BI limitation was considered 
during development: Base64 images must 
remain below 32,768 characters.

Therefore, the pipeline automatically 
optimizes images until they fit the 
Power BI limitation. ([load_images_from_folder.py](codes/load_images_from_folder.py))

This works especially well for:

 - Team logos.
 - Small icons.

For large images, such as car photos, 
GitHub hosting can be used as 
an alternative.

## Power BI Data Model

The visualization layer was developed 
using Power BI.

The database was modeled using a 
Star Schema approach.

![Star Schema](https://github.com/Benfluc/Projects/blob/main/f1_analytics/imgs/star_schema.png)

The model separates:

**Dimensions**

Descriptive entities:

- Drivers
- Constructors
- Circuits
- Races
- Dates

**Facts**

Numerical performance data:

- Points
- Positions
- Lap times
- Qualifying results
- Race results

## DAX Measures and KPIs

Several analytical measures were 
created using DAX.

Examples:

• Total wins.
• Pole positions.
• Championship points.
• Average finishing position.
• Driver performance evolution.
• Constructor comparison.
• Season rankings.

The goal was not only to display data 
but to create meaningful performance 
indicators for Formula 1 analysis.

**DAX Measures**
- [Analytics Measures](codes/dax_measures.dax)
- [Projection Measures](codes/dax_medidas_extras.dax)

## Conclusion

![Mercedes Analytics](https://github.com/Benfluc/Projects/blob/main/f1_analytics/imgs/mercedes_relat.png)
![McLaren Analytics](https://github.com/Benfluc/Projects/blob/main/f1_analytics/imgs/mclaren_relat.png)

The F1 Analytics Platform demonstrates 
how modern data engineering and business 
intelligence techniques can be integrated 
into a complete analytical solution. 
By combining automated ETL pipelines, 
API integration, PostgreSQL, Docker, 
image processing, dimensional modeling, 
and interactive Power BI dashboards, 
the project provides a scalable and 
maintainable environment for exploring 
Formula 1 data.

This project reflects not only the 
development of dashboards, but also the
implementation of a complete end-to-end 
data pipeline, covering data acquisition, 
storage, transformation, modeling, and 
visualization. As the platform continues 
to evolve, new features and analytical 
capabilities will be incorporated, 
making it an increasingly comprehensive 
resource for Formula 1 data analysis.
