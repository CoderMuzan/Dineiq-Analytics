#!/usr/bin/env sh
# Runs the whole DineIQ pipeline (Phases 1-3) from the project root.   Usage:  sh run_all.sh
# Needs: Python 3.10+, Java 17+, and  pip install -r requirements.txt
set -e
echo "== Phase 1: generate raw dataset, validate, convert to Parquet"
(cd data_generator && python generate_dataset.py --out .. && python validate_dataset.py --root .. && python to_parquet.py --root ..)
echo "== Phase 2: Spark ingestion, data quality, cleaning"
(cd spark_jobs && python 01_ingest_validate.py --root .. && python 02_data_quality_report.py --root .. && python 03_clean_data.py --root ..)
python tests/test_phase2_cleaning.py --root .
echo "== Phase 3: Spark SQL integration and feature engineering"
(cd spark_jobs && python 04_integrate_spark_sql.py --root .. && python 05_feature_engineering.py --root ..)
python tests/test_phase3_features.py --root .
(cd spark_jobs && python 06_analytics_sql.py --root .. && python 07_pricing_promotions_locations.py --root .. && python 08_anomalies_satisfaction.py --root ..)
python tests/test_phase4_analytics.py --root .
echo "ALL DONE - see reports/"
