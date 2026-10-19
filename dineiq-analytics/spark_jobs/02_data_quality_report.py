"""
02_data_quality_report.py - SRS Step 4: Data Quality Assessment.

Looks at the RAW tables only (nothing is changed here) and writes
    reports/data_quality_report.md   human-readable Data Quality Report
    reports/data_quality_report.csv  the same findings as a table (used by the tests)

Every finding has: table, check, rule, rows affected, % of table, severity.
Severity:  HIGH   = would corrupt revenue / profit / model results if left in
           MEDIUM = wrong but local
           INFO   = not an error, but analysts must know (e.g. guest orders, cancelled orders)

Run:  python 02_data_quality_report.py --root ..
"""
import os

from pyspark.sql import Window
from pyspark.sql import functions as F

import spark_common as S
from spark_common import Timer, get_spark, parse_args, read_raw

args = parse_args("DineIQ data-quality assessment")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-02-data-quality", args.driver_memory)
J = "02_data_quality"
findings = []          # dicts: table, check, rule, rows, total, severity


def add(table, check, rule, rows, total, severity):
    findings.append(dict(table=table, check=check, rule=rule, rows=int(rows or 0), total=int(total),
                         pct=round(100.0 * (rows or 0) / max(total, 1), 4), severity=severity))
    print(f"   {table:16s} {check:38s} {int(rows or 0):>9,}", flush=True)


def count_if(cond):
    return F.sum(F.when(cond, 1).otherwise(0))


# reference data -------------------------------------------------------------------------------
menu = read_raw(spark, ROOT, "menu_items").cache()
items = [r[0] for r in menu.select("item_id").collect()]
locs = [r[0] for r in read_raw(spark, ROOT, "restaurants").select("location_id").collect()]
customers_raw = read_raw(spark, ROOT, "customers").cache()
promos = [r[0] for r in read_raw(spark, ROOT, "promotions").select("promo_id").collect()]
D0, D1 = S.VALID_DATE_MIN, S.VALID_DATE_MAX

# ============================================================== ORDERS
with Timer(ROOT, J, "orders checks"):
    o = read_raw(spark, ROOT, "orders").withColumn("ts", F.to_timestamp("order_datetime", "yyyy-MM-dd HH:mm:ss")).cache()
    n = o.count()
    a = o.agg(
        count_if(F.col("order_datetime").isNull()).alias("dt_null"),
        count_if(F.col("order_datetime").isNotNull() & F.col("ts").isNull()).alias("dt_unparseable"),
        count_if(F.col("ts").isNotNull() & ((F.col("ts") < F.lit(D0).cast("timestamp")) |
                                             (F.col("ts") >= F.date_add(F.lit(D1).cast("date"), 1).cast("timestamp")))).alias("dt_range"),
        count_if(F.col("location_id").isNull()).alias("loc_null"),
        count_if(F.col("location_id").isNotNull() & ~F.col("location_id").isin(locs)).alias("loc_bad"),
        count_if(F.col("customer_id").isNull()).alias("cust_null"),
        count_if(F.col("payment_method").isNull()).alias("pay_null"),
        count_if(F.col("order_status") == "CANCELLED").alias("cancelled"),
        count_if(F.col("order_status") == "REFUNDED").alias("refunded"),
        count_if(F.col("order_status") == "VOID").alias("void"),
        count_if(F.col("promo_id").isNotNull() & ~F.col("promo_id").isin(promos)).alias("promo_bad"),
        count_if(F.col("total_amount") < 0).alias("neg_total"),
        count_if(F.col("discount_total") > F.col("subtotal")).alias("disc_gt_sub"),
    ).collect()[0].asDict()
    dup_ids = o.groupBy("order_id").count().filter("count > 1").agg(F.sum(F.col("count") - 1)).collect()[0][0]
    add("orders", "Duplicate orders", "same order_id appears more than once (extra copies)", dup_ids, n, "HIGH")
    add("orders", "Missing order date", "order_datetime is NULL", a["dt_null"], n, "HIGH")
    add("orders", "Invalid date (unparseable)", "order_datetime is not 'yyyy-MM-dd HH:mm:ss' (e.g. 2026-13-45)", a["dt_unparseable"], n, "HIGH")
    add("orders", "Invalid date (out of period)", f"parsed date outside {D0} .. {D1}", a["dt_range"], n, "HIGH")
    add("orders", "Missing restaurant id", "location_id is NULL", a["loc_null"], n, "HIGH")
    add("orders", "Invalid restaurant id", "location_id not in restaurants", a["loc_bad"], n, "HIGH")
    add("orders", "Missing customer id", "customer_id is NULL (guest checkout - legitimate, but no customer analytics possible)", a["cust_null"], n, "INFO")
    add("orders", "Missing payment method", "payment_method is NULL", a["pay_null"], n, "MEDIUM")
    add("orders", "Cancelled transactions", "order_status = CANCELLED", a["cancelled"], n, "INFO")
    add("orders", "Refunded transactions", "order_status = REFUNDED", a["refunded"], n, "INFO")
    add("orders", "Void transactions", "order_status = VOID", a["void"], n, "INFO")
    add("orders", "Unknown promotion id", "promo_id not in promotions", a["promo_bad"], n, "MEDIUM")
    add("orders", "Negative order total", "total_amount < 0", a["neg_total"], n, "HIGH")

