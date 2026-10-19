"""
03_clean_data.py - SRS Step 5: Data Cleaning.

Input : raw_data/            (dirty CSV, read with the explicit schemas)
Output: clean_data/          analysis-ready Parquet tables
        quarantine/          every rejected row, with a `quarantine_reason`   (nothing is silently deleted)
        reports/cleaning_decisions.md / .csv   every cleaning decision with the number of rows it touched

THE THREE POSSIBLE ACTIONS (SRS: "clean, correct, remove, or quarantine")
  REMOVE      exact copies of a row we already keep (true duplicates).  No information is lost.
  REPAIR      the correct value can be derived from other data  (e.g. a bad price -> list price on that date).
  QUARANTINE  the row cannot be trusted or repaired  -> moved to quarantine/ with the reason.
  ROUTE       valid but not part of normal revenue analysis (cancelled / refunded / void orders)
              -> kept in clean_data/cancelled_orders for cancellation-rate analysis.
  FLAG        row kept, but a column marks it (guest orders, ratings without a purchase ...).

Run:  python 03_clean_data.py --root ..
"""
import csv
import os

from pyspark import StorageLevel
from pyspark.sql import Window
from pyspark.sql import functions as F

import spark_common as S
from spark_common import Timer, get_spark, parse_args, read_raw

args = parse_args("DineIQ data cleaning")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-03-clean", args.driver_memory)
J = "03_clean"
CLEAN, QUAR = os.path.join(ROOT, "clean_data"), os.path.join(ROOT, "quarantine")
D0, D1 = S.VALID_DATE_MIN, S.VALID_DATE_MAX
decisions = []   # table, rule_id, condition, action, rows, why


def decide(table, rule_id, condition, action, rows, why):
    decisions.append(dict(table=table, rule_id=rule_id, condition=condition, action=action, rows=int(rows or 0), why=why))
    print(f"   {rule_id:6s} {table:15s} {action:10s} {int(rows or 0):>9,}  {condition[:70]}", flush=True)


def write(df, name, base=CLEAN, partition=None, parts=None):
    w = df if parts is None else df.repartition(parts)
    w = w.write.mode("overwrite")
    if partition: w = w.partitionBy(partition)
    w.parquet(os.path.join(base, name))


def quarantine_report(df, table, rules):
    """Counts quarantined rows per reason and records one decision per reason."""
    for r in df.groupBy("quarantine_reason").count().collect():
        reason = r["quarantine_reason"]
        rid, cond, why = rules.get(reason.split(":")[0], ("Q-??", reason, "see code"))
        decide(table, rid, cond, "QUARANTINE", r["count"], why)


P = StorageLevel.MEMORY_AND_DISK
menu = read_raw(spark, ROOT, "menu_items").cache()
restaurants = read_raw(spark, ROOT, "restaurants")
promotions = read_raw(spark, ROOT, "promotions")
promo_items = read_raw(spark, ROOT, "promotion_items")
items = [r[0] for r in menu.select("item_id").collect()]
locs = [r[0] for r in restaurants.select("location_id").collect()]

# =========================================================================================== CUSTOMERS
with Timer(ROOT, J, "customers"):
    c_raw = read_raw(spark, ROOT, "customers")
    c = c_raw.dropDuplicates(["customer_id"])
    decide("customers", "C-01", "same customer_id repeated", "REMOVE", c_raw.count() - c.count(),
           "identical copies of a profile; one is enough")
    n_age = c.filter(F.col("age_band").isNull()).count()
    c = c.withColumn("age_band", F.coalesce("age_band", F.lit("UNKNOWN")))
    decide("customers", "C-02", "age_band is NULL", "REPAIR", n_age, "filled with 'UNKNOWN' so group-bys do not silently drop customers")
    write(c, "customers", parts=1)

