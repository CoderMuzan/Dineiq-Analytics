"""
06_analytics_sql.py - Phase 4A: set-based analytics with Spark SQL (SRS Steps 8-11, 15-19, 23, 32, 34, 35, 36-rules).

Runs spark_sql/10..15, then writes every view whose name starts with `out_` to
    processed_data/analytics/<name>/   (Parquet)       and      reports/tables/<name>.csv   (small tables, open in Excel)

Run:  python 06_analytics_sql.py --root ..
"""
import os

from spark_common import Timer, get_spark, parse_args, register_all_views, run_sql_file, sql_params

args = parse_args("DineIQ analytics with Spark SQL")
ROOT = os.path.abspath(args.root)
spark = get_spark("DineIQ-06-analytics", args.driver_memory)
J = "06_analytics"
register_all_views(spark, ROOT)
run_sql_file(spark, ROOT, "01_lookup_tables.sql")          # cost_day (used by some views)
OUT = os.path.join(ROOT, "processed_data", "analytics")
CSV = os.path.join(ROOT, "reports", "tables")
os.makedirs(CSV, exist_ok=True)
written = []
for sql in ["10_eda_channels.sql", "11_menu_classification.sql", "12_customers.sql", "13_baskets.sql", "14_peak_periods.sql", "15_wastage.sql"]:
    with Timer(ROOT, J, sql):
        run_sql_file(spark, ROOT, sql)
        names = sorted(t.name for t in spark.catalog.listTables() if t.name.startswith("out_"))
        for name in names:
            if name in written: continue
            df = spark.table(name)
            df.write.mode("overwrite").parquet(os.path.join(OUT, name[4:]))
            n = spark.read.parquet(os.path.join(OUT, name[4:])).count()
            if n <= 20000:
                spark.read.parquet(os.path.join(OUT, name[4:])).toPandas().to_csv(os.path.join(CSV, name[4:] + ".csv"), index=False)
            written.append(name)
            print(f"   {name[4:]:34s} {n:>8,} rows", flush=True)
spark.stop()

# ------------------------------------------------------------------ plain-language findings (insights, not just charts)
import pandas as pd
A = lambda n: pd.read_parquet(os.path.join(OUT, n))
num = lambda df: df.apply(lambda c: pd.to_numeric(c, errors="ignore") if c.dtype == object else c)
mp, seg, ss = num(A("menu_performance")), A("customer_segments"), num(A("segment_summary"))
md = ["# Phase 4A - menu, customers, baskets, peaks, wastage (generated from the data)\n"]
names = lambda df, n=6: ", ".join(df.sort_values("units_sold", ascending=False).item_name.head(n))
md.append("## Menu performance (Steps 9-11, 32, 34)\n")
md.append("Thresholds computed from the data: " + f"demand cut {mp.mean_upd.iloc[0] * 0.7:.1f} units/day (70% of the average dish), chain profit % {mp.chain_profit_pct.iloc[0]:.1%}, "
          f"chain wastage % {mp.chain_wastage_pct.iloc[0]:.1%}, chain rating {mp.chain_rating.iloc[0]:.2f}.\n")
for cl, text in [("PROFIT_DRIVER", "keep, protect and feature"), ("VOLUME_DRIVER", "review price or recipe cost"),
                 ("HIDDEN_OPPORTUNITY", "promote and make more visible"), ("LOW_PERFORMER", "fix, reprice or remove")]:
    g = mp[mp.performance_class == cl]
    md.append(f"- **{cl.replace('_', ' ').title()}** ({len(g)} dishes, {g.revenue.sum() / mp.revenue.sum():.0%} of revenue, {g.contribution_margin.sum() / mp.contribution_margin.sum():.0%} of margin) - {text}: {names(g)}.")