# ============================================================== ORDER ITEMS
with Timer(ROOT, J, "order_items checks"):
    l = read_raw(spark, ROOT, "order_items").cache()
    n = l.count()
    ph_all = read_raw(spark, ROOT, "pricing_history").join(menu.select("item_id", "base_price"), "item_id")
    ph_ok = ph_all.filter((F.col("price") > 0) & (F.col("price") >= S.PRICING_ROW_RATIO_MIN * F.col("base_price")) &
                          (F.col("price") <= S.PRICING_ROW_RATIO_MAX * F.col("base_price")))
    # reference list price per item = median of its VALID price rows; menu base_price if it has none
    ref_med = (menu.select("item_id", "base_price")
               .join(ph_ok.groupBy("item_id").agg(F.expr("percentile_approx(price, 0.5)").alias("med")), "item_id", "left")
               .select("item_id", F.coalesce("med", "base_price").alias("ref_price")))
    lj = l.join(ref_med, "item_id", "left")
    a = lj.agg(
        count_if(F.col("item_id").isNull()).alias("item_null"),
        count_if(F.col("item_id").isNotNull() & ~F.col("item_id").isin(items)).alias("item_unknown"),
        count_if(F.col("quantity") <= 0).alias("qty_bad"),
        count_if(F.col("quantity").isNull()).alias("qty_null"),
        count_if(F.col("unit_price") <= 0).alias("price_nonpos"),
        count_if(F.col("unit_price") > S.PRICE_RATIO_MAX * 2 * F.col("ref_price")).alias("price_extreme"),
        count_if((F.col("discount_amount") < 0) | (F.col("discount_amount") > F.col("unit_price") * F.abs(F.col("quantity")))).alias("disc_bad"),
        count_if(F.abs(F.col("line_total") - (F.col("quantity") * F.col("unit_price") - F.col("discount_amount"))) > 0.01).alias("total_mismatch"),
    ).collect()[0].asDict()
    dup_lines = l.groupBy("order_line_id").count().filter("count > 1").agg(F.sum(F.col("count") - 1)).collect()[0][0]
    orphan = l.join(o.select("order_id").distinct(), "order_id", "left_anti").count()
    add("order_items", "Duplicate order lines", "same order_line_id appears more than once (extra copies)", dup_lines, n, "HIGH")
    add("order_items", "Missing menu id", "item_id is NULL", a["item_null"], n, "HIGH")
    add("order_items", "Unknown menu id", "item_id not in menu_items", a["item_unknown"], n, "HIGH")
    add("order_items", "Negative or zero quantity", "quantity <= 0", a["qty_bad"], n, "HIGH")
    add("order_items", "Missing quantity", "quantity is NULL", a["qty_null"], n, "HIGH")
    add("order_items", "Invalid menu price", "unit_price <= 0", a["price_nonpos"], n, "HIGH")
    add("order_items", "Extreme menu price", "unit_price more than 4x the item's median list price", a["price_extreme"], n, "HIGH")
    add("order_items", "Incorrect discount", "discount < 0 or discount > quantity x unit_price", a["disc_bad"], n, "HIGH")
    add("order_items", "Line total does not add up", "line_total != quantity x unit_price - discount", a["total_mismatch"], n, "MEDIUM")
    add("order_items", "Orphan order lines", "order_id not found in orders", orphan, n, "HIGH")
    # lines of orders that carry a header problem
    # ---- near-duplicate transactions: same customer + restaurant + channel + basket + total, within seconds
    fp = (l.dropDuplicates(["order_line_id"])
           .groupBy("order_id").agg(F.concat_ws(",", F.sort_array(F.collect_list(
               F.concat(F.coalesce(F.col("item_id"), F.lit("?")), F.lit("x"), F.col("quantity").cast("string"))))).alias("basket")))
    od = o.dropDuplicates(["order_id"]).filter(F.col("ts").isNotNull()).join(fp, "order_id")
    w = Window.partitionBy(F.coalesce("customer_id", F.lit("GUEST")), "location_id", "channel", "basket", "total_amount").orderBy("ts")
    od = od.withColumn("gap_s", F.col("ts").cast("long") - F.lag(F.col("ts").cast("long")).over(w))
    near = od.filter(F.col("gap_s") <= S.NEAR_DUP_SECONDS).count()
    add("orders", "Duplicate transactions (near-duplicates)",
        f"same customer, restaurant, channel, basket and total again within {S.NEAR_DUP_SECONDS} seconds", near, o.count(), "HIGH")

