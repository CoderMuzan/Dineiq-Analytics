# DineIQ Analytics - MenuMatrix Dining Intelligence
Aptech Semester 4 capstone, Data Science Intelligence Arena (TechWiz 7). Solo project.

This folder is the whole project in one place. It is built in phases; each phase has a guide in `documentation/`.

| Phase | SRS steps | What it does | Status |
|---|---|---|---|
| 1 Dataset | 1, 2 | ER design, synthetic raw dataset (1.15M order lines, planted dirt and business cases), Parquet | Done and tested |
| 2 Spark ingestion, quality, cleaning | 3, 4, 5 | explicit schemas, data-quality report, cleaning with quarantine and decision log | Done and tested |
| 3 Integration and features | 6, 7 | Spark SQL joins into a fact table, daily table, item / customer / location / order features | Done and tested |
| 4a Analytics | 8-11, 15-19, 23, 25-36 | EDA, menu classification, segmentation, baskets, peaks, wastage, pricing, promotion traps, anomalies, satisfaction | Done and tested |
| 4b Models and engine | 12-14, 20-22, 24, 37-41 | Spark MLlib (3+ models) vs independent Python models, forecasting, wastage-risk and churn models, recommendation engine, what-if | NOT built yet |
| 5 Web app and delivery | 42-50 + deliverables | dashboards, recommendations, what-if, reports, login, deployment, video, blog | NOT built yet |

## Folder map
```
data_generator/   Phase 1: config.py, generate_dataset.py, validate_dataset.py, to_parquet.py
spark_jobs/       Phases 2-3: spark_common.py, 01..05 jobs, feature_docs.py
spark_sql/        Spark SQL scripts (lookup tables, fact table, daily table, order / item / customer / location features)
tests/            automated tests for Phases 2, 3 and 4a (154 checks)
documentation/    ER_diagram.mermaid, data_dictionary.md, PHASE1/2/3 guides, GITHUB_QUICKSTART.md, DEV_LOG.md
reports/          generated evidence: data-quality report, cleaning decisions, integration report, feature catalogue, test results, timings
sample_data/      first rows of each raw table
AI_USAGE.md       declaration of AI help (complete it yourself)
raw_data/ parquet_data/ clean_data/ quarantine/ processed_data/   generated data (not in the zip of code; see below)
```

## Run everything
Requirements: Python 3.10+, **Java 17 or newer**, then `pip install -r requirements.txt`.
```
sh run_all.sh        (Linux / macOS)          run_all.bat      (Windows)
```
About 25 minutes on a single CPU core (Phase 4 analytics is about 11 of them). Or run the phases one by one as described in each guide.
The `raw_data/_ground_truth/` folder holds the answer keys of the generator. It is used ONLY by tests to check your analytics - never as ML features.

## Rules of the competition you must remember (SRS 1.8)
You must be able to explain every line, make a surprise change live, and keep `AI_USAGE.md`, `DEV_LOG.md` and daily GitHub commits up to date.
