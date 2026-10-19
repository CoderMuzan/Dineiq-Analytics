# Data Quality Report (raw layer)

Assessed by Spark 4.2.0 against the explicit schemas in `spark_common.py`. Valid order period: 2025-10-01 .. 2026-09-30.

Nothing is changed in this step. The cleaning decisions taken for every finding are in `cleaning_decisions.md`.

| Table | Check | Rule | Rows | % of table | Severity |
|---|---|---|---|---|---|
| inventory | Negative stock | closing_stock < 0 | 96 | 0.048% | HIGH |
| inventory | Inconsistent units | unit is not 'portion' (kg rows must be converted) | 3,873 | 1.954% | HIGH |
| order_items | Duplicate order lines | same order_line_id appears more than once (extra copies) | 3,462 | 0.299% | HIGH |
| order_items | Missing menu id | item_id is NULL | 1,104 | 0.095% | HIGH |
| order_items | Unknown menu id | item_id not in menu_items | 1,164 | 0.101% | HIGH |
| order_items | Negative or zero quantity | quantity <= 0 | 602 | 0.052% | HIGH |
| order_items | Missing quantity | quantity is NULL | 0 | 0.000% | HIGH |
| order_items | Invalid menu price | unit_price <= 0 | 469 | 0.041% | HIGH |
| order_items | Extreme menu price | unit_price more than 4x the item's median list price | 207 | 0.018% | HIGH |
| order_items | Incorrect discount | discount < 0 or discount > quantity x unit_price | 906 | 0.078% | HIGH |
| order_items | Orphan order lines | order_id not found in orders | 0 | 0.000% | HIGH |
| orders | Duplicate orders | same order_id appears more than once (extra copies) | 1,545 | 0.398% | HIGH |
| orders | Missing order date | order_datetime is NULL | 0 | 0.000% | HIGH |
| orders | Invalid date (unparseable) | order_datetime is not 'yyyy-MM-dd HH:mm:ss' (e.g. 2026-13-45) | 127 | 0.033% | HIGH |
| orders | Invalid date (out of period) | parsed date outside 2025-10-01 .. 2026-09-30 | 64 | 0.017% | HIGH |
| orders | Missing restaurant id | location_id is NULL | 234 | 0.060% | HIGH |
| orders | Invalid restaurant id | location_id not in restaurants | 376 | 0.097% | HIGH |
| orders | Negative order total | total_amount < 0 | 0 | 0.000% | HIGH |
| orders | Duplicate transactions (near-duplicates) | same customer, restaurant, channel, basket and total again within 200 seconds | 331 | 0.085% | HIGH |
| pricing_history | Invalid menu prices | price <= 0 or outside 0.5x..3.0x of base_price | 6 | 1.373% | HIGH |
| ratings | Invalid ratings | rating_value not in 1..5 | 294 | 0.209% | HIGH |
| wastage | Inconsistent units | unit is not 'portion' (found: PORTION, Portion, g, kg, pcs, portion, portions) | 8,106 | 8.975% | HIGH |
| wastage | Impossible wastage quantities | quantity <= 0, more than was prepared, or > 1000 portions | 50 | 0.055% | HIGH |
| customers | Duplicate customers | same customer_id appears more than once | 110 | 0.200% | MEDIUM |
| customers | Missing age band | age_band is NULL | 2,155 | 3.910% | MEDIUM |
| customers | Invalid home restaurant | home_location_id not in restaurants | 0 | 0.000% | MEDIUM |
| inventory | Invalid restaurant id | location_id not in restaurants | 106 | 0.053% | MEDIUM |
| order_items | Line total does not add up | line_total != quantity x unit_price - discount | 0 | 0.000% | MEDIUM |
| orders | Missing payment method | payment_method is NULL | 7,783 | 2.005% | MEDIUM |
| orders | Unknown promotion id | promo_id not in promotions | 0 | 0.000% | MEDIUM |
| pricing_history | Item without valid price | item_id not in menu_items | 0 | 0.000% | MEDIUM |
| ratings | Invalid restaurant id | location_id not in restaurants | 75 | 0.053% | MEDIUM |
| wastage | Missing menu id | item_id is NULL | 52 | 0.058% | MEDIUM |
| wastage | Invalid restaurant id | location_id not in restaurants | 38 | 0.042% | MEDIUM |
| menu_items | Missing description | description is NULL | 4 | 2.381% | INFO |
| orders | Missing customer id | customer_id is NULL (guest checkout - legitimate, but no customer analytics possible) | 46,704 | 12.033% | INFO |
| orders | Cancelled transactions | order_status = CANCELLED | 11,484 | 2.959% | INFO |
| orders | Refunded transactions | order_status = REFUNDED | 3,587 | 0.924% | INFO |
| orders | Void transactions | order_status = VOID | 2,221 | 0.572% | INFO |
| ratings | Ratings without a purchase | order_id is NULL (not an error, but suspicious - used by anomaly detection) | 880 | 0.626% | INFO |
| ratings | Restaurant-level ratings | item_id is NULL (rating of the restaurant, not a dish) | 29,759 | 21.171% | INFO |

**Summary:** 41 checks, 19 HIGH-severity problems present, 33 checks with at least one affected row.
