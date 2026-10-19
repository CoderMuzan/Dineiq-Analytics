-- 14_peak_periods.sql : SRS Step 19 - peak hours, days, weekend patterns, monthly and seasonal trends, location peaks, channel peaks
-- A peak = an index of at least 1.25 (25% above the average of its group).

CREATE OR REPLACE TEMP VIEW pk_dates AS SELECT COUNT(DISTINCT order_date) AS n_dates FROM order_features;

CREATE OR REPLACE TEMP VIEW pk_hour AS
SELECT order_hour, COUNT(*) AS n_orders, COUNT(*) / (SELECT n_dates FROM pk_dates) AS avg_orders_per_day FROM order_features GROUP BY order_hour;
CREATE OR REPLACE TEMP VIEW out_peak_hour AS
SELECT order_hour, n_orders, avg_orders_per_day, n_orders / SUM(n_orders) OVER () AS share_of_orders,
       avg_orders_per_day / AVG(avg_orders_per_day) OVER () AS peak_index,
       (avg_orders_per_day / AVG(avg_orders_per_day) OVER () >= 1.25) AS is_peak
FROM pk_hour;

CREATE OR REPLACE TEMP VIEW out_peak_day AS
SELECT day_of_week, CASE day_of_week WHEN 0 THEN 'Mon' WHEN 1 THEN 'Tue' WHEN 2 THEN 'Wed' WHEN 3 THEN 'Thu' WHEN 4 THEN 'Fri'
                                      WHEN 5 THEN 'Sat' ELSE 'Sun' END AS day_name,
       COUNT(*) AS n_orders, COUNT(*) / COUNT(DISTINCT order_date) AS avg_orders_per_date,
       (COUNT(*) / COUNT(DISTINCT order_date)) / AVG(COUNT(*) / COUNT(DISTINCT order_date)) OVER () AS peak_index,
       SUM(revenue) / COUNT(DISTINCT order_date) AS avg_revenue_per_date,
       ((COUNT(*) / COUNT(DISTINCT order_date)) / AVG(COUNT(*) / COUNT(DISTINCT order_date)) OVER () >= 1.25) AS is_peak
FROM order_features GROUP BY day_of_week;

CREATE OR REPLACE TEMP VIEW out_weekend_pattern AS
SELECT is_weekend, order_hour, COUNT(*) / COUNT(DISTINCT order_date) AS avg_orders_per_date
FROM order_features GROUP BY is_weekend, order_hour;

CREATE OR REPLACE TEMP VIEW out_monthly_trend AS
SELECT order_month, COUNT(*) AS n_orders, SUM(revenue) AS revenue, SUM(margin_after_fees) AS margin_after_fees,
       COUNT(*) / COUNT(DISTINCT order_date) AS avg_orders_per_day,
       (COUNT(*) / COUNT(DISTINCT order_date)) / AVG(COUNT(*) / COUNT(DISTINCT order_date)) OVER () AS month_index
FROM order_features GROUP BY order_month;

-- seasonal trend: each category's units in a month relative to its own monthly average (per day, so month length does not matter)
CREATE OR REPLACE TEMP VIEW out_seasonal_category AS
SELECT order_month, category_name, units_per_day,
       units_per_day / AVG(units_per_day) OVER (PARTITION BY category_name) AS seasonal_index
FROM (SELECT order_month, category_name, SUM(quantity) / COUNT(DISTINCT order_date) AS units_per_day
      FROM fact_order_lines GROUP BY order_month, category_name) t;

CREATE OR REPLACE TEMP VIEW loc_hour AS SELECT location_id, order_hour, COUNT(*) AS n FROM order_features GROUP BY location_id, order_hour;
CREATE OR REPLACE TEMP VIEW loc_dow AS SELECT location_id, day_of_week, COUNT(*) / COUNT(DISTINCT order_date) AS n FROM order_features GROUP BY location_id, day_of_week;
CREATE OR REPLACE TEMP VIEW out_location_peaks AS
SELECT h.location_id, h.order_hour AS peak_hour, h.n / SUM(h.n) OVER (PARTITION BY h.location_id) AS peak_hour_share,
       d.day_of_week AS peak_day_of_week
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY n DESC) AS rn FROM loc_hour) h
JOIN (SELECT *, ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY n DESC) AS rn FROM loc_dow) d
  ON h.location_id = d.location_id AND d.rn = 1
WHERE h.rn = 1;

-- dine-in versus delivery peaks
CREATE OR REPLACE TEMP VIEW out_channel_peaks AS
SELECT channel, order_hour AS peak_hour, share_of_channel_orders AS peak_hour_share FROM (
  SELECT channel, order_hour, COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY channel) AS share_of_channel_orders,
         ROW_NUMBER() OVER (PARTITION BY channel ORDER BY COUNT(*) DESC) AS rn
  FROM order_features GROUP BY channel, order_hour) t WHERE rn = 1;
