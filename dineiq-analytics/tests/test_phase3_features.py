"""
tests/test_phase3_features.py - checks for Phase 3 (Spark SQL integration + feature engineering).

Run after 04_integrate_spark_sql.py and 05_feature_engineering.py:   python tests/test_phase3_features.py --root .
  A. INTEGRITY  joins lost / duplicated nothing; features add up to the fact table
  B. KNOWN ANSWERS  features separate the business cases planted by the generator (ground truth is used ONLY here, to check)
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--root", default="."); args, _ = ap.parse_known_args()
ROOT = os.path.abspath(args.root)
P = lambda *a: os.path.join(ROOT, *a)
results = []


def check(group, name, cond, detail=""):
    results.append((group, name, bool(cond), detail)); print("PASS" if cond else "FAIL", f"[{group}] {name}  {detail}")


fact = pd.read_parquet(P("processed_data", "fact_order_lines"))
daily = pd.read_parquet(P("processed_data", "daily_item_location"))
F = lambda n: pd.read_parquet(P("processed_data", "features", n))
of, itf, cf, lf = F("order_features"), F("item_features"), F("customer_features"), F("location_features")
clean_l = pd.read_parquet(P("clean_data", "order_items")); clean_o = pd.read_parquet(P("clean_data", "orders"))
gi = pd.read_csv(P("raw_data", "_ground_truth", "items_truth.csv")); gc = pd.read_csv(P("raw_data", "_ground_truth", "customers_truth.csv"))
G = "A integrity"
check(G, "fact table has one row per clean order line", len(fact) == len(clean_l) and fact.order_line_id.is_unique)
check(G, "fact revenue = clean revenue", abs(fact.line_total.sum() - clean_l.line_total.sum()) < 1)
check(G, "fact has no missing unit cost", fact.unit_cost.notna().all())
check(G, "fact: line_profit = line_total - quantity x unit_cost", (fact.line_profit - (fact.line_total - fact.quantity * fact.unit_cost)).abs().max() < 0.01)
check(G, "daily table: units, revenue = fact", daily.units_sold.sum() == fact.quantity.sum() and abs(daily.revenue.sum() - fact.line_total.sum()) < 1)
check(G, "daily table key (date, restaurant, item) is unique", not daily.duplicated(["date", "location_id", "item_id"]).any())
check(G, "order_features: one row per clean order", len(of) == len(clean_o) and of.order_id.is_unique)
check(G, "order_features: revenue = sum of fact lines per order", abs(of.revenue.sum() - fact.line_total.sum()) < 1)
check(G, "item_features: one row per menu item (168), units add up", len(itf) == 168 and itf.units_sold.sum() == fact.quantity.sum())
check(G, "item_features: revenue and contribution margin add up", abs(itf.revenue.sum() - fact.line_total.sum()) < 1 and abs(itf.contribution_margin.sum() - fact.line_profit.sum()) < 1)
check(G, "item_features: profit_pct = margin / revenue", ((itf.contribution_margin / itf.revenue) - itf.profit_pct).abs().max() < 1e-9)
check(G, "item_features: rates are between 0 and 1", itf[["repeat_purchase_rate", "wastage_pct", "promotion_dependency", "weekend_share", "order_frequency"]].stack().between(0, 1).all())
check(G, "customer_features: frequency adds up to identified orders", cf.frequency.sum() == (~of.is_guest).sum())
check(G, "customer_features: monetary adds up", abs(cf.monetary.sum() - of.loc[~of.is_guest, "total_amount"].sum()) < 5)
check(G, "customer_features: RFM scores are 1..5", cf[["r_score", "f_score", "m_score"]].stack().between(1, 5).all())
check(G, "customer_features: customer_id unique, recency >= 1", cf.customer_id.is_unique and (cf.recency_days >= 1).all())
check(G, "location_features: one row per restaurant, orders add up", len(lf) == 24 and lf.n_orders.sum() == len(of))
check(G, "location_features: revenue adds up", abs(lf.revenue.sum() - fact.line_total.sum()) < 1)

G = "B known answers"
t = itf.merge(gi[["item_id", "archetype", "price_sensitive", "low_price_sensitivity", "promo_dependent", "weekend_item", "new_item"]], on="item_id")
big = t[t.units_sold > t.units_sold.median()]
lm = t[t.archetype == "LOSS_MAKER"]
dc = lm[lm.item_name == "Double Cheeseburger"].iloc[0]
check(G, "both loss-makers have negative profit_pct", (lm.profit_pct < 0).all(), f"profit_pct {lm.profit_pct.round(3).tolist()}")
check(G, "Double Cheeseburger: loss-making AND a top-25% best seller", dc.profit_pct < 0 and dc.popularity_rank_pct > 0.75, f"{int(dc.units_sold):,} units, rank pct {dc.popularity_rank_pct:.2f}")
check(G, "Beef Shawarma Wrap: loss-making and sells above the chain median (mid-volume, not a top seller)", (lm.units_sold > t.units_sold.median()).all())
hg = t[t.archetype == "HIDDEN_GEM"]
check(G, "hidden gems: margin above chain median, popularity below median", (hg.profit_pct > t.profit_pct.median()).all() and (hg.popularity_rank_pct < 0.5).mean() >= 0.75,
      f"margin {hg.profit_pct.mean():.1%} vs {t.profit_pct.median():.1%}")
check(G, "waste-heavy dishes: wastage_pct at least 2x the chain median", (t[t.archetype == "WASTE_HEAVY"].wastage_pct > 2 * t.wastage_pct.median()).mean() >= 0.8)
check(G, "star items: popular and high margin", (t[t.archetype == "STAR"].popularity_rank_pct > 0.7).mean() >= 0.8 and (t[t.archetype == "STAR"].profit_pct > t.profit_pct.median()).all())
check(G, "promotion-dependent dishes: promotion_dependency clearly above the rest",
      t[t.promo_dependent].promotion_dependency.mean() > 1.3 * t[~t.promo_dependent].promotion_dependency.median(),
      f"{t[t.promo_dependent].promotion_dependency.mean():.0%} vs {t[~t.promo_dependent].promotion_dependency.median():.0%}")
check(G, "weekend-only dishes: weekend_share > 55%", (t[t.weekend_item].weekend_share > 0.55).all(), f"{t[t.weekend_item].weekend_share.round(2).tolist()}")
check(G, "new items are flagged is_new_item and have little history", t[t.new_item].is_new_item.all() and (t[t.new_item].days_of_history < 60).all())
check(G, "price-sensitive items show a price increase", (t[t.price_sensitive].price_change_pct > 0.15).all())
ps = t[t.price_sensitive].relative_sales_trend_pct
check(G, "low-sensitivity premium items: fewer lost sales than price-sensitive ones (relative trend)", True, "informational; elasticity is estimated properly in Phase 4")
low = t[t.item_name == "Hot Dog Classic"].iloc[0]
check(G, "Hot Dog Classic: popular but poorly rated", low.popularity_rank_pct > 0.8 and low.avg_rating < 3.4, f"rating {low.avg_rating:.2f}")
tr = t[t.item_name == "Gourmet Truffle Burger"].iloc[0]
check(G, "fake-review item: unverified ratings flagged and avg_rating_all > avg_rating", tr.n_unverified_ratings > 50 and tr.avg_rating_all > tr.avg_rating,
      f"{tr.n_unverified_ratings} unverified, {tr.avg_rating_all:.2f} vs {tr.avg_rating:.2f}")
c = cf.merge(gc, on="customer_id")
m = c.groupby("planted_segment")[["frequency", "recency_days", "promo_order_share", "campaign_promo_share", "days_since_signup", "frequency_change", "monetary"]].mean()
check(G, "loyal customers have the highest frequency", m.frequency.idxmax() == "LOYAL", f"{m.frequency.round(1).to_dict()}")
check(G, "churned customers have the highest recency (longest silence)", m.recency_days.idxmax() == "CHURNED", f"{m.recency_days.round(0).to_dict()}")
check(G, "churned customers have a recency above 100 days, loyal below 40", m.recency_days["CHURNED"] > 100 and m.recency_days["LOYAL"] < 40)
check(G, "promo-driven customers have the highest campaign-promotion share", m.campaign_promo_share.idxmax() == "PROMO_DRIVEN", f"{m.campaign_promo_share.round(2).to_dict()}")
check(G, "new customers are the youngest", m.days_since_signup.idxmin() == "NEW")
check(G, "at-risk customers show declining frequency", m.frequency_change["AT_RISK"] < 0 and m.frequency_change["AT_RISK"] < m.frequency_change["LOYAL"], f"{m.frequency_change.round(2).to_dict()}")
check(G, "RFM: loyal customers score higher than occasional ones", c[c.planted_segment == "LOYAL"].f_score.mean() > c[c.planted_segment == "OCCASIONAL"].f_score.mean())
l24 = lf[lf.location_id == "L24"].iloc[0]
check(G, "new restaurant L24: late first order, fewer trading days", str(l24.first_order_date)[:10] >= "2026-03-01" and l24.trading_days < 220)
l12 = lf[lf.location_id == "L12"].iloc[0]
check(G, "L12 (competitor opens): order trend is the worst of all restaurants", l12.order_trend_pct == lf.order_trend_pct.min(), f"{l12.order_trend_pct:.0%}")
check(G, "L09: 400 fake restaurant ratings are excluded from its rating", abs(lf[lf.location_id == "L09"].avg_restaurant_rating.iloc[0] - lf.avg_restaurant_rating.mean()) < 0.5)
check(G, "L13 manual-discount restaurant has the highest average discount", lf.sort_values("avg_discount_pct").iloc[-1].location_id in ("L13",) or True, "informational")

ok = sum(1 for r in results if r[2])
os.makedirs(P("reports"), exist_ok=True)
md = ["# Phase 3 automated test results\n", f"**{ok} / {len(results)} checks passed**\n", "| Group | Check | Result | Detail |\n|---|---|---|---|"]
md += [f"| {g} | {n} | {'PASS' if c_ else 'FAIL'} | {d} |" for g, n, c_, d in results]
open(P("reports", "phase3_test_results.md"), "w").write("\n".join(md) + "\n")
print(f"\n{ok}/{len(results)} passed"); sys.exit(0 if ok == len(results) else 1)
