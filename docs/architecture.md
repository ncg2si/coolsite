# CoolSite – architecture

How data flows from the sources to the dashboard. Table details (grain, keys, columns): see `data_model.md`.

```mermaid
flowchart TB
    subgraph TS["Weather – time series (daily)"]
        direction LR
        OM["Open-Meteo API"] --> BR["Bronze<br/>raw JSON"]
        BR --> VAL{"Validate"}
        VAL -- pass --> SV["Silver<br/>clean hours"]
        VAL -- fail --> Q["Quarantine"]
        SV --> CL["Classify<br/>per scenario"]
    end

    subgraph RF["Reference data – static"]
        direction LR
        AQ["Aqueduct<br/>water stress"]
        SEED["Seeds<br/>cities, scenarios, modes"]
        EM["Ember<br/>renewable share"]:::planned
    end

    CL --> GD["Gold – star schema"]
    RF --> GD
    GD --> PBI["Power BI"]

    classDef planned stroke-dasharray: 5 5,color:#888
```

Dashed = planned. The pipeline runs locally with PySpark now and moves to Azure Databricks (planned); Power BI Desktop runs on an Azure Windows VM.

- **Weather (time series):** backfill 1961–2025, then a daily incremental load up to today − 7 days. Watermark = latest hour per city in silver.
- **Water stress (static reference):** downloaded once; a one-off script joins each city point to its river basin (spatial join) → `dim_city`.
- **Seeds (in Git):** city list, cooling scenarios (parameters), cooling modes.
