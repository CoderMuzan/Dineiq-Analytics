# Integration report (Spark SQL, SRS Step 6)

Scripts: `spark_sql/01_lookup_tables.sql`, `02_fact_order_lines.sql`, `03_daily_item_location.sql`.

## Relationships implemented

| # | Relationship (SRS Step 6) | Join key | Join type | Cardinality |
|---|---|---|---|---|
| 1 | Orders with customers | orders.customer_id = customers.customer_id | LEFT (guests have no customer) | many orders : 1 customer |
| 2 | Orders with order items | order_items.order_id = orders.order_id | INNER | 1 order : many lines |
| 3 | Order items with menu items | order_items.item_id = menu_items.item_id | INNER | many lines : 1 item |
| 4 | Menu items with categories | menu_items.category_id = menu_categories.category_id | INNER | many items : 1 category |
| 5 | Orders with restaurant locations | orders.location_id = restaurants.location_id | INNER | many orders : 1 restaurant |
| 6 | Orders with promotions | orders.promo_id = promotions.promo_id | LEFT (most orders have no promotion) | many orders : 1 promotion |
| 7 | Menu items with pricing history | item_id and the price period valid on the order date (as-of join through `cost_day`) | LEFT | 1 line : 1 price period |
| 8 | Menu items with ratings | daily table: (date, restaurant, item) | LEFT | day-grain aggregate |
| 9 | Menu items with inventory | daily table: week_start_date + restaurant + item | LEFT | weekly stock row : 7 days |
| 10 | Menu items with wastage | daily table: (date, restaurant, item) | LEFT | day-grain aggregate |

Ratings, wastage and inventory have a different grain from order lines, so they are first aggregated to day x restaurant x item and only then joined (joining them directly to order lines would multiply rows and inflate sums).

## Join integrity checks

| Check | Result | Detail |
|---|---|---|
| fact_order_lines row count = clean order_items | PASS | 1,096,701 vs 1,096,701 |
| fact_order_lines has no duplicated order_line_id | PASS | 1,096,701 distinct |
| fact units = clean units | PASS | 1,464,027 vs 1,464,027 |
| fact revenue = clean revenue | PASS | 6,147,583,414.75 vs 6,147,583,414.75 |
| every line has an item name | PASS | 0 missing |
| every line has a category | PASS | 0 missing |
| every line has a restaurant | PASS | 0 missing |
| every line has a unit cost (price history covers the order date) | PASS | 0 missing |
| every promo_id resolves to a promotion | PASS | 0 orphans |
| every identified customer resolves to a customer profile | PASS | 0 orphans |
| daily table units = fact units | PASS | 1,464,027 vs 1,464,027 |
| daily table revenue = fact revenue | PASS | 6,147,583,414.75 vs 6,147,583,414.75 |
| daily table wasted portions = clean wastage | PASS | 108,230 vs 108,230 |
| daily table ratings = verified item ratings | PASS | 110,107 vs 110,107 |

Output sizes: `fact_order_lines` 1,096,701 rows; `daily_item_location` 610,428 rows (610,108 of them have a weekly inventory record).
