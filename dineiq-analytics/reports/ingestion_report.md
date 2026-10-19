# Spark ingestion report

Spark version: `4.2.0`  |  master: `local[*]`


## 1. Explicit schema vs inferred schema, and data-type validation

| Table | Rows | Columns | Columns where inference differs from the explicit schema | Rows that do not fit the schema |
|---|---|---|---|---|
| orders | 388,130 | 15 | none | 0 |
| order_items | 1,157,551 | 7 | none | 0 |
| customers | 55,110 | 9 | none | 0 |
| menu_items | 168 | 14 | none | 0 |
| menu_categories | 12 | 4 | none | 0 |
| restaurants | 24 | 9 | none | 0 |
| pricing_history | 437 | 7 | none | 0 |
| promotions | 17 | 10 | none | 0 |
| promotion_items | 1,218 | 2 | none | 0 |
| ratings | 140,565 | 8 | none | 0 |
| wastage | 90,318 | 10 | none | 0 |
| inventory | 198,178 | 11 | none | 0 |

On this dataset inference happens to agree with the explicit schema, but it still costs an extra pass over the data and it only guesses from the values it sees: one dirty value in a hidden evaluation file (a word in a numeric column) or an all-empty column can silently change an inferred type. An explicit schema is faster, stable between runs and is the contract the data-quality step checks against.

## 2. Multiple-file ingestion

| Table | Part files read | Rows | Spark input partitions |
|---|---|---|---|
| orders | 13 | 388,130 | 1 |
| order_items | 13 | 1,157,551 | 1 |

## 3. Partition handling

- `order_items` read as **1** partitions; `repartition(8)` -> **8** (full shuffle, balances data); `coalesce(2)` -> **1** (no shuffle, only merges).
- `parquet_data/orders_by_month` is partitioned by `order_month` (13 partitions: 2025-10, 2025-11, 2025-12, 2026-01, 2026-02, 2026-03, 2026-04, 2026-05, 2026-06, 2026-07, 2026-08, 2026-09, unknown).
- Reading only `order_month = 2026-01` returns 30,631 rows and Spark skips the other folders (*partition pruning*). Plan evidence: `PartitionFilters: [isnotnull(order_month#7481), (order_month#7481 = 2026-01)]`
- Rows whose date is invalid sit in `order_month=unknown`: a first, free hint of the data-quality problem.

## 4. CSV versus Parquet

| Format | Task | Seconds |
|---|---|---|
| CSV (explicit schema) | group order lines by item (229 groups) | 1.53 |
| Parquet (snappy) | group order lines by item (229 groups) | 1.43 |

On disk: CSV `order_items` 57.5 MB vs Parquet 16.2 MB (columnar, compressed, typed - and Spark only reads the columns a query needs). Timings come from a small local machine; the first query also pays for JVM warm-up.