# =========================================================================================== PRICING HISTORY
with Timer(ROOT, J, "pricing_history"):
    ph_raw = read_raw(spark, ROOT, "pricing_history").join(menu.select("item_id", "base_price"), "item_id", "left")
    bad = ((F.col("price") <= 0) | (F.col("price") < S.PRICING_ROW_RATIO_MIN * F.col("base_price")) |
           (F.col("price") > S.PRICING_ROW_RATIO_MAX * F.col("base_price")) | F.col("base_price").isNull())
    ph_bad = ph_raw.filter(bad).withColumn("quarantine_reason", F.lit("INVALID_PRICE")).drop("base_price")
    ph = ph_raw.filter(~bad).drop("base_price").cache()
    write(ph_bad, "pricing_history", base=QUAR, parts=1)
    decide("pricing_history", "P-01", f"price <= 0 or outside {S.PRICING_ROW_RATIO_MIN}x..{S.PRICING_ROW_RATIO_MAX}x base price",
           "QUARANTINE", ph_bad.count(), "wrong price; the previous valid period's price is used for that period via the as-of lookup (rule L-05)")
    write(ph, "pricing_history", parts=1)

    # price lookup table: list price of every item on every day of the valid period ("as-of join")
    #   1. latest valid pricing_history row with effective_from <= day
    #   2. else the item's earliest valid row (its first period was quarantined)
    #   3. else the menu's base_price (the item has no valid pricing row at all)
    days = spark.range(1).select(F.explode(F.sequence(F.lit(D0).cast("date"), F.lit(D1).cast("date"))).alias("order_date"))
    grid = days.crossJoin(menu.select("item_id", "base_price"))
    cand = days.crossJoin(menu.select("item_id")).join(ph.select("item_id", "effective_from", "price"), "item_id") \
        .filter(F.col("effective_from") <= F.col("order_date"))
    w = Window.partitionBy("item_id", "order_date").orderBy(F.col("effective_from").desc())
    asof = cand.withColumn("rn", F.row_number().over(w)).filter("rn = 1").select("item_id", "order_date", F.col("price").alias("asof_price"))
    first = ph.groupBy("item_id").agg(F.expr("min_by(price, effective_from)").alias("first_price"))
    price_day = (grid.join(asof, ["item_id", "order_date"], "left").join(first, "item_id", "left")
                 .select("item_id", "order_date", F.coalesce("asof_price", "first_price", "base_price").alias("ref_price")).cache())

# =========================================================================================== ORDERS (header classification)
with Timer(ROOT, J, "orders + lines classification"):
    o_raw = read_raw(spark, ROOT, "orders")
    l_raw = read_raw(spark, ROOT, "order_items")
    o = o_raw.dropDuplicates(["order_id"]).withColumn("ts", F.to_timestamp("order_datetime", "yyyy-MM-dd HH:mm:ss"))
    l = l_raw.dropDuplicates(["order_line_id"]).persist(P)
    n_o_raw, n_o = o_raw.count(), o.count()
    n_l_raw, n_l = l_raw.count(), l.count()
    decide("orders", "O-01", "same order_id repeated", "REMOVE", n_o_raw - n_o, "exact copies of an order header")
    decide("order_items", "L-01", "same order_line_id repeated", "REMOVE", n_l_raw - n_l, "exact copies of an order line")

    # near-duplicate transactions: same customer + restaurant + channel + basket + total within a few seconds
    fp = l.groupBy("order_id").agg(F.concat_ws(",", F.sort_array(F.collect_list(
        F.concat(F.coalesce("item_id", F.lit("?")), F.lit("x"), F.col("quantity").cast("string"))))).alias("basket"))
    dd = o.filter(F.col("ts").isNotNull()).join(fp, "order_id")
    w = Window.partitionBy(F.coalesce("customer_id", F.lit("GUEST")), "location_id", "channel", "basket", "total_amount").orderBy("ts")
    dd = dd.withColumn("gap_s", F.col("ts").cast("long") - F.lag(F.col("ts").cast("long")).over(w))
    near = dd.filter(F.col("gap_s") <= S.NEAR_DUP_SECONDS).select("order_id", F.lit(True).alias("is_near_dup"))

    d0_ts = F.lit(D0).cast("timestamp")
    d1_ts = F.date_add(F.lit(D1).cast("date"), 1).cast("timestamp")
    o_class = (o.join(near, "order_id", "left")
               .withColumn("quarantine_reason",
                           F.when(F.col("ts").isNull(), "INVALID_DATE")
                            .when((F.col("ts") < d0_ts) | (F.col("ts") >= d1_ts), "DATE_OUT_OF_PERIOD")
                            .when(F.col("location_id").isNull() | ~F.col("location_id").isin(locs), "INVALID_LOCATION")
                            .when(F.col("is_near_dup"), "NEAR_DUPLICATE_TRANSACTION"))
               .drop("is_near_dup").persist(P))
    O_RULES = {
        "INVALID_DATE": ("O-02", "order_datetime missing or impossible (e.g. 2026-13-45)", "an order without a date cannot be placed in time; the date cannot be guessed"),
        "DATE_OUT_OF_PERIOD": ("O-03", f"order date outside {D0}..{D1}", "future / ancient dates are impossible for this dataset"),
        "INVALID_LOCATION": ("O-04", "location_id missing or not in restaurants", "cannot be attributed to a restaurant; guessing would corrupt location analysis"),
        "NEAR_DUPLICATE_TRANSACTION": ("O-05", f"same customer, restaurant, channel, basket and total again within {S.NEAR_DUP_SECONDS}s", "a double-submitted transaction; the first one is kept, the repeat would double-count revenue"),
    }
    q_orders = o_class.filter(F.col("quarantine_reason").isNotNull())
    quarantine_report(q_orders, "orders", O_RULES)
    rest = o_class.filter(F.col("quarantine_reason").isNull())

    cancelled = rest.filter(F.col("order_status") != "COMPLETED")
    for r in cancelled.groupBy("order_status").count().collect():
        decide("orders", "O-06", f"order_status = {r['order_status']}", "ROUTE", r["count"],
               "valid record but not revenue; kept in clean_data/cancelled_orders for cancellation analysis")

