# ADR-001: Storage and query layer for silver and gold data

## Status
Proposed (draft — blanks are mine to fill)

## Context
- Hourly climate time series for 15 cities, history since ____ → approx. ____ rows (15 × 8,760 × years)
- Access pattern: filter by city/year, aggregate (SUM/COUNT of hours)
- Loaded in bulk + daily append; no single-row updates, no transactions

## Decision
Silver and gold stored as Parquet in S3 (data lake), partitioned by ____,
queried with ____.

## Alternatives considered
- DynamoDB: rejected because ____
- RDS/Aurora: rejected because ____

## Consequences
- (+) ____
- (–) ____
- Corrected recent data: ____ (hint: overwrite partition vs update row)
