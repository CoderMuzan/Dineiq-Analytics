-- 05_item_features.sql : one row per menu item (SRS Step 7: revenue, cost, margin, popularity, repeat rate, rating,
-- rating trend, wastage, promotion dependency, discount %, price change ...)
-- Parameters: ${SNAPSHOT} (day after the last order)  ${TREND_DAYS}  ${RATING_WINDOW}  ${NEW_ITEM_DAYS}

CREATE OR REPLACE TEMP VIEW chain_totals AS
SELECT COUNT(DISTINCT order_id) AS total_orders, SUM(quantity) AS total_units, SUM(line_total) AS total_revenue,
       SUM(CASE WHEN order_date > date_sub(to_date('${SNAPSHOT}'), ${TREND_DAYS}) THEN quantity ELSE 0 END) AS chain_recent_units,
       SUM(CASE WHEN order_date <= date_sub(to_date('${SNAPSHOT}'), ${TREND_DAYS})
                 AND order_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${TREND_DAYS}) THEN quantity ELSE 0 END) AS chain_prior_units
FROM fact_order_lines;

CREATE OR REPLACE TEMP VIEW item_sales AS
SELECT item_id,
       SUM(quantity) AS units_sold, SUM(line_total) AS revenue, SUM(line_gross) AS gross_revenue,
       SUM(discount_amount) AS discount_total, SUM(line_cost) AS ingredient_cost, SUM(line_profit) AS contribution_margin,
       COUNT(DISTINCT order_id) AS n_orders, COUNT(DISTINCT location_id) AS n_locations,
       COUNT(DISTINCT order_date) AS active_days, MIN(order_date) AS first_sale_date, MAX(order_date) AS last_sale_date,
       SUM(CASE WHEN is_discounted_line THEN quantity ELSE 0 END) AS discounted_units,
       SUM(CASE WHEN is_weekend THEN quantity ELSE 0 END) AS weekend_units,
       SUM(CASE WHEN order_date > date_sub(to_date('${SNAPSHOT}'), ${TREND_DAYS}) THEN quantity ELSE 0 END) AS recent_units,
       SUM(CASE WHEN order_date <= date_sub(to_date('${SNAPSHOT}'), ${TREND_DAYS})
                 AND order_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${TREND_DAYS}) THEN quantity ELSE 0 END) AS prior_units
FROM fact_order_lines GROUP BY item_id;

-- repeat purchase: share of identified customers who bought the item in 2 or more different orders
CREATE OR REPLACE TEMP VIEW item_repeat AS
SELECT item_id, COUNT(*) AS n_buyers, SUM(CASE WHEN n_orders >= 2 THEN 1 ELSE 0 END) AS n_repeat_buyers
FROM (SELECT item_id, customer_id, COUNT(DISTINCT order_id) AS n_orders
      FROM fact_order_lines WHERE NOT is_guest GROUP BY item_id, customer_id) t
GROUP BY item_id;

-- ratings tied to a real purchase = trusted; the rest (no order_id) are counted separately as 'unverified'
CREATE OR REPLACE TEMP VIEW item_rating AS
SELECT item_id, COUNT(*) AS n_ratings, AVG(rating_value) AS avg_rating,
       SUM(CASE WHEN rating_date > date_sub(to_date('${SNAPSHOT}'), ${RATING_WINDOW}) THEN 1 ELSE 0 END) AS n_recent_ratings,
       AVG(CASE WHEN rating_date > date_sub(to_date('${SNAPSHOT}'), ${RATING_WINDOW}) THEN rating_value END) AS avg_rating_recent,
       SUM(CASE WHEN rating_date <= date_sub(to_date('${SNAPSHOT}'), ${RATING_WINDOW})
                 AND rating_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${RATING_WINDOW}) THEN 1 ELSE 0 END) AS n_prior_ratings,
       AVG(CASE WHEN rating_date <= date_sub(to_date('${SNAPSHOT}'), ${RATING_WINDOW})
                 AND rating_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${RATING_WINDOW}) THEN rating_value END) AS avg_rating_prior
FROM ratings WHERE item_id IS NOT NULL AND has_purchase_link GROUP BY item_id;

CREATE OR REPLACE TEMP VIEW item_rating_all AS
SELECT item_id, COUNT(*) AS n_ratings_all, AVG(rating_value) AS avg_rating_all,
       SUM(CASE WHEN has_purchase_link THEN 0 ELSE 1 END) AS n_unverified_ratings
FROM ratings WHERE item_id IS NOT NULL GROUP BY item_id;

CREATE OR REPLACE TEMP VIEW item_waste AS
SELECT item_id, SUM(quantity_wasted) AS wasted_portions, SUM(wastage_cost) AS wastage_cost FROM wastage GROUP BY item_id;