# =========================================================================================== ORDER LINES
with Timer(ROOT, J, "order_items cleaning"):
    base_cols = ["order_line_id", "order_id", "item_id", "quantity", "unit_price", "discount_amount", "line_total"]
    info = o_class.select("order_id", F.col("quarantine_reason").alias("o_reason"), "order_status", "ts", "promo_id",
                          F.lit(True).alias("has_parent"))
    lj = l.join(info, "order_id", "left")
    lj = lj.withColumn("stage_reason",
                       F.when(F.col("has_parent").isNull(), "ORPHAN_LINE")
                        .when(F.col("o_reason").isNotNull(), F.concat(F.lit("PARENT_ORDER_"), F.col("o_reason"))))
    q1 = lj.filter(F.col("stage_reason").isNotNull()).select(*base_cols, F.col("stage_reason").alias("quarantine_reason"))
    rest_l = lj.filter(F.col("stage_reason").isNull())
    cancelled_lines = rest_l.filter(F.col("order_status") != "COMPLETED").select(*base_cols)
    cand = rest_l.filter(F.col("order_status") == "COMPLETED")

    cand = cand.withColumn("item_reason",
                           F.when(F.col("item_id").isNull(), "MISSING_ITEM_ID")
                            .when(~F.col("item_id").isin(items), "UNKNOWN_ITEM_ID")
                            .when(F.col("quantity").isNull() | (F.col("quantity") <= 0), "INVALID_QUANTITY"))
    q2 = cand.filter(F.col("item_reason").isNotNull()).select(*base_cols, F.col("item_reason").alias("quarantine_reason"))
    ok = cand.filter(F.col("item_reason").isNull()).withColumn("order_date", F.to_date("ts"))

    ok = ok.join(price_day, ["item_id", "order_date"], "left")
    price_bad = (F.col("unit_price").isNull() | (F.col("unit_price") <= 0) |
                 (F.col("ref_price").isNotNull() & ((F.col("unit_price") < S.PRICE_RATIO_MIN * F.col("ref_price")) |
                                                    (F.col("unit_price") > S.PRICE_RATIO_MAX * F.col("ref_price")))))
    ok = ok.withColumn("price_bad", price_bad)
    q3 = ok.filter(F.col("price_bad") & F.col("ref_price").isNull()).select(*base_cols, F.lit("UNREPAIRABLE_PRICE").alias("quarantine_reason"))
    ok = ok.filter(~(F.col("price_bad") & F.col("ref_price").isNull()))
    ok = ok.withColumn("price_repaired", F.col("price_bad")) \
           .withColumn("unit_price", F.when(F.col("price_bad"), F.col("ref_price")).otherwise(F.col("unit_price")))
    gross = F.col("quantity") * F.col("unit_price")
    scope = promo_items.join(promotions.select("promo_id", "discount_pct"), "promo_id")
    ok = ok.join(scope, ["promo_id", "item_id"], "left")
    disc_bad = F.col("discount_amount").isNull() | (F.col("discount_amount") < 0) | (F.col("discount_amount") > gross + 0.01)
    ok = ok.withColumn("discount_repaired", disc_bad) \
           .withColumn("discount_amount", F.when(disc_bad, F.round(F.coalesce(gross * F.col("discount_pct"), F.lit(0.0)), 2))
                                           .otherwise(F.col("discount_amount"))) \
           .withColumn("line_total", F.round(gross - F.col("discount_amount"), 2))
    clean_lines = ok.select(*base_cols, "price_repaired", "discount_repaired").persist(P)

    L_RULES = {
        "ORPHAN_LINE": ("L-02", "order_id not found in orders", "a line without a header cannot be dated or attributed"),
        "PARENT_ORDER_INVALID_DATE": ("L-03", "parent order quarantined (invalid date)", "lines follow their order"),
        "PARENT_ORDER_DATE_OUT_OF_PERIOD": ("L-03", "parent order quarantined (date out of period)", "lines follow their order"),
        "PARENT_ORDER_INVALID_LOCATION": ("L-03", "parent order quarantined (invalid location)", "lines follow their order"),
        "PARENT_ORDER_NEAR_DUPLICATE_TRANSACTION": ("L-03", "parent order quarantined (near-duplicate)", "lines follow their order"),
        "MISSING_ITEM_ID": ("L-04", "item_id is NULL", "cannot tell what was sold; item-level and profit analysis would be wrong"),
        "UNKNOWN_ITEM_ID": ("L-04", "item_id not in menu_items", "unknown dish: no cost, category or price to analyse (a NEW item in hidden data should be added to the menu first)"),
        "INVALID_QUANTITY": ("L-04", "quantity <= 0 or NULL", "negative / zero quantity is not a sale; not repairable"),
        "UNREPAIRABLE_PRICE": ("L-05", "bad price and no list price available for that date", "price cannot be recovered"),
    }
    q_lines = q1.unionByName(q2).unionByName(q3)
    quarantine_report(q_lines, "order_items", L_RULES)
    n_pr = clean_lines.filter("price_repaired").count()
    n_dr = clean_lines.filter("discount_repaired").count()
    decide("order_items", "L-05", f"unit_price <= 0 or outside {S.PRICE_RATIO_MIN}x..{S.PRICE_RATIO_MAX}x of the list price on the order date",
           "REPAIR", n_pr, "replaced by the list price valid on the order date (pricing_history as-of lookup)")
    decide("order_items", "L-06", "discount < 0 or discount > quantity x price", "REPAIR", n_dr,
           "recomputed from the order's promotion (discount_pct x gross if the item is in promotion scope, else 0). "
           "Large but valid discounts (e.g. manual 60-90%) are NOT changed - they are anomalies to detect later")
    decide("order_items", "L-07", "line_total recomputed", "REPAIR", clean_lines.count(), "line_total = quantity x unit_price - discount_amount for every kept line")
    decide("order_items", "L-08", "lines of cancelled / refunded / void orders", "ROUTE", cancelled_lines.count(),
           "stored in clean_data/cancelled_order_items")

    write(q_lines, "order_items", base=QUAR, parts=1)
    write(cancelled_lines, "cancelled_order_items", parts=1)
    write(clean_lines, "order_items", parts=8)

