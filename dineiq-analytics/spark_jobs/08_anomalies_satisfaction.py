"""
08_anomalies_satisfaction.py - Phase 4B (SRS Steps 29, 30, 31)

  Step 31  Sales anomalies   spikes / drops (restaurant-day), sustained drops, abnormal order values, unusual discounts,
                             unexpected item demand, duplicate transactions
  Step 30  Rating anomalies  bursts of ratings with no purchase, sudden rating spikes / drops, one account posting identical ratings,
                             unusually many ratings in a short period, ratings inconsistent with purchases
  Step 29  Rating and satisfaction analysis   by month, restaurant, dish, profitability, sales, repeat purchase, promotion status, time of day

All detectors are ROBUST statistics (median and MAD, not mean and standard deviation), so the anomalies themselves do not distort the baseline.
Spark does the aggregation; the detectors run in pandas on the small summaries.

Run:  python 08_anomalies_satisfaction.py --root ..
"""
import os

import numpy as np
import pandas as pd

import spark_common as S
from spark_common import Timer, get_spark, parse_args, register_all_views

args = parse_args("DineIQ anomalies and satisfaction")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-08-anomalies", args.driver_memory)
J = "08_anomalies"
register_all_views(spark, ROOT)
OUT = os.path.join(ROOT, "processed_data", "analytics")
CSV = os.path.join(ROOT, "reports", "tables")
os.makedirs(CSV, exist_ok=True)
D0, D1 = pd.Timestamp(S.VALID_DATE_MIN), pd.Timestamp(S.VALID_DATE_MAX)
md = ["# Phase 4B - anomalies and customer satisfaction (generated from the data)\n"]


def save(df, name):
    path = os.path.join(OUT, name)
    os.makedirs(path, exist_ok=True)
    df.to_parquet(os.path.join(path, "part-0.parquet"), index=False)
    df.to_csv(os.path.join(CSV, name + ".csv"), index=False)


def mad_z(x, ref):
    """robust z-score of x against a reference sample (median / MAD, floor on the scale)"""
    med = np.median(ref)
    mad = np.median(np.abs(ref - med)) * 1.4826
    return (x - med) / max(mad, 0.1 * abs(med), 1e-9), med


def runs(dates):
    """group sorted dates into runs of consecutive days -> list of (start, end)"""
    out, start, prev = [], None, None
    for d in sorted(dates):
        if start is None: start = prev = d
        elif (d - prev).days <= 1: prev = d
        else: out.append((start, prev)); start = prev = d
    if start is not None: out.append((start, prev))
    return out


events = []   # one dict per sales anomaly

