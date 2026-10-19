-- 01_lookup_tables.sql : calendar and "price/cost on any day" lookup (SRS Step 6: menu items <-> pricing history)
-- Parameters are filled in by the Python runner: ${DATE_MIN}  ${DATE_MAX}

CREATE OR REPLACE TEMP VIEW date_dim AS
SELECT explode(sequence(to_date('${DATE_MIN}'), to_date('${DATE_MAX}'))) AS order_date;

-- As-of join: for every item and day take the pricing_history row with the latest effective_from that is <= that day.
-- ROW_NUMBER() ranks the candidate rows newest first; we keep rank 1.
CREATE OR REPLACE TEMP VIEW cost_asof AS
SELECT item_id, order_date, price, unit_cost
FROM (
  SELECT m.item_id, d.order_date, p.price, p.unit_cost,
         ROW_NUMBER() OVER (PARTITION BY m.item_id, d.order_date ORDER BY p.effective_from DESC) AS rn
  FROM menu_items m
  CROSS JOIN date_dim d
  JOIN pricing_history p ON p.item_id = m.item_id AND p.effective_from <= d.order_date
) t
WHERE rn = 1;

-- Back-fill: if the FIRST price period of an item (or ALL its periods) was quarantined as invalid (cleaning rule P-01),
-- some days have no earlier valid row. For those days we use the item's earliest valid period, or - when the item has no valid
-- period at all - the menu master data (menu_items.base_price / base_cost = the launch values). Assumption documented in the guide.
CREATE OR REPLACE TEMP VIEW cost_first AS
SELECT m.item_id, COALESCE(f.price, m.base_price) AS price, COALESCE(f.unit_cost, m.base_cost) AS unit_cost
FROM menu_items m
LEFT JOIN (SELECT item_id, min_by(price, effective_from) AS price, min_by(unit_cost, effective_from) AS unit_cost
           FROM pricing_history GROUP BY item_id) f ON f.item_id = m.item_id;

CREATE OR REPLACE TEMP VIEW cost_day AS
SELECT d.item_id, d.order_date,
       COALESCE(a.price, f.price) AS list_price, COALESCE(a.unit_cost, f.unit_cost) AS unit_cost,
       (a.price IS NULL) AS is_backfilled
FROM (SELECT m.item_id, dd.order_date FROM menu_items m CROSS JOIN date_dim dd) d
LEFT JOIN cost_asof a ON a.item_id = d.item_id AND a.order_date = d.order_date
LEFT JOIN cost_first f ON f.item_id = d.item_id;

CACHE TABLE cost_day;
