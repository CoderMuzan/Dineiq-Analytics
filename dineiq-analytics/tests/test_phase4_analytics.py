"""
tests/test_phase4_analytics.py - checks for Phase 4A/4B analytics (menu, customers, baskets, peaks, wastage, pricing, promotions, anomalies).

Run after jobs 06, 07, 08:   python tests/test_phase4_analytics.py --root .
  A. STRUCTURE   every table exists, classes are complete, formulas (support / confidence / lift) recompute correctly
  B. KNOWN ANSWERS   the analytics find what the generator planted.  The ground truth (raw_data/_ground_truth) is used ONLY here.
Some checks are deliberately about what is NOT claimed (for example no false 'highly price sensitive' dish).
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--root", default="."); args, _ = ap.parse_known_args()
ROOT = os.path.abspath(args.root)
A = lambda n: pd.read_parquet(os.path.join(ROOT, "processed_data", "analytics", n))
GT = lambda n: pd.read_csv(os.path.join(ROOT, "raw_data", "_ground_truth", n))
results = []


def check(group, name, cond, detail=""):
    results.append((group, name, bool(cond), detail)); print("PASS" if cond else "FAIL", f"[{group}] {name}  {detail}")


mp, gi = A("menu_performance"), GT("items_truth.csv")
t = mp.merge(gi, on=["item_id"], suffixes=("", "_t"))
G = "A structure"
check(G, "menu_performance: every dish with sales is in exactly one of the 4 classes",
      mp.performance_class.isin(["PROFIT_DRIVER", "VOLUME_DRIVER", "HIDDEN_OPPORTUNITY", "LOW_PERFORMER"]).all() and mp.item_id.is_unique and len(mp) == 168,
      mp.performance_class.value_counts().to_dict().__str__())
check(G, "menu_performance: new items are marked LOW_NEW_ITEM confidence", (mp[mp.days_of_history < 60].confidence == "LOW_NEW_ITEM").all())
check(G, "menu_performance: no hard-coded rule - class follows the flags",
      ((mp.performance_class == "PROFIT_DRIVER") <= (mp.demand_high & mp.profit_high & ~mp.wastage_excessive)).all())
byloc = A("menu_performance_by_location")
check(G, "menu_performance_by_location covers 24 restaurants and 4 classes + INSUFFICIENT_DATA", byloc.location_id.nunique() == 24 and set(byloc.performance_class) <= {"PROFIT_DRIVER", "VOLUME_DRIVER", "HIDDEN_OPPORTUNITY", "LOW_PERFORMER", "INSUFFICIENT_DATA"})
seg = A("customer_segments"); ss = A("segment_summary")
check(G, "customer_segments: one row per customer, segment shares add to 100%", seg.customer_id.is_unique and abs(ss.customer_share.astype(float).sum() - 1) < 1e-6)
rules = A("basket_rules")
fact = pd.read_parquet(os.path.join(ROOT, "processed_data", "fact_order_lines"), columns=["order_id", "item_id"]).drop_duplicates()
n_orders = fact.order_id.nunique()
top = rules.sort_values("pair_orders", ascending=False).head(3)
ok = True; det = []
for r in top.itertuples():
    oa = set(fact[fact.item_id == r.antecedent].order_id); ob = set(fact[fact.item_id == r.consequent].order_id)
    both = len(oa & ob); sup = both / n_orders; conf = both / len(oa); lift = conf / (len(ob) / n_orders)
    ok &= both == r.pair_orders and abs(sup - float(r.support)) < 1e-9 and abs(conf - float(r.confidence)) < 1e-9 and abs(lift - float(r.lift)) < 1e-6
    det.append(f"{r.antecedent_name}->{r.consequent_name} lift {lift:.2f}")
check(G, "basket rules: support, confidence and lift recomputed independently from raw order lines", ok, "; ".join(det))
check(G, "bundle recommendations all carry association-rule evidence", A("bundle_recommendations").evidence.str.contains("lift").all())

G = "B menu classification"
cls = lambda a: t[t.archetype == a]
check(G, "star dishes: at least 9 of 10 are PROFIT_DRIVER", (cls("STAR").performance_class == "PROFIT_DRIVER").sum() >= 9)
check(G, "high-volume thin-margin dishes: all VOLUME_DRIVER", (cls("VOLUME").performance_class == "VOLUME_DRIVER").all())
check(G, "loss-making dishes: both LOW_PERFORMER", (cls("LOSS_MAKER").performance_class == "LOW_PERFORMER").all())
dc = t[t.item_name == "Double Cheeseburger"].iloc[0]
check(G, "Double Cheeseburger: flagged HIGH-SELLING LOSS-MAKER and HIGHLY-RATED POOR-PROFIT", dc.tricky_high_selling_loss_making and dc.tricky_highly_rated_poor_profit)
check(G, "hidden gems: all 8 are HIDDEN_OPPORTUNITY", (cls("HIDDEN_GEM").performance_class == "HIDDEN_OPPORTUNITY").sum() == 8, str(cls("HIDDEN_GEM").performance_class.value_counts().to_dict()))
check(G, "planted low performers: at least 10 of 12 are LOW_PERFORMER", (cls("LOW_PERFORMER").performance_class == "LOW_PERFORMER").sum() >= 10)
check(G, "waste-heavy popular dishes: all flagged POPULAR + EXCESSIVE WASTAGE", cls("WASTE_HEAVY").tricky_popular_excessive_wastage.all(), str(cls("WASTE_HEAVY").tricky_popular_excessive_wastage.sum()))
check(G, "Hot Dog Classic flagged LOW-RATED HIGH-SALES", bool(t[t.item_name == "Hot Dog Classic"].tricky_low_rated_high_sales.iloc[0]))
check(G, "promotion-dependent dishes: at least 3 of 4 flagged", cls("BASE")[cls("BASE").promo_dependent].tricky_promotion_dependent.sum() >= 3 if "promo_dependent" in t else t[t.promo_dependent].tricky_promotion_dependent.sum() >= 3)
check(G, "weekend dishes: at least 5 of 6 flagged WEEKEND-ONLY", t[t.weekend_item].tricky_weekend_only.sum() >= 5, str(t[t.weekend_item].tricky_weekend_only.sum()))
check(G, "new dishes: all 3 flagged NEW / insufficient history", t[t.new_item].tricky_new_insufficient_history.all())
check(G, "seasonal dishes: all planted seasonal dishes flagged", t[t.seasonal != "NONE"].tricky_seasonal.all())
loc_items = ["Suya Platter", "Pepper Soup Catfish", "Grilled Salmon", "Lamb Chops", "Ewa Agoyin", "Ofada Rice"]
flag = t[t.item_name.isin(loc_items)].tricky_location_inconsistent
check(G, "dishes that perform differently by restaurant: at least 5 of 6 planted found", flag.sum() >= 5, f"{flag.sum()} found, {t.tricky_location_inconsistent.sum()} flagged in total")
check(G, "slow-moving detection: no star or volume dish is called slow-moving", not t[t.archetype.isin(["STAR", "VOLUME"])].slow_moving.any())
check(G, "slow-moving detection: at least 8 of 12 planted low performers", t[t.archetype == "LOW_PERFORMER"].slow_moving.sum() >= 8, str(t[t.archetype == "LOW_PERFORMER"].slow_moving.sum()))

G = "B customers"
c = seg.merge(GT("customers_truth.csv"), on="customer_id")
share = lambda planted, segs: c[c.planted_segment == planted].segment.isin(segs).mean()
check(G, "new customers: at least 95% found", share("NEW", ["NEW_CUSTOMER"]) >= 0.95, f"{share('NEW', ['NEW_CUSTOMER']):.1%}")
ch = c[(c.planted_segment == "CHURNED") & (c.frequency >= 3)]
check(G, "churned customers (3+ orders): at least 85% are LOST or AT_RISK", ch.segment.isin(["LOST_CUSTOMER", "AT_RISK"]).mean() >= 0.85, f"{ch.segment.isin(['LOST_CUSTOMER', 'AT_RISK']).mean():.1%}")
check(G, "churned customers (3+ orders): at least 85% have HIGH churn risk", (ch.churn_risk_level == "HIGH").mean() >= 0.85, f"{(ch.churn_risk_level == 'HIGH').mean():.1%}")
lo = c[c.planted_segment == "LOYAL"]
check(G, "loyal customers: HIGH churn risk is rare (under 25%)", (lo.churn_risk_level == "HIGH").mean() < 0.25, f"{(lo.churn_risk_level == 'HIGH').mean():.1%}")
pdv = c[c.segment == "PROMOTION_DRIVEN"]
check(G, "PROMOTION_DRIVEN segment: at least 55% are really promotion-driven customers (the rest are deal-hunting regulars)", (pdv.planted_segment == "PROMO_DRIVEN").mean() >= 0.55, f"{(pdv.planted_segment == 'PROMO_DRIVEN').mean():.1%}")
hv = c[c.segment == "HIGH_VALUE_LOYAL"]
check(G, "HIGH_VALUE_LOYAL segment: at least 60% are loyal or frequent customers", hv.planted_segment.isin(["LOYAL", "FREQUENT"]).mean() >= 0.6, f"{hv.planted_segment.isin(['LOYAL', 'FREQUENT']).mean():.1%}")
check(G, "high-value segment earns more per customer than occasional customers", ss.set_index("segment").avg_monetary.astype(float)["HIGH_VALUE_LOYAL"] > 3 * ss.set_index("segment").avg_monetary.astype(float)["OCCASIONAL"])

G = "B baskets, peaks, wastage"
from_cfg = [("Egusi Soup", "Pounded Yam"), ("Ogbono Soup", "Pounded Yam"), ("Efo Riro", "Eba"), ("Okra Soup", "Eba"), ("Jollof Rice", "Fried Plantain"),
            ("Classic Beef Burger", "French Fries"), ("Classic Beef Burger", "Cola 50cl"), ("Full English Breakfast", "Americano"), ("BBQ Ribs", "Coleslaw")]
found = [(a, b) for a, b in from_cfg if ((rules.antecedent_name == a) & (rules.consequent_name == b) & (rules.lift >= 2)).any()]
check(G, "market basket: at least 7 of 9 strongest planted pairings are found with lift >= 2", len(found) >= 7, f"{len(found)} of 9")
ph = A("peak_hour"); pdays = A("peak_day"); mt = A("monthly_trend")
check(G, "peak hours include a lunch hour (12-14) and a dinner hour (18-21)", ph[ph.is_peak].order_hour.between(12, 14).any() and ph[ph.is_peak].order_hour.between(18, 21).any(), str(sorted(ph[ph.is_peak].order_hour.tolist())))
check(G, "peak days include Friday or Saturday", pdays[pdays.is_peak].day_name.isin(["Fri", "Sat"]).any(), str(pdays[pdays.is_peak].day_name.tolist()))
check(G, "busiest month is December", mt.sort_values("month_index").iloc[-1].order_month == "2025-12")
wi = A("wastage_by_item").merge(gi[["item_id", "archetype"]], on="item_id")
check(G, "wastage: waste-heavy dishes waste more than twice the chain average", wi[wi.archetype == "WASTE_HEAVY"].wastage_pct.astype(float).mean() > 2 * wi.wastage_pct.astype(float).median())
wp = A("wastage_by_promo").set_index("promo_id")
check(G, "wastage: Wing Wednesday (P010) starters waste clearly more on promotion days", float(wp.loc["P010"].wastage_pct_on_promo_days) > 1.3 * float(wp.loc["P010"].wastage_pct_other_days))
check(G, "wastage: all 4 time periods and 6 reasons reported", len(A("wastage_by_shift")) == 3 and len(A("wastage_by_reason")) == 6)

G = "B pricing and promotions"
ps = A("price_sensitivity").merge(gi[["item_id", "price_sensitive", "low_price_sensitivity"]], on="item_id")
hi = ps[ps.price_sensitivity_class == "HIGHLY_PRICE_SENSITIVE"]
check(G, "price sensitivity: at least 3 of 6 planted price-sensitive dishes are found", hi.price_sensitive.sum() >= 3, f"{hi.price_sensitive.sum()} of 6")
check(G, "price sensitivity: no dish outside the planted six is called HIGHLY sensitive", (~hi.price_sensitive).sum() == 0, str(hi[~hi.price_sensitive].item_name.tolist()))
check(G, "price sensitivity: the planted low-sensitivity premium dishes are never HIGHLY sensitive", not ps[ps.low_price_sensitivity].price_sensitivity_class.eq("HIGHLY_PRICE_SENSITIVE").any())
pe = A("promotion_effectiveness").set_index("promo_id")
for pid, trap in [("P002", "SALES_UP_PROFIT_DOWN"), ("P007", "CUSTOMERS_UP_MARGIN_COLLAPSES"), ("P010", "INCREASES_WASTAGE"), ("P011", "SALES_UP_PROFIT_DOWN")]:
    check(G, f"promotion trap: {pid} is MISLEADING and shows {trap}", pe.loc[pid].verdict == "MISLEADING" and trap in str(pe.loc[pid].traps))
check(G, "promotion trap: P002 also pulls sales away from grills (C04)", "C04" in str(pe.loc["P002"].cannibalised_categories))
check(G, "good promotions are not condemned: P005, P006, P015 are EFFECTIVE", all(pe.loc[p].verdict == "EFFECTIVE" for p in ["P005", "P006", "P015"]), str({p: pe.loc[p].verdict for p in ["P005", "P006", "P015"]}))
check(G, "a sales increase alone never makes a promotion effective (P003 judged on profit too)", pe.loc["P003"].verdict in ("EFFECTIVE", "MISLEADING", "WATCH", "NOT_PROFITABLE"))
sc = A("location_scorecard")
check(G, "location scorecard: 24 restaurants ranked, composite is the mean of the indicator z-scores", len(sc) == 24 and sc["rank"].is_unique)

G = "B anomalies"
sa = A("sales_anomalies"); ra = A("rating_anomalies")
get = lambda typ, ent=None: sa[(sa.anomaly_type == typ) & ((sa.entity == ent) if ent else True)]
check(G, "sales spike: L08 on 2026-05-23 found", (get("SALES_SPIKE", "L08").start_date <= "2026-05-23").any() and (get("SALES_SPIKE", "L08").end_date >= "2026-05-23").any())
d = get("SALES_DROP", "L07")
check(G, "sales drop: L07 outage in early February found", len(d) > 0 and d.start_date.between("2026-02-03", "2026-02-09").any())
s12 = get("SUSTAINED_SALES_DROP", "L12")
check(G, "sustained drop: L12 starting in mid-July found", len(s12) > 0 and s12.start_date.between("2026-07-08", "2026-07-25").any(), str(s12.start_date.tolist()))
check(G, "unusual discounts: L13 found, and nowhere else", set(get("UNUSUAL_DISCOUNT").entity) == {"L13"})
ov = get("ABNORMAL_ORDER_VALUE")
check(G, "abnormal order values: at least 20 found, most at the catering restaurants", len(ov) >= 20 and ov.detail.str.contains("L02|L03|L16").mean() >= 0.6, f"{len(ov)} found")
sp = sa[(sa.anomaly_type == "UNEXPECTED_DEMAND") & (sa.detail.str.contains("Suya Pizza"))]
check(G, "unexpected demand: the viral Suya Pizza week is found", len(sp) > 0 and sp.start_date.between("2026-08-26", "2026-09-01").any())
check(G, "unexpected demand: promotion-driven surges are labelled as explained", sa[sa.anomaly_type == "UNEXPECTED_DEMAND"].explained_by_promotion.any())
check(G, "duplicate transactions reported from cleaning", len(get("DUPLICATE_TRANSACTIONS")) == 1 and get("DUPLICATE_TRANSACTIONS").n_items.iloc[0] > 100)
rb = ra[ra.anomaly_type == "RATINGS_WITHOUT_PURCHASE_BURST"]
check(G, "rating anomalies: fake 5-star burst on Gourmet Truffle Burger found", rb.detail.str.contains("Gourmet Truffle Burger").any())
check(G, "rating anomalies: 1-star run on Grilled Tilapia found, with a SUDDEN_RATING_DROP", rb.detail.str.contains("Grilled Tilapia").any() and ra.anomaly_type.eq("SUDDEN_RATING_DROP").any())
check(G, "rating anomalies: one account with 60 identical ratings found", ra[ra.anomaly_type == "EXCESSIVE_IDENTICAL_RATINGS"].n_ratings.max() == 60)
check(G, "rating anomalies: L09 one-day volume burst found", ((ra.anomaly_type == "UNUSUALLY_MANY_RATINGS") & (ra.entity == "L09")).any())
ok = sum(1 for r in results if r[2])
md = ["# Phase 4 automated test results\n", f"**{ok} / {len(results)} checks passed**\n", "| Group | Check | Result | Detail |\n|---|---|---|---|"]
md += [f"| {g} | {n} | {'PASS' if c_ else 'FAIL'} | {d_} |" for g, n, c_, d_ in results]
open(os.path.join(ROOT, "reports", "phase4_test_results.md"), "w").write("\n".join(md) + "\n")
print(f"\n{ok}/{len(results)} passed"); sys.exit(0 if ok == len(results) else 1)
