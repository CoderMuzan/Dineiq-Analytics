@echo off
REM Runs the whole DineIQ pipeline (Phases 1-4a) on Windows. Needs Python 3.10+, Java 17+, pip install -r requirements.txt
cd data_generator
python generate_dataset.py --out .. || exit /b 1
python validate_dataset.py --root .. || exit /b 1
python to_parquet.py --root .. || exit /b 1
cd ..\spark_jobs
python 01_ingest_validate.py --root .. || exit /b 1
python 02_data_quality_report.py --root .. || exit /b 1
python 03_clean_data.py --root .. || exit /b 1
python 04_integrate_spark_sql.py --root .. || exit /b 1
python 05_feature_engineering.py --root .. || exit /b 1
python 06_analytics_sql.py --root .. || exit /b 1
python 07_pricing_promotions_locations.py --root .. || exit /b 1
python 08_anomalies_satisfaction.py --root .. || exit /b 1
cd ..
python tests\test_phase2_cleaning.py --root . || exit /b 1
python tests\test_phase3_features.py --root . || exit /b 1
python tests\test_phase4_analytics.py --root . || exit /b 1
echo ALL DONE - see reports\
