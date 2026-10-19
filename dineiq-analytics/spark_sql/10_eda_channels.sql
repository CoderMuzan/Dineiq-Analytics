-- 10_eda_channels.sql : SRS Step 8 (EDA) and Step 35 (ordering-channel analysis)
-- Every view whose name starts with out_ is written to processed_data/analytics/ by 06_analytics_sql.py

-- Step 8: rankings (top 10 of each). Minimum sample sizes stop tiny items from winning "highest margin" or "best rated".
CREATE OR REPLACE TEMP VIEW out_eda_item_rankings AS
WITH base AS (
  SELECT item_id, item_name, category_name, units_sold, revenue, contribution_margin, profit_pct, wastage_pct,
         avg_rating, n_ratings, is_new_item
  FROM item_features WHERE units_sold > 0
), r AS (
  SELECT 'TOP_SELLING' AS ranking, item_id, item_name, category_name, CAST(units_sold AS DOUBLE) AS metric,
         ROW_NUMBER() OVER (ORDER BY units_sold DESC) AS rnk FROM base
  UNION ALL SELECT 'LOWEST_SELLING', item_id, item_name, category_name, CAST(units_sold AS DOUBLE),
         ROW_NUMBER() OVER (ORDER BY units_sold ASC) FROM base WHERE NOT is_new_item
  UNION ALL SELECT 'HIGHEST_REVENUE', item_id, item_name, category_name, revenue,
         ROW_NUMBER() OVER (ORDER BY revenue DESC) FROM base
  UNION ALL SELECT 'HIGHEST_PROFIT', item_id, item_name, category_name, contribution_margin,
         ROW_NUMBER() OVER (ORDER BY contribution_margin DESC) FROM base
  UNION ALL SELECT 'HIGHEST_MARGIN_PCT', item_id, item_name, category_name, profit_pct,
         ROW_NUMBER() OVER (ORDER BY profit_pct DESC) FROM base WHERE units_sold >= 500
  UNION ALL SELECT 'HIGH_WASTAGE_PCT', item_id, item_name, category_name, wastage_pct,
         ROW_NUMBER() OVER (ORDER BY wastage_pct DESC) FROM base WHERE units_sold >= 500
  UNION ALL SELECT 'BEST_RATED', item_id, item_name, category_name, avg_rating,
         ROW_NUMBER() OVER (ORDER BY avg_rating DESC) FROM base WHERE n_ratings >= 50
  UNION ALL SELECT 'POORLY_RATED', item_id, item_name, category_name, avg_rating,
         ROW_NUMBER() OVER (ORDER BY avg_rating ASC) FROM base WHERE n_ratings >= 50
)
SELECT * FROM r WHERE rnk <= 10;

CREATE OR REPLACE TEMP VIEW out_eda_category AS
SELECT category_id, category_name, COUNT(*) AS n_items, SUM(units_sold) AS units_sold, SUM(revenue) AS revenue,
       SUM(contribution_margin) AS contribution_margin, SUM(contribution_margin) / SUM(revenue) AS profit_pct,
       SUM(revenue) / SUM(SUM(revenue)) OVER () AS revenue_share, SUM(units_sold) / SUM(SUM(units_sold)) OVER () AS unit_share,
       SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS wastage_pct,
       SUM(avg_rating * n_ratings) / SUM(n_ratings) AS avg_rating
FROM item_features GROUP BY category_id, category_name;

-- sales that were promotion driven: share of revenue and margin by promotion
CREATE OR REPLACE TEMP VIEW out_eda_promo_sales AS
SELECT COALESCE(o.promo_id, 'NO_PROMOTION') AS promo_id, COALESCE(p.promo_name, 'No promotion') AS promo_name,
       COUNT(*) AS n_orders, SUM(o.revenue) AS revenue, SUM(o.revenue) / SUM(SUM(o.revenue)) OVER () AS revenue_share,
       SUM(o.discount_total) AS discount_total, SUM(o.margin_after_fees) AS margin_after_fees,
       SUM(o.margin_after_fees) / SUM(o.revenue) AS margin_pct, AVG(o.total_amount) AS avg_order_value
FROM order_features o LEFT JOIN promotions p ON o.promo_id = p.promo_id
GROUP BY o.promo_id, p.promo_name;

-- Step 35: channels compared on basket size, AOV, discounts, promotions, peak periods and profitability
CREATE OR REPLACE TEMP VIEW out_channel_analysis AS
SELECT channel, COUNT(*) AS n_orders, COUNT(*) / SUM(COUNT(*)) OVER () AS order_share,
       SUM(revenue) AS revenue, AVG(total_amount) AS avg_order_value, AVG(basket_units) AS avg_basket_units,
       AVG(basket_lines) AS avg_basket_lines, SUM(discount_total) / SUM(gross_revenue) AS discount_pct,
       AVG(CASE WHEN has_promo THEN 1D ELSE 0D END) AS promo_order_share,
       AVG(CASE WHEN is_peak_hour THEN 1D ELSE 0D END) AS peak_hour_share,
       AVG(CASE WHEN is_weekend THEN 1D ELSE 0D END) AS weekend_share,
       SUM(contribution_margin) / SUM(revenue) AS contribution_margin_pct,
       SUM(platform_fee) / SUM(revenue) AS platform_fee_pct,
       SUM(margin_after_fees) / SUM(revenue) AS margin_after_fees_pct,
       AVG(margin_after_fees) AS margin_per_order
FROM order_features GROUP BY channel;

-- menu preferences by channel: share of units by category
CREATE OR REPLACE TEMP VIEW out_channel_category_mix AS
SELECT channel, category_name, SUM(quantity) AS units,
       SUM(quantity) / SUM(SUM(quantity)) OVER (PARTITION BY channel) AS unit_share
FROM fact_order_lines GROUP BY channel, category_name;

CREATE OR REPLACE TEMP VIEW out_channel_hour AS
SELECT channel, order_hour, COUNT(*) AS n_orders, COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY channel) AS share_of_channel_orders
FROM order_features GROUP BY channel, order_hour;
