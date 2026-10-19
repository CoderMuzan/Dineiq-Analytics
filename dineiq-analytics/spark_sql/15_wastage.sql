-- 15_wastage.sql : SRS Step 23 - food wastage by item, category, restaurant, day, time period (shift), demand,
-- inventory, promotion and preparation quantity.  wastage % = wasted portions / (sold + wasted portions).

CREATE OR REPLACE TEMP VIEW out_wastage_by_item AS
SELECT item_id, item_name, category_name, units_sold, wasted_portions, wastage_cost, wastage_pct,
       wastage_cost / NULLIF(revenue, 0) AS wastage_cost_pct_revenue,
       wastage_cost / SUM(wastage_cost) OVER () AS share_of_total_wastage_cost,
       RANK() OVER (ORDER BY wastage_pct DESC) AS wastage_pct_rank
FROM item_features WHERE units_sold > 0;

CREATE OR REPLACE TEMP VIEW out_wastage_by_category AS
SELECT category_name, SUM(units_sold) AS units_sold, SUM(wasted_portions) AS wasted_portions, SUM(wastage_cost) AS wastage_cost,
       SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS wastage_pct
FROM item_features GROUP BY category_name;

CREATE OR REPLACE TEMP VIEW out_wastage_by_location AS
SELECT location_id, restaurant_name, city, units_sold, wasted_portions, wastage_cost, wastage_pct, wastage_cost_pct_revenue
FROM location_features;

CREATE OR REPLACE TEMP VIEW out_wastage_by_day AS
SELECT day_of_week, SUM(units_sold) AS units_sold, SUM(wasted_portions) AS wasted_portions, SUM(wastage_cost) AS wastage_cost,
       SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS wastage_pct
FROM daily_item_location GROUP BY day_of_week;

CREATE OR REPLACE TEMP VIEW out_wastage_by_month AS
SELECT date_format(date, 'yyyy-MM') AS month, SUM(units_sold) AS units_sold, SUM(wasted_portions) AS wasted_portions,
       SUM(wastage_cost) AS wastage_cost, SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS wastage_pct
FROM daily_item_location GROUP BY date_format(date, 'yyyy-MM');

-- time period of the day (the shift in which the waste was recorded)
CREATE OR REPLACE TEMP VIEW out_wastage_by_shift AS
SELECT shift, COUNT(*) AS n_events, SUM(quantity_wasted) AS wasted_portions, SUM(wastage_cost) AS wastage_cost,
       SUM(wastage_cost) / SUM(SUM(wastage_cost)) OVER () AS share_of_wastage_cost
FROM wastage GROUP BY shift;

CREATE OR REPLACE TEMP VIEW out_wastage_by_reason AS
SELECT reason, COUNT(*) AS n_events, SUM(quantity_wasted) AS wasted_portions, SUM(wastage_cost) AS wastage_cost
FROM wastage GROUP BY reason;

-- demand: do busier dishes waste more or less? (dishes grouped in demand quartiles; 4 = highest demand)
CREATE OR REPLACE TEMP VIEW out_wastage_vs_demand AS
SELECT demand_quartile, COUNT(*) AS n_items, SUM(units_sold) AS units_sold, SUM(wasted_portions) AS wasted_portions,
       SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS wastage_pct
FROM (SELECT *, NTILE(4) OVER (ORDER BY units_sold) AS demand_quartile FROM item_features WHERE units_sold > 0) t
GROUP BY demand_quartile;

-- preparation quantity: wasted share of what was prepared (days with a waste record)
CREATE OR REPLACE TEMP VIEW out_wastage_vs_prep AS
SELECT item_id, SUM(prep_portions) AS prepared_portions, SUM(wasted_portions) AS wasted_portions,
       SUM(wasted_portions) / NULLIF(SUM(prep_portions), 0) AS wasted_share_of_prepared
FROM daily_item_location WHERE prep_portions IS NOT NULL GROUP BY item_id;

-- inventory consumption: weeks in which the restaurant ran out of stock vs weeks it did not
CREATE OR REPLACE TEMP VIEW out_wastage_vs_inventory AS
SELECT COALESCE(stockout_week, false) AS stockout_week, COUNT(*) AS n_item_days, SUM(units_sold) AS units_sold,
       SUM(wasted_portions) AS wasted_portions, SUM(wasted_portions) / (SUM(units_sold) + SUM(wasted_portions)) AS wastage_pct
FROM daily_item_location GROUP BY COALESCE(stockout_week, false);

-- promotion: wastage of the dishes in a promotion's scope on promotion days vs on all other days
CREATE OR REPLACE TEMP VIEW w_scope AS
SELECT p.promo_id, p.promo_name, d.date, d.units_sold, d.wasted_portions, d.wastage_cost,
       (d.date BETWEEN p.start_date AND p.end_date
        AND (p.applicable_days IS NULL OR instr(p.applicable_days, CASE weekday(d.date) WHEN 0 THEN 'MON' WHEN 1 THEN 'TUE' WHEN 2 THEN 'WED'
             WHEN 3 THEN 'THU' WHEN 4 THEN 'FRI' WHEN 5 THEN 'SAT' ELSE 'SUN' END) > 0)) AS on_promo_day
FROM daily_item_location d
JOIN promotion_items pi ON d.item_id = pi.item_id
JOIN promotions p ON pi.promo_id = p.promo_id
WHERE p.discount_pct > 0 AND p.promo_type = 'CATEGORY_DISCOUNT';
CREATE OR REPLACE TEMP VIEW out_wastage_by_promo AS
SELECT promo_id, promo_name,
       SUM(CASE WHEN on_promo_day THEN wasted_portions END) / (SUM(CASE WHEN on_promo_day THEN units_sold + wasted_portions END)) AS wastage_pct_on_promo_days,
       SUM(CASE WHEN NOT on_promo_day THEN wasted_portions END) / (SUM(CASE WHEN NOT on_promo_day THEN units_sold + wasted_portions END)) AS wastage_pct_other_days,
       SUM(CASE WHEN on_promo_day THEN wastage_cost END) AS wastage_cost_on_promo_days
FROM w_scope GROUP BY promo_id, promo_name;
