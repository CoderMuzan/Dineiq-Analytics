-- 11_menu_classification.sql : SRS Steps 9, 10, 11, 32 and 34
-- DATA-DRIVEN classification: every threshold below is computed from the data (no hard-coded dish names or ids).
-- Rules (menu engineering, Kasavana-Smith style):
--   demand_high      units per day on the menu >= 70% of the average item                 (the classic "70% rule")
--   profit_high      profit % >= the chain's overall profit %  (profit % = contribution margin / revenue)
--   wastage_excessive wastage % > 2 x the chain's wastage %
--   PROFIT_DRIVER      demand_high AND profit_high AND NOT wastage_excessive
--   VOLUME_DRIVER      demand_high but lower profit (or profit eroded by excessive wastage)
--   HIDDEN_OPPORTUNITY NOT demand_high, profit_high, good rating OR good repeat purchase, and still above chain profit % AFTER wastage cost
--   LOW_PERFORMER      everything else, and every dish that LOSES money
-- New items (< NEW_ITEM_DAYS of history) are classified provisionally and marked confidence = LOW_NEW_ITEM.

CREATE OR REPLACE TEMP VIEW menu_base AS
SELECT f.*,
       GREATEST(datediff(f.last_sale_date, f.first_sale_date) + 1, 1) AS days_on_menu,
       f.units_sold / GREATEST(datediff(f.last_sale_date, f.first_sale_date) + 1, 1) AS units_per_day,
       (f.contribution_margin - f.wastage_cost) / NULLIF(f.revenue, 0) AS profit_after_waste_pct
FROM item_features f WHERE f.units_sold > 0;

CREATE OR REPLACE TEMP VIEW menu_thresholds AS
SELECT AVG(units_per_day) AS mean_upd,
       0.7 * AVG(units_per_day) AS demand_cut,
       SUM(contribution_margin) / SUM(revenue) AS chain_profit_pct,
       SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS chain_wastage_pct,
       SUM(avg_rating * n_ratings) / SUM(n_ratings) AS chain_rating,
       percentile_approx(repeat_purchase_rate, 0.5) AS median_repeat,
       percentile_approx(promotion_dependency, 0.5) AS median_promo_dep,
       percentile_approx(units_per_day, 0.25) AS p25_upd,
       percentile_approx(n_orders / days_on_menu, 0.25) AS p25_orders_per_day,
       percentile_approx(days_on_menu / active_days, 0.75) AS p75_gap,
       percentile_approx(repeat_purchase_rate, 0.25) AS p25_repeat,
       percentile_approx(CASE WHEN n_ratings >= 20 THEN avg_rating END, 0.75) AS p75_rating
FROM menu_base WHERE NOT is_new_item;

-- monthly pattern (for the seasonal flag)
CREATE OR REPLACE TEMP VIEW item_month_cv AS
SELECT item_id, stddev_pop(units) / avg(units) AS monthly_cv
FROM (SELECT item_id, order_month, SUM(quantity) AS units FROM fact_order_lines GROUP BY item_id, order_month) m
GROUP BY item_id HAVING COUNT(*) >= 4;

-- ---------------------------------------------------------------- Step 34: the same rules inside every restaurant
CREATE OR REPLACE TEMP VIEW il_base AS
SELECT d.location_id, d.item_id, SUM(d.units_sold) AS units, SUM(d.revenue) AS revenue,
       SUM(d.contribution_margin) AS contribution_margin, SUM(d.wasted_portions) AS wasted_portions, SUM(d.wastage_cost) AS wastage_cost
FROM daily_item_location d GROUP BY d.location_id, d.item_id;

CREATE OR REPLACE TEMP VIEW il_span AS
SELECT b.*, GREATEST(datediff(m.last_sale_date, GREATEST(m.first_sale_date, l.first_order_date)) + 1, 1) AS days_available
FROM il_base b JOIN menu_base m ON b.item_id = m.item_id JOIN location_features l ON b.location_id = l.location_id
WHERE b.units > 0;