CREATE OR REPLACE TEMP VIEW item_price AS
SELECT item_id, min_by(list_price, order_date) AS first_list_price, max_by(list_price, order_date) AS last_list_price,
       min_by(unit_cost, order_date) AS first_unit_cost, max_by(unit_cost, order_date) AS last_unit_cost,
       COUNT(DISTINCT list_price) - 1 AS n_price_changes
FROM cost_day GROUP BY item_id;

CREATE OR REPLACE TEMP VIEW item_features AS
SELECT m.item_id, m.item_name, m.category_id, cat.category_name, m.season_tag, m.is_active, m.available_from, m.available_to,
       COALESCE(s.units_sold, 0) AS units_sold,
       COALESCE(s.revenue, 0) AS revenue,
       COALESCE(s.ingredient_cost, 0) AS ingredient_cost,
       COALESCE(s.contribution_margin, 0) AS contribution_margin,
       CASE WHEN s.revenue > 0 THEN s.contribution_margin / s.revenue END AS profit_pct,
       CASE WHEN s.units_sold > 0 THEN s.contribution_margin / s.units_sold END AS margin_per_unit,
       COALESCE(s.n_orders, 0) AS n_orders,
       s.n_orders / t.total_orders AS order_frequency,                          -- share of all orders that contain the item
       s.units_sold / t.total_units AS popularity_share,                        -- share of all units sold
       PERCENT_RANK() OVER (ORDER BY COALESCE(s.units_sold, 0)) AS popularity_rank_pct,   -- 1.0 = best seller
       s.n_locations, s.active_days, s.first_sale_date, s.last_sale_date,
       datediff(to_date('${SNAPSHOT}'), s.first_sale_date) AS days_of_history,
       (datediff(to_date('${SNAPSHOT}'), s.first_sale_date) < ${NEW_ITEM_DAYS}) AS is_new_item,
       datediff(to_date('${SNAPSHOT}'), s.last_sale_date) AS days_since_last_sale,
       CASE WHEN rp.n_buyers > 0 THEN rp.n_repeat_buyers / rp.n_buyers END AS repeat_purchase_rate,
       rp.n_buyers AS n_identified_buyers,
       r.avg_rating, COALESCE(r.n_ratings, 0) AS n_ratings,
       CASE WHEN r.n_recent_ratings >= 5 AND r.n_prior_ratings >= 5 THEN r.avg_rating_recent - r.avg_rating_prior END AS rating_trend,
       ra.avg_rating_all, COALESCE(ra.n_unverified_ratings, 0) AS n_unverified_ratings,
       COALESCE(w.wasted_portions, 0) AS wasted_portions, COALESCE(w.wastage_cost, 0) AS wastage_cost,
       CASE WHEN COALESCE(s.units_sold, 0) + COALESCE(w.wasted_portions, 0) > 0
            THEN COALESCE(w.wasted_portions, 0) / (COALESCE(s.units_sold, 0) + COALESCE(w.wasted_portions, 0)) END AS wastage_pct,
       CASE WHEN s.units_sold > 0 THEN s.discounted_units / s.units_sold END AS promotion_dependency,
       CASE WHEN s.gross_revenue > 0 THEN s.discount_total / s.gross_revenue END AS avg_discount_pct,
       CASE WHEN s.units_sold > 0 THEN s.weekend_units / s.units_sold END AS weekend_share,
       COALESCE(s.recent_units, 0) AS recent_units, COALESCE(s.prior_units, 0) AS prior_units,
       CASE WHEN s.prior_units >= 20 THEN s.recent_units / s.prior_units - 1 END AS sales_trend_pct,
       CASE WHEN s.prior_units >= 20 AND t.chain_prior_units > 0 AND t.chain_recent_units > 0
            THEN (s.recent_units / s.prior_units) / (t.chain_recent_units / t.chain_prior_units) - 1 END AS relative_sales_trend_pct,
       p.first_list_price, p.last_list_price, p.n_price_changes,
       CASE WHEN p.first_list_price > 0 THEN p.last_list_price / p.first_list_price - 1 END AS price_change_pct,
       CASE WHEN p.first_unit_cost > 0 THEN p.last_unit_cost / p.first_unit_cost - 1 END AS cost_change_pct
FROM menu_items m
JOIN menu_categories cat ON m.category_id = cat.category_id
CROSS JOIN chain_totals t
LEFT JOIN item_sales s ON m.item_id = s.item_id
LEFT JOIN item_repeat rp ON m.item_id = rp.item_id
LEFT JOIN item_rating r ON m.item_id = r.item_id
LEFT JOIN item_rating_all ra ON m.item_id = ra.item_id
LEFT JOIN item_waste w ON m.item_id = w.item_id
LEFT JOIN item_price p ON m.item_id = p.item_id;
