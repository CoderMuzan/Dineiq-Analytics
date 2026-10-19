# DineIQ Analytics - Phase 2 guide: Spark ingestion, data quality, cleaning

SRS steps covered: **3** (Spark ingestion), **4** (data-quality assessment), **5** (data cleaning).
Steps 6 and 7 are in `PHASE3_GUIDE.md`.

## Raw layer vs clean layer
| Layer | Folder | What it is |
|---|---|---|
| Raw | `raw_data/` (+ `parquet_data/`) | The deliberately dirty Phase 1 output. Never edited. |
| Clean | `clean_data/` | Analysis-ready Parquet produced by `03_clean_data.py`. This is the input of everything from Phase 3 on. |
| Quarantine | `quarantine/` | Every rejected row with a `quarantine_reason`. Nothing is silently deleted. |

## Install and run
Needs Java 17 or newer (check `java -version`) and `pip install -r requirements.txt`.
```
cd spark_jobs
python 01_ingest_validate.py        --root ..     # -> reports/ingestion_report.md
python 02_data_quality_report.py    --root ..     # -> reports/data_quality_report.md/.csv
python 03_clean_data.py             --root ..     # -> clean_data/, quarantine/, reports/cleaning_decisions.md/.csv
cd ..
python tests/test_phase2_cleaning.py --root .     # -> reports/phase2_test_results.md   (53 checks)
```
Run time at full size: about 4 minutes for the three jobs on one CPU core (timings in `reports/processing_times.csv`).
If Spark runs out of memory: `--driver-memory 3g`. On Windows, if Spark complains about `winutils`/`HADOOP_HOME`, search that error - it is a
known Windows-only setup step, not a bug in the jobs.

## What each job does
**spark_common.py** - Spark session settings, the explicit schema of every table, the business limits (valid date range, price ratio ...), a timer.
Edit limits here (e.g. the valid period) if the evaluators change them.
**01_ingest_validate.py** - explicit schema vs `inferSchema`, rows that do not fit the schema, multi-file ingestion, partitions
(`repartition`/`coalesce`, month-partitioned Parquet and partition pruning), CSV vs Parquet speed and size.
**02_data_quality_report.py** - 41 checks (33 find problems in this dataset; the rest are informational). Changes nothing. Severity HIGH / MEDIUM / INFO.
**03_clean_data.py** - applies the rules in `reports/cleaning_decisions.md`. Order of work: dedupe -> classify orders (invalid date / restaurant,
near-duplicate) -> route cancelled orders -> clean lines (quantity, item, price repair via an as-of price lookup, discount repair, recompute totals)
-> recompute order totals -> ratings, wastage, inventory.

## Key decisions you must be able to defend
1. **Quarantine instead of delete.** A row we cannot trust goes to `quarantine/` with a reason, so the loss is visible and auditable.
2. **Repair only when the true value is derivable.** A bad line price is replaced by the list price on that date (pricing history; if an item's price rows were all invalid, the menu's base price is used), a bad discount is
   recomputed from the order's promotion, kg/g wastage is converted with the dish's portion weight. A missing date or restaurant cannot be derived -> quarantine.
3. **Large but valid values are kept.** 60-90% manual discounts and huge catering orders are *anomalies to detect later*, not errors to clean.
4. **Cancelled / refunded / void orders are routed, not dropped.** They are needed for cancellation-rate analysis but must not enter revenue.
5. **Near-duplicate transactions** (same customer, restaurant, channel, basket and total within 200 s): the later one is quarantined.
   Honest limit: if independent dirt hits only one copy (e.g. one gets an invalid restaurant id), the pair no longer matches; the dirty original is then quarantined by
   its own rule, so revenue is still not double counted.
6. **Order totals are recomputed** from the cleaned lines; the original totals stay in `*_original` columns.

## Results at full size (seed 42)
- Orders: 386,585 raw unique = 368,132 clean + 17,195 cancelled/refunded/void + 1,258 quarantined.
- Order lines: 1,154,089 raw unique = 1,096,701 clean + 51,309 cancelled + 6,079 quarantined.
- All 53 automated tests pass: invariants (no duplicates, positive quantities and prices, totals add up), row reconciliation (raw = clean + cancelled + quarantined),
  and known answers (the data-quality report finds the dirt the generator planted; planted business cases survive cleaning).

## Limits to state in your report
- The data-quality "known answer" test uses the generator's injection log; on an unknown hidden dataset you only have the data-quality report.
- Cleaning rules use thresholds (price 0.5x-2x of list price, 200 s duplicate window). They suit this data; revisit them for the hidden dataset.
- Tested with PySpark 4.2 on Java 21 in a Linux sandbox; not tested on your machine.


