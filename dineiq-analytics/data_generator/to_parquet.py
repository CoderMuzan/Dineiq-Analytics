#!/usr/bin/env python3
"""
to_parquet.py - converts the raw CSV files to Parquet (SRS Step 2: "at least one large dataset in Parquet").

  * Big tables (orders, order_items) are converted PART BY PART, so they stay as many files
    inside one folder.  Spark reads the folder as one table  ->  demonstrates multiple-file ingestion.
  * orders is ALSO written partitioned by month (parquet_data/orders_by_month/order_month=2026-01/...)
    to demonstrate partition handling.  Rows with an invalid date go to order_month=unknown.
  * Column types are forced explicitly so every part file has an identical schema.

Run:  python to_parquet.py --root ..
"""
import argparse
import glob
import os
import shutil

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="..")
args = ap.parse_args()
RAW, OUT = os.path.join(args.root, "raw_data"), os.path.join(args.root, "parquet_data")
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)

S, F, I = "string", "float64", "Int64"
SCHEMAS = {
    "orders": dict(order_id=S, customer_id=S, location_id=S, order_datetime=S, channel=S, delivery_platform=S,
                   order_status=S, promo_id=S, party_size=F, subtotal=F, discount_total=F, delivery_fee=F,
                   platform_fee=F, total_amount=F, payment_method=S),
    "order_items": dict(order_line_id=S, order_id=S, item_id=S, quantity=I, unit_price=F, discount_amount=F, line_total=F),
    "customers": dict(customer_id=S, signup_date=S, age_band=S, home_location_id=S, city=S, preferred_channel=S,
                      acquisition_source=S, marketing_opt_in="boolean", loyalty_member="boolean"),
    "menu_items": dict(item_id=S, item_name=S, category_id=S, description=S, base_price=F, base_cost=F,
                       portion_weight_g=I, prep_time_min=I, is_vegetarian="boolean", launch_date=S,
                       available_from=S, available_to=S, is_active="boolean", season_tag=S),
    "menu_categories": dict(category_id=S, category_name=S, perishability=S, meal_period=S),
    "restaurants": dict(location_id=S, restaurant_name=S, area=S, city=S, state=S, region=S, opening_date=S,
                        seating_capacity=I, size_tier=S),
    "pricing_history": dict(price_id=S, item_id=S, effective_from=S, effective_to=S, price=F, unit_cost=F, change_reason=S),
    "promotions": dict(promo_id=S, promo_name=S, promo_type=S, discount_pct=F, start_date=S, end_date=S,
                       applicable_days=S, channel_restriction=S, target_segment=S, promo_code=S),
    "promotion_items": dict(promo_id=S, item_id=S),
    "ratings": dict(rating_id=S, order_id=S, customer_id=S, item_id=S, location_id=S, rating_value=I, rating_date=S, source=S),
    "wastage": dict(wastage_id=S, wastage_date=S, location_id=S, item_id=S, shift=S, prep_quantity=F,
                    quantity_wasted=F, unit=S, wastage_cost=F, reason=S),
    "inventory": dict(inventory_id=S, week_start_date=S, location_id=S, item_id=S, opening_stock=F, replenished_qty=F,
                      consumed_qty=F, closing_stock=F, reorder_level=F, stockout_flag="boolean", unit=S),
}
rows = {}
for folder in ("orders", "order_items"):                       # chunked tables -> one parquet part per CSV part
    os.makedirs(f"{OUT}/{folder}")
    n = 0
    for f in sorted(glob.glob(f"{RAW}/{folder}/*.csv")):
        df = pd.read_csv(f, dtype=SCHEMAS[folder])
        df.to_parquet(f"{OUT}/{folder}/{os.path.basename(f).replace('.csv', '.parquet')}", index=False, compression="snappy")
        n += len(df)
    rows[folder] = n
for name in [k for k in SCHEMAS if k not in ("orders", "order_items")]:   # small tables -> single file
    df = pd.read_csv(f"{RAW}/{name}.csv", dtype=SCHEMAS[name])
    df.to_parquet(f"{OUT}/{name}.parquet", index=False, compression="snappy")
    rows[name] = len(df)
# partitioned copy of orders (by month)
parts = pd.concat([pd.read_csv(f, dtype=SCHEMAS["orders"]) for f in sorted(glob.glob(f"{RAW}/orders/*.csv"))], ignore_index=True)
dt = pd.to_datetime(parts.order_datetime, errors="coerce")
parts["order_month"] = dt.dt.strftime("%Y-%m").where(dt.between("2025-01-01", "2026-12-31"), "unknown")
parts.to_parquet(f"{OUT}/orders_by_month", partition_cols=["order_month"], index=False, compression="snappy")
for k, v in rows.items(): print(f"{k:16s} {v:>10,} rows")
size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs) / 1e6
print(f"parquet_data total {size:.1f} MB")
