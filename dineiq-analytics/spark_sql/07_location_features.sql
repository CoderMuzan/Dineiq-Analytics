-- 07_location_features.sql : one row per restaurant (SRS Step 7 "location performance"; Step 33 inputs)
-- Parameters: ${SNAPSHOT}  ${TREND_DAYS}

CREATE OR REPLACE TEMP VIEW loc_core AS
SELECT location_id,
       COUNT(*) AS n_orders, ROUND(SUM(revenue), 2) AS revenue, ROUND(SUM(contribution_margin), 2) AS contribution_margin,
       ROUND(SUM(margin_after_fees), 2) AS margin_after_fees, SUM(basket_units) AS units_sold,
       AVG(total_amount) AS avg_order_value, COUNT(DISTINCT customer_id) AS n_customers,
       AVG(discount_pct) AS avg_discount_pct,
       AVG(CASE WHEN has_promo THEN 1D ELSE 0D END) AS promo_order_share,
       AVG(CASE WHEN channel IN ('WEBSITE_APP', 'THIRD_PARTY_DELIVERY') THEN 1D ELSE 0D END) AS online_order_share,
       AVG(CASE WHEN is_weekend THEN 1D ELSE 0D END) AS weekend_order_share,
       MIN(order_date) AS first_order_date, COUNT(DISTINCT order_date) AS trading_days,
       SUM(CASE WHEN order_date > date_sub(to_date('${SNAPSHOT}'), ${TREND_DAYS}) THEN 1 ELSE 0 END) AS orders_recent,
       SUM(CASE WHEN order_date <= date_sub(to_date('${SNAPSHOT}'), ${TREND_DAYS})
                 AND order_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${TREND_DAYS}) THEN 1 ELSE 0 END) AS orders_prior
FROM order_features GROUP BY location_id;

CREATE OR REPLACE TEMP VIEW loc_repeat AS
SELECT location_id, AVG(CASE WHEN n >= 2 THEN 1D ELSE 0D END) AS repeat_customer_rate
FROM (SELECT location_id, customer_id, COUNT(*) AS n FROM order_features WHERE NOT is_guest GROUP BY location_id, customer_id) t
GROUP BY location_id;

CREATE OR REPLACE TEMP VIEW loc_cancel AS
SELECT location_id, COUNT(*) AS n_cancelled_orders FROM cancelled_orders GROUP BY location_id;

CREATE OR REPLACE TEMP VIEW loc_waste AS
SELECT location_id, SUM(quantity_wasted) AS wasted_portions, SUM(wastage_cost) AS wastage_cost FROM wastage GROUP BY location_id;

-- ratings tied to a real purchase only (the 400-rating one-day burst has no order_id and is excluded)
CREATE OR REPLACE TEMP VIEW loc_rating AS
SELECT location_id,
       AVG(CASE WHEN item_id IS NULL THEN rating_value END) AS avg_restaurant_rating,
       AVG(CASE WHEN item_id IS NOT NULL THEN rating_value END) AS avg_item_rating,
       COUNT(*) AS n_ratings
FROM ratings WHERE has_purchase_link GROUP BY location_id;

CREATE OR REPLACE TEMP VIEW loc_items AS
SELECT location_id, COUNT(DISTINCT item_id) AS n_items_sold FROM fact_order_lines GROUP BY location_id;

CREATE OR REPLACE TEMP VIEW location_features AS
SELECT r.location_id, r.restaurant_name, r.city, r.region, r.size_tier, r.seating_capacity, r.opening_date,
       c.n_orders, c.revenue, c.contribution_margin, c.margin_after_fees,
       c.margin_after_fees / c.revenue AS margin_after_fees_pct,
       c.units_sold, c.avg_order_value, c.n_customers, rp.repeat_customer_rate,
       c.avg_discount_pct, c.promo_order_share, c.online_order_share, c.weekend_order_share,
       c.first_order_date, c.trading_days, c.n_orders / c.trading_days AS orders_per_trading_day,
       c.revenue / c.trading_days AS revenue_per_trading_day, c.revenue / r.seating_capacity AS revenue_per_seat,
       COALESCE(cn.n_cancelled_orders, 0) AS n_cancelled_orders,
       COALESCE(cn.n_cancelled_orders, 0) / (c.n_orders + COALESCE(cn.n_cancelled_orders, 0)) AS cancellation_rate,
       COALESCE(w.wasted_portions, 0) AS wasted_portions, COALESCE(w.wastage_cost, 0) AS wastage_cost,
       COALESCE(w.wasted_portions, 0) / (c.units_sold + COALESCE(w.wasted_portions, 0)) AS wastage_pct,
       COALESCE(w.wastage_cost, 0) / c.revenue AS wastage_cost_pct_revenue,
       q.avg_restaurant_rating, q.avg_item_rating, q.n_ratings, i.n_items_sold,
       c.orders_recent, c.orders_prior,
       CASE WHEN c.orders_prior >= 50 THEN c.orders_recent / c.orders_prior - 1 END AS order_trend_pct
FROM restaurants r
JOIN loc_core c ON r.location_id = c.location_id
LEFT JOIN loc_repeat rp ON r.location_id = rp.location_id
LEFT JOIN loc_cancel cn ON r.location_id = cn.location_id
LEFT JOIN loc_waste w ON r.location_id = w.location_id
LEFT JOIN loc_rating q ON r.location_id = q.location_id
LEFT JOIN loc_items i ON r.location_id = i.location_id;
