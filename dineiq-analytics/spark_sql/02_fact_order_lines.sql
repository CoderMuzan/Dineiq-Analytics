-- 02_fact_order_lines.sql : ONE wide table, one row per cleaned order line (SRS Step 6, required relationships)
--   orders <-> customers          LEFT JOIN  (guest orders have no customer)
--   orders <-> order_items        JOIN
--   order_items <-> menu_items    JOIN
--   menu_items <-> categories     JOIN
--   orders <-> restaurants        JOIN
--   orders <-> promotions         LEFT JOIN  (most orders have no promotion)
--   menu_items <-> pricing_history  LEFT JOIN through cost_day (price and cost valid on the order date)
-- Inner joins must NOT lose rows: the Python runner checks row count and revenue against clean_data/order_items.

CREATE OR REPLACE TEMP VIEW fact_order_lines AS
SELECT
  l.order_line_id, l.order_id,
  o.order_ts, o.order_date, o.order_month, o.order_hour,
  weekday(o.order_date)              AS day_of_week,        -- 0 = Monday ... 6 = Sunday
  (weekday(o.order_date) >= 5)       AS is_weekend,
  o.channel, o.location_id, r.restaurant_name, r.city, r.region, r.size_tier,
  o.customer_id, o.is_guest, c.loyalty_member, c.signup_date,
  o.promo_id, p.promo_type, p.discount_pct AS promo_discount_pct,
  l.item_id, m.item_name, m.category_id, cat.category_name,
  l.quantity, l.unit_price,
  l.quantity * l.unit_price          AS line_gross,
  l.discount_amount,
  (l.discount_amount > 0)            AS is_discounted_line,
  l.line_total,
  cd.unit_cost,
  l.quantity * cd.unit_cost          AS line_cost,
  l.line_total - l.quantity * cd.unit_cost AS line_profit    -- contribution margin: revenue after discount minus ingredient cost
FROM order_items l
JOIN orders o            ON l.order_id = o.order_id
JOIN menu_items m        ON l.item_id = m.item_id
JOIN menu_categories cat ON m.category_id = cat.category_id
JOIN restaurants r       ON o.location_id = r.location_id
LEFT JOIN customers c    ON o.customer_id = c.customer_id
LEFT JOIN promotions p   ON o.promo_id = p.promo_id
LEFT JOIN cost_day cd    ON l.item_id = cd.item_id AND o.order_date = cd.order_date;