# ============================================================== CUSTOMERS / MENU / PRICING / PROMOTIONS
with Timer(ROOT, J, "reference tables checks"):
    c = customers_raw
    n = c.count()
    cd = c.groupBy("customer_id").count().filter("count > 1").agg(F.sum(F.col("count") - 1)).collect()[0][0]
    add("customers", "Duplicate customers", "same customer_id appears more than once", cd, n, "MEDIUM")
    add("customers", "Missing age band", "age_band is NULL", c.filter(F.col("age_band").isNull()).count(), n, "MEDIUM")
    add("customers", "Invalid home restaurant", "home_location_id not in restaurants",
        c.filter(~F.col("home_location_id").isin(locs)).count(), n, "MEDIUM")
    add("menu_items", "Missing description", "description is NULL", menu.filter(F.col("description").isNull()).count(), menu.count(), "INFO")
    ph = read_raw(spark, ROOT, "pricing_history")
    pj = ph.join(menu.select("item_id", "base_price"), "item_id", "left")
    bad = pj.filter((F.col("price") <= 0) | (F.col("price") < S.PRICING_ROW_RATIO_MIN * F.col("base_price")) |
                    (F.col("price") > S.PRICING_ROW_RATIO_MAX * F.col("base_price"))).count()
    add("pricing_history", "Invalid menu prices", f"price <= 0 or outside {S.PRICING_ROW_RATIO_MIN}x..{S.PRICING_ROW_RATIO_MAX}x of base_price", bad, ph.count(), "HIGH")
    add("pricing_history", "Item without valid price", "item_id not in menu_items", ph.join(menu, "item_id", "left_anti").count(), ph.count(), "MEDIUM")

# ============================================================== RATINGS
with Timer(ROOT, J, "ratings checks"):
    r = read_raw(spark, ROOT, "ratings").cache()
    n = r.count()
    a = r.agg(count_if(~F.col("rating_value").between(1, 5) | F.col("rating_value").isNull()).alias("bad"),
              count_if(~F.col("location_id").isin(locs) | F.col("location_id").isNull()).alias("loc_bad"),
              count_if(F.col("order_id").isNull()).alias("no_order"),
              count_if(F.col("item_id").isNull()).alias("restaurant_level")).collect()[0].asDict()
    add("ratings", "Invalid ratings", "rating_value not in 1..5", a["bad"], n, "HIGH")
    add("ratings", "Invalid restaurant id", "location_id not in restaurants", a["loc_bad"], n, "MEDIUM")
    add("ratings", "Ratings without a purchase", "order_id is NULL (not an error, but suspicious - used by anomaly detection)", a["no_order"], n, "INFO")
    add("ratings", "Restaurant-level ratings", "item_id is NULL (rating of the restaurant, not a dish)", a["restaurant_level"], n, "INFO")