# =========================================================================================== ORDERS (final)
with Timer(ROOT, J, "orders final"):
    agg = clean_lines.groupBy("order_id").agg(
        F.round(F.sum(F.col("quantity") * F.col("unit_price")), 2).alias("subtotal_clean"),
        F.round(F.sum("discount_amount"), 2).alias("discount_total_clean"),
        F.count("*").alias("n_lines"))
    in_counts = lj.groupBy("order_id").agg(F.count("*").alias("n_lines_in"))
    good = rest.filter(F.col("order_status") == "COMPLETED")
    final = good.join(agg, "order_id", "left").join(in_counts, "order_id", "left")
    q_nolines = final.filter(F.col("n_lines").isNull()).select(*o_raw.columns, F.lit("NO_VALID_LINES").alias("quarantine_reason"))
    n_nl = q_nolines.count()
    decide("orders", "O-07", "no valid line left after line cleaning (or no lines at all)", "QUARANTINE", n_nl, "an order without items has no analytical value")
    final = final.filter(F.col("n_lines").isNotNull())
    clean_orders = (final
        .withColumn("subtotal_original", F.col("subtotal")).withColumn("discount_total_original", F.col("discount_total"))
        .withColumn("total_amount_original", F.col("total_amount"))
        .withColumn("subtotal", F.col("subtotal_clean")).withColumn("discount_total", F.col("discount_total_clean"))
        .withColumn("total_amount", F.round(F.col("subtotal_clean") - F.col("discount_total_clean") + F.col("delivery_fee"), 2))
        .withColumn("payment_method", F.coalesce("payment_method", F.lit("UNKNOWN")))
        .withColumn("is_guest", F.col("customer_id").isNull())
        .withColumn("n_lines_removed", F.col("n_lines_in") - F.col("n_lines"))
        .withColumn("order_date", F.to_date("ts")).withColumn("order_hour", F.hour("ts"))
        .withColumn("order_month", F.date_format("ts", "yyyy-MM"))
        .withColumnRenamed("ts", "order_ts")
        .drop("order_datetime", "subtotal_clean", "discount_total_clean", "n_lines_in", "quarantine_reason", "n_lines").persist(P))
    decide("orders", "O-08", "payment_method is NULL", "REPAIR", clean_orders.filter(F.col("payment_method") == "UNKNOWN").count(), "filled with 'UNKNOWN'")
    decide("orders", "O-09", "customer_id is NULL", "FLAG", clean_orders.filter("is_guest").count(),
           "kept; column is_guest = true (guest checkout is legitimate, but excluded from customer analytics)")
    changed = clean_orders.filter(F.abs(F.col("total_amount") - F.col("total_amount_original")) > 0.01).count()
    decide("orders", "O-10", "order totals recomputed from the cleaned lines", "REPAIR", changed,
           "subtotal, discount_total and total_amount now equal the sum of the kept lines; originals kept in *_original columns")
    write(clean_orders, "orders", partition="order_month", parts=4)
    write(cancelled.select(*o_raw.columns, "ts").withColumnRenamed("ts", "order_ts"), "cancelled_orders", parts=1)
    write(q_orders.select(*o_raw.columns, "quarantine_reason").unionByName(q_nolines), "orders", base=QUAR, parts=1)

