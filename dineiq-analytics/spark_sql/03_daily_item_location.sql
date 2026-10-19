-- 03_daily_item_location.sql : grain = day x restaurant x menu item
-- Brings sales, wastage, ratings and inventory (tables with DIFFERENT grains) onto one common grain.
-- (SRS Step 6: menu items <-> ratings, inventory, wastage).  This table is the base for wastage analysis and demand forecasting.

CREATE OR REPLACE TEMP VIEW d_sales AS
SELECT order_date AS date, location_id, item_id,
       SUM(quantity) AS units_sold, SUM(line_total) AS revenue, SUM(line_gross) AS gross_revenue,
       SUM(discount_amount) AS discount_total, SUM(line_cost) AS ingredient_cost, SUM(line_profit) AS contribution_margin,
       COUNT(DISTINCT order_id) AS n_orders,
       SUM(CASE WHEN is_discounted_line THEN quantity ELSE 0 END) AS discounted_units
FROM fact_order_lines
GROUP BY order_date, location_id, item_id;

CREATE OR REPLACE TEMP VIEW d_waste AS
SELECT wastage_date AS date, location_id, item_id,
       SUM(quantity_wasted) AS wasted_portions, SUM(wastage_cost) AS wastage_cost, MAX(prep_quantity) AS prep_portions
FROM wastage
GROUP BY wastage_date, location_id, item_id;

-- only ratings that are linked to a real purchase are used for item quality (unlinked ones are suspected fakes)
CREATE OR REPLACE TEMP VIEW d_rating AS
SELECT rating_date AS date, location_id, item_id, COUNT(*) AS n_ratings, AVG(rating_value) AS avg_rating
FROM ratings
WHERE item_id IS NOT NULL AND has_purchase_link
GROUP BY rating_date, location_id, item_id;

CREATE OR REPLACE TEMP VIEW d_keys AS
SELECT date, location_id, item_id FROM d_sales
UNION SELECT date, location_id, item_id FROM d_waste
UNION SELECT date, location_id, item_id FROM d_rating;

-- inventory is WEEKLY: week_start = DATE_MIN + 7 * whole weeks since DATE_MIN
CREATE OR REPLACE TEMP VIEW d_keys_wk AS
SELECT k.*, date_add(to_date('${DATE_MIN}'), 7 * CAST(floor(datediff(k.date, to_date('${DATE_MIN}')) / 7) AS INT)) AS week_start_date
FROM d_keys k;

CREATE OR REPLACE TEMP VIEW daily_item_location AS
SELECT k.date, k.location_id, k.item_id, weekday(k.date) AS day_of_week, (weekday(k.date) >= 5) AS is_weekend,
       COALESCE(s.units_sold, 0) AS units_sold, COALESCE(s.revenue, 0) AS revenue, COALESCE(s.gross_revenue, 0) AS gross_revenue,
       COALESCE(s.discount_total, 0) AS discount_total, COALESCE(s.ingredient_cost, 0) AS ingredient_cost,
       COALESCE(s.contribution_margin, 0) AS contribution_margin, COALESCE(s.n_orders, 0) AS n_orders,
       COALESCE(s.discounted_units, 0) AS discounted_units,
       COALESCE(w.wasted_portions, 0) AS wasted_portions, COALESCE(w.wastage_cost, 0) AS wastage_cost, w.prep_portions,
       COALESCE(q.n_ratings, 0) AS n_ratings, q.avg_rating,
       i.closing_stock AS stock_week_end, i.consumed_qty AS consumed_week, i.reorder_level, i.stockout_flag AS stockout_week
FROM d_keys_wk k
LEFT JOIN d_sales  s ON k.date = s.date AND k.location_id = s.location_id AND k.item_id = s.item_id
LEFT JOIN d_waste  w ON k.date = w.date AND k.location_id = w.location_id AND k.item_id = w.item_id
LEFT JOIN d_rating q ON k.date = q.date AND k.location_id = q.location_id AND k.item_id = q.item_id
LEFT JOIN inventory i ON i.week_start_date = k.week_start_date AND i.location_id = k.location_id AND i.item_id = k.item_id;