# ============================================================== WASTAGE / INVENTORY
with Timer(ROOT, J, "wastage + inventory checks"):
    wst = read_raw(spark, ROOT, "wastage").join(menu.select("item_id", "portion_weight_g"), "item_id", "left").cache()
    n = wst.count()
    units = {r["unit"]: r["count"] for r in wst.groupBy("unit").count().collect()}
    a = wst.agg(count_if(F.col("item_id").isNull()).alias("item_null"),
                count_if(~F.col("location_id").isin(locs) | F.col("location_id").isNull()).alias("loc_bad")).collect()[0].asDict()
    add("wastage", "Inconsistent units", f"unit is not 'portion' (found: {', '.join(sorted(units))})",
        sum(v for k, v in units.items() if k != "portion"), n, "HIGH")
    # impossible quantity: judged AFTER converting to portions
    conv = (F.when(F.col("unit") == "kg", F.col("quantity_wasted") * 1000 / F.col("portion_weight_g"))
             .when(F.col("unit") == "g", F.col("quantity_wasted") / F.col("portion_weight_g"))
             .otherwise(F.col("quantity_wasted")))
    imp = wst.filter((conv <= 0) | (F.round(conv) > F.col("prep_quantity")) | (conv > 1000)).count()
    add("wastage", "Impossible wastage quantities", "quantity <= 0, more than was prepared, or > 1000 portions", imp, n, "HIGH")
    add("wastage", "Missing menu id", "item_id is NULL", a["item_null"], n, "MEDIUM")
    add("wastage", "Invalid restaurant id", "location_id not in restaurants", a["loc_bad"], n, "MEDIUM")
    inv = read_raw(spark, ROOT, "inventory")
    n = inv.count()
    a = inv.agg(count_if(F.col("closing_stock") < 0).alias("neg"),
                count_if(F.col("unit") != "portion").alias("unit"),
                count_if(~F.col("location_id").isin(locs) | F.col("location_id").isNull()).alias("loc_bad")).collect()[0].asDict()
    add("inventory", "Negative stock", "closing_stock < 0", a["neg"], n, "HIGH")
    add("inventory", "Inconsistent units", "unit is not 'portion' (kg rows must be converted)", a["unit"], n, "HIGH")
    add("inventory", "Invalid restaurant id", "location_id not in restaurants", a["loc_bad"], n, "MEDIUM")

# ============================================================== write report
import csv
out_csv = os.path.join(ROOT, "reports", "data_quality_report.csv")
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(findings[0].keys()))
    w.writeheader(); w.writerows(findings)
sev_order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
md = ["# Data Quality Report (raw layer)\n",
      f"Assessed by Spark {spark.version} against the explicit schemas in `spark_common.py`. Valid order period: {D0} .. {D1}.\n",
      "Nothing is changed in this step. The cleaning decisions taken for every finding are in `cleaning_decisions.md`.\n",
      "| Table | Check | Rule | Rows | % of table | Severity |\n|---|---|---|---|---|---|"]
for f_ in sorted(findings, key=lambda x: (sev_order[x["severity"]], x["table"])):
    md.append(f"| {f_['table']} | {f_['check']} | {f_['rule']} | {f_['rows']:,} | {f_['pct']:.3f}% | {f_['severity']} |")
high = [f_ for f_ in findings if f_["severity"] == "HIGH" and f_["rows"] > 0]
md.append(f"\n**Summary:** {len(findings)} checks, {len(high)} HIGH-severity problems present, "
          f"{sum(1 for f_ in findings if f_['rows'] > 0)} checks with at least one affected row.")
open(os.path.join(ROOT, "reports", "data_quality_report.md"), "w").write("\n".join(md) + "\n")
print("report written")
spark.stop()