# =============================================================================== SALES ANOMALIES
with Timer(ROOT, J, "sales anomalies"):
    ld = spark.sql("SELECT location_id, order_date AS date, COUNT(*) AS orders FROM order_features GROUP BY location_id, order_date").toPandas()
    ld["date"] = pd.to_datetime(ld.date)
    first_day = ld.groupby("location_id").date.min()
    days = pd.date_range(D0, D1)
    wide = ld.pivot(index="date", columns="location_id", values="orders").reindex(days).fillna(0)
    chain = wide.sum(axis=1)
    # (a) restaurant-day spikes and drops. Expected orders = the restaurant's usual SHARE of chain orders on the same weekday (median of the
    #     3 weeks before and after) x the chain's orders that day, so holidays and seasons that move every restaurant do not count as anomalies.
    #     The noise allowance is Poisson-like: 1.5 x sqrt(expected) + 10% of expected.
    share = wide.div(chain, axis=0)
    for loc in wide.columns:
        s_, sh = wide[loc], share[loc]
        flagged = {"SALES_SPIKE": [], "SALES_DROP": []}
        for i in range(len(s_)):
            t = s_.index[i]
            if t < first_day[loc] + pd.Timedelta(days=60): continue                  # a new restaurant is still ramping up
            ref = [sh.iloc[i + k * 7] for k in (-3, -2, -1, 1, 2, 3) if 0 <= i + k * 7 < len(s_) and s_.index[i + k * 7] >= first_day[loc]]
            if len(ref) < 4: continue
            exp = float(np.median(ref) * chain.iloc[i])
            z = (s_.iloc[i] - exp) / (1.5 * np.sqrt(max(exp, 1)) + 0.1 * exp)
            if z >= 5 and s_.iloc[i] >= 1.5 * exp: flagged["SALES_SPIKE"].append((t, s_.iloc[i], exp))
            if z <= -3 and s_.iloc[i] <= 0.4 * exp: flagged["SALES_DROP"].append((t, s_.iloc[i], exp))
        for typ, lst in flagged.items():
            for a, b in runs([x[0] for x in lst]):
                part = [x for x in lst if a <= x[0] <= b]
                obs = float(np.mean([x[1] for x in part])); exp = float(np.mean([x[2] for x in part]))
                events.append(dict(anomaly_type=typ, entity_type="RESTAURANT", entity=loc, start_date=a.date().isoformat(), end_date=b.date().isoformat(),
                                   observed=obs, expected=exp, ratio=obs / max(exp, 1e-9), n_items=len(part),
                                   detail=f"{obs:.0f} orders/day against about {exp:.0f} expected for its usual share of chain orders"))
    # (b) sustained drop in a restaurant's share of chain orders (a level shift is invisible to the spike test above)
    for loc in share.columns:
        s = share[loc]
        cur = s.rolling(14).mean(); prev = s.shift(14).rolling(56).mean()
        ratio = (cur / prev)
        ok = ratio.index[(ratio <= 0.70) & (s.index > first_day[loc] + pd.Timedelta(days=120))]
        for a, b in runs(list(ok)):
            if (b - a).days >= 21:
                base_lvl = float(prev[a]); a0 = a
                for k in range(1, 22):                                   # walk back to where the level really changed
                    if s[a - pd.Timedelta(days=k):a - pd.Timedelta(days=k) + pd.Timedelta(days=2)].mean() > 0.75 * base_lvl: a0 = a - pd.Timedelta(days=k) + pd.Timedelta(days=1); break
                a = a0
                events.append(dict(anomaly_type="SUSTAINED_SALES_DROP", entity_type="RESTAURANT", entity=loc, start_date=a.date().isoformat(), end_date=b.date().isoformat(),
                                   observed=float(cur[b]), expected=float(prev[b]), ratio=float(ratio[b]), n_items=(b - a).days + 1,
                                   detail=f"share of chain orders fell to {ratio[b]:.0%} of its earlier level (14-day average vs the 56 days before)"))
    # (c) abnormally high order values: robust z-score of ln(order value) within each channel
    ov = spark.sql("SELECT order_id, order_date, location_id, channel, total_amount, basket_units, discount_pct, promo_id FROM order_features").toPandas()
    ov["total_amount"] = pd.to_numeric(ov.total_amount); ov["discount_pct"] = pd.to_numeric(ov.discount_pct)
    ov["ln"] = np.log(ov.total_amount.clip(lower=1))
    ov["z"] = ov.groupby("channel").ln.transform(lambda x: (x - x.median()) / (1.4826 * np.median(np.abs(x - x.median()))))
    big = ov[ov.z >= 5].sort_values("total_amount", ascending=False)
    for r in big.itertuples():
        events.append(dict(anomaly_type="ABNORMAL_ORDER_VALUE", entity_type="ORDER", entity=r.order_id, start_date=str(r.order_date), end_date=str(r.order_date),
                           observed=float(r.total_amount), expected=float(ov[ov.channel == r.channel].total_amount.median()), ratio=float(r.total_amount / ov[ov.channel == r.channel].total_amount.median()),
                           n_items=int(r.basket_units), detail=f"{r.location_id}, {r.channel}: {r.total_amount:,.0f} NGN, {int(r.basket_units)} units (robust z {r.z:.1f})"))
    # (d) unusual discounts: a deep discount with no promotion behind it
    ud = ov[(ov.discount_pct >= 0.5) & (ov.promo_id.isna())]
    for loc, g in ud.groupby("location_id"):
        events.append(dict(anomaly_type="UNUSUAL_DISCOUNT", entity_type="RESTAURANT", entity=loc, start_date=str(g.order_date.min()), end_date=str(g.order_date.max()),
                           observed=float(g.discount_pct.mean()), expected=0.0, ratio=np.nan, n_items=len(g),
                           detail=f"{len(g)} orders discounted by {g.discount_pct.mean():.0%} on average with no promotion applied"))
    # (e) unexpected demand for one dish
    di = spark.sql("SELECT item_id, order_date AS date, SUM(quantity) AS units FROM fact_order_lines GROUP BY item_id, order_date").toPandas()
    di["date"] = pd.to_datetime(di.date); di["units"] = pd.to_numeric(di.units)
    names = spark.table("item_features").select("item_id", "item_name").toPandas().set_index("item_id").item_name
    promos = spark.table("promotions").toPandas(); pitems = spark.table("promotion_items").toPandas()
    chain_units = di.groupby("date").units.sum()
    for item, g in di.groupby("item_id"):
        g = g.set_index("date").units.reindex(pd.date_range(g.date.min(), g.date.max()), fill_value=0)
        if len(g) < 20: continue
        shr = g / chain_units.reindex(g.index).replace(0, np.nan)             # share of the chain's units that day (removes holidays / seasons)
        rel = shr / shr.groupby(shr.index.dayofweek).transform("median").replace(0, np.nan)   # relative to the same weekday (weekend-only dishes are not "unexpected" every weekend)
        zs = (rel - 1) / max(1.4826 * np.nanmedian(np.abs(rel - 1)), 0.1)
        hit = g.index[(zs >= 6) & (rel >= 2.5) & (g >= 50)]
        for a, b in runs(list(hit)):
            sc = promos[promos.promo_id.isin(pitems[pitems.item_id == item].promo_id) & (promos.discount_pct > 0) & ~promos.promo_type.isin(["NEW_CUSTOMER", "LOYALTY"])]
            dn = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            def runs_on(r):          # does the promotion actually run on at least one of the event's days (respecting weekday-only promotions)?
                dd = pd.date_range(max(a, pd.Timestamp(r.start_date)), min(b, pd.Timestamp(r.end_date)))
                if isinstance(r.applicable_days, str): dd = [d_ for d_ in dd if dn[d_.dayofweek] in r.applicable_days]
                return len(dd) > 0
            expl = [r.promo_id for r in sc.itertuples() if runs_on(r)]
            part = g[a:b]; pshare = rel[a:b].mean()
            events.append(dict(anomaly_type="UNEXPECTED_DEMAND", entity_type="ITEM", entity=item, start_date=a.date().isoformat(), end_date=b.date().isoformat(),
                               observed=float(part.mean()), expected=float(g.median()), ratio=float(pshare), n_items=len(part),
                               detail=f"{names[item]}: {part.mean():.0f} units/day, {pshare:.1f}x its usual share of chain sales on that weekday" + (f" (a promotion explains it: {', '.join(expl)})" if expl else " (no promotion explains it)")))
    # (f) duplicate transactions found and removed by the cleaning step
    q = spark.read.parquet(os.path.join(ROOT, "quarantine", "orders")).filter("quarantine_reason = 'NEAR_DUPLICATE_TRANSACTION'").groupBy("location_id").count().toPandas()
    dec = pd.read_csv(os.path.join(ROOT, "reports", "cleaning_decisions.csv"))
    n_exact = int(dec[dec.rule_id == "O-01"].rows.sum())
    events.append(dict(anomaly_type="DUPLICATE_TRANSACTIONS", entity_type="CHAIN", entity="ALL", start_date=S.VALID_DATE_MIN, end_date=S.VALID_DATE_MAX,
                       observed=float(q["count"].sum()), expected=0.0, ratio=np.nan, n_items=int(q["count"].sum()),
                       detail=f"{int(q['count'].sum())} near-duplicate transactions (same customer, basket and total within {S.NEAR_DUP_SECONDS}s) and {n_exact} exact duplicate order rows were removed in cleaning"))
    sa = pd.DataFrame(events)
    sa["explained_by_promotion"] = sa.detail.str.contains("a promotion explains it")
    save(sa, "sales_anomalies")
    cnt = sa.anomaly_type.value_counts()
    md.append("## Sales anomalies (Step 31)\n")
    md.append("| Type | Events | Examples |\n|---|---|---|")
    for typ, n in cnt.items():
        ex = sa[sa.anomaly_type == typ].head(3)
        md.append(f"| {typ} | {n} | " + "; ".join(f"{r.entity} {r.start_date}" for r in ex.itertuples()) + " |")
    md.append("")
    for r in sa[sa.anomaly_type.isin(["SALES_SPIKE", "SALES_DROP", "SUSTAINED_SALES_DROP", "UNEXPECTED_DEMAND", "UNUSUAL_DISCOUNT"])].itertuples():
        md.append(f"- **{r.anomaly_type}** {r.entity} {r.start_date}" + (f" to {r.end_date}" if r.end_date != r.start_date else "") + f": {r.detail}")

