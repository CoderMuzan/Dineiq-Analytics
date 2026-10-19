"""
04_integrate_spark_sql.py - SRS Step 6: Data Integration with Spark SQL.

Reads clean_data/, runs the SQL scripts in spark_sql/ (01 lookup tables, 02 fact table, 03 daily table), CHECKS that the joins
neither lost nor duplicated rows, and writes
    processed_data/fact_order_lines/        1 row per cleaned order line, all dimensions attached   (partitioned by order_month)
    processed_data/daily_item_location/     1 row per day x restaurant x menu item: sales + wastage + ratings + inventory
    reports/integration_report.md

Run:  python 04_integrate_spark_sql.py --root ..
"""
import os

from pyspark.sql import functions as F

from spark_common import Timer, get_spark, parse_args, register_clean_views, run_sql_file

args = parse_args("DineIQ integration with Spark SQL")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-04-integrate", args.driver_memory)
J = "04_integrate"
OUT = os.path.join(ROOT, "processed_data")
register_clean_views(spark, ROOT)

with Timer(ROOT, J, "SQL 01 lookup tables"):
    run_sql_file(spark, ROOT, "01_lookup_tables.sql")
with Timer(ROOT, J, "SQL 02 fact_order_lines"):
    run_sql_file(spark, ROOT, "02_fact_order_lines.sql")
    fact = spark.table("fact_order_lines")
    fact.write.mode("overwrite").partitionBy("order_month").parquet(os.path.join(OUT, "fact_order_lines"))
fact = spark.read.parquet(os.path.join(OUT, "fact_order_lines")).cache()
fact.createOrReplaceTempView("fact_order_lines")
with Timer(ROOT, J, "SQL 03 daily_item_location"):
    run_sql_file(spark, ROOT, "03_daily_item_location.sql")
    spark.table("daily_item_location").repartition(4).write.mode("overwrite").parquet(os.path.join(OUT, "daily_item_location"))
daily = spark.read.parquet(os.path.join(OUT, "daily_item_location")).cache()

# ------------------------------------------------------------------ join integrity checks
src = spark.table("order_items").agg(F.count("*").alias("n"), F.sum("quantity").alias("q"), F.round(F.sum("line_total"), 2).alias("rev")).collect()[0]
ft = fact.agg(F.count("*").alias("n"), F.sum("quantity").alias("q"), F.round(F.sum("line_total"), 2).alias("rev"),
              F.countDistinct("order_line_id").alias("uniq"),
              F.sum(F.col("unit_cost").isNull().cast("int")).alias("no_cost"),
              F.sum(F.col("item_name").isNull().cast("int")).alias("no_item"),
              F.sum(F.col("restaurant_name").isNull().cast("int")).alias("no_loc"),
              F.sum(F.col("category_name").isNull().cast("int")).alias("no_cat"),
              F.sum((F.col("promo_id").isNotNull() & F.col("promo_type").isNull()).cast("int")).alias("promo_orphan"),
              F.sum((~F.col("is_guest") & F.col("signup_date").isNull()).cast("int")).alias("cust_orphan")).collect()[0]
dl = daily.agg(F.sum("units_sold").alias("u"), F.round(F.sum("revenue"), 2).alias("rev"), F.sum("wasted_portions").alias("w"),
               F.sum("n_ratings").alias("r"), F.count("*").alias("n"),
               F.sum(F.col("stock_week_end").isNotNull().cast("int")).alias("with_inv")).collect()[0]
