"""
05_feature_engineering.py - SRS Step 7: feature engineering with Spark SQL.

Reads processed_data/fact_order_lines (from step 04) and clean_data/, runs
    spark_sql/04_order_features.sql      per order
    spark_sql/05_item_features.sql       per menu item
    spark_sql/06_customer_features.sql   per customer  (RFM, behaviour)
    spark_sql/07_location_features.sql   per restaurant
and writes processed_data/features/<name>/ plus reports/feature_catalogue.md (every column explained).

Snapshot date = the day after the last order (spark_common.sql_params). Recency, trends and "recent" windows are measured from it.
IMPORTANT for modelling later: these features use the WHOLE year. For forecasting or any time-based model you must rebuild features
using only data before the prediction date (SRS Step 21, no future leakage).

Run:  python 05_feature_engineering.py --root ..
"""
import os

from pyspark.sql import functions as F

from spark_common import Timer, get_spark, parse_args, register_clean_views, run_sql_file, sql_params

args = parse_args("DineIQ feature engineering")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-05-features", args.driver_memory)
J = "05_features"
OUT = os.path.join(ROOT, "processed_data", "features")
register_clean_views(spark, ROOT)
run_sql_file(spark, ROOT, "01_lookup_tables.sql")
spark.read.parquet(os.path.join(ROOT, "processed_data", "fact_order_lines")).createOrReplaceTempView("fact_order_lines")

tables = {}
for sql, name, parts in [("04_order_features.sql", "order_features", 4), ("05_item_features.sql", "item_features", 1),
                         ("06_customer_features.sql", "customer_features", 2), ("07_location_features.sql", "location_features", 1)]:
    with Timer(ROOT, J, name):
        run_sql_file(spark, ROOT, sql)
        df = spark.table(name)
        df.repartition(parts).write.mode("overwrite").parquet(os.path.join(OUT, name))
        tables[name] = spark.read.parquet(os.path.join(OUT, name))
        if name == "order_features":
            tables[name].createOrReplaceTempView("order_features")      # later scripts read the stored copy
        print(f"   {name}: {tables[name].count():,} rows x {len(tables[name].columns)} columns", flush=True)

try:
    from feature_docs import DOCS
except ImportError:
    DOCS = {}
md = ["# Feature catalogue (SRS Step 7)\n", f"Parameters: {sql_params()}\n",
      "Profit = contribution margin = revenue after discount minus ingredient cost (from the price/cost valid on the order date). "
      "Platform commission is an order-level cost, so it appears only in order and restaurant features (`margin_after_fees`).\n"]
missing = []
for name, df in tables.items():
    md.append(f"\n## {name}  ({df.count():,} rows)\n\n| Column | Type | Meaning |\n|---|---|---|")
    for col, typ in df.dtypes:
        doc = DOCS.get(name, {}).get(col)
        if doc is None: missing.append(f"{name}.{col}")
        md.append(f"| {col} | {typ} | {doc or ''} |")
open(os.path.join(ROOT, "reports", "feature_catalogue.md"), "w").write("\n".join(md) + "\n")
if missing:
    print("UNDOCUMENTED COLUMNS:", ", ".join(missing))
spark.stop()
