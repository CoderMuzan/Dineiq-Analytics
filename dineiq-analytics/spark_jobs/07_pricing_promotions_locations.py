"""
07_pricing_promotions_locations.py - Phase 4B (SRS Steps 25-28 and 33)

Spark aggregates the big tables into SMALL daily / weekly summaries; the statistics on those summaries are done in pandas.
  * Price intelligence and price sensitivity  (Steps 25, 26)   elasticity from weekly data + before/after price-change events
  * Promotion effectiveness and trap detection (Steps 27, 28)  every promotion vs a matched baseline, post-promotion dip, cannibalisation
  * Location scorecard                          (Step 33)       standardised indicators, composite score, "investigate" flags

Writes processed_data/analytics/<table>/ (Parquet) and reports/tables/<table>.csv, and reports/phase4b_pricing_promotions_locations.md.

Run:  python 07_pricing_promotions_locations.py --root ..
"""
import os

import numpy as np
import pandas as pd

import spark_common as S
from spark_common import Timer, get_spark, parse_args, register_all_views, run_sql_file

args = parse_args("DineIQ pricing, promotions, locations")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-07-pricing-promos", args.driver_memory)
J = "07_pricing_promos"
register_all_views(spark, ROOT)
run_sql_file(spark, ROOT, "01_lookup_tables.sql")
OUT = os.path.join(ROOT, "processed_data", "analytics")
CSV = os.path.join(ROOT, "reports", "tables")
os.makedirs(CSV, exist_ok=True)
D0, D1 = pd.Timestamp(S.VALID_DATE_MIN), pd.Timestamp(S.VALID_DATE_MAX)
md = ["# Phase 4B - pricing, promotions and locations (generated from the data)\n"]


def save(df, name):
    path = os.path.join(OUT, name)
    os.makedirs(path, exist_ok=True)
    df.to_parquet(os.path.join(path, "part-0.parquet"), index=False)
    df.to_csv(os.path.join(CSV, name + ".csv"), index=False)


def pct(x, d=0):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.{d}%}"