# =========================================================================================== RATINGS
with Timer(ROOT, J, "ratings"):
    r = read_raw(spark, ROOT, "ratings")
    o_loc = o_raw.dropDuplicates(["order_id"]).select("order_id", F.col("location_id").alias("order_loc"))
    r = r.join(o_loc, "order_id", "left")
    inv_range = ~F.col("rating_value").between(1, 5) | F.col("rating_value").isNull()
    q_r1 = r.filter(inv_range).withColumn("quarantine_reason", F.lit("INVALID_RATING_VALUE"))
    r2 = r.filter(~inv_range)
    loc_bad = F.col("location_id").isNull() | ~F.col("location_id").isin(locs)
    fixable = loc_bad & F.col("order_loc").isin(locs)
    q_r2 = r2.filter(loc_bad & ~fixable).withColumn("quarantine_reason", F.lit("INVALID_LOCATION_UNREPAIRABLE"))
    r3 = r2.filter(~(loc_bad & ~fixable))
    n_fix = r3.filter(loc_bad).count()
    r3 = (r3.withColumn("location_id", F.when(loc_bad, F.col("order_loc")).otherwise(F.col("location_id")))
            .withColumn("has_purchase_link", F.col("order_id").isNotNull())
            .withColumn("is_restaurant_rating", F.col("item_id").isNull()).drop("order_loc"))
    q_r = q_r1.drop("order_loc").unionByName(q_r2.drop("order_loc"))
    quarantine_report(q_r, "ratings", {
        "INVALID_RATING_VALUE": ("R-01", "rating_value not in 1..5", "impossible score; cannot know the real one"),
        "INVALID_LOCATION_UNREPAIRABLE": ("R-02", "location invalid and no order to recover it from", "cannot be attributed to a restaurant")})
    decide("ratings", "R-03", "location_id invalid but order_id points to a valid order", "REPAIR", n_fix, "restaurant taken from the rated order")
    decide("ratings", "R-04", "order_id is NULL (no purchase)", "FLAG", r3.filter(~F.col("has_purchase_link")).count(),
           "kept; has_purchase_link = false. Used later by rating-anomaly detection (do NOT delete: these may be fake reviews)")
    write(q_r, "ratings", base=QUAR, parts=1)
    write(r3, "ratings", parts=1)

