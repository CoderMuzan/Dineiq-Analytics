"""
spark_common.py - shared helpers for every Spark job in the DineIQ project.

Contains
  * get_spark()      one place that configures the Spark session
  * SCHEMAS          EXPLICIT schema of every raw table (SRS Step 3: "explicit schema definition")
  * read_raw()       reads a raw CSV table (or a whole folder of part-files) with its schema
  * VALID_*          business limits used by the data-quality checks AND the cleaning rules
  * Timer            writes processing times to reports/processing_times.csv (SRS: processing-time results)
"""
import argparse
import csv
import os
import time

from pyspark.sql import SparkSession
from pyspark.sql.types import (BooleanType, DateType, DoubleType, IntegerType, StringType, StructField, StructType)

# ----------------------------------------------------------------------------------------------
# Business limits. If the evaluators change the period or the thresholds ("surprise modification"),
# this is the only place to edit.
# ----------------------------------------------------------------------------------------------
VALID_DATE_MIN = "2025-10-01"          # first valid order date
VALID_DATE_MAX = "2026-09-30"          # last valid order date
PRICE_RATIO_MIN, PRICE_RATIO_MAX = 0.5, 2.0       # a line price must be within 0.5x..2x of the list price at that date
PRICING_ROW_RATIO_MIN, PRICING_ROW_RATIO_MAX = 0.5, 3.0   # a pricing_history price must be within 0.5x..3x of the menu base price
NEAR_DUP_SECONDS = 200                 # same customer/restaurant/basket/total within 200 s = duplicate transaction
UNIT_TO_PORTION_G = "portion_weight_g"  # kg and g quantities are converted with menu_items.portion_weight_g

_T = {"string": StringType(), "double": DoubleType(), "int": IntegerType(), "bool": BooleanType(), "date": DateType()}


def struct(cols):
    """Build a StructType from [(name, type_name), ...] - every field nullable (raw data has gaps)."""
    return StructType([StructField(n, _T[t], True) for n, t in cols])


# ----------------------------------------------------------------------------------------------
# EXPLICIT SCHEMAS (one per raw table).  order_datetime stays a STRING on purpose: the raw file
# contains impossible dates ("2026-13-45 ...", "not_a_date"), so it is parsed later, in the cleaning step.
# ----------------------------------------------------------------------------------------------
SCHEMAS = {
    "orders": struct([("order_id", "string"), ("customer_id", "string"), ("location_id", "string"),
                      ("order_datetime", "string"), ("channel", "string"), ("delivery_platform", "string"),
                      ("order_status", "string"), ("promo_id", "string"), ("party_size", "double"),
                      ("subtotal", "double"), ("discount_total", "double"), ("delivery_fee", "double"),
                      ("platform_fee", "double"), ("total_amount", "double"), ("payment_method", "string")]),
    "order_items": struct([("order_line_id", "string"), ("order_id", "string"), ("item_id", "string"),
                           ("quantity", "int"), ("unit_price", "double"), ("discount_amount", "double"),
                           ("line_total", "double")]),
    "customers": struct([("customer_id", "string"), ("signup_date", "date"), ("age_band", "string"),
                         ("home_location_id", "string"), ("city", "string"), ("preferred_channel", "string"),
                         ("acquisition_source", "string"), ("marketing_opt_in", "bool"), ("loyalty_member", "bool")]),
    "menu_items": struct([("item_id", "string"), ("item_name", "string"), ("category_id", "string"),
                          ("description", "string"), ("base_price", "double"), ("base_cost", "double"),
                          ("portion_weight_g", "int"), ("prep_time_min", "int"), ("is_vegetarian", "bool"),
                          ("launch_date", "date"), ("available_from", "date"), ("available_to", "date"),
                          ("is_active", "bool"), ("season_tag", "string")]),
    "menu_categories": struct([("category_id", "string"), ("category_name", "string"),
                               ("perishability", "string"), ("meal_period", "string")]),
    "restaurants": struct([("location_id", "string"), ("restaurant_name", "string"), ("area", "string"),
                           ("city", "string"), ("state", "string"), ("region", "string"),
                           ("opening_date", "date"), ("seating_capacity", "int"), ("size_tier", "string")]),
    "pricing_history": struct([("price_id", "string"), ("item_id", "string"), ("effective_from", "date"),
                               ("effective_to", "date"), ("price", "double"), ("unit_cost", "double"),
                               ("change_reason", "string")]),
    "promotions": struct([("promo_id", "string"), ("promo_name", "string"), ("promo_type", "string"),
                          ("discount_pct", "double"), ("start_date", "date"), ("end_date", "date"),
                          ("applicable_days", "string"), ("channel_restriction", "string"),
                          ("target_segment", "string"), ("promo_code", "string")]),
    "promotion_items": struct([("promo_id", "string"), ("item_id", "string")]),
    "ratings": struct([("rating_id", "string"), ("order_id", "string"), ("customer_id", "string"),
                       ("item_id", "string"), ("location_id", "string"), ("rating_value", "int"),
                       ("rating_date", "date"), ("source", "string")]),
    "wastage": struct([("wastage_id", "string"), ("wastage_date", "date"), ("location_id", "string"),
                       ("item_id", "string"), ("shift", "string"), ("prep_quantity", "double"),
                       ("quantity_wasted", "double"), ("unit", "string"), ("wastage_cost", "double"),
                       ("reason", "string")]),
    "inventory": struct([("inventory_id", "string"), ("week_start_date", "date"), ("location_id", "string"),
                         ("item_id", "string"), ("opening_stock", "double"), ("replenished_qty", "double"),
                         ("consumed_qty", "double"), ("closing_stock", "double"), ("reorder_level", "double"),
                         ("stockout_flag", "bool"), ("unit", "string")]),
}
CHUNKED = ("orders", "order_items")      # raw tables stored as many part files in a folder


