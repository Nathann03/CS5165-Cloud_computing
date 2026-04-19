# Project Write-Ups

## Retail Dashboard Question
The dashboard is designed to answer a practical retail question: how do demographics, engagement patterns, brand mix, seasonality, and basket behavior explain customer value and retention risk? The dashboard combines KPI cards, spend-over-time charts, department and region views, brand preference summaries, and basket-pair analysis so a reviewer can see both descriptive trends and action-oriented outcomes. The at-risk household table connects the analytical views to a specific business decision: which households should receive retention attention first.

## Basket Analysis ML Application
Retail question: what product combinations are commonly purchased together, and how can they drive cross-selling opportunities? This project uses a Random Forest classifier at the basket level. For baskets containing a high-frequency primary commodity, the model predicts whether a likely cross-sell target commodity will also appear. Features include total basket spend, total units, item count, department count, month, region, loyalty, and income range. The output is useful because it converts basket co-occurrence patterns into a clear cross-sell recommendation supported by measurable model performance.

## CLV Write-Up
Customer lifetime value is modeled as future household spend after a historical cutoff date. A Gradient Boosting Regressor was selected because retail purchasing behavior is usually non-linear and influenced by interactions among order count, spend, units, category breadth, region, age, income, and loyalty. The model uses household-level engineered features from transaction history to estimate downstream value. This is more useful than raw descriptive spend because it creates a forward-looking prioritization of households that appear likely to generate more future revenue.

## Churn / At-Risk Household Write-Up
Churn is defined as no baskets in the final 60 days of the analysis window. The churn model uses spend, basket count, item count, recency, and recent basket activity to estimate disengagement risk. In the live Azure demo, the deployment dataset was rebuilt as a balanced household-level sample so the churn model could be evaluated using a real holdout split instead of a fallback training-only score. The resulting ranked at-risk household list on the dashboard is the practical output: it identifies which households are most likely to disengage and therefore are the best candidates for retention offers or reminder campaigns.

## Azure Deployment Write-Up
The deployed application uses Azure App Service for hosting and Azure Database for PostgreSQL Flexible Server as the managed relational database. This architecture is simple enough for a class project, inexpensive enough for student credits, and unambiguous for rubric grading because the database is a separate managed Azure service. The application reads from the managed database at runtime, while data loading is handled separately so web startup remains fast and stable.
