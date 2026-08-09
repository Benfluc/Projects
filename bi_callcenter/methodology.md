# Methodology
## Objective

The project was developed to analyze the operational performance of a customer service team, integrating traditional metrics with artificial intelligence techniques to generate strategic insights and support managerial decisions. To achieve this, a data-driven approach using synthetic data was adopted, constructed in Python and carefully modeled to reflect real call center characteristics, such as variation in conversions across campaigns and operators, a high number of missed calls, and a heterogeneous distribution of service interactions.

## Data Generation and Processing

The data were synthetically generated using Python scripts, ensuring that typical operational patterns were preserved, such as differences in performance among operators and campaigns, varied average handling times, and realistic recovered values. After generation, the data underwent cleaning, standardization, and validation to ensure consistency, absence of duplicates, and statistical plausibility of the indicators. Care was taken to ensure that the data closely reflected the peculiarities of call center operations.

## Construction of Performance Indicators and Score

To facilitate comparative evaluation and reduce biases arising from the isolated analysis of metrics, a performance score was developed. The score consolidated multiple weighted variables according to their relevance to business results: conversion rate, abandonment rate, average handling time, number of interactions, closed contracts, and recovered amounts. Artificial intelligence techniques were applied to calibrate the metric weights, ensuring that the score accurately reflected each operator's overall performance.

The score calculation is performed as follows:

$$
\text{Score Operador} = 0.40 \times [\text{Conversão Norm}] + 0.30 \times [\text{Abandono Norm}] + 0.20 \times [\text{Tempo Norm}] + 0.10 \times \frac{[\text{Atendimentos}]}{[\text{Max Atendimentos Operador}]}
$$

The components of the score are described as follows:

Conversion Norm (40%): Represents the operator's conversion rate, normalized between 0 and 1. This metric indicates the operator's effectiveness in closing contracts or generating business results from the interactions handled. It was assigned the highest weight in the score due to its direct relevance to the operation's success.

Abandonment Norm (30%): Refers to the abandonment rate, normalized so that lower values indicate better performance. This indicator measures the operator's ability to maintain interactions until completion, reflecting the quality and engagement in service.

Time Norm (20%): Corresponds to the operator's average handling time, normalized so that values appropriate for the call center's service profile are considered positive. This component captures the operator's efficiency and ability to conduct interactions in a balanced manner, ensuring both quality and conversion.

Interactions (10%): Represents the number of interactions handled by the operator, normalized relative to the maximum recorded in the operation. This factor incorporates individual productivity, recognizing that operators handling more interactions have greater exposure to conversion opportunities.

The weighted combination of these four elements allows for a multidimensional evaluation of performance, balancing productivity, service quality, and business results. In this way, the Operator Score provides management with a single, objective, and comparable indicator, capable of consistently identifying both top and low performers, avoiding biased interpretations derived from the isolated analysis of individual metrics.

## Visualization and Insights

The results were presented in interactive Power BI dashboards, including rankings of the best and worst operators, consolidated metrics, and comparisons across campaigns and monthly periods. The interface allowed for detailed individual and collective analyses, as well as generating strategic insights, such as the correlation between average handling time and conversion rate, and the importance of interaction volume for commercial performance.

## Validation and Application

Although the data were synthetic, they were designed to faithfully reflect the behavior of a real call center, allowing conceptual validation of the methodology. The consolidated model began to be used as a management support tool, providing a global view of the operation and informing decisions regarding resource allocation, campaign strategies, and operator training.