def parse_args(description):
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--root", default="..", help="project root that contains raw_data/")
    ap.add_argument("--driver-memory", default="2g")
    return ap.parse_args()


def get_spark(app_name, driver_memory="2g"):
    spark = (SparkSession.builder.appName(app_name).master("local[*]")
             .config("spark.driver.memory", driver_memory)
             .config("spark.sql.shuffle.partitions", "8")        # small data: the default 200 would just add overhead
             .config("spark.sql.session.timeZone", "UTC")
             # ANSI off => to_timestamp() returns NULL for impossible dates instead of failing the job.
             # We WANT that: invalid dates are then caught by an explicit data-quality rule.
             .config("spark.sql.ansi.enabled", "false")
             .config("spark.ui.showConsoleProgress", "false")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def raw_path(root, table):
    return os.path.join(root, "raw_data", table) if table in CHUNKED else os.path.join(root, "raw_data", f"{table}.csv")


def read_raw(spark, root, table, with_corrupt=False):
    """Read one raw table with its explicit schema.  Folders are read as ONE table (multiple-file ingestion)."""
    schema = SCHEMAS[table]
    reader = spark.read.option("header", True).option("mode", "PERMISSIVE")
    if with_corrupt:                       # rows that do not fit the schema are kept in a helper column
        schema = StructType(schema.fields + [StructField("_corrupt_record", StringType(), True)])
        reader = reader.option("columnNameOfCorruptRecord", "_corrupt_record")
    return reader.schema(schema).csv(raw_path(root, table))


class Timer:
    """with Timer(root, 'job', 'step'):  ...  -> appends a row to reports/processing_times.csv"""
    def __init__(self, root, job, step):
        self.root, self.job, self.step = root, job, step

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *exc):
        secs = round(time.time() - self.t0, 2)
        path = os.path.join(self.root, "reports", "processing_times.csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(["job", "step", "seconds", "logged_at"])
            w.writerow([self.job, self.step, secs, time.strftime("%Y-%m-%d %H:%M:%S")])
        print(f"   [{self.job}] {self.step}: {secs}s", flush=True)


# ----------------------------------------------------------------------------------------------
# Spark SQL script runner
# ----------------------------------------------------------------------------------------------
def sql_params():
    """Values substituted into ${...} placeholders of the .sql scripts."""
    import datetime
    snap = (datetime.date.fromisoformat(VALID_DATE_MAX) + datetime.timedelta(days=1)).isoformat()
    return {"DATE_MIN": VALID_DATE_MIN, "DATE_MAX": VALID_DATE_MAX, "SNAPSHOT": snap,
            "TREND_DAYS": "56", "RECENT_DAYS": "90", "RATING_WINDOW": "90", "NEW_ITEM_DAYS": "60"}


def run_sql_file(spark, root, filename):
    """Run every statement of spark_sql/<filename>. '--' comment lines are dropped; statements are split on ';'."""
    path = os.path.join(root, "spark_sql", filename)
    text = open(path).read()
    for k, v in sql_params().items():
        text = text.replace("${" + k + "}", v)
    text = "\n".join(ln for ln in text.split("\n") if not ln.strip().startswith("--"))
    n = 0
    for stmt in split_statements(text):
        spark.sql(stmt)
        n += 1
    return n


def split_statements(text):
    """Split on ';' but NOT inside '...' string literals (e.g. concat_ws('; ', ...))."""
    out, cur, in_q = [], [], False
    for ch in text:
        if ch == "'": in_q = not in_q
        if ch == ";" and not in_q:
            stmt = "".join(cur).strip()
            if stmt: out.append(stmt)
            cur = []
        else:
            cur.append(ch)
    tail = "".join(cur).strip()
    if tail: out.append(tail)
    return out


def register_clean_views(spark, root):
    """Expose every table of clean_data/ as a SQL view with the table's own name."""
    base = os.path.join(root, "clean_data")
    for t in sorted(os.listdir(base)):
        if os.path.isdir(os.path.join(base, t)):
            spark.read.parquet(os.path.join(base, t)).createOrReplaceTempView(t)


def register_all_views(spark, root):
    """clean_data tables + processed_data (fact, daily) + every feature table, each as a SQL view named after the table."""
    register_clean_views(spark, root)
    base = os.path.join(root, "processed_data")
    for name, path in [("fact_order_lines", "fact_order_lines"), ("daily_item_location", "daily_item_location"),
                       ("order_features", "features/order_features"), ("item_features", "features/item_features"),
                       ("customer_features", "features/customer_features"), ("location_features", "features/location_features")]:
        spark.read.parquet(os.path.join(base, path)).createOrReplaceTempView(name)