wst = spark.table("wastage").agg(F.sum("quantity_wasted")).collect()[0][0]
rat = spark.table("ratings").filter("item_id IS NOT NULL AND has_purchase_link").count()
checks = [
    ("fact_order_lines row count = clean order_items", ft["n"] == src["n"], f"{ft['n']:,} vs {src['n']:,}"),
    ("fact_order_lines has no duplicated order_line_id", ft["uniq"] == ft["n"], f"{ft['uniq']:,} distinct"),
    ("fact units = clean units", ft["q"] == src["q"], f"{ft['q']:,} vs {src['q']:,}"),
    ("fact revenue = clean revenue", abs(ft["rev"] - src["rev"]) < 0.5, f"{ft['rev']:,.2f} vs {src['rev']:,.2f}"),
    ("every line has an item name", ft["no_item"] == 0, f"{ft['no_item']} missing"),
    ("every line has a category", ft["no_cat"] == 0, f"{ft['no_cat']} missing"),
    ("every line has a restaurant", ft["no_loc"] == 0, f"{ft['no_loc']} missing"),
    ("every line has a unit cost (price history covers the order date)", ft["no_cost"] == 0, f"{ft['no_cost']} missing"),
    ("every promo_id resolves to a promotion", ft["promo_orphan"] == 0, f"{ft['promo_orphan']} orphans"),
    ("every identified customer resolves to a customer profile", ft["cust_orphan"] == 0, f"{ft['cust_orphan']} orphans"),
    ("daily table units = fact units", dl["u"] == ft["q"], f"{dl['u']:,} vs {ft['q']:,}"),
    ("daily table revenue = fact revenue", abs(dl["rev"] - ft["rev"]) < 0.5, f"{dl['rev']:,.2f} vs {ft['rev']:,.2f}"),
    ("daily table wasted portions = clean wastage", abs(dl["w"] - wst) < 0.5, f"{dl['w']:,.0f} vs {wst:,.0f}"),
    ("daily table ratings = verified item ratings", dl["r"] == rat, f"{dl['r']:,} vs {rat:,}"),
]
md = ["# Integration report (Spark SQL, SRS Step 6)\n",
      "Scripts: `spark_sql/01_lookup_tables.sql`, `02_fact_order_lines.sql`, `03_daily_item_location.sql`.\n",
      "## Relationships implemented\n",
      "| # | Relationship (SRS Step 6) | Join key | Join type | Cardinality |\n|---|---|---|---|---|",
      "| 1 | Orders with customers | orders.customer_id = customers.customer_id | LEFT (guests have no customer) | many orders : 1 customer |",
      "| 2 | Orders with order items | order_items.order_id = orders.order_id | INNER | 1 order : many lines |",
      "| 3 | Order items with menu items | order_items.item_id = menu_items.item_id | INNER | many lines : 1 item |",
      "| 4 | Menu items with categories | menu_items.category_id = menu_categories.category_id | INNER | many items : 1 category |",
      "| 5 | Orders with restaurant locations | orders.location_id = restaurants.location_id | INNER | many orders : 1 restaurant |",
      "| 6 | Orders with promotions | orders.promo_id = promotions.promo_id | LEFT (most orders have no promotion) | many orders : 1 promotion |",
      "| 7 | Menu items with pricing history | item_id and the price period valid on the order date (as-of join through `cost_day`) | LEFT | 1 line : 1 price period |",
      "| 8 | Menu items with ratings | daily table: (date, restaurant, item) | LEFT | day-grain aggregate |",
      "| 9 | Menu items with inventory | daily table: week_start_date + restaurant + item | LEFT | weekly stock row : 7 days |",
      "| 10 | Menu items with wastage | daily table: (date, restaurant, item) | LEFT | day-grain aggregate |",
      "\nRatings, wastage and inventory have a different grain from order lines, so they are first aggregated to day x restaurant x item and only then joined "
      "(joining them directly to order lines would multiply rows and inflate sums).\n",
      "## Join integrity checks\n", "| Check | Result | Detail |\n|---|---|---|"]
md += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d} |" for n, ok, d in checks]
md.append(f"\nOutput sizes: `fact_order_lines` {ft['n']:,} rows; `daily_item_location` {dl['n']:,} rows "
          f"({dl['with_inv']:,} of them have a weekly inventory record).")
os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
open(os.path.join(ROOT, "reports", "integration_report.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md[-18:]))
spark.stop()
if not all(c[1] for c in checks):
    raise SystemExit("join integrity check failed")
