-- 12_customers.sql : SRS Steps 15, 16, 36 and the customer dashboard inputs (Step 44)
-- Segment rules are applied in this order (first match wins). Thresholds can be edited here:
--   NEW             first order within the last 100 days
--   LOST            frequency >= 3 and no order for more than 180 days
--   AT_RISK         frequency >= 3 and (silent for longer than max(60 days, 3 x the customer's own average gap between orders),
--                   or orders in the last 90 days at least 3 below the 90 days before)
--   PROMOTION_DRIVEN  at least 30% of orders use a public campaign promotion (and 3+ orders); the typical customer is at 17%
--   HIGH_VALUE_LOYAL  frequency score >= 4, monetary score >= 4 and ordered within the last 45 days
--   FREQUENT        frequency score >= 4
--   OCCASIONAL      everyone else

CREATE OR REPLACE TEMP VIEW cust_signals AS
SELECT c.*,
       -- churn-risk signals (Step 36): each one is 0 or 1
       CAST(c.avg_days_between_orders IS NOT NULL AND c.recency_days > GREATEST(3 * c.avg_days_between_orders, 30) AS INT) AS sig_overdue,
       CAST(c.orders_prior >= 2 AND c.orders_recent < c.orders_prior AS INT) AS sig_frequency_down,
       CAST(COALESCE(c.spend_change_pct <= -0.3, false) AS INT) AS sig_spend_down,
       CAST(c.recency_days > 60 AS INT) AS sig_long_silence
FROM customer_features c;

CREATE OR REPLACE TEMP VIEW out_customer_segments AS
SELECT s.customer_id, s.signup_date, s.home_location_id, s.acquisition_source, s.loyalty_member,
       CASE
         WHEN datediff(to_date('${SNAPSHOT}'), s.first_order_date) <= 100 THEN 'NEW_CUSTOMER'
         WHEN s.frequency >= 3 AND s.recency_days > 180 THEN 'LOST_CUSTOMER'
         WHEN s.frequency >= 3 AND (s.recency_days > GREATEST(60, 3 * COALESCE(s.avg_days_between_orders, 0)) OR (s.frequency_change <= -3 AND s.frequency >= 5)) THEN 'AT_RISK'
         WHEN s.campaign_promo_share >= 0.3 AND s.frequency >= 3 THEN 'PROMOTION_DRIVEN'
         WHEN s.f_score >= 4 AND s.m_score >= 4 AND s.recency_days <= 45 THEN 'HIGH_VALUE_LOYAL'
         WHEN s.f_score >= 4 THEN 'FREQUENT'
         ELSE 'OCCASIONAL' END AS segment,
       s.recency_days, s.frequency, s.monetary, s.r_score, s.f_score, s.m_score, s.avg_order_value,
       s.avg_days_between_orders, s.promo_order_share, s.campaign_promo_share, s.peak_hour_share, s.weekend_order_ratio,
       s.online_order_share, s.preferred_channel, s.favorite_category, s.category_diversity,
       s.orders_recent, s.orders_prior, s.frequency_change, s.spend_change_pct,
       s.sig_overdue + s.sig_frequency_down + s.sig_spend_down + s.sig_long_silence AS churn_signal_count,
       CASE WHEN s.frequency < 3 THEN 'NOT_ASSESSED'
            WHEN s.recency_days > 90 OR s.sig_overdue + s.sig_frequency_down + s.sig_spend_down + s.sig_long_silence >= 3 THEN 'HIGH'
            WHEN s.sig_overdue + s.sig_frequency_down + s.sig_spend_down + s.sig_long_silence = 2 THEN 'MEDIUM'
            ELSE 'LOW' END AS churn_risk_level,
       CASE WHEN s.frequency >= 3 THEN concat_ws('; ',
              CASE WHEN s.sig_overdue = 1 THEN 'overdue for an order' END,
              CASE WHEN s.sig_frequency_down = 1 THEN 'orders falling' END,
              CASE WHEN s.sig_spend_down = 1 THEN 'spend falling' END,
              CASE WHEN s.sig_long_silence = 1 THEN 'silent for 60+ days' END) END AS churn_reasons
FROM cust_signals s;

CREATE OR REPLACE TEMP VIEW out_segment_summary AS
SELECT segment, COUNT(*) AS n_customers, COUNT(*) / SUM(COUNT(*)) OVER () AS customer_share,
       SUM(monetary) AS revenue, SUM(monetary) / SUM(SUM(monetary)) OVER () AS revenue_share,
       AVG(frequency) AS avg_frequency, AVG(monetary) AS avg_monetary, AVG(avg_order_value) AS avg_order_value,
       AVG(recency_days) AS avg_recency_days, AVG(campaign_promo_share) AS avg_campaign_promo_share,
       AVG(online_order_share) AS avg_online_share, AVG(peak_hour_share) AS avg_peak_hour_share,
       SUM(CASE WHEN churn_risk_level = 'HIGH' THEN 1 ELSE 0 END) AS n_high_churn_risk
FROM out_customer_segments GROUP BY segment;

CREATE OR REPLACE TEMP VIEW out_rfm_distribution AS
SELECT r_score, f_score, COUNT(*) AS n_customers, AVG(monetary) AS avg_monetary, AVG(recency_days) AS avg_recency_days
FROM customer_features GROUP BY r_score, f_score;

CREATE OR REPLACE TEMP VIEW out_high_value_customers AS
SELECT customer_id, segment, recency_days, frequency, monetary, avg_order_value, favorite_category, preferred_channel, churn_risk_level
FROM out_customer_segments ORDER BY monetary DESC LIMIT 2000;

-- Step 44: customer trends - active, new and returning customers per month
CREATE OR REPLACE TEMP VIEW out_customer_trend_monthly AS
SELECT o.order_month, COUNT(DISTINCT o.customer_id) AS active_customers,
       COUNT(DISTINCT CASE WHEN date_format(c.first_order_date, 'yyyy-MM') = o.order_month THEN o.customer_id END) AS new_customers,
       COUNT(DISTINCT CASE WHEN date_format(c.first_order_date, 'yyyy-MM') < o.order_month THEN o.customer_id END) AS returning_customers,
       COUNT(*) AS orders, SUM(o.revenue) AS revenue
FROM order_features o JOIN customer_features c ON o.customer_id = c.customer_id
WHERE NOT o.is_guest GROUP BY o.order_month;