md.append("")
for col, label in [("tricky_high_selling_loss_making", "High-selling but loss-making"), ("tricky_profitable_rarely_purchased", "Profitable but rarely purchased"),
                   ("tricky_popular_excessive_wastage", "Popular with excessive wastage"), ("tricky_highly_rated_poor_profit", "Highly rated but poor profitability"),
                   ("tricky_low_rated_high_sales", "Low rated but high sales"), ("tricky_promotion_dependent", "Promotion-dependent"),
                   ("tricky_weekend_only", "Weekend-only"), ("tricky_seasonal", "Seasonal"), ("tricky_new_insufficient_history", "New with insufficient history"),
                   ("tricky_location_inconsistent", "Performs differently across restaurants"), ("slow_moving", "Slow-moving")]:
    g = mp[mp[col]]
    md.append(f"- {label}: {len(g)} - " + (", ".join(g.item_name.head(8)) + (" ..." if len(g) > 8 else "") if len(g) else "none"))
md.append("\n## Customers (Steps 15, 16, 36)\n")
md.append("| Segment | Customers | Share | Revenue share | Avg orders | Avg spend | Avg days since last order |\n|---|---|---|---|---|---|---|")
for r in ss.sort_values("revenue_share", ascending=False).itertuples():
    md.append(f"| {r.segment} | {r.n_customers:,} | {float(r.customer_share):.1%} | {float(r.revenue_share):.1%} | {float(r.avg_frequency):.1f} | {float(r.avg_monetary):,.0f} | {float(r.avg_recency_days):.0f} |")
hr = seg[seg.churn_risk_level == "HIGH"]
md.append(f"\n- {len(hr):,} customers with 3+ orders show HIGH churn risk; they have spent {pd.to_numeric(hr.monetary).sum():,.0f} NGN in the year.")
bun = num(A("bundle_recommendations")).sort_values("priority_score", ascending=False)
md.append("\n## Bundles and cross-sell (Steps 17-18)\n")
for r in bun.head(8).itertuples():
    md.append(f"- **{r.recommendation_type.replace('_', ' ').title()}**: {r.antecedent_name} + {r.consequent_name} - {r.evidence}")
ph, pdays = num(A("peak_hour")), num(A("peak_day"))
md.append("\n## Peak periods (Step 19)\n")
md.append(f"- Peak hours (25%+ above the average hour): {', '.join(f'{int(h)}:00' for h in sorted(ph[ph.is_peak].order_hour))}.")
md.append(f"- Peak days: {', '.join(pdays[pdays.is_peak].day_name) or 'none above 25%'}; busiest weekday {pdays.sort_values('peak_index').iloc[-1].day_name} (index {float(pdays.peak_index.max()):.2f}).")
mt = num(A("monthly_trend")).sort_values("month_index")
md.append(f"- Busiest month {mt.iloc[-1].order_month} (index {float(mt.iloc[-1].month_index):.2f}); quietest {mt.iloc[0].order_month} ({float(mt.iloc[0].month_index):.2f}).")
w = num(A("wastage_by_item")).sort_values("wastage_cost", ascending=False)
md.append("\n## Wastage (Step 23)\n")
md.append(f"- The 5 dishes with the highest wastage COST: " + ", ".join(f"{r.item_name} ({float(r.share_of_total_wastage_cost):.1%} of waste cost)" for r in w.head(5).itertuples()) + ".")
wc = num(A("wastage_by_category")).sort_values("wastage_pct", ascending=False)
md.append(f"- Highest wastage % by category: " + ", ".join(f"{r.category_name} {float(r.wastage_pct):.1%}" for r in wc.head(3).itertuples()) + ".")
ch = num(A("channel_analysis")).sort_values("margin_after_fees_pct")
md.append("\n## Ordering channels (Step 35)\n")
for r in ch.itertuples():
    md.append(f"- {r.channel}: {float(r.order_share):.0%} of orders, average order {float(r.avg_order_value):,.0f} NGN, {float(r.avg_basket_units):.1f} units per basket, margin after fees {float(r.margin_after_fees_pct):.1%}.")
open(os.path.join(ROOT, "reports", "phase4a_menu_customers_baskets.md"), "w").write("\n".join(md) + "\n")
print("insights written")
