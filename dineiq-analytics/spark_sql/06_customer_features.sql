-- 06_customer_features.sql : one row per IDENTIFIED customer who has at least one completed order
-- (guest orders cannot be attributed to a customer).  SRS Step 7: recency, frequency, monetary value, AOV, peak-hour frequency,
-- weekend-order ratio, channel preference, promotion sensitivity, favourite category ...
-- Parameters: ${SNAPSHOT}  ${RECENT_DAYS}

CREATE OR REPLACE TEMP VIEW cust_orders AS
SELECT * FROM order_features WHERE NOT is_guest;

CREATE OR REPLACE TEMP VIEW cust_core AS
SELECT customer_id,
       COUNT(*) AS frequency,
       ROUND(SUM(total_amount), 2) AS monetary,
       ROUND(AVG(total_amount), 2) AS avg_order_value,
       MIN(order_date) AS first_order_date, MAX(order_date) AS last_order_date,
       datediff(to_date('${SNAPSHOT}'), MAX(order_date)) AS recency_days,
       datediff(MAX(order_date), MIN(order_date)) AS span_days,
       COUNT(DISTINCT order_date) AS active_days, COUNT(DISTINCT order_month) AS active_months,
       AVG(basket_units) AS avg_basket_units, AVG(basket_lines) AS avg_basket_lines,
       AVG(CASE WHEN has_promo THEN 1D ELSE 0D END) AS promo_order_share,
       AVG(CASE WHEN has_campaign_promo THEN 1D ELSE 0D END) AS campaign_promo_share,
       AVG(discount_pct) AS avg_discount_pct,
       AVG(CASE WHEN is_peak_hour THEN 1D ELSE 0D END) AS peak_hour_share,
       AVG(CASE WHEN is_weekend THEN 1D ELSE 0D END) AS weekend_order_ratio,
       AVG(CASE WHEN channel IN ('WEBSITE_APP', 'THIRD_PARTY_DELIVERY') THEN 1D ELSE 0D END) AS online_order_share,
       COUNT(DISTINCT channel) AS n_channels, COUNT(DISTINCT location_id) AS n_locations,
       SUM(CASE WHEN order_date > date_sub(to_date('${SNAPSHOT}'), ${RECENT_DAYS}) THEN 1 ELSE 0 END) AS orders_recent,
       SUM(CASE WHEN order_date <= date_sub(to_date('${SNAPSHOT}'), ${RECENT_DAYS})
                 AND order_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${RECENT_DAYS}) THEN 1 ELSE 0 END) AS orders_prior,
       SUM(CASE WHEN order_date > date_sub(to_date('${SNAPSHOT}'), ${RECENT_DAYS}) THEN total_amount ELSE 0 END) AS spend_recent,
       SUM(CASE WHEN order_date <= date_sub(to_date('${SNAPSHOT}'), ${RECENT_DAYS})
                 AND order_date >  date_sub(to_date('${SNAPSHOT}'), 2 * ${RECENT_DAYS}) THEN total_amount ELSE 0 END) AS spend_prior
FROM cust_orders GROUP BY customer_id;

CREATE OR REPLACE TEMP VIEW cust_channel AS
SELECT customer_id, channel AS preferred_channel FROM (
  SELECT customer_id, channel, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY COUNT(*) DESC, channel) AS rn
  FROM cust_orders GROUP BY customer_id, channel) t WHERE rn = 1;

CREATE OR REPLACE TEMP VIEW cust_category AS
SELECT customer_id, category_name AS favorite_category, n_categories FROM (
  SELECT customer_id, category_name,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY SUM(quantity) DESC, category_name) AS rn,
         COUNT(*) OVER (PARTITION BY customer_id) AS n_categories
  FROM fact_order_lines WHERE NOT is_guest GROUP BY customer_id, category_name) t WHERE rn = 1;

-- RFM scores 1-5 (5 = best) from percent ranks. PERCENT_RANK gives tied customers the SAME score (NTILE would split ties arbitrarily).
CREATE OR REPLACE TEMP VIEW customer_features AS
SELECT c.customer_id, cu.signup_date, cu.age_band, cu.home_location_id, cu.acquisition_source, cu.loyalty_member,
       datediff(to_date('${SNAPSHOT}'), cu.signup_date) AS days_since_signup,
       c.recency_days, c.frequency, c.monetary,
       LEAST(5, FLOOR(PERCENT_RANK() OVER (ORDER BY c.recency_days DESC) * 5) + 1) AS r_score,
       LEAST(5, FLOOR(PERCENT_RANK() OVER (ORDER BY c.frequency) * 5) + 1) AS f_score,
       LEAST(5, FLOOR(PERCENT_RANK() OVER (ORDER BY c.monetary) * 5) + 1) AS m_score,
       c.avg_order_value, c.first_order_date, c.last_order_date, c.span_days, c.active_days, c.active_months,
       CASE WHEN c.frequency > 1 THEN c.span_days / (c.frequency - 1) END AS avg_days_between_orders,
       c.avg_basket_units, c.avg_basket_lines, c.promo_order_share, c.campaign_promo_share, c.avg_discount_pct, c.peak_hour_share,
       c.weekend_order_ratio, c.online_order_share, c.n_channels, c.n_locations,
       ch.preferred_channel, cat.favorite_category, cat.n_categories AS category_diversity,
       c.orders_recent, c.orders_prior, c.orders_recent - c.orders_prior AS frequency_change,
       c.spend_recent, c.spend_prior,
       CASE WHEN c.spend_prior > 0 THEN c.spend_recent / c.spend_prior - 1 END AS spend_change_pct
FROM cust_core c
LEFT JOIN customers cu ON c.customer_id = cu.customer_id
LEFT JOIN cust_channel ch ON c.customer_id = ch.customer_id
LEFT JOIN cust_category cat ON c.customer_id = cat.customer_id;
