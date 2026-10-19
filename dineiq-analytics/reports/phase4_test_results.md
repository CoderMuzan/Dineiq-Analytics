# Phase 4 automated test results

**59 / 59 checks passed**

| Group | Check | Result | Detail |
|---|---|---|---|
| A structure | menu_performance: every dish with sales is in exactly one of the 4 classes | PASS | {'LOW_PERFORMER': 71, 'PROFIT_DRIVER': 57, 'VOLUME_DRIVER': 26, 'HIDDEN_OPPORTUNITY': 14} |
| A structure | menu_performance: new items are marked LOW_NEW_ITEM confidence | PASS |  |
| A structure | menu_performance: no hard-coded rule - class follows the flags | PASS |  |
| A structure | menu_performance_by_location covers 24 restaurants and 4 classes + INSUFFICIENT_DATA | PASS |  |
| A structure | customer_segments: one row per customer, segment shares add to 100% | PASS |  |
| A structure | basket rules: support, confidence and lift recomputed independently from raw order lines | PASS | French Fries->Cola 50cl lift 1.41; Cola 50cl->French Fries lift 1.41; Classic Beef Burger->French Fries lift 2.72 |
| A structure | bundle recommendations all carry association-rule evidence | PASS |  |
| B menu classification | star dishes: at least 9 of 10 are PROFIT_DRIVER | PASS |  |
| B menu classification | high-volume thin-margin dishes: all VOLUME_DRIVER | PASS |  |
| B menu classification | loss-making dishes: both LOW_PERFORMER | PASS |  |
| B menu classification | Double Cheeseburger: flagged HIGH-SELLING LOSS-MAKER and HIGHLY-RATED POOR-PROFIT | PASS |  |
| B menu classification | hidden gems: all 8 are HIDDEN_OPPORTUNITY | PASS | {'HIDDEN_OPPORTUNITY': 8} |
| B menu classification | planted low performers: at least 10 of 12 are LOW_PERFORMER | PASS |  |
| B menu classification | waste-heavy popular dishes: all flagged POPULAR + EXCESSIVE WASTAGE | PASS | 5 |
| B menu classification | Hot Dog Classic flagged LOW-RATED HIGH-SALES | PASS |  |
| B menu classification | promotion-dependent dishes: at least 3 of 4 flagged | PASS |  |
| B menu classification | weekend dishes: at least 5 of 6 flagged WEEKEND-ONLY | PASS | 6 |
| B menu classification | new dishes: all 3 flagged NEW / insufficient history | PASS |  |
| B menu classification | seasonal dishes: all planted seasonal dishes flagged | PASS |  |
| B menu classification | dishes that perform differently by restaurant: at least 5 of 6 planted found | PASS | 6 found, 12 flagged in total |
| B menu classification | slow-moving detection: no star or volume dish is called slow-moving | PASS |  |
| B menu classification | slow-moving detection: at least 8 of 12 planted low performers | PASS | 11 |
| B customers | new customers: at least 95% found | PASS | 100.0% |
| B customers | churned customers (3+ orders): at least 85% are LOST or AT_RISK | PASS | 99.3% |
| B customers | churned customers (3+ orders): at least 85% have HIGH churn risk | PASS | 100.0% |
| B customers | loyal customers: HIGH churn risk is rare (under 25%) | PASS | 7.1% |
| B customers | PROMOTION_DRIVEN segment: at least 55% are really promotion-driven customers (the rest are deal-hunting regulars) | PASS | 58.6% |
| B customers | HIGH_VALUE_LOYAL segment: at least 60% are loyal or frequent customers | PASS | 72.6% |
| B customers | high-value segment earns more per customer than occasional customers | PASS |  |
| B baskets, peaks, wastage | market basket: at least 7 of 9 strongest planted pairings are found with lift >= 2 | PASS | 9 of 9 |
| B baskets, peaks, wastage | peak hours include a lunch hour (12-14) and a dinner hour (18-21) | PASS | [12, 13, 18, 19, 20, 21] |
| B baskets, peaks, wastage | peak days include Friday or Saturday | PASS | ['Sat'] |
| B baskets, peaks, wastage | busiest month is December | PASS |  |
| B baskets, peaks, wastage | wastage: waste-heavy dishes waste more than twice the chain average | PASS |  |
| B baskets, peaks, wastage | wastage: Wing Wednesday (P010) starters waste clearly more on promotion days | PASS |  |
| B baskets, peaks, wastage | wastage: all 4 time periods and 6 reasons reported | PASS |  |
| B pricing and promotions | price sensitivity: at least 3 of 6 planted price-sensitive dishes are found | PASS | 4 of 6 |
| B pricing and promotions | price sensitivity: no dish outside the planted six is called HIGHLY sensitive | PASS | [] |
| B pricing and promotions | price sensitivity: the planted low-sensitivity premium dishes are never HIGHLY sensitive | PASS |  |
| B pricing and promotions | promotion trap: P002 is MISLEADING and shows SALES_UP_PROFIT_DOWN | PASS |  |
| B pricing and promotions | promotion trap: P007 is MISLEADING and shows CUSTOMERS_UP_MARGIN_COLLAPSES | PASS |  |
| B pricing and promotions | promotion trap: P010 is MISLEADING and shows INCREASES_WASTAGE | PASS |  |
| B pricing and promotions | promotion trap: P011 is MISLEADING and shows SALES_UP_PROFIT_DOWN | PASS |  |
| B pricing and promotions | promotion trap: P002 also pulls sales away from grills (C04) | PASS |  |
| B pricing and promotions | good promotions are not condemned: P005, P006, P015 are EFFECTIVE | PASS | {'P005': 'EFFECTIVE', 'P006': 'EFFECTIVE', 'P015': 'EFFECTIVE'} |
| B pricing and promotions | a sales increase alone never makes a promotion effective (P003 judged on profit too) | PASS |  |
| B pricing and promotions | location scorecard: 24 restaurants ranked, composite is the mean of the indicator z-scores | PASS |  |
| B anomalies | sales spike: L08 on 2026-05-23 found | PASS |  |
| B anomalies | sales drop: L07 outage in early February found | PASS |  |
| B anomalies | sustained drop: L12 starting in mid-July found | PASS | ['2026-07-15'] |
| B anomalies | unusual discounts: L13 found, and nowhere else | PASS |  |
| B anomalies | abnormal order values: at least 20 found, most at the catering restaurants | PASS | 33 found |
| B anomalies | unexpected demand: the viral Suya Pizza week is found | PASS |  |
| B anomalies | unexpected demand: promotion-driven surges are labelled as explained | PASS |  |
| B anomalies | duplicate transactions reported from cleaning | PASS |  |
| B anomalies | rating anomalies: fake 5-star burst on Gourmet Truffle Burger found | PASS |  |
| B anomalies | rating anomalies: 1-star run on Grilled Tilapia found, with a SUDDEN_RATING_DROP | PASS |  |
| B anomalies | rating anomalies: one account with 60 identical ratings found | PASS |  |
| B anomalies | rating anomalies: L09 one-day volume burst found | PASS |  |