# =============================================================================== PRICE SENSITIVITY
with Timer(ROOT, J, "price sensitivity"):
    wk = "CAST(floor(datediff(order_date, to_date('%s')) / 7) AS INT)" % S.VALID_DATE_MIN
    units_w = spark.sql(f"SELECT item_id, {wk} AS wk, SUM(quantity) AS units FROM fact_order_lines GROUP BY item_id, {wk}").toPandas()
    price_w = spark.sql(f"SELECT item_id, {wk} AS wk, AVG(list_price) AS price FROM cost_day GROUP BY item_id, {wk}").toPandas()
    items = spark.table("item_features").select("item_id", "item_name", "category_name", "units_sold", "profit_pct", "avg_rating",
                                                "repeat_purchase_rate", "promotion_dependency", "avg_discount_pct", "last_list_price",
                                                "price_change_pct", "n_price_changes", "contribution_margin", "revenue").toPandas()
    for c in items.columns[3:]: items[c] = pd.to_numeric(items[c], errors="coerce")
    n_weeks = (D1 - D0).days // 7
    price_w = price_w[price_w.wk < n_weeks]
    units_w = units_w[units_w.wk < n_weeks]
    first = price_w.sort_values("wk").groupby("item_id").price.first().rename("p0")
    price_w = price_w.join(first, on="item_id")
    price_w["rel"] = price_w.price / price_w.p0
    index_w = price_w.groupby("wk").rel.mean().rename("idx")                       # chain price index: removes inflation shared by all items
    price_w = price_w.join(index_w, on="wk")
    price_w["x"] = np.log(price_w.rel / price_w.idx)
    chain_w = units_w.groupby("wk").units.sum().rename("chain_units")
    d = units_w.join(chain_w, on="wk").merge(price_w[["item_id", "wk", "x"]], on=["item_id", "wk"])
    d = d[d.units >= 5]
    # weeks in which the dish was part of a running discount promotion are removed: a promotion moves demand for reasons other than list price
    pr_all = spark.table("promotions").toPandas(); pi_all = spark.table("promotion_items").toPandas()
    excl = set()
    for r in pr_all.itertuples():
        if r.discount_pct <= 0 or r.promo_type in ("NEW_CUSTOMER", "LOYALTY"): continue
        w0 = (pd.Timestamp(r.start_date) - D0).days // 7; w1 = (pd.Timestamp(r.end_date) - D0).days // 7
        scope = set(pi_all[pi_all.promo_id == r.promo_id].item_id)
        for it_ in scope:
            for w_ in range(w0, w1 + 1): excl.add((it_, w_))
    d = d[[(a, b) not in excl for a, b in zip(d.item_id, d.wk)]]
    seasonal_ids = set(spark.table("item_features").filter("season_tag <> 'NONE'").select("item_id").toPandas().item_id)
    d["y"] = np.log(d.units / d.chain_units)
    rows = []
    for item_id, g in d.groupby("item_id"):
        if len(g) < 20 or g.x.std() < 0.03:
            rows.append(dict(item_id=item_id, n_weeks=len(g), price_variation_sd=g.x.std() if len(g) > 1 else np.nan,
                             elasticity=np.nan, std_error=np.nan, r_squared=np.nan)); continue
        slope, icpt = np.polyfit(g.x, g.y, 1)
        resid = g.y - (slope * g.x + icpt)
        se = np.sqrt((resid ** 2).sum() / (len(g) - 2) / ((g.x - g.x.mean()) ** 2).sum())
        r2 = np.corrcoef(g.x, g.y)[0, 1] ** 2
        rows.append(dict(item_id=item_id, n_weeks=len(g), price_variation_sd=g.x.std(), elasticity=slope, std_error=se, r_squared=r2))
    el = pd.DataFrame(rows)

    def classify(r):
        if np.isnan(r.elasticity): return "INSUFFICIENT_PRICE_VARIATION"
        if r.item_id in seasonal_ids: return "INSUFFICIENT_EVIDENCE"        # seasonal demand swings are mixed up with price moves in one year of data
        if r.std_error > 1.0: return "INSUFFICIENT_EVIDENCE"
        upper = r.elasticity + 1.96 * r.std_error                          # 95% confidence bound
        if r.elasticity <= -1.5 and upper < -1.0: return "HIGHLY_PRICE_SENSITIVE"
        if r.elasticity <= -0.7: return "MODERATELY_PRICE_SENSITIVE"
        return "LOW_PRICE_SENSITIVITY"
    el["price_sensitivity_class"] = el.apply(classify, axis=1)

    # event study: demand 28 days after every price change vs 28 days before, relative to the whole chain
    cd = spark.sql("SELECT item_id, order_date AS date, list_price FROM cost_day").toPandas()
    cd["date"] = pd.to_datetime(cd.date); cd["list_price"] = pd.to_numeric(cd.list_price); cd = cd.sort_values(["item_id", "date"])
    cd["prev"] = cd.groupby("item_id").list_price.shift(1)
    ev = cd[(cd.prev.notna()) & (cd.list_price != cd.prev) & (cd.date > D0 + pd.Timedelta(days=28)) & (cd.date <= D1 - pd.Timedelta(days=28))]
    daily_item = spark.sql("SELECT item_id, order_date AS date, SUM(quantity) AS units FROM fact_order_lines GROUP BY item_id, order_date").toPandas()
    daily_item["date"] = pd.to_datetime(daily_item.date)
    chain_d = daily_item.groupby("date").units.sum()
    erows = []
    for r in ev.itertuples():
        t = pd.Timestamp(r.date)
        s = daily_item[daily_item.item_id == r.item_id].set_index("date").units.reindex(pd.date_range(t - pd.Timedelta(days=28), t + pd.Timedelta(days=27)), fill_value=0)
        ch = chain_d.reindex(s.index, fill_value=0)
        b, a = s.iloc[:28].sum(), s.iloc[28:].sum()
        cb, ca = ch.iloc[:28].sum(), ch.iloc[28:].sum()
        if b < 100: continue
        erows.append(dict(item_id=r.item_id, change_date=t.date().isoformat(), price_before=r.prev, price_after=r.list_price,
                          price_change_pct=r.list_price / r.prev - 1, units_28d_before=int(b), units_28d_after=int(a),
                          relative_demand_change=(a / b) / (ca / cb) - 1))
    events = pd.DataFrame(erows)
    events["significant_demand_change"] = events.relative_demand_change.abs() >= 0.15
    events["implied_elasticity"] = events.relative_demand_change / events.price_change_pct
    ev_sum = events.groupby("item_id").agg(n_price_events=("change_date", "count"), mean_relative_demand_change=("relative_demand_change", "mean"),
                                           n_significant_demand_changes=("significant_demand_change", "sum")).reset_index()
    pi = items.merge(el, on="item_id", how="left").merge(ev_sum, on="item_id", how="left")
    pi["price_sensitivity_class"] = pi.price_sensitivity_class.fillna("INSUFFICIENT_PRICE_VARIATION")
    pi["classified_by"] = np.where(pi.price_sensitivity_class.isin(["INSUFFICIENT_PRICE_VARIATION", "INSUFFICIENT_EVIDENCE"]), "none", "weekly regression")
    pi = pi.merge(events.groupby("item_id").apply(lambda g: g.sort_values("price_change_pct", ascending=False).iloc[0][["price_change_pct", "relative_demand_change"]].rename({"price_change_pct": "largest_price_rise_pct", "relative_demand_change": "demand_change_after_largest_rise"}), include_groups=False).reset_index(), on="item_id", how="left")
    ev_named = events.merge(items[["item_id", "item_name", "category_name"]], on="item_id")
    save(pi, "price_sensitivity"); save(ev_named, "price_change_events")
    # relationship between price level and demand / revenue / margin / discount / rating / repeat (across dishes)
    cor = []
    base = items[items.units_sold > 0].copy(); base["ln_price"] = np.log(base.last_list_price)
    for col, label in [("units_sold", "Demand (units)"), ("revenue", "Revenue"), ("profit_pct", "Profit %"), ("avg_discount_pct", "Discount %"),
                       ("avg_rating", "Rating"), ("repeat_purchase_rate", "Repeat purchase rate")]:
        cor.append(dict(relationship=f"price level vs {label}", spearman_correlation=base.ln_price.corr(base[col], method="spearman"), n_items=int(base[col].notna().sum())))
    save(pd.DataFrame(cor), "price_correlations")
    cls = pi.price_sensitivity_class.value_counts()
    hi = pi[pi.price_sensitivity_class == "HIGHLY_PRICE_SENSITIVE"].sort_values("elasticity")
    md.append("## Price sensitivity (Steps 25-26)\n")
    md.append(f"- Weekly regression of ln(item share of chain units) on ln(price relative to the chain price index) for {len(el)} dishes. "
              f"Classes: {', '.join(f'{k} {v}' for k, v in cls.items())}.")
    md.append("- Dishes with no clear price change, a seasonal pattern, or too few promotion-free weeks are reported as INSUFFICIENT_*, not guessed. "
              "(Jollof Spaghetti, for example, is covered by a recurring Friday promotion, which removes most of its weeks from the regression; "
              "the price-change event table still shows what happened after each of its price rises.)")
    md.append(f"- Highly price-sensitive dishes: {', '.join(f'{r.item_name} (elasticity {r.elasticity:.1f})' for r in hi.itertuples()) or 'none'}.")
    sig = events[events.significant_demand_change & (events.price_change_pct > 0)]
    md.append(f"- {len(events)} price changes were studied (28 days before vs after, relative to the whole chain); "
              f"{len(sig)} price rises were followed by a demand change of 15% or more, in {sig.item_id.nunique()} dishes.")