# =========================================================================================== WASTAGE
with Timer(ROOT, J, "wastage"):
    wst = read_raw(spark, ROOT, "wastage").join(menu.select("item_id", "portion_weight_g"), "item_id", "left")
    wst = wst.withColumn("quarantine_reason",
                         F.when(F.col("item_id").isNull(), "MISSING_ITEM_ID")
                          .when(F.col("location_id").isNull() | ~F.col("location_id").isin(locs), "INVALID_LOCATION"))
    q_w1 = wst.filter(F.col("quarantine_reason").isNotNull())
    w2 = wst.filter(F.col("quarantine_reason").isNull())
    u = F.lower(F.col("unit"))
    qty = (F.when(u == "kg", F.col("quantity_wasted") * 1000 / F.col("portion_weight_g"))
            .when(u == "g", F.col("quantity_wasted") / F.col("portion_weight_g"))
            .otherwise(F.col("quantity_wasted")))
    w2 = (w2.withColumn("qty_portions", F.round(qty)).withColumn("unit_changed", F.col("unit") != "portion")
            .withColumn("quarantine_reason", F.when((F.col("qty_portions") <= 0) | (F.col("qty_portions") > F.col("prep_quantity")) |
                                                   (F.col("qty_portions") > 1000), "IMPOSSIBLE_QUANTITY")))
    q_w2 = w2.filter(F.col("quarantine_reason").isNotNull())
    w3 = w2.filter(F.col("quarantine_reason").isNull())
    q_w = q_w1.select("wastage_id", "wastage_date", "location_id", "item_id", "unit", "quantity_wasted", "prep_quantity", "quarantine_reason") \
        .unionByName(q_w2.select("wastage_id", "wastage_date", "location_id", "item_id", "unit", "quantity_wasted", "prep_quantity", "quarantine_reason"))
    quarantine_report(q_w, "wastage", {
        "MISSING_ITEM_ID": ("W-01", "item_id is NULL", "cannot attribute waste to a dish"),
        "INVALID_LOCATION": ("W-01", "location_id not in restaurants", "cannot attribute waste to a restaurant"),
        "IMPOSSIBLE_QUANTITY": ("W-02", "quantity <= 0, larger than the prepared quantity, or > 1000 portions (after unit conversion)", "physically impossible; cannot be repaired")})
    clean_w = (w3.withColumn("quantity_wasted_original", F.col("quantity_wasted")).withColumn("unit_original", F.col("unit"))
                 .withColumn("quantity_wasted", F.col("qty_portions")).withColumn("unit", F.lit("portion"))
                 .drop("qty_portions", "quarantine_reason", "portion_weight_g"))
    decide("wastage", "W-03", "unit is kg / g / pcs / Portion / PORTION / portions (anything but exactly 'portion')", "REPAIR", w3.filter("unit_changed").count(),
           "all quantities converted to portions: kg x 1000 / portion_weight_g, g / portion_weight_g, pcs and spelling variants = portions")
    write(q_w, "wastage", base=QUAR, parts=1)
    write(clean_w.drop("unit_changed"), "wastage", parts=1)

