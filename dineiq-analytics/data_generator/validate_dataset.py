#!/usr/bin/env python3
"""
validate_dataset.py - proves the generated dataset satisfies the SRS minimums and that the
planted "tricky cases" are really visible in the data.

This is a quick pandas sanity check (NOT your Spark data-quality step). Run it right after the
generator:        python validate_dataset.py --root ..
Output:           documentation/validation_report.md  +  raw_data/dataset_statistics.json
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="..")
args = ap.parse_args()
RAW = os.path.join(args.root, "raw_data")
rd = lambda name: pd.read_csv(os.path.join(RAW, name + ".csv"))
rd_parts = lambda folder: pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{RAW}/{folder}/*.csv"))], ignore_index=True)

menu, cats, locs, cust = rd("menu_items"), rd("menu_categories"), rd("restaurants"), rd("customers")
ph, promos, ratings, wastage, inv = rd("pricing_history"), rd("promotions"), rd("ratings"), rd("wastage"), rd("inventory")
orders, lines = rd_parts("orders"), rd_parts("order_items")
gt = lambda n: pd.read_csv(f"{RAW}/_ground_truth/{n}.csv")

out = []
P = out.append
ok = lambda c: "PASS" if c else "FAIL"

# ---------------------------------------------------------------- 1. SRS minimums
dates = pd.to_datetime(orders.order_datetime, errors="coerce")
valid_dates = dates[(dates >= "2025-01-01") & (dates <= "2026-12-31")]
months = valid_dates.dt.to_period("M").nunique()
stats = {
    "order_line_rows": len(lines), "unique_order_line_ids": int(lines.order_line_id.nunique()),
    "unique_orders": int(orders.order_id.nunique()), "unique_customers": int(cust.customer_id.nunique()),
    "menu_items": len(menu), "menu_categories": len(cats), "restaurants": len(locs),
    "months_of_history": int(months), "date_min": str(valid_dates.min().date()), "date_max": str(valid_dates.max().date()),
    "ratings": len(ratings), "wastage_records": len(wastage), "inventory_records": len(inv),
    "pricing_history_rows": len(ph), "promotions": len(promos),
}
P("# DineIQ dataset validation report\n")
P("## 1. SRS minimum requirements\n")
P("| Requirement | Required | Actual | Result |\n|---|---|---|---|")
req = [("Order-line records", 1_000_000, stats["order_line_rows"]), ("Unique orders", 100_000, stats["unique_orders"]),
       ("Customers", 50_000, stats["unique_customers"]), ("Menu items", 150, stats["menu_items"]),
       ("Menu categories", 10, stats["menu_categories"]), ("Restaurant locations", 20, stats["restaurants"]),
       ("Months of history", 12, stats["months_of_history"]), ("Rating records", 100_000, stats["ratings"]),
       ("Wastage records", 50_000, stats["wastage_records"]),
       ("Pricing records (multiple per item)", len(menu) + 1, stats["pricing_history_rows"]),
       ("Promotion campaigns (multiple)", 2, stats["promotions"])]
for name, need, got in req:
    P(f"| {name} | {need:,} | {got:,} | {ok(got >= need)} |")

# ---------------------------------------------------------------- 2. keys
P("\n## 2. Primary / foreign key health (raw data - problems here are PLANTED)\n")
P("| Check | Violations | Share |\n|---|---|---|")
def chk(name, bad, total):
    P(f"| {name} | {int(bad):,} | {bad / max(total, 1):.3%} |")
chk("orders.order_id duplicated", orders.order_id.duplicated().sum(), len(orders))
chk("order_items.order_line_id duplicated", lines.order_line_id.duplicated().sum(), len(lines))
chk("order_items.order_id not in orders", (~lines.order_id.isin(orders.order_id)).sum(), len(lines))
chk("order_items.item_id missing or unknown", (~lines.item_id.isin(menu.item_id)).sum(), len(lines))
chk("orders.location_id missing or unknown", (~orders.location_id.isin(locs.location_id)).sum(), len(orders))
chk("orders.customer_id null (guest orders + dirt)", orders.customer_id.isna().sum(), len(orders))
chk("orders.customer_id not in customers (non-null)", (~orders.customer_id.dropna().isin(cust.customer_id)).sum(), orders.customer_id.notna().sum())
chk("orders.promo_id not in promotions (non-null)", (~orders.promo_id.dropna().isin(promos.promo_id)).sum(), orders.promo_id.notna().sum())
chk("ratings.item_id not in menu (non-null)", (~ratings.item_id.dropna().isin(menu.item_id)).sum(), ratings.item_id.notna().sum())
chk("wastage.location_id unknown", (~wastage.location_id.isin(locs.location_id)).sum(), len(wastage))
chk("customers.customer_id duplicated", cust.customer_id.duplicated().sum(), len(cust))

# ---------------------------------------------------------------- 3. clean working frame (for planted-case checks only)
o = orders.drop_duplicates("order_id").copy()
o["dt"] = pd.to_datetime(o.order_datetime, errors="coerce")
o = o[(o.order_status == "COMPLETED") & o.dt.between("2025-10-01", "2026-09-30 23:59:59")]
l = lines.drop_duplicates("order_line_id")
l = l[(l.quantity > 0) & (l.unit_price > 0) & (l.unit_price < 200000) & l.item_id.isin(menu.item_id)]
l = l.merge(o[["order_id", "dt", "location_id", "channel", "promo_id", "customer_id"]], on="order_id")
l["date"] = l.dt.dt.normalize()
phc = ph[(ph.price > 0) & (ph.price < 1_000_000)].copy()
phc["eff"] = pd.to_datetime(phc.effective_from)
l = l.sort_values("date")
l = pd.merge_asof(l, phc.sort_values("eff")[["item_id", "eff", "unit_cost"]], left_on="date", right_on="eff",
                  by="item_id", direction="backward")
l = l.merge(menu[["item_id", "base_cost"]], on="item_id", how="left")
l["unit_cost"] = l.unit_cost.fillna(l.base_cost)      # price rows that were planted as invalid are skipped
l["cost"] = l.quantity * l.unit_cost
l["profit"] = l.line_total - l.cost
it = l.groupby("item_id").agg(units=("quantity", "sum"), revenue=("line_total", "sum"), profit=("profit", "sum")).reset_index()
it["margin"] = it.profit / it.revenue
it = it.merge(menu[["item_id", "item_name"]], on="item_id").merge(gt("items_truth")[["item_id", "archetype"]], on="item_id")
rt = ratings[ratings.rating_value.between(1, 5) & ratings.item_id.notna()].groupby("item_id").rating_value.mean().rename("avg_rating")
ws = wastage[(wastage.quantity_wasted > 0) & (wastage.quantity_wasted <= wastage.prep_quantity) & (wastage.unit == "portion")].groupby("item_id").quantity_wasted.sum().rename("wasted")
it = it.merge(rt, on="item_id", how="left").merge(ws, on="item_id", how="left")
it["waste_pct"] = it.wasted.fillna(0) / (it.units + it.wasted.fillna(0))

P("\n## 3. Planted menu cases (clean completed orders only)\n")
top = it.sort_values("units", ascending=False)
P("**Top 12 items by units sold**\n")
P("| Item | Planted type | Units | Margin | Avg rating | Waste % |\n|---|---|---|---|---|---|")
for _, r in top.head(12).iterrows():
    P(f"| {r.item_name} | {r.archetype} | {int(r.units):,} | {r.margin:.1%} | {r.avg_rating:.2f} | {r.waste_pct:.1%} |")
P("\n**Summary by planted archetype (mean over items)**\n")
P("| Archetype | Items | Avg units | Avg margin | Avg rating | Avg waste % |\n|---|---|---|---|---|---|")
for a, g in it.groupby("archetype"):
    P(f"| {a} | {len(g)} | {g.units.mean():,.0f} | {g.margin.mean():.1%} | {g.avg_rating.mean():.2f} | {g.waste_pct.mean():.1%} |")
lm = it[it.archetype == "LOSS_MAKER"]
loss_ok = bool((lm.profit < 0).all() and (lm.units.rank(ascending=False) < 40).all())
P(f"\nHigh-selling loss-making dishes ({', '.join(lm.item_name)}): profit < 0 and top-40 seller -> **{ok(loss_ok)}**")
hg = it[it.archetype == "HIDDEN_GEM"]
P(f"Hidden gems: avg margin {hg.margin.mean():.1%} vs overall {it.margin.mean():.1%}; avg units {hg.units.mean():,.0f} vs {it.units.mean():,.0f} -> **{ok(hg.margin.mean() > it.margin.mean() and hg.units.mean() < it.units.mean())}**")
wh = it[it.archetype == "WASTE_HEAVY"]
P(f"Waste-heavy popular dishes: waste {wh.waste_pct.mean():.1%} vs overall {it.waste_pct.mean():.1%} -> **{ok(wh.waste_pct.mean() > 1.8 * it.waste_pct.mean())}**")

# ---------------------------------------------------------------- 4. promotions
P("\n## 4. Promotion traps - daily profit during promo vs the 14 days before\n")
daily = l.groupby("date").agg(orders=("order_id", "nunique"), revenue=("line_total", "sum"), profit=("profit", "sum"))
P("| Promo | Planted truth | Orders/day | Profit/day | In-scope units/day | Margin before -> during |\n|---|---|---|---|---|---|")
pit = rd("promotion_items")
promo_scope = {pid: set(g.item_id) for pid, g in pit.groupby("promo_id") if len(g) < len(menu)}
pt = gt("promotions_truth").merge(promos.drop(columns="promo_name"), on="promo_id")
for _, r in pt.iterrows():
    if r.promo_id in ("P013", "P014", "P016", "P017", "P010"): continue
    s, e = pd.Timestamp(r.start_date), pd.Timestamp(r.end_date)
    dur = daily.loc[s:e]; pre = daily.loc[s - pd.Timedelta(days=14): s - pd.Timedelta(days=1)]
    if len(pre) == 0 or len(dur) == 0: continue
    sc = promo_scope.get(r.promo_id)
    if sc is None: scope_txt = "n/a"
    else:
        sl = l[l.item_id.isin(sc)].groupby("date").quantity.sum()
        scope_txt = f"{sl.reindex(dur.index).fillna(0).mean() / max(sl.reindex(pre.index).fillna(0).mean(), 1) - 1:+.0%}"
    P(f"| {r.promo_id} {r.promo_name} | {r.planted_truth} | {dur.orders.mean() / pre.orders.mean() - 1:+.0%} | "
      f"{dur.profit.mean() / pre.profit.mean() - 1:+.0%} | {scope_txt} | {pre.profit.sum() / pre.revenue.sum():.1%} -> {dur.profit.sum() / dur.revenue.sum():.1%} |")
wp = it  # wing wednesday wastage
st = wastage[(wastage.location_id.isin(locs.location_id))].merge(menu[["item_id", "category_id"]], on="item_id")
st["date"] = pd.to_datetime(st.wastage_date)
st = st[(st.category_id == "C01") & (st.unit == "portion") & (st.quantity_wasted > 0) & (st.quantity_wasted <= st.prep_quantity)]
wed = st[(st.date.dt.dayofweek == 2) & st.date.between("2026-06-03", "2026-08-26")].quantity_wasted.sum() / 12
oth = st[(st.date.dt.dayofweek == 1) & st.date.between("2026-06-03", "2026-08-26")].quantity_wasted.sum() / 12
P(f"\nP010 Wing Wednesday: starters wastage per Wednesday {wed:,.0f} vs per Tuesday {oth:,.0f} (x{wed / max(oth, 1):.1f}) -> **{ok(wed > 1.5 * oth)}**")

# ---------------------------------------------------------------- 5. price sensitivity
P("\n## 5. Price-sensitive vs low-sensitivity items (units change in the 30 days after the first price increase, relative to ALL items to remove seasonality)\n")
P("| Item | Type | Price change | Units/day change |\n|---|---|---|---|")
for nm, d0, kind in [("Chicken Shawarma Wrap", 100, "price sensitive"), ("Jollof Spaghetti", 100, "price sensitive"),
                     ("Malt Drink", 95, "price sensitive"), ("Grilled Salmon", 110, "low sensitivity"),
                     ("Beef Steak", 100, "low sensitivity"), ("Lamb Chops", 105, "low sensitivity")]:
    iid = menu.loc[menu.item_name == nm, "item_id"].iloc[0]
    day0 = pd.Timestamp("2025-10-01") + pd.Timedelta(days=d0)
    x = l[l.item_id == iid]
    b = x[x.date.between(day0 - pd.Timedelta(days=30), day0 - pd.Timedelta(days=1))].quantity.sum() / 30
    a = x[x.date.between(day0, day0 + pd.Timedelta(days=29))].quantity.sum() / 30
    tb = l[l.date.between(day0 - pd.Timedelta(days=30), day0 - pd.Timedelta(days=1))].quantity.sum()
    ta = l[l.date.between(day0, day0 + pd.Timedelta(days=29))].quantity.sum()
    pr = ph[ph.item_id == iid].sort_values("effective_from")
    P(f"| {nm} | {kind} | {pr.price.iloc[1] / pr.price.iloc[0] - 1:+.0%} | {(a / b) / (ta / tb) - 1:+.0%} |")

# ---------------------------------------------------------------- 6. location & customers & anomalies
P("\n## 6. Location differences, customers and anomalies\n")
sp = l[l.item_id == menu.loc[menu.item_name == "Pepper Soup Catfish", "item_id"].iloc[0]].groupby("location_id").quantity.sum()
P(f"Pepper Soup Catfish units: Port Harcourt (L19+L20) {sp.get('L19', 0) + sp.get('L20', 0):,} vs Lagos (L01..L15) {sp[[x for x in sp.index if x <= 'L15']].sum():,} (L19 per-location {sp.get('L19', 0):,}, L04 {sp.get('L04', 0):,})")
lr = o.groupby("location_id").size()
P(f"Orders per location range: min {lr.min():,} ({lr.idxmin()}) .. max {lr.max():,} ({lr.idxmax()}); new location L24 has {lr.get('L24', 0):,} orders, first on {o[o.location_id == 'L24'].dt.min().date()}")
l07 = o[(o.location_id == "L07") & o.dt.between("2026-02-03", "2026-02-09 23:59")]
P(f"L07 Ikoyi outage Feb 3-9: {len(l07)} orders in the window (normal ~{lr['L07'] / 365 * 7:.0f}/week)")
od = o.dt.dt.normalize().value_counts().sort_index()
P(f"L08 event day 2026-05-23 orders at L08: {len(o[(o.location_id == 'L08') & (o.dt.dt.date == pd.Timestamp('2026-05-23').date())])} (typical day ~{lr['L08'] / 365:.0f})")
cr = o.dropna(subset=["customer_id"]).groupby("customer_id").dt.agg(["min", "max", "count"])
tr = gt("customers_truth").set_index("customer_id").planted_segment
cr = cr.join(tr)
cr["recency_days"] = (pd.Timestamp("2026-09-30") - cr["max"]).dt.days
P("\n| Planted segment | Customers | Avg orders | Avg recency (days) |\n|---|---|---|---|")
for a, g in cr.groupby("planted_segment"):
    P(f"| {a} | {len(g):,} | {g['count'].mean():.1f} | {g.recency_days.mean():.0f} |")
big = o.merge(lines.drop_duplicates("order_line_id").groupby("order_id").line_total.sum().rename("v"), on="order_id")
P(f"\nOrder value: median {big.v.median():,.0f} NGN, 99.9th pct {big.v.quantile(0.999):,.0f}, max {big.v.max():,.0f} (catering anomalies)")
disc = big[(big.promo_id.isna())]
P(f"Orders with no promo but discount_total > 50% of subtotal: {int(((disc.discount_total > 0.5 * disc.subtotal) & (disc.subtotal > 0)).sum())}")
rt2 = ratings[ratings.rating_value.between(1, 5)].copy()
rt2["d"] = pd.to_datetime(rt2.rating_date)
P(f"Ratings with no order_id (inconsistent with purchases): {int(rt2.order_id.isna().sum())}")
pz = menu.loc[menu.item_name == "Suya Pizza", "item_id"].iloc[0]
sz = l[l.item_id == pz].groupby("date").quantity.sum()
P(f"Suya Pizza units/day: launch week {sz['2026-08-24':'2026-08-25'].mean():.0f}, viral week {sz['2026-08-26':'2026-09-01'].mean():.0f}, after {sz['2026-09-02':].mean():.0f}")
P("\nAverage basket: %.2f lines/order, %.2f units/order" % (len(l) / l.order_id.nunique(), l.quantity.sum() / l.order_id.nunique()))
chm = l.groupby("channel").agg(rev=("line_total", "sum"), orders=("order_id", "nunique"))
P("Channel share of orders: " + ", ".join(f"{k} {v:.0%}" for k, v in (chm.orders / chm.orders.sum()).items()))

open(os.path.join(args.root, "documentation", "validation_report.md"), "w").write("\n".join(out))
json.dump(stats, open(os.path.join(RAW, "dataset_statistics.json"), "w"), indent=2)
print("\n".join(out))
