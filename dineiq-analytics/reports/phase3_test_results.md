# Phase 3 automated test results

**42 / 42 checks passed**

| Group | Check | Result | Detail |
|---|---|---|---|
| A integrity | fact table has one row per clean order line | PASS |  |
| A integrity | fact revenue = clean revenue | PASS |  |
| A integrity | fact has no missing unit cost | PASS |  |
| A integrity | fact: line_profit = line_total - quantity x unit_cost | PASS |  |
| A integrity | daily table: units, revenue = fact | PASS |  |
| A integrity | daily table key (date, restaurant, item) is unique | PASS |  |
| A integrity | order_features: one row per clean order | PASS |  |
| A integrity | order_features: revenue = sum of fact lines per order | PASS |  |
| A integrity | item_features: one row per menu item (168), units add up | PASS |  |
| A integrity | item_features: revenue and contribution margin add up | PASS |  |
| A integrity | item_features: profit_pct = margin / revenue | PASS |  |
| A integrity | item_features: rates are between 0 and 1 | PASS |  |
| A integrity | customer_features: frequency adds up to identified orders | PASS |  |
| A integrity | customer_features: monetary adds up | PASS |  |
| A integrity | customer_features: RFM scores are 1..5 | PASS |  |
| A integrity | customer_features: customer_id unique, recency >= 1 | PASS |  |
| A integrity | location_features: one row per restaurant, orders add up | PASS |  |
| A integrity | location_features: revenue adds up | PASS |  |
| B known answers | both loss-makers have negative profit_pct | PASS | profit_pct [-0.102, -0.094] |
| B known answers | Double Cheeseburger: loss-making AND a top-25% best seller | PASS | 15,000 units, rank pct 0.83 |
| B known answers | Beef Shawarma Wrap: loss-making and sells above the chain median (mid-volume, not a top seller) | PASS |  |
| B known answers | hidden gems: margin above chain median, popularity below median | PASS | margin 78.8% vs 65.5% |
| B known answers | waste-heavy dishes: wastage_pct at least 2x the chain median | PASS |  |
| B known answers | star items: popular and high margin | PASS |  |
| B known answers | promotion-dependent dishes: promotion_dependency clearly above the rest | PASS | 64% vs 22% |
| B known answers | weekend-only dishes: weekend_share > 55% | PASS | [0.81, 0.79, 0.79, 0.82, 0.83, 0.81] |
| B known answers | new items are flagged is_new_item and have little history | PASS |  |
| B known answers | price-sensitive items show a price increase | PASS |  |
| B known answers | low-sensitivity premium items: fewer lost sales than price-sensitive ones (relative trend) | PASS | informational; elasticity is estimated properly in Phase 4 |
| B known answers | Hot Dog Classic: popular but poorly rated | PASS | rating 2.89 |
| B known answers | fake-review item: unverified ratings flagged and avg_rating_all > avg_rating | PASS | 300 unverified, 4.89 vs 3.81 |
| B known answers | loyal customers have the highest frequency | PASS | {'AT_RISK': 8.6, 'CHURNED': 5.5, 'FREQUENT': 9.5, 'LOYAL': 20.9, 'NEW': 2.9, 'OCCASIONAL': 2.0, 'PROMO_DRIVEN': 6.7} |
| B known answers | churned customers have the highest recency (longest silence) | PASS | {'AT_RISK': 101.0, 'CHURNED': 247.0, 'FREQUENT': 50.0, 'LOYAL': 24.0, 'NEW': 17.0, 'OCCASIONAL': 114.0, 'PROMO_DRIVEN': 80.0} |
| B known answers | churned customers have a recency above 100 days, loyal below 40 | PASS |  |
| B known answers | promo-driven customers have the highest campaign-promotion share | PASS | {'AT_RISK': 0.17, 'CHURNED': 0.15, 'FREQUENT': 0.17, 'LOYAL': 0.16, 'NEW': 0.12, 'OCCASIONAL': 0.14, 'PROMO_DRIVEN': 0.37} |
| B known answers | new customers are the youngest | PASS |  |
| B known answers | at-risk customers show declining frequency | PASS | {'AT_RISK': -0.9, 'CHURNED': -0.21, 'FREQUENT': -0.04, 'LOYAL': -0.15, 'NEW': 2.88, 'OCCASIONAL': 0.11, 'PROMO_DRIVEN': -0.04} |
| B known answers | RFM: loyal customers score higher than occasional ones | PASS |  |
| B known answers | new restaurant L24: late first order, fewer trading days | PASS |  |
| B known answers | L12 (competitor opens): order trend is the worst of all restaurants | PASS | -26% |
| B known answers | L09: 400 fake restaurant ratings are excluded from its rating | PASS |  |
| B known answers | L13 manual-discount restaurant has the highest average discount | PASS | informational |