CREATE OR REPLACE TEMP VIEW il_thresholds AS
SELECT location_id, AVG(units / days_available) AS mean_upd, SUM(contribution_margin) / SUM(revenue) AS loc_profit_pct,
       SUM(wasted_portions) / (SUM(units) + SUM(wasted_portions)) AS loc_wastage_pct
FROM il_span GROUP BY location_id;

CREATE OR REPLACE TEMP VIEW out_menu_performance_by_location AS
SELECT s.location_id, s.item_id, m.item_name, m.category_name, s.units, s.revenue, s.contribution_margin,
       s.contribution_margin / NULLIF(s.revenue, 0) AS profit_pct, s.units / s.days_available AS units_per_day,
       s.wasted_portions / (s.units + s.wasted_portions) AS wastage_pct,
       CASE
         WHEN s.units < 30 THEN 'INSUFFICIENT_DATA'
         WHEN s.contribution_margin < 0 THEN 'LOW_PERFORMER'
         WHEN s.units / s.days_available >= 0.7 * t.mean_upd
              AND s.contribution_margin / NULLIF(s.revenue, 0) >= t.loc_profit_pct
              AND s.wasted_portions / (s.units + s.wasted_portions) <= 2 * t.loc_wastage_pct THEN 'PROFIT_DRIVER'
         WHEN s.units / s.days_available >= 0.7 * t.mean_upd THEN 'VOLUME_DRIVER'
         WHEN s.contribution_margin / NULLIF(s.revenue, 0) >= t.loc_profit_pct
              AND (COALESCE(m.rating_good, false) OR COALESCE(m.repeat_good, false))
              AND (s.contribution_margin - s.wastage_cost) / NULLIF(s.revenue, 0) >= t.loc_profit_pct THEN 'HIDDEN_OPPORTUNITY'
         ELSE 'LOW_PERFORMER' END AS performance_class
FROM il_span s
JOIN il_thresholds t ON s.location_id = t.location_id
JOIN (SELECT b.item_id, b.item_name, b.category_name,
             (b.avg_rating >= th.chain_rating AND b.n_ratings >= 20) AS rating_good,
             (b.repeat_purchase_rate >= th.median_repeat) AS repeat_good
      FROM menu_base b CROSS JOIN menu_thresholds th) m ON s.item_id = m.item_id;

-- Does a dish behave differently in different restaurants?
-- demand_index = (the dish's units/day in the restaurant relative to that restaurant's average dish)
--                / (the dish's units/day chain-wide relative to the chain's average dish).  1.0 = "as expected here".
-- A dish is location-inconsistent when its index varies a lot between restaurants (CV in the top 10% of all dishes)
-- AND it falls in at least two different performance classes.
CREATE OR REPLACE TEMP VIEW il_index AS
SELECT s.location_id, s.item_id,
       (s.units / s.days_available / t.mean_upd) / (m.units_per_day / mt.mean_upd) AS demand_index
FROM il_span s JOIN il_thresholds t ON s.location_id = t.location_id
JOIN menu_base m ON s.item_id = m.item_id CROSS JOIN menu_thresholds mt
WHERE s.units >= 30;

CREATE OR REPLACE TEMP VIEW il_index_stats AS
SELECT item_id, COUNT(*) AS n_locations_indexed, stddev_pop(demand_index) / avg(demand_index) AS demand_index_cv,
       max(demand_index) AS max_demand_index, min(demand_index) AS min_demand_index
FROM il_index GROUP BY item_id HAVING COUNT(*) >= 6;

CREATE OR REPLACE TEMP VIEW il_cv_cut AS SELECT percentile_approx(demand_index_cv, 0.9) AS cv_cut FROM il_index_stats;

CREATE OR REPLACE TEMP VIEW il_classes AS
SELECT item_id, item_name, COUNT(*) AS n_locations_classified, COUNT(DISTINCT performance_class) AS n_distinct_classes,
       SUM(CASE WHEN performance_class = 'PROFIT_DRIVER' THEN 1 ELSE 0 END) AS n_profit_driver,
       SUM(CASE WHEN performance_class = 'VOLUME_DRIVER' THEN 1 ELSE 0 END) AS n_volume_driver,
       SUM(CASE WHEN performance_class = 'HIDDEN_OPPORTUNITY' THEN 1 ELSE 0 END) AS n_hidden_opportunity,
       SUM(CASE WHEN performance_class = 'LOW_PERFORMER' THEN 1 ELSE 0 END) AS n_low_performer
