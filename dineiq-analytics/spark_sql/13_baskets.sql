-- 13_baskets.sql : SRS Steps 17 and 18 - market-basket analysis (support, confidence, lift) and bundle recommendations
-- support(A,B)      = orders containing both / all orders
-- confidence(A->B)  = orders containing both / orders containing A
-- lift(A->B)        = confidence / (orders containing B / all orders)    lift > 1: bought together more often than by chance
-- Pairs below 100 joint orders are ignored (too rare to trust).

CREATE OR REPLACE TEMP VIEW bk_items AS SELECT DISTINCT order_id, item_id FROM fact_order_lines;
CREATE OR REPLACE TEMP VIEW bk_total AS SELECT COUNT(DISTINCT order_id) AS n_orders FROM bk_items;
CREATE OR REPLACE TEMP VIEW bk_item_cnt AS SELECT item_id, COUNT(*) AS cnt FROM bk_items GROUP BY item_id;
CREATE OR REPLACE TEMP VIEW bk_pairs AS
SELECT a.item_id AS item_a, b.item_id AS item_b, COUNT(*) AS pair_orders
FROM bk_items a JOIN bk_items b ON a.order_id = b.order_id AND a.item_id < b.item_id
GROUP BY a.item_id, b.item_id HAVING COUNT(*) >= 100;

CREATE OR REPLACE TEMP VIEW bk_directed AS
SELECT item_a AS antecedent, item_b AS consequent, pair_orders FROM bk_pairs
UNION ALL SELECT item_b, item_a, pair_orders FROM bk_pairs;

CREATE OR REPLACE TEMP VIEW out_basket_rules AS
SELECT d.antecedent, ia.item_name AS antecedent_name, ia.category_id AS antecedent_category,
       d.consequent, ib.item_name AS consequent_name, ib.category_id AS consequent_category,
       d.pair_orders, d.pair_orders / t.n_orders AS support,
       d.pair_orders / ca.cnt AS confidence,
       (d.pair_orders / ca.cnt) / (cb.cnt / t.n_orders) AS lift,
       ia.last_list_price AS antecedent_price, ib.last_list_price AS consequent_price,
       ia.margin_per_unit AS antecedent_margin_per_unit, ib.margin_per_unit AS consequent_margin_per_unit
FROM bk_directed d CROSS JOIN bk_total t
JOIN bk_item_cnt ca ON d.antecedent = ca.item_id JOIN bk_item_cnt cb ON d.consequent = cb.item_id
JOIN item_features ia ON d.antecedent = ia.item_id JOIN item_features ib ON d.consequent = ib.item_id;

-- Step 18: recommendations, each supported by association-rule evidence
CREATE OR REPLACE TEMP VIEW out_bundle_recommendations AS
SELECT antecedent, antecedent_name, consequent, consequent_name,
       CASE WHEN antecedent_category IN ('C02','C03','C04','C05','C06','C11','C12') AND consequent_category IN ('C01','C07','C08','C09','C10')
                 THEN 'COMBO_MEAL'
            WHEN antecedent_category = consequent_category AND consequent_price > antecedent_price THEN 'UPSELL'
            WHEN confidence >= 0.15 THEN 'CROSS_SELL'
            ELSE 'FREQUENTLY_PAIRED' END AS recommendation_type,
       pair_orders, support, confidence, lift, lift * confidence AS priority_score,
       antecedent_margin_per_unit + consequent_margin_per_unit AS bundle_margin_per_pair,
       concat('bought together in ', CAST(pair_orders AS STRING), ' orders; support ', CAST(round(support * 100, 2) AS STRING),
              '%, confidence ', CAST(round(confidence * 100, 1) AS STRING), '%, lift ', CAST(round(lift, 1) AS STRING)) AS evidence
FROM out_basket_rules
WHERE lift >= 2.0 AND pair_orders >= 150 AND confidence >= 0.08
  -- COMBO_MEAL is directional (main -> add-on); other types may run both ways
  AND NOT (antecedent_category IN ('C01','C07','C08','C09','C10') AND consequent_category IN ('C02','C03','C04','C05','C06','C11','C12'));
