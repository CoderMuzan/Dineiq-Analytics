# DineIQ Analytics - Phase 4 guide (part 1): analytics

This part turns the features into business insight. **The machine-learning half of Phase 4 is not built yet** (see the table at the end).

## Run (about 11 minutes for the three jobs on one CPU core)
```
cd spark_jobs
python 06_analytics_sql.py                  --root ..     # Spark SQL: EDA, menu, customers, baskets, peaks, wastage, channels
python 07_pricing_promotions_locations.py   --root ..     # price sensitivity, promotion effectiveness and traps, location scorecard
python 08_anomalies_satisfaction.py         --root ..     # sales anomalies, rating anomalies, satisfaction analysis
cd ..
python tests/test_phase4_analytics.py --root .            # 59 checks
```
Outputs: `processed_data/analytics/<table>/` (Parquet, 50 tables), `reports/tables/*.csv` (the same tables for Excel),
and three generated finding reports: `reports/phase4a_menu_customers_baskets.md`, `phase4b_pricing_promotions_locations.md`, `phase4b_anomalies_satisfaction.md`.
The reports are written by code from the data (no hand-typed numbers), which is what the SRS means by "insights rather than only visualizations".

## What each job covers
| Job | SRS steps | Method in one line |
|---|---|---|
| 06 (SQL 10-15) | 8 EDA, 9-11 menu profitability / classification / tricky cases, 15-16 segmentation and RFM, 17-18 baskets and bundles, 19 peak periods, 23 wastage, 32 slow-moving dishes, 34 per-restaurant menu classes, 35 channels, 36 churn risk (rules) | Spark SQL on the feature tables |
| 07 | 25-26 price intelligence and sensitivity, 27-28 promotion effectiveness and trap detection, 33 location comparison | Spark builds daily / weekly summaries, pandas does the statistics |
| 08 | 29 satisfaction analysis, 30 rating anomalies, 31 sales anomalies | robust statistics (median / MAD) on small summaries |

## Decisions you must be able to defend
**Menu classification (SQL 11).** Menu-engineering style, all thresholds computed from the data: demand is high when units per day on the menu >= 70% of the average dish;
profit is high when profit % >= the chain's profit %; wastage is excessive above 2x the chain's. PROFIT_DRIVER = both high and wastage acceptable; VOLUME_DRIVER = high demand but lower profit
(or profit eroded by wastage); HIDDEN_OPPORTUNITY = profitable (also after wastage cost), good rating or repeat purchase, but not high demand; everything else, and every dish that loses money, is LOW_PERFORMER.
New dishes are classified provisionally with confidence LOW_NEW_ITEM. The class is never read from a single field, and no dish name appears in the SQL.

**Per-restaurant classes and "performs differently across restaurants".** The same rules run inside each restaurant. A dish is flagged location-inconsistent when its demand index
(its units/day relative to that restaurant's average dish, divided by the same ratio chain-wide) varies more between restaurants than 90% of dishes AND it falls in at least two classes.

**Customer segments (SQL 12).** First match wins: NEW (first order within 100 days), LOST (3+ orders, silent over 180 days), AT_RISK (3+ orders and silent longer than max(60 days, 3x the
customer's own usual gap), or orders falling by 3+), PROMOTION_DRIVEN (30%+ of orders use a public campaign promotion; the typical customer is at 17%), HIGH_VALUE_LOYAL, FREQUENT, OCCASIONAL.
Churn risk is a transparent signal count (overdue, orders falling, spend falling, long silence); a trained churn model is part of the next step.

**Market basket (SQL 13).** support = joint orders / all orders; confidence = joint orders / orders with A; lift = confidence / share of orders with B.
Pairs under 100 joint orders are ignored; recommendations need lift >= 2, 150+ joint orders and confidence >= 8%, and every row carries its evidence text.
The tests recompute support, confidence and lift for the top rules directly from raw order lines.

**Price sensitivity (job 07).** Weekly regression of ln(dish share of chain units) on ln(price relative to the chain price index), after removing weeks in which the dish was in a running
discount promotion. HIGHLY sensitive needs elasticity <= -1.5 and the 95% upper bound below -1.0. Seasonal dishes and dishes without price variation are reported as INSUFFICIENT_*, never guessed.
A before/after event table (28 days around every price change, relative to the whole chain) is kept as supporting evidence.

**Promotions (job 07).** Each promotion is compared with up to 28 matching days before it (same weekdays, excluding days of other 15%+ promotions) and 14 days after. Traps: SALES_UP_PROFIT_DOWN,
CUSTOMERS_UP_MARGIN_COLLAPSES, INCREASES_WASTAGE, SHIFTS_SALES_FROM_MORE_PROFITABLE_PRODUCT (a better-margin category loses 25%+ units per order), DISCOUNT_DEPENDENT_DEMAND. Promotions covering
only some dishes are judged per order, which removes most calendar effects.

**Anomalies (job 08).** A restaurant's expected daily orders = its usual share of chain orders on that weekday x the chain's orders that day (holidays do not trigger alarms), with a Poisson-like
noise allowance. Item surges are judged on the dish's share of chain units relative to the same weekday, and labelled "explained" when a running promotion covers the dish.

## Honest limits (put these in your report)
1. **One year of data.** Holidays and seasons cannot be separated from the effect of all-menu promotions (Black Friday, festive season, Easter). The report says so; use last year's data when you have it.
2. **Price sensitivity found 4 of the 6 planted dishes.** Ice Cream Sundae is seasonal (gated out) and Jollof Spaghetti sits inside a recurring Friday promotion that removes most of its weeks. No dish outside the six is called highly sensitive.
3. **71 of 168 dishes are LOW_PERFORMER.** The 70% rule is applied to a skewed distribution (a few drinks sell very many units), so many ordinary dishes fall below the demand cut. This is a known weakness of the method; the cut is one line to change in SQL 11.
4. **Slow-moving dishes (34)** include profitable low-volume dishes (hidden opportunities). Treat "slow-moving AND weak profit" as the removal list and "slow-moving AND profitable" as the promotion list.
5. **Sales anomaly recall is not perfect:** the L07 outage is reported for 3 of its 7 days and the viral Suya Pizza week for one day. Precision is good (no false restaurant spikes), recall on short events is limited.
6. **Rule-based segments and churn risk** were calibrated on this dataset's distributions (for example the 30% promotion share). Re-check the thresholds on the hidden evaluation data.
7. The tests use the generator's ground truth. On the hidden dataset only the structural checks apply.

## SRS coverage after this part
| Steps | Status |
|---|---|
| 8-11, 15-19, 23, 25-35, 36 (rules) | done and tested |
| 12-14 Spark MLlib models (3+ algorithms), independent Python pipeline, Spark-vs-Python comparison on 100+ unseen records | **not built** |
| 20-22 demand forecasting, time-aware validation, MAE / RMSE / MAPE | **not built** |
| 24 wastage-risk prediction; model-based churn prediction | **not built** |
| 37-39 recommendation engine with evidence and priority | **not built** (all its inputs now exist) |
| 40-41 what-if scenarios | **not built** |
| 42-50 dashboards, filters, reports, export | **not built** |
