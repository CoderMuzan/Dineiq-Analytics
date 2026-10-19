"""
tests/test_phase2_cleaning.py - automated checks for Phase 2 (ingestion, data quality, cleaning).

Run after the three Spark jobs:      python tests/test_phase2_cleaning.py --root .
Works with plain python or pytest.   Writes reports/phase2_test_results.md.

Three kinds of tests
  A. INVARIANTS     the cleaned data obeys the rules (no duplicates, no negative quantities, totals add up ...)
  B. RECONCILIATION nothing disappears: raw rows = clean + cancelled + quarantined
  C. KNOWN ANSWERS  the data-quality report found what the generator planted (injection_log.json), and the
                    planted business cases (loss-maker, manual discounts, catering orders) survived cleaning
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=".")
args, _ = ap.parse_known_args()
ROOT = os.path.abspath(args.root)
RAW, CLEAN, QUAR, REP = (os.path.join(ROOT, d) for d in ("raw_data", "clean_data", "quarantine", "reports"))
results = []


def check(group, name, cond, detail=""):
    results.append((group, name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), f"[{group}] {name}  {detail}")


rd = lambda p: pd.read_parquet(p)
raw_csv = lambda folder: pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{RAW}/{folder}/*.csv"))], ignore_index=True)

menu = pd.read_csv(f"{RAW}/menu_items.csv"); locs = pd.read_csv(f"{RAW}/restaurants.csv")
orders = rd(f"{CLEAN}/orders"); lines = rd(f"{CLEAN}/order_items")
canc = rd(f"{CLEAN}/cancelled_orders"); canc_l = rd(f"{CLEAN}/cancelled_order_items")
q_o = rd(f"{QUAR}/orders"); q_l = rd(f"{QUAR}/order_items")
dq = pd.read_csv(f"{REP}/data_quality_report.csv")
inj = json.load(open(f"{RAW}/_ground_truth/injection_log.json"))
G = "A invariants"

# ---------------------------------------------------------------- A. invariants
check(G, "orders: order_id unique", orders.order_id.is_unique)
check(G, "orders: all COMPLETED", (orders.order_status == "COMPLETED").all())
check(G, "orders: no missing date, all inside the valid period",
      orders.order_ts.notna().all() and orders.order_ts.between("2025-10-01", "2026-10-01").all())
check(G, "orders: every restaurant id valid", orders.location_id.isin(locs.location_id).all())
check(G, "orders: payment_method never NULL", orders.payment_method.notna().all())
check(G, "orders: is_guest matches customer_id NULL", (orders.is_guest == orders.customer_id.isna()).all())
check(G, "order_items: order_line_id unique", lines.order_line_id.is_unique)
check(G, "order_items: quantity > 0", (lines.quantity > 0).all())
check(G, "order_items: unit_price > 0", (lines.unit_price > 0).all())
check(G, "order_items: item_id always a known menu item", lines.item_id.isin(menu.item_id).all())
check(G, "order_items: discount between 0 and gross", ((lines.discount_amount >= 0) & (lines.discount_amount <= lines.quantity * lines.unit_price + 0.01)).all())
check(G, "order_items: line_total = qty x price - discount",
      (lines.line_total - (lines.quantity * lines.unit_price - lines.discount_amount)).abs().max() < 0.02)
check(G, "order_items: every line belongs to a clean order", lines.order_id.isin(orders.order_id).all())
check(G, "orders: every clean order has at least one line", orders.order_id.isin(lines.order_id).all())
agg = lines.assign(g=lines.quantity * lines.unit_price).groupby("order_id").agg(g=("g", "sum"), d=("discount_amount", "sum"))
o2 = orders.set_index("order_id").join(agg)
check(G, "orders: subtotal = sum of line gross", (o2.subtotal - o2.g).abs().max() < 0.02)
check(G, "orders: discount_total = sum of line discounts", (o2.discount_total - o2.d).abs().max() < 0.02)
check(G, "orders: total = subtotal - discount + delivery fee", (o2.total_amount - (o2.subtotal - o2.discount_total + o2.delivery_fee)).abs().max() < 0.02)
nd = orders.assign(b=orders.order_id.map(lines.sort_values("item_id").groupby("order_id").apply(lambda g: ",".join(g.item_id + "x" + g.quantity.astype(str)), include_groups=False)))
nd = nd.sort_values("order_ts")
k = nd.groupby([nd.customer_id.fillna("G"), "location_id", "channel", "b", "total_amount"]).order_ts.diff().dt.total_seconds()
check(G, "no near-duplicate transactions left in clean orders", (k <= 200).sum() == 0, f"found {(k <= 200).sum()}")
w = rd(f"{CLEAN}/wastage"); inv = rd(f"{CLEAN}/inventory"); r = rd(f"{CLEAN}/ratings"); ph = rd(f"{CLEAN}/pricing_history")
check(G, "wastage: unit always 'portion' and 0 < qty <= prepared", (w.unit == "portion").all() and ((w.quantity_wasted > 0) & (w.quantity_wasted <= w.prep_quantity)).all())
check(G, "wastage: ids valid", w.location_id.isin(locs.location_id).all() and w.item_id.isin(menu.item_id).all())
check(G, "inventory: unit portion, stock >= 0, closing = max(open+repl-cons,0)",
      (inv.unit == "portion").all() and (inv.closing_stock >= 0).all() and
      ((inv.opening_stock + inv.replenished_qty - inv.consumed_qty).clip(lower=0) - inv.closing_stock).abs().max() < 1.01)
check(G, "ratings: values 1..5 and restaurant ids valid", r.rating_value.between(1, 5).all() and r.location_id.isin(locs.location_id).all())
check(G, "pricing_history: all prices positive", (ph.price > 0).all())
check(G, "quarantine tables carry a reason", q_o.quarantine_reason.notna().all() and q_l.quarantine_reason.notna().all())

# ---------------------------------------------------------------- B. reconciliation
G = "B reconciliation"
raw_o = raw_csv("orders"); raw_l = raw_csv("order_items")
check(G, "orders: raw unique ids = clean + cancelled + quarantined",
      raw_o.order_id.nunique() == len(orders) + len(canc) + len(q_o), f"{raw_o.order_id.nunique():,} = {len(orders):,} + {len(canc):,} + {len(q_o):,}")
check(G, "order_items: raw unique ids = clean + cancelled + quarantined",
      raw_l.order_line_id.nunique() == len(lines) + len(canc_l) + len(q_l), f"{raw_l.order_line_id.nunique():,} = {len(lines):,} + {len(canc_l):,} + {len(q_l):,}")
check(G, "no id is in two outputs", len(set(orders.order_id) & set(canc.order_id)) == 0 and len(set(orders.order_id) & set(q_o.order_id)) == 0)
raw_r = pd.read_csv(f"{RAW}/ratings.csv")
check(G, "ratings: raw = clean + quarantined", len(raw_r) == len(r) + len(rd(f"{QUAR}/ratings")))
raw_w = pd.read_csv(f"{RAW}/wastage.csv")
check(G, "wastage: raw = clean + quarantined", len(raw_w) == len(w) + len(rd(f"{QUAR}/wastage")))
raw_i = pd.read_csv(f"{RAW}/inventory.csv")
check(G, "inventory: raw = clean + quarantined", len(raw_i) == len(inv) + len(rd(f"{QUAR}/inventory")))

# ---------------------------------------------------------------- C. known answers
G = "C known answers"
f = dq.set_index(["table", "check"]).rows


def same(table, chk, key, lo=0, hi=0):
    """report must be within [planted-lo, planted+hi].
    hi > 0 for line-level dirt: the generator copies some dirty lines into duplicate rows AFTER counting them,
    so the report legitimately finds a few more (max ~3%).  lo > 0 only for near-duplicates, see below."""
    got, want = int(f[(table, chk)]), int(inj[key])
    check(G, f"DQ found planted '{key}'", want - lo <= got <= want + hi, f"report {got:,} vs planted {want:,}")


same("orders", "Duplicate orders", "orders.exact_duplicate_order_rows")
# a near-duplicate pair is missed when independent dirt hits ONE copy (e.g. original gets an invalid restaurant id): then the
# original is quarantined by its own rule and the copy is the only valid record -> no revenue is double counted
same("orders", "Duplicate transactions (near-duplicates)", "orders.near_duplicate_transactions", lo=5)
check(G, "DQ found planted invalid dates", int(f[("orders", "Invalid date (unparseable)")]) + int(f[("orders", "Invalid date (out of period)")]) + int(f[("orders", "Missing order date")]) == inj["orders.invalid_dates"])
same("orders", "Invalid restaurant id", "orders.invalid_location_id")
same("orders", "Missing restaurant id", "orders.missing_location_id")
same("order_items", "Duplicate order lines", "order_items.exact_duplicate_line_rows")
same("order_items", "Negative or zero quantity", "order_items.negative_or_zero_quantity")
same("order_items", "Invalid menu price", "order_items.invalid_unit_price", hi=int(inj["order_items.invalid_unit_price"]*0.03)+5)
same("order_items", "Extreme menu price", "order_items.extreme_unit_price", hi=int(inj["order_items.extreme_unit_price"]*0.03)+5)
same("order_items", "Missing menu id", "order_items.missing_item_id", hi=int(inj["order_items.missing_item_id"]*0.03)+5)
check(G, "DQ unknown item ids >= planted (copies of planted lines add a few)", int(f[("order_items", "Unknown menu id")]) >= inj["order_items.unknown_item_id"])
check(G, "DQ incorrect discounts >= planted (zero-price lines add a few)", int(f[("order_items", "Incorrect discount")]) >= inj["order_items.discount_exceeds_line_value"])
same("ratings", "Invalid ratings", "ratings.invalid_rating_value")
same("wastage", "Inconsistent units", "wastage.inconsistent_units")
same("wastage", "Impossible wastage quantities", "wastage.impossible_quantities")
same("inventory", "Negative stock", "inventory.negative_closing_stock")
same("inventory", "Inconsistent units", "inventory.inconsistent_units")
same("pricing_history", "Invalid menu prices", "pricing_history.invalid_price_rows")
same("customers", "Duplicate customers", "customers.duplicate_rows")

# business cases must survive cleaning
lines2 = lines.merge(orders[["order_id", "order_date", "promo_id", "location_id", "total_amount"]], on="order_id")
ph2 = ph.sort_values("effective_from")
lm = menu[menu.item_name.isin(["Double Cheeseburger", "Beef Shawarma Wrap"])].item_id
x = lines2[lines2.item_id.isin(lm)].copy()
x["od"] = pd.to_datetime(x.order_date)
x = pd.merge_asof(x.sort_values("od"), ph2.assign(e=pd.to_datetime(ph2.effective_from))[["item_id", "e", "unit_cost"]].sort_values("e"),
                  left_on="od", right_on="e", by="item_id")
check(G, "loss-making best-sellers are still loss-making after cleaning", (x.line_total.sum() - (x.quantity * x.unit_cost).sum()) < 0,
      f"profit {(x.line_total.sum() - (x.quantity * x.unit_cost).sum()):,.0f} NGN")
man = o2[(o2.promo_id.isna()) & (o2.subtotal > 0) & (o2.discount_total > 0.5 * o2.subtotal)]
scale = pd.read_csv(f"{RAW}/customers.csv").customer_id.nunique() / 55000
check(G, "manual-discount anomalies were NOT cleaned away", len(man) >= max(3, 0.7 * 150 * scale), f"{len(man)} orders with >50% discount and no promotion")
check(G, "catering anomalies survive: some orders above 500k NGN", (orders.total_amount > 500_000).sum() >= max(2, 0.3 * 60 * scale), f"{(orders.total_amount > 500_000).sum()} orders")
check(G, "ratings without a purchase are kept and flagged", (~r.has_purchase_link).sum() > 100)

# ---------------------------------------------------------------- report
ok = sum(1 for x in results if x[2])
md = ["# Phase 2 automated test results\n", f"**{ok} / {len(results)} checks passed**\n", "| Group | Check | Result | Detail |\n|---|---|---|---|"]
md += [f"| {g} | {n} | {'PASS' if c else 'FAIL'} | {d} |" for g, n, c, d in results]
open(f"{REP}/phase2_test_results.md", "w").write("\n".join(md) + "\n")
print(f"\n{ok}/{len(results)} passed")
sys.exit(0 if ok == len(results) else 1)