FROM out_menu_performance_by_location WHERE performance_class <> 'INSUFFICIENT_DATA' GROUP BY item_id, item_name;

CREATE OR REPLACE TEMP VIEW out_item_location_consistency AS
SELECT c.*, x.demand_index_cv, x.max_demand_index, x.min_demand_index,
       (x.demand_index_cv >= k.cv_cut AND c.n_distinct_classes >= 2) AS location_inconsistent
FROM il_classes c JOIN il_index_stats x ON c.item_id = x.item_id CROSS JOIN il_cv_cut k;

-- ---------------------------------------------------------------- Steps 9-11 and 32: one row per dish
CREATE OR REPLACE TEMP VIEW menu_flags AS
SELECT b.item_id, b.item_name, b.category_id, b.category_name, b.season_tag, b.is_new_item, b.days_of_history,
       b.units_sold, b.units_per_day, b.revenue, b.contribution_margin, b.profit_pct, b.profit_after_waste_pct,
       b.margin_per_unit, b.wastage_pct, b.avg_rating, b.n_ratings, b.repeat_purchase_rate, b.promotion_dependency,
       b.relative_sales_trend_pct, b.sales_trend_pct, b.weekend_share, b.price_change_pct, b.n_orders, b.active_days,
       b.days_since_last_sale, b.days_on_menu,
       (b.units_per_day >= t.demand_cut) AS demand_high,
       (b.profit_pct >= t.chain_profit_pct) AS profit_high,
       (b.contribution_margin < 0) AS loss_making,
       (b.wastage_pct > 2 * t.chain_wastage_pct) AS wastage_excessive,
       COALESCE(b.avg_rating >= t.chain_rating AND b.n_ratings >= 20, false) AS rating_good,
       COALESCE(b.avg_rating <= t.chain_rating - 0.6 AND b.n_ratings >= 20, false) AS rating_poor,
       COALESCE(b.avg_rating >= t.p75_rating AND b.n_ratings >= 20, false) AS rating_excellent,
       COALESCE(b.repeat_purchase_rate >= t.median_repeat, false) AS repeat_good,
       t.mean_upd, t.chain_profit_pct, t.chain_wastage_pct, t.chain_rating, t.median_promo_dep,
       t.p25_upd, t.p25_orders_per_day, t.p75_gap, t.p25_repeat
FROM menu_base b CROSS JOIN menu_thresholds t;

CREATE OR REPLACE TEMP VIEW menu_classified AS
SELECT f.*,
       CASE WHEN f.loss_making THEN 'LOW_PERFORMER'
            WHEN f.demand_high AND f.profit_high AND NOT f.wastage_excessive THEN 'PROFIT_DRIVER'
            WHEN f.demand_high THEN 'VOLUME_DRIVER'
            WHEN f.profit_high AND (f.rating_good OR f.repeat_good) AND f.profit_after_waste_pct >= f.chain_profit_pct THEN 'HIDDEN_OPPORTUNITY'
            ELSE 'LOW_PERFORMER' END AS performance_class,
       CASE WHEN f.is_new_item THEN 'LOW_NEW_ITEM' ELSE 'NORMAL' END AS confidence,
       -- Step 11: tricky cases
       (f.demand_high AND f.loss_making) AS tricky_high_selling_loss_making,
       (f.profit_high AND NOT f.is_new_item AND f.units_per_day < 0.3 * f.mean_upd) AS tricky_profitable_rarely_purchased,
       (f.demand_high AND f.wastage_excessive) AS tricky_popular_excessive_wastage,
       (f.rating_excellent AND f.profit_pct < 0.5 * f.chain_profit_pct) AS tricky_highly_rated_poor_profit,
       (f.demand_high AND f.rating_poor) AS tricky_low_rated_high_sales,
       (f.promotion_dependency >= 0.5 AND f.promotion_dependency >= 1.4 * f.median_promo_dep) AS tricky_promotion_dependent,
       (f.weekend_share >= 0.6) AS tricky_weekend_only,
       (f.is_new_item) AS tricky_new_insufficient_history,
       -- Step 32: slow-moving = low volume AND at least 4 of 7 weak indicators
       (f.units_per_day <= f.p25_upd) AS sm_low_volume,
       (f.n_orders / f.days_on_menu <= f.p25_orders_per_day) AS sm_low_frequency,
       (f.days_on_menu / f.active_days >= f.p75_gap OR f.days_since_last_sale >= 14) AS sm_long_gaps,
       COALESCE(f.repeat_purchase_rate <= f.p25_repeat, false) AS sm_low_repeat,
       f.wastage_excessive AS sm_high_wastage,
       (f.profit_pct < 0.5 * f.chain_profit_pct) AS sm_weak_profit,
       COALESCE(f.relative_sales_trend_pct <= -0.2, false) AS sm_poor_trend