# =========================================================================================== INVENTORY
with Timer(ROOT, J, "inventory"):
    inv = read_raw(spark, ROOT, "inventory").join(menu.select("item_id", "portion_weight_g"), "item_id", "left")
    loc_bad = F.col("location_id").isNull() | ~F.col("location_id").isin(locs)
    q_i = inv.filter(loc_bad).withColumn("quarantine_reason", F.lit("INVALID_LOCATION")) \
        .select("inventory_id", "week_start_date", "location_id", "item_id", "unit", "closing_stock", "quarantine_reason")
    quarantine_report(q_i, "inventory", {"INVALID_LOCATION": ("I-01", "location_id not in restaurants", "cannot attribute stock to a restaurant")})
    i2 = inv.filter(~loc_bad)
    kg = F.col("unit") == "kg"
    n_kg = i2.filter(kg).count()
    for col in ["opening_stock", "replenished_qty", "consumed_qty", "closing_stock"]:
        i2 = i2.withColumn(col, F.when(kg, F.round(F.col(col) * 1000 / F.col("portion_weight_g"))).otherwise(F.col(col)))
    i2 = i2.withColumn("unit", F.lit("portion"))
    decide("inventory", "I-02", "unit = kg", "REPAIR", n_kg, "converted to portions with portion_weight_g")
    neg = F.col("closing_stock") < 0
    n_neg = i2.filter(neg).count()
    i2 = i2.withColumn("closing_stock", F.when(neg, F.greatest(F.col("opening_stock") + F.col("replenished_qty") - F.col("consumed_qty"), F.lit(0.0)))
                                         .otherwise(F.col("closing_stock"))).drop("portion_weight_g")
    decide("inventory", "I-03", "closing_stock < 0", "REPAIR", n_neg, "recomputed: max(opening + replenished - consumed, 0)")
    write(q_i, "inventory", base=QUAR, parts=1)
    write(i2, "inventory", parts=2)

# =========================================================================================== reference tables copied as-is
with Timer(ROOT, J, "reference tables"):
    for t in ["menu_items", "menu_categories", "restaurants", "promotions", "promotion_items"]:
        write(read_raw(spark, ROOT, t), t, parts=1)

# =========================================================================================== reports
os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
with open(os.path.join(ROOT, "reports", "cleaning_decisions.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(decisions[0].keys())); w.writeheader(); w.writerows(decisions)
md = ["# Cleaning decisions\n",
      "Every rule applied by `spark_jobs/03_clean_data.py`, in execution order, with the number of rows it touched.\n",
      "Actions: **REMOVE** exact duplicate | **REPAIR** value derived from other data | **QUARANTINE** moved to `quarantine/` with a reason | "
      "**ROUTE** valid but not revenue (cancelled etc.) | **FLAG** kept, marked by a column.\n",
      "| Rule | Table | Condition | Action | Rows | Why |\n|---|---|---|---|---|---|"]
for d in decisions:
    md.append(f"| {d['rule_id']} | {d['table']} | {d['condition']} | {d['action']} | {d['rows']:,} | {d['why']} |")
md.append("\n## Row reconciliation\n")
rec = []
for name, raw_n, kept, extra in [
        ("orders (unique ids)", n_o, clean_orders.count(), f"cancelled {cancelled.count():,} + quarantined {q_orders.count() + n_nl:,}"),
        ("order_items (unique ids)", n_l, clean_lines.count(), f"cancelled {cancelled_lines.count():,} + quarantined {q_lines.count():,}")]:
    rec.append(f"- **{name}**: {raw_n:,} raw = {kept:,} clean + {extra}")
md += rec
open(os.path.join(ROOT, "reports", "cleaning_decisions.md"), "w").write("\n".join(md) + "\n")
print("\n".join(rec))
spark.stop()