# =============================================================================== PROMOTIONS
with Timer(ROOT, J, "promotions"):
    promos = spark.table("promotions").toPandas()
    pitems = spark.table("promotion_items").toPandas()
    menu = spark.table("menu_items").select("item_id", "category_id").toPandas()
    dchain = spark.sql("""SELECT order_date AS date, COUNT(*) AS orders, SUM(revenue) AS revenue, SUM(margin_after_fees) AS mfa,
                          SUM(total_amount) AS total_amount, COUNT(DISTINCT CASE WHEN NOT is_guest THEN customer_id END) AS customers
                          FROM order_features GROUP BY order_date""").toPandas()
    dchain["date"] = pd.to_datetime(dchain.date); dchain = dchain.set_index("date").sort_index()
    for c in dchain.columns: dchain[c] = pd.to_numeric(dchain[c])
    newc = spark.sql("""SELECT first_order_date AS date, COUNT(*) AS new_customers FROM customer_features
                        WHERE signup_date >= to_date('%s') GROUP BY first_order_date""" % S.VALID_DATE_MIN).toPandas()
    newc["date"] = pd.to_datetime(newc.date); dchain["new_customers"] = newc.set_index("date").new_customers.reindex(dchain.index).fillna(0)
    ditem = spark.sql("""SELECT date, item_id, SUM(units_sold) AS units, SUM(contribution_margin) AS cm, SUM(wasted_portions) AS wasted,
                         SUM(wastage_cost) AS wcost FROM daily_item_location GROUP BY date, item_id""").toPandas()
    ditem["date"] = pd.to_datetime(ditem.date)
    for c in ["units", "cm", "wasted", "wcost"]: ditem[c] = pd.to_numeric(ditem[c])
    ditem = ditem.merge(menu, on="item_id")
    cust_orders = spark.sql("SELECT customer_id, order_date FROM order_features WHERE NOT is_guest").toPandas()
    cust_orders["order_date"] = pd.to_datetime(cust_orders.order_date)
    cat_profit = spark.table("item_features").groupBy("category_id").agg({"contribution_margin": "sum", "revenue": "sum"}).toPandas()
    cat_profit["profit_pct"] = pd.to_numeric(cat_profit["sum(contribution_margin)"]) / pd.to_numeric(cat_profit["sum(revenue)"])
    cat_pp = cat_profit.set_index("category_id").profit_pct
    dow_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    def active_days(p):
        days = pd.date_range(max(pd.Timestamp(p.start_date), D0), min(pd.Timestamp(p.end_date), D1))
        if isinstance(p.applicable_days, str):
            keep = [dow_names.index(x) for x in p.applicable_days.split(",")]
            days = days[days.dayofweek.isin(keep)]
        return days

    others_big = {r.promo_id: set(active_days(r)) for r in promos.itertuples() if r.discount_pct >= 0.15 and r.promo_type not in ("NEW_CUSTOMER", "LOYALTY")}
    full_scope = len(menu)
    results = []
    for p in promos.itertuples():
        if p.promo_type in ("NEW_CUSTOMER", "LOYALTY"):
            continue                                              # always-on entitlements: no before/after
        days = active_days(p)
        if len(days) == 0: continue
        dows = set(days.dayofweek)
        busy = set().union(*[v for k, v in others_big.items() if k != p.promo_id]) if len(others_big) > 1 else set()
        start = days.min()
        cand = [d for d in pd.date_range(start - pd.Timedelta(days=90), start - pd.Timedelta(days=1)) if d >= D0 and d.dayofweek in dows and d not in busy]
        base = pd.DatetimeIndex(cand[-28:])
        after = pd.date_range(days.max() + pd.Timedelta(days=1), days.max() + pd.Timedelta(days=21))
        post = pd.DatetimeIndex([d for d in after if d <= D1 and d.dayofweek in dows and d not in busy][:14])
        sc_items = set(pitems[pitems.promo_id == p.promo_id].item_id)
        all_scope = len(sc_items) >= 0.95 * full_scope or len(sc_items) == 0
        sc_cats = set(menu[menu.item_id.isin(sc_items)].category_id)
        full_cats = {c for c in sc_cats if set(menu[menu.category_id == c].item_id) <= sc_items}

        def window(idx):
            if len(idx) == 0: return None
            c = dchain.reindex(idx).fillna(0)
            di = ditem[ditem.date.isin(idx)]
            sc = di[di.item_id.isin(sc_items)] if not all_scope else di
            n = len(idx)
            m = dict(days=n, orders=c.orders.sum() / n, revenue=c.revenue.sum() / n, mfa=c.mfa.sum() / n,
                     aov=c.total_amount.sum() / max(c.orders.sum(), 1), customers=c.customers.sum() / n,
                     margin_pct=c.mfa.sum() / max(c.revenue.sum(), 1), new_customers=c.new_customers.sum() / n,
                     scope_units=sc.units.sum() / n, scope_cm=sc.cm.sum() / n, scope_wcost=sc.wcost.sum() / n,
                     scope_wastage_pct=sc.wasted.sum() / max(sc.units.sum() + sc.wasted.sum(), 1))
            cats = di.groupby("category_id").units.sum() / n
            m["cat_units"] = cats
            la = idx.max() + pd.Timedelta(days=30)
            if la <= D1:
                act = set(cust_orders[cust_orders.order_date.isin(idx)].customer_id)
                nxt = set(cust_orders[(cust_orders.order_date > idx.max()) & (cust_orders.order_date <= la)].customer_id)
                m["repeat_30d"] = len(act & nxt) / max(len(act), 1)
            else:
                m["repeat_30d"] = np.nan
            return m
        w_p, w_b, w_a = window(days), window(base), window(post)
        row = dict(promo_id=p.promo_id, promo_name=p.promo_name, promo_type=p.promo_type, discount_pct=p.discount_pct,
                   start_date=days.min().date().isoformat(), end_date=days.max().date().isoformat(), n_promo_days=len(days),
                   n_baseline_days=len(base), n_post_days=len(post), scope="ALL ITEMS" if all_scope else ",".join(sorted(sc_cats)))
        if w_b is None or w_b["days"] < 5:
            row["verdict"] = "INSUFFICIENT_BASELINE"; results.append(row); continue
        ch = lambda k: w_p[k] / w_b[k] - 1 if w_b[k] else np.nan
        for k in ["orders", "revenue", "mfa", "customers", "scope_units", "scope_cm", "scope_wcost"]:
            row[f"{k}_change"] = ch(k)
        # per-order versions remove calendar effects (holidays, seasons) that move ALL sales, so a scoped promotion is judged on its own products
        po = lambda w, k: w[k] / max(w["orders"], 1e-9)
        row["scope_units_per_order_change"] = po(w_p, "scope_units") / po(w_b, "scope_units") - 1 if w_b["scope_units"] else np.nan
        row["scope_cm_per_order_change"] = po(w_p, "scope_cm") / po(w_b, "scope_cm") - 1 if w_b["scope_cm"] else np.nan
        row["mfa_per_order_change"] = po(w_p, "mfa") / po(w_b, "mfa") - 1
        row.update(aov_change=ch("aov"), margin_pct_before=w_b["margin_pct"], margin_pct_during=w_p["margin_pct"],
                   margin_pct_change_pts=(w_p["margin_pct"] - w_b["margin_pct"]) * 100,
                   scope_wastage_pct_before=w_b["scope_wastage_pct"], scope_wastage_pct_during=w_p["scope_wastage_pct"],
                   new_customers_per_day_before=w_b["new_customers"], new_customers_per_day_during=w_p["new_customers"],
                   repeat_30d_before=w_b["repeat_30d"], repeat_30d_during=w_p["repeat_30d"],
                   post_orders_change=(w_a["orders"] / w_b["orders"] - 1) if w_a else np.nan)
        # cannibalisation: an out-of-scope category MORE profitable than the promoted one loses 25%+ units per order
        lost = []
        promo_pp = float(np.mean([cat_pp[c] for c in sc_cats])) if sc_cats and not all_scope else None
        if promo_pp is not None:
            for c in w_b["cat_units"].index:
                if c in full_cats: continue
                b, d_ = w_b["cat_units"][c] / max(w_b["orders"], 1e-9), w_p["cat_units"].get(c, 0) / max(w_p["orders"], 1e-9)   # units per order
                if w_b["cat_units"][c] > 20 and cat_pp.get(c, 0) > promo_pp and d_ / b - 1 <= -0.25:
                    lost.append(f"{c} {d_ / b - 1:+.0%} units per order")
        row["cannibalised_categories"] = ", ".join(lost)
        # ---- trap rules
        if all_scope:
            sales_up = row["orders_change"] >= 0.10
            profit_down = row["mfa_change"] < 0
        else:
            sales_up = row["scope_units_per_order_change"] >= 0.30
            profit_down = row["scope_cm_per_order_change"] < 0
        traps = []
        if sales_up and profit_down: traps.append("SALES_UP_PROFIT_DOWN")
        if row["customers_change"] >= 0.10 and row["margin_pct_change_pts"] <= -3: traps.append("CUSTOMERS_UP_MARGIN_COLLAPSES")
        if not all_scope and row["scope_wcost_change"] >= 0.5 and row["scope_wastage_pct_during"] - row["scope_wastage_pct_before"] >= 0.02: traps.append("INCREASES_WASTAGE")
        if lost: traps.append("SHIFTS_SALES_FROM_MORE_PROFITABLE_PRODUCT")
        if all_scope and not np.isnan(row["post_orders_change"]) and row["post_orders_change"] <= -0.10: traps.append("DISCOUNT_DEPENDENT_DEMAND")
        row["traps"] = "; ".join(traps)
        row["verdict"] = ("MISLEADING" if any(t in ("SALES_UP_PROFIT_DOWN", "CUSTOMERS_UP_MARGIN_COLLAPSES", "INCREASES_WASTAGE") for t in traps)
                          else "WATCH" if traps else "EFFECTIVE" if (row["mfa_change"] >= 0 if all_scope else row["scope_cm_per_order_change"] >= 0) else "NOT_PROFITABLE")
        results.append(row)
    pe = pd.DataFrame(results)
    save(pe, "promotion_effectiveness")
    md.append("\n## Promotion effectiveness and traps (Steps 27-28)\n")
    md.append("**Limit:** the data covers one year only, so holidays and seasons cannot be separated from the effect of all-menu promotions "
              "(for example Black Friday and the festive season coincide with busy periods). Promotions that cover only some products are judged per order, which removes "
              "most calendar effects. With a second year of data, compare with the same period of the previous year.\n")
    md.append("Each promotion is compared with up to 28 matching days before it (same weekdays, excluding days of other big promotions) and 14 days after it. "
              "A rise in sales alone never makes a promotion 'successful': profit after platform fees, margin %, wastage, post-promotion demand and "
              "sales shifted from better products are all checked.\n")
    md.append("| Promotion | Orders/day | Profit/day | Margin % (before -> during) | Traps | Verdict |\n|---|---|---|---|---|---|")
    for r in pe.itertuples():
        if r.verdict == "INSUFFICIENT_BASELINE":
            md.append(f"| {r.promo_id} {r.promo_name} | - | - | - | - | INSUFFICIENT_BASELINE |"); continue
        md.append(f"| {r.promo_id} {r.promo_name} | {pct(r.orders_change)} | {pct(r.mfa_change)} | {r.margin_pct_before:.1%} -> {r.margin_pct_during:.1%} | {r.traps or '-'} | {r.verdict} |")