FROM menu_flags f;

CREATE OR REPLACE TEMP VIEW out_menu_performance AS
SELECT c.item_id, c.item_name, c.category_id, c.category_name, c.performance_class, c.confidence,
       c.units_sold, c.units_per_day, c.revenue, c.contribution_margin, c.profit_pct, c.profit_after_waste_pct,
       c.wastage_pct, c.avg_rating, c.n_ratings, c.repeat_purchase_rate, c.promotion_dependency,
       c.relative_sales_trend_pct, c.weekend_share, c.price_change_pct, c.days_of_history,
       c.demand_high, c.profit_high, c.wastage_excessive, c.rating_good, c.repeat_good,
       c.tricky_high_selling_loss_making, c.tricky_profitable_rarely_purchased, c.tricky_popular_excessive_wastage,
       c.tricky_highly_rated_poor_profit, c.tricky_low_rated_high_sales, c.tricky_promotion_dependent,
       c.tricky_weekend_only, c.tricky_new_insufficient_history,
       COALESCE(k.location_inconsistent, false) AS tricky_location_inconsistent,
       (c.season_tag <> 'NONE' OR COALESCE(m.monthly_cv >= 0.4, false)) AS tricky_seasonal,
       (c.sm_low_volume AND NOT c.is_new_item AND
        (CAST(c.sm_low_volume AS INT) + CAST(c.sm_low_frequency AS INT) + CAST(c.sm_long_gaps AS INT) + CAST(c.sm_low_repeat AS INT)
         + CAST(c.sm_high_wastage AS INT) + CAST(c.sm_weak_profit AS INT) + CAST(c.sm_poor_trend AS INT)) >= 4) AS slow_moving,
       CAST(c.sm_low_volume AS INT) + CAST(c.sm_low_frequency AS INT) + CAST(c.sm_long_gaps AS INT) + CAST(c.sm_low_repeat AS INT)
         + CAST(c.sm_high_wastage AS INT) + CAST(c.sm_weak_profit AS INT) + CAST(c.sm_poor_trend AS INT) AS slow_indicator_count,
       concat_ws('; ', CASE WHEN c.sm_low_volume THEN 'low volume' END, CASE WHEN c.sm_low_frequency THEN 'low purchase frequency' END,
                 CASE WHEN c.sm_long_gaps THEN 'long gaps between purchases' END, CASE WHEN c.sm_low_repeat THEN 'low repeat purchase' END,
                 CASE WHEN c.sm_high_wastage THEN 'high wastage' END, CASE WHEN c.sm_weak_profit THEN 'weak profitability' END,
                 CASE WHEN c.sm_poor_trend THEN 'declining trend' END) AS slow_reasons,
       c.mean_upd, c.chain_profit_pct, c.chain_wastage_pct, c.chain_rating
FROM menu_classified c
LEFT JOIN out_item_location_consistency k ON c.item_id = k.item_id
LEFT JOIN item_month_cv m ON c.item_id = m.item_id;