# =============================================================================== RATING ANOMALIES
with Timer(ROOT, J, "rating anomalies"):
    rt = spark.table("ratings").toPandas()
    rt["rating_date"] = pd.to_datetime(rt.rating_date)
    ritems = spark.table("item_features").select("item_id", "item_name").toPandas().set_index("item_id").item_name
    ra = []
    unl = rt[~rt.has_purchase_link]
    # (a) bursts of ratings with no purchase behind them: 40+ in any 7 days for one dish, one dish-in-one-restaurant, or one restaurant
    for level, keys in [("ITEM", ["item_id"]), ("ITEM_AT_RESTAURANT", ["item_id", "location_id"]), ("RESTAURANT", ["location_id"])]:
        sub = unl[unl.item_id.notna()] if level != "RESTAURANT" else unl[unl.item_id.isna()]
        for key, g in sub.groupby(keys if len(keys) > 1 else keys[0]):
            ser = g.groupby("rating_date").size().reindex(pd.date_range(D0, D1), fill_value=0)
            roll = ser.rolling(7).sum()
            hit = roll.index[roll >= 40]
            for a, b in runs(list(hit)):
                a = a - pd.Timedelta(days=6)
                part = g[(g.rating_date >= a) & (g.rating_date <= b)]
                ent = key if isinstance(key, str) else "@".join(key)
                label = ritems.get(key if isinstance(key, str) else key[0], key) if level != "RESTAURANT" else key
                ra.append(dict(anomaly_type="RATINGS_WITHOUT_PURCHASE_BURST", level=level, entity=ent, start_date=part.rating_date.min().date().isoformat(),
                               end_date=part.rating_date.max().date().isoformat(), n_ratings=len(part), avg_rating=float(part.rating_value.mean()),
                               detail=f"{len(part)} ratings with no order behind them for {label}, average {part.rating_value.mean():.1f}, from {part.customer_id.nunique()} accounts"))
    # (b) sudden spike / drop of the weekly average rating of a dish
    rw = rt[rt.item_id.notna()].copy()
    rw["wk"] = ((rw.rating_date - D0).dt.days // 7)
    wk = rw.groupby(["item_id", "wk"]).rating_value.agg(["mean", "count"]).reset_index()
    for item, g in wk.groupby("item_id"):
        g = g[g["count"] >= 5].set_index("wk")
        for w in g.index:
            if g.loc[w, "count"] < 15: continue                                   # the suspicious week needs a real number of ratings
            prev = g.loc[[x for x in g.index if w - 6 <= x < w], "mean"]
            if len(prev) < 2: continue
            delta = g.loc[w, "mean"] - prev.mean()
            if abs(delta) >= 1.0:
                part = rw[(rw.item_id == item) & (rw.wk == w)]
                top_loc = part.groupby("location_id").size().idxmax()
                ra.append(dict(anomaly_type="SUDDEN_RATING_DROP" if delta < 0 else "SUDDEN_RATING_SPIKE", level="ITEM", entity=item,
                               start_date=(D0 + pd.Timedelta(days=7 * int(w))).date().isoformat(), end_date=(D0 + pd.Timedelta(days=7 * int(w) + 6)).date().isoformat(),
                               n_ratings=int(g.loc[w, "count"]), avg_rating=float(g.loc[w, "mean"]),
                               detail=f"{ritems[item]}: weekly average {g.loc[w, 'mean']:.1f} vs {prev.mean():.1f} in the previous weeks ({delta:+.1f}); most ratings from {top_loc}; {int((~part.has_purchase_link).sum())} of {len(part)} have no purchase"))
    # (c) one account posting many identical ratings in a day
    ident = rt[rt.customer_id.notna()].groupby(["customer_id", "rating_date"]).agg(n=("rating_value", "size"), n_distinct=("rating_value", "nunique"), v=("rating_value", "first"),
                                                                              items=("item_id", lambda x: x.nunique())).reset_index()
    for r in ident[(ident.n >= 20) & (ident.n_distinct == 1)].itertuples():
        ra.append(dict(anomaly_type="EXCESSIVE_IDENTICAL_RATINGS", level="CUSTOMER", entity=r.customer_id, start_date=r.rating_date.date().isoformat(), end_date=r.rating_date.date().isoformat(),
                       n_ratings=int(r.n), avg_rating=float(r.v), detail=f"one account posted {int(r.n)} ratings, all {int(r.v)} stars, in one day"))
    # (d) unusually many ratings for a restaurant in one day (robust z against its own history)
    daily = rt.groupby(["location_id", "rating_date"]).size().rename("n").reset_index()
    for loc, g in daily.groupby("location_id"):
        ser = g.set_index("rating_date").n.reindex(pd.date_range(D0, D1), fill_value=0)
        for t in ser.index[ser >= 50]:
            z, med = mad_z(ser[t], ser.drop(t).values)
            if z >= 8 and ser[t] >= 5 * max(med, 1):
                part = rt[(rt.location_id == loc) & (rt.rating_date == t)]
                ra.append(dict(anomaly_type="UNUSUALLY_MANY_RATINGS", level="RESTAURANT", entity=loc, start_date=t.date().isoformat(), end_date=t.date().isoformat(),
                               n_ratings=int(ser[t]), avg_rating=float(part.rating_value.mean()), detail=f"{int(ser[t])} ratings in one day against a typical {med:.0f}; {int((~part.has_purchase_link).sum())} have no purchase"))
    # (e) ratings inconsistent with purchasing patterns
    mism = spark.sql("""SELECT COUNT(*) AS n FROM ratings r WHERE r.order_id IS NOT NULL AND r.item_id IS NOT NULL
                        AND EXISTS (SELECT 1 FROM fact_order_lines f WHERE f.order_id = r.order_id)
                        AND NOT EXISTS (SELECT 1 FROM fact_order_lines f WHERE f.order_id = r.order_id AND f.item_id = r.item_id)""").collect()[0]["n"]
    gone = spark.sql("""SELECT COUNT(*) AS n FROM ratings r WHERE r.order_id IS NOT NULL
                        AND NOT EXISTS (SELECT 1 FROM fact_order_lines f WHERE f.order_id = r.order_id)""").collect()[0]["n"]
    n_unl = int((rt.item_id.notna() & ~rt.has_purchase_link).sum())
    ra.append(dict(anomaly_type="RATINGS_INCONSISTENT_WITH_PURCHASES", level="CHAIN", entity="ALL", start_date=S.VALID_DATE_MIN, end_date=S.VALID_DATE_MAX,
                   n_ratings=n_unl + int(mism), avg_rating=np.nan,
                   detail=f"{n_unl} dish ratings have no order behind them and {int(mism)} ratings name a dish that is no longer among the cleaned lines of the rated order (mostly lines quarantined in cleaning); ({int(gone)} further ratings belong to orders removed in cleaning: cancelled, quarantined or voided)"))
    rta = pd.DataFrame(ra)
    cover = rta[(rta.anomaly_type == "RATINGS_WITHOUT_PURCHASE_BURST") & (rta.level == "ITEM")][["entity", "start_date", "end_date"]]
    dup = rta.level.eq("ITEM_AT_RESTAURANT") & rta.entity.str.split("@").str[0].isin(cover.entity)
    rta = rta[~dup].reset_index(drop=True)
    save(rta, "rating_anomalies")
    md.append("\n## Rating anomalies (Step 30)\n")
    for r in rta.itertuples():
        md.append(f"- **{r.anomaly_type}** ({r.level} {r.entity}) {r.start_date}" + (f" to {r.end_date}" if r.end_date != r.start_date else "") + f": {r.detail}")

# =============================================================================== SATISFACTION
with Timer(ROOT, J, "satisfaction analysis"):
    q = lambda sql: spark.sql(sql).toPandas()
    base = "FROM ratings r JOIN order_features o ON r.order_id = o.order_id WHERE r.has_purchase_link"
    by_promo = q(f"SELECT CASE WHEN o.has_promo THEN 'PROMOTION' ELSE 'NO_PROMOTION' END AS promo_status, COUNT(*) AS n_ratings, AVG(r.rating_value) AS avg_rating {base} AND r.item_id IS NOT NULL GROUP BY o.has_promo")
    by_hour = q(f"""SELECT CASE WHEN o.order_hour <= 10 THEN '1 Breakfast 7-10' WHEN o.order_hour <= 14 THEN '2 Lunch 11-14' WHEN o.order_hour <= 17 THEN '3 Afternoon 15-17' ELSE '4 Dinner 18-22' END AS time_period,
                    COUNT(*) AS n_ratings, AVG(r.rating_value) AS avg_rating {base} AND r.item_id IS NOT NULL GROUP BY 1 ORDER BY 1""")
    by_channel = q(f"SELECT o.channel, COUNT(*) AS n_ratings, AVG(r.rating_value) AS avg_rating {base} AND r.item_id IS NOT NULL GROUP BY o.channel")
    by_month = q("""SELECT date_format(rating_date, 'yyyy-MM') AS month, COUNT(*) AS n_ratings, AVG(rating_value) AS avg_rating
                    FROM ratings WHERE has_purchase_link AND item_id IS NOT NULL GROUP BY 1 ORDER BY 1""")
    by_loc = q("""SELECT l.location_id, l.restaurant_name, l.avg_item_rating, l.avg_restaurant_rating, l.n_ratings, l.revenue, l.margin_after_fees_pct,
                  l.repeat_customer_rate, l.wastage_pct FROM location_features l""")
    for c in by_loc.columns[2:]: by_loc[c] = pd.to_numeric(by_loc[c])
    it = q("SELECT item_id, item_name, avg_rating, n_ratings, profit_pct, units_sold, repeat_purchase_rate, wastage_pct FROM item_features WHERE n_ratings >= 20")
    for c in it.columns[2:]: it[c] = pd.to_numeric(it[c])
    cor = pd.DataFrame([dict(relationship=f"dish rating vs {lab}", spearman_correlation=it.avg_rating.corr(it[col], method="spearman"), n=len(it))
                        for col, lab in [("profit_pct", "profit %"), ("units_sold", "sales (units)"), ("repeat_purchase_rate", "repeat purchase rate"), ("wastage_pct", "wastage %")]]
                       + [dict(relationship=f"restaurant rating vs {lab}", spearman_correlation=by_loc.avg_item_rating.corr(by_loc[col], method="spearman"), n=len(by_loc))
                          for col, lab in [("revenue", "revenue"), ("margin_after_fees_pct", "profit %"), ("repeat_customer_rate", "repeat customer rate")]])
    for df, nm in [(by_promo, "rating_by_promotion_status"), (by_hour, "rating_by_time_period"), (by_channel, "rating_by_channel"),
                   (by_month, "rating_by_month"), (by_loc, "rating_by_location"), (cor, "rating_correlations")]:
        save(df, nm)
    md.append("\n## Rating and satisfaction analysis (Step 29)\n")
    md.append("Only ratings tied to a real purchase are used. Rank correlations are across dishes (or restaurants).\n")
    for r in cor.itertuples():
        md.append(f"- {r.relationship}: Spearman {r.spearman_correlation:+.2f} (n={r.n})")
    for r in by_promo.itertuples():
        md.append(f"- Dish ratings on {r.promo_status}: {float(r.avg_rating):.2f} ({r.n_ratings:,} ratings)")
    md.append("- By time period: " + "; ".join(f"{r.time_period[2:]} {float(r.avg_rating):.2f}" for r in by_hour.itertuples()))
    lo, hi = by_loc.sort_values("avg_item_rating").iloc[0], by_loc.sort_values("avg_item_rating").iloc[-1]
    md.append(f"- Lowest-rated restaurant: {lo.restaurant_name} ({lo.avg_item_rating:.2f}); highest: {hi.restaurant_name} ({hi.avg_item_rating:.2f}).")

open(os.path.join(ROOT, "reports", "phase4b_anomalies_satisfaction.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md[:60]))
spark.stop()