# =============================================================================== LOCATION SCORECARD
with Timer(ROOT, J, "location scorecard"):
    lf = spark.table("location_features").toPandas()
    num = [c for c in lf.columns if c not in ("location_id", "restaurant_name", "city", "region", "size_tier", "opening_date", "first_order_date")]
    for c in num: lf[c] = pd.to_numeric(lf[c], errors="coerce")
    mp = spark.sql("""SELECT location_id, AVG(CASE WHEN performance_class = 'PROFIT_DRIVER' THEN 1D ELSE 0D END) AS profit_driver_share,
                      AVG(CASE WHEN performance_class = 'LOW_PERFORMER' THEN 1D ELSE 0D END) AS low_performer_share
                      FROM (SELECT * FROM parquet.`%s`) t WHERE performance_class <> 'INSUFFICIENT_DATA' GROUP BY location_id"""
                      % os.path.join(OUT, "menu_performance_by_location")).toPandas()
    lf = lf.merge(mp, on="location_id", how="left")
    ind = {"revenue_per_seat": 1, "margin_after_fees_pct": 1, "avg_order_value": 1, "repeat_customer_rate": 1, "wastage_pct": -1,
           "avg_restaurant_rating": 1, "cancellation_rate": -1, "profit_driver_share": 1, "order_trend_pct": 1}
    sc = lf[["location_id", "restaurant_name", "city", "size_tier"] + list(ind)].copy()
    for k, sign in ind.items():
        z = (lf[k] - lf[k].mean()) / lf[k].std(ddof=0)
        sc[k + "_z"] = sign * z
    zc = [k + "_z" for k in ind]
    sc["composite_score"] = sc[zc].mean(axis=1)
    sc["rank"] = sc.composite_score.rank(ascending=False).astype(int)
    sc["n_extreme_indicators"] = (sc[zc].abs() >= 2).sum(axis=1)
    sc["investigate"] = sc.n_extreme_indicators >= 1
    sc["investigate_reasons"] = sc.apply(lambda r: "; ".join(f"{k} {'unusually good' if r[k + '_z'] > 0 else 'unusually weak'}" for k in ind if abs(r[k + "_z"]) >= 2), axis=1)
    save(sc.sort_values("rank"), "location_scorecard")
    md.append("\n## Location scorecard (Step 33)\n")
    md.append("Nine standardised indicators (z-scores, signs flipped so that higher is always better); composite = their mean; a location is flagged when any indicator is 2 or more standard deviations from the chain average.\n")
    md.append("| Rank | Restaurant | Composite | Flagged reasons |\n|---|---|---|---|")
    for r in sc.sort_values("rank").itertuples():
        md.append(f"| {r.rank} | {r.location_id} {r.restaurant_name} | {r.composite_score:+.2f} | {r.investigate_reasons or '-'} |")

open(os.path.join(ROOT, "reports", "phase4b_pricing_promotions_locations.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md[:40]))
spark.stop()
