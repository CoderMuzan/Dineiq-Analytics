# DineIQ Analytics - Phase 3 guide: Spark SQL integration and feature engineering

SRS steps covered: **6** (data integration with Spark SQL / PySpark joins) and **7** (feature engineering).

## Run
```
cd spark_jobs
python 04_integrate_spark_sql.py --root ..     # -> processed_data/fact_order_lines, daily_item_location, reports/integration_report.md
python 05_feature_engineering.py --root ..     # -> processed_data/features/*, reports/feature_catalogue.md
cd ..
python tests/test_phase3_features.py --root .  # -> reports/phase3_test_results.md  (42 checks)
```
About 2 minutes for both jobs at full size (one CPU core). The SQL itself lives in `spark_sql/*.sql` so you can read and edit it without touching Python.

## Step 6 - integration (spark_sql/01-03)
| Output | Grain | Rows (seed 42) |
|---|---|---|
| `fact_order_lines` | one cleaned order line, with customer, order, restaurant, promotion, item, category, price and cost attached | 1,096,701 |
| `daily_item_location` | day x restaurant x menu item: sales, wastage, verified ratings, weekly inventory | 610,428 |

All ten relationships required by the SRS are implemented; the table of join keys, join types and cardinalities is in `reports/integration_report.md`.
Three ideas to be able to explain:
1. **As-of join for prices.** `cost_day` gives the list price and unit cost of every item on every day: for each (item, day) it keeps the pricing_history row with the latest `effective_from` that is not after that day (`ROW_NUMBER() ... ORDER BY effective_from DESC`, keep rank 1).
   If an item's first price period was removed by cleaning, the earliest valid period is used; if it has none, the menu's base price and cost are used.
2. **Different grains are aggregated first.** Ratings, wastage and inventory are not per order line. Joining them directly to lines would multiply rows and inflate sums, so they are aggregated to day x restaurant x item before joining.
3. **Join integrity is tested, not assumed.** The job stops if the fact table has a different row count, units or revenue from `clean_data/order_items`, or if any line lacks an item, category, restaurant or cost (14 checks, all PASS).

## Step 7 - features (spark_sql/04-07)
Every column is explained in `reports/feature_catalogue.md` (the job lists any undocumented column). Summary:
| Table | Rows | Highlights |
|---|---|---|
| `order_features` | 368,132 | basket size, categories, peak-hour and weekend flags, contribution margin, margin after platform fees, discount % |
| `item_features` | 168 | revenue, cost, contribution margin, profit %, popularity, order frequency, repeat-purchase rate, average rating and rating trend, wastage %, promotion dependency, discount %, weekend share, sales trend (absolute and relative to the chain), price change %, days of history / new-item flag |
| `customer_features` | 54,293 | RFM (recency, frequency, monetary + 1-5 scores), average order value, basket size, peak-hour frequency, weekend ratio, channel preference, favourite category and diversity, promotion sensitivity, 90-day vs previous-90-day frequency and spend |
| `location_features` | 24 | revenue, margin, average order value, customers, repeat rate, wastage, cancellation rate, verified ratings, promotion share, revenue per seat, order trend |

Decisions to defend:
- **Profit** here = contribution margin = revenue after discount minus ingredient cost on the order date. Platform commission is an order-level cost, so it appears in order and restaurant features only.
- **Ratings without a purchase are excluded** from average ratings (they include the planted fake-review bursts) and counted separately as `n_unverified_ratings`.
- **Two promotion features.** `promo_order_share` counts any promotion, but welcome (first order) and loyalty promotions are automatic entitlements, so loyal and new customers score high without being deal chasers. `campaign_promo_share` counts only public campaigns and is the real promotion-sensitivity feature. (The test caught this: the first version ranked loyal customers as the most promotion-driven.)
- **RFM scores use PERCENT_RANK**, not NTILE, so customers with identical values get identical scores.
- **Relative trends**: an item's sales trend is also reported relative to the whole chain, to remove seasonality and growth shared by all items.
- **Guests** (no customer id) are excluded from customer features but kept in orders, items and restaurants.

## Honest limits
- Features use the whole year with a snapshot on 2026-10-01. For forecasting or any time-based model, rebuild features using only data before the prediction date (SRS Step 21).
- Cost for a price period removed by cleaning falls back to the previous period's cost (or base cost), so profit for those few days is approximate.
- No churn label is defined yet; `frequency_change`, `recency_days` and `spend_change_pct` are the churn signals for Phase 4.
- The ground-truth tests need the generator's `_ground_truth` files; on the hidden evaluation dataset only the integrity checks apply.

## Next: Phase 4 - EDA, menu classification, segmentation, basket analysis, forecasting, wastage, pricing and promotion analytics, Spark MLlib models and the independent Python models.
