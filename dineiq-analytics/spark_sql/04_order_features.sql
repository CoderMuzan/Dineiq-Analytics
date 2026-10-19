-- 04_order_features.sql : one row per cleaned order (basket size, time flags, margin after platform fees)
-- Peak hours = 12:00-14:59 and 18:00-21:59 (business assumption, change here if the evaluators ask).

CREATE OR REPLACE TEMP VIEW order_features AS
SELECT o.order_id, o.order_ts, o.order_date, o.order_month, o.order_hour,
       weekday(o.order_date) AS day_of_week,
       (weekday(o.order_date) >= 5) AS is_weekend,
       (o.order_hour BETWEEN 12 AND 14 OR o.order_hour BETWEEN 18 AND 21) AS is_peak_hour,
       o.location_id, o.channel, o.customer_id, o.is_guest, o.payment_method,
       o.promo_id, (o.promo_id IS NOT NULL) AS has_promo, pr.promo_type,
       -- campaign promotion = a public offer the customer chose to chase (NOT the automatic welcome / loyalty entitlements)
       (pr.promo_type IS NOT NULL AND pr.promo_type NOT IN ('NEW_CUSTOMER', 'LOYALTY')) AS has_campaign_promo,
       o.party_size,
       a.basket_lines, a.basket_units, a.n_categories,
       a.gross_revenue, a.discount_total, a.revenue, a.ingredient_cost,
       a.revenue - a.ingredient_cost AS contribution_margin,
       o.delivery_fee, o.platform_fee, o.total_amount,
       a.revenue - a.ingredient_cost - o.platform_fee AS margin_after_fees,
       CASE WHEN a.revenue > 0 THEN (a.revenue - a.ingredient_cost - o.platform_fee) / a.revenue END AS margin_pct,
       CASE WHEN a.gross_revenue > 0 THEN a.discount_total / a.gross_revenue ELSE 0 END AS discount_pct
FROM orders o
LEFT JOIN promotions pr ON o.promo_id = pr.promo_id
JOIN (
  SELECT order_id, COUNT(*) AS basket_lines, SUM(quantity) AS basket_units, COUNT(DISTINCT category_id) AS n_categories,
         SUM(line_gross) AS gross_revenue, SUM(discount_amount) AS discount_total, SUM(line_total) AS revenue,
         SUM(line_cost) AS ingredient_cost
  FROM fact_order_lines GROUP BY order_id
) a ON o.order_id = a.order_id;
