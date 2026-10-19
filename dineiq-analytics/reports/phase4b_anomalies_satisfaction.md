# Phase 4B - anomalies and customer satisfaction (generated from the data)

## Sales anomalies (Step 31)

| Type | Events | Examples |
|---|---|---|
| UNEXPECTED_DEMAND | 41 | M003 2025-11-19; M005 2026-07-15; M007 2026-09-18 |
| ABNORMAL_ORDER_VALUE | 33 | ORD00276955 2026-06-11; ORD00368045 2026-09-18; ORD00335193 2026-08-18 |
| SALES_DROP | 1 | L07 2026-02-06 |
| SALES_SPIKE | 1 | L08 2026-05-23 |
| SUSTAINED_SALES_DROP | 1 | L12 2026-07-15 |
| UNUSUAL_DISCOUNT | 1 | L13 2025-10-02 |
| DUPLICATE_TRANSACTIONS | 1 | ALL 2025-10-01 |

- **SALES_DROP** L07 2026-02-06 to 2026-02-08: 0 orders/day against about 54 expected for its usual share of chain orders
- **SALES_SPIKE** L08 2026-05-23: 223 orders/day against about 56 expected for its usual share of chain orders
- **SUSTAINED_SALES_DROP** L12 2026-07-15 to 2026-09-05: share of chain orders fell to 70% of its earlier level (14-day average vs the 56 days before)
- **UNUSUAL_DISCOUNT** L13 2025-10-02 to 2026-09-30: 137 orders discounted by 75% on average with no promotion applied
- **UNEXPECTED_DEMAND** M003 2025-11-19: Spring Rolls: 54 units/day, 3.7x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M005 2026-07-15: Puff Puff Bites: 84 units/day, 2.5x its usual share of chain sales on that weekday (a promotion explains it: P010)
- **UNEXPECTED_DEMAND** M007 2026-09-18: Calamari Rings: 81 units/day, 2.9x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M038 2026-08-18: Fisherman Rice: 65 units/day, 6.5x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M057 2025-11-07 to 2025-11-08: Classic Beef Burger: 281 units/day, 2.9x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M057 2025-11-10: Classic Beef Burger: 168 units/day, 2.6x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M057 2025-11-12 to 2025-11-14: Classic Beef Burger: 222 units/day, 2.8x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M057 2025-11-16: Classic Beef Burger: 231 units/day, 2.5x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M058 2025-11-03: Double Cheeseburger: 111 units/day, 2.8x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M058 2025-11-05 to 2025-11-06: Double Cheeseburger: 115 units/day, 2.7x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M058 2025-11-08 to 2025-11-10: Double Cheeseburger: 139 units/day, 2.7x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M058 2025-11-12 to 2025-11-16: Double Cheeseburger: 139 units/day, 2.8x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M062 2025-11-04: Club Sandwich: 71 units/day, 3.1x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M062 2025-11-07: Club Sandwich: 103 units/day, 3.6x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M062 2025-11-09: Club Sandwich: 103 units/day, 3.6x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M062 2025-11-11: Club Sandwich: 69 units/day, 3.0x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M062 2025-11-14: Club Sandwich: 102 units/day, 3.5x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M063 2025-11-03 to 2025-11-07: Chicken Shawarma Wrap: 81 units/day, 3.9x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M063 2025-11-11: Chicken Shawarma Wrap: 78 units/day, 4.0x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M063 2025-11-13 to 2025-11-16: Chicken Shawarma Wrap: 102 units/day, 3.9x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M064 2025-11-06: Beef Shawarma Wrap: 72 units/day, 4.1x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M064 2025-11-09: Beef Shawarma Wrap: 60 units/day, 3.3x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M064 2025-11-12 to 2025-11-13: Beef Shawarma Wrap: 66 units/day, 3.6x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M064 2025-11-16: Beef Shawarma Wrap: 62 units/day, 3.3x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M065 2025-11-03: Hot Dog Classic: 130 units/day, 2.7x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M065 2025-11-05 to 2025-11-07: Hot Dog Classic: 166 units/day, 2.9x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M065 2025-11-11 to 2025-11-15: Hot Dog Classic: 166 units/day, 2.8x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M066 2025-11-16: Fish Burger: 74 units/day, 4.0x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M067 2025-11-07 to 2025-11-08: BLT Sandwich: 65 units/day, 3.5x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M067 2025-11-15: BLT Sandwich: 87 units/day, 4.6x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M068 2025-11-05 to 2025-11-07: Philly Steak Sandwich: 62 units/day, 3.2x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M068 2025-11-14 to 2025-11-16: Philly Steak Sandwich: 69 units/day, 3.1x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M069 2025-11-07 to 2025-11-09: Egg Sandwich: 110 units/day, 2.8x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M069 2025-11-14 to 2025-11-16: Egg Sandwich: 111 units/day, 2.8x its usual share of chain sales on that weekday (a promotion explains it: P002)
- **UNEXPECTED_DEMAND** M075 2026-08-31: Suya Pizza: 62 units/day, 4.4x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M081 2026-03-18: Lasagna: 55 units/day, 3.6x its usual share of chain sales on that weekday (a promotion explains it: P007)
- **UNEXPECTED_DEMAND** M114 2026-01-01: Orange Soda 50cl: 149 units/day, 3.1x its usual share of chain sales on that weekday (a promotion explains it: P004)
- **UNEXPECTED_DEMAND** M119 2025-12-10: Pineapple Juice: 71 units/day, 3.6x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M151 2026-06-11: Kids Mac & Cheese: 74 units/day, 22.9x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M158 2026-02-06: Cheese Omelette: 60 units/day, 3.1x its usual share of chain sales on that weekday (no promotion explains it)
- **UNEXPECTED_DEMAND** M163 2026-08-07: Breakfast Burrito: 75 units/day, 3.0x its usual share of chain sales on that weekday (no promotion explains it)

## Rating anomalies (Step 30)

- **RATINGS_WITHOUT_PURCHASE_BURST** (ITEM M044) 2026-03-10 to 2026-03-16: 119 ratings with no order behind them for Grilled Tilapia, average 1.0, from 119 accounts
- **RATINGS_WITHOUT_PURCHASE_BURST** (ITEM M070) 2026-08-20 to 2026-08-21: 300 ratings with no order behind them for Gourmet Truffle Burger, average 5.0, from 300 accounts
- **RATINGS_WITHOUT_PURCHASE_BURST** (ITEM M105) 2026-04-12: 60 ratings with no order behind them for Tiramisu, average 5.0, from 1 accounts
- **RATINGS_WITHOUT_PURCHASE_BURST** (RESTAURANT L09) 2026-06-20: 400 ratings with no order behind them for L09, average 5.0, from 398 accounts
- **SUDDEN_RATING_DROP** (ITEM M044) 2026-03-04 to 2026-03-10: Grilled Tilapia: weekly average 1.5 vs 4.2 in the previous weeks (-2.7); most ratings from L05; 12 of 15 have no purchase
- **SUDDEN_RATING_DROP** (ITEM M044) 2026-03-11 to 2026-03-17: Grilled Tilapia: weekly average 1.2 vs 3.3 in the previous weeks (-2.1); most ratings from L05; 107 of 113 have no purchase
- **EXCESSIVE_IDENTICAL_RATINGS** (CUSTOMER CU004430) 2026-04-12: one account posted 60 ratings, all 5 stars, in one day
- **UNUSUALLY_MANY_RATINGS** (RESTAURANT L09) 2026-06-20: 418 ratings in one day against a typical 14; 400 have no purchase
- **RATINGS_INCONSISTENT_WITH_PURCHASES** (CHAIN ALL) 2025-10-01 to 2026-09-30: 479 dish ratings have no order behind them and 248 ratings name a dish that is not in the rated order (314 further ratings belong to orders removed in cleaning: cancelled, quarantined or voided)

## Rating and satisfaction analysis (Step 29)

Only ratings tied to a real purchase are used. Rank correlations are across dishes (or restaurants).

- dish rating vs profit %: Spearman +0.38 (n=167)
- dish rating vs sales (units): Spearman +0.17 (n=167)
- dish rating vs repeat purchase rate: Spearman +0.16 (n=167)
- dish rating vs wastage %: Spearman -0.06 (n=167)
- restaurant rating vs revenue: Spearman +0.04 (n=24)
- restaurant rating vs profit %: Spearman +0.33 (n=24)
- restaurant rating vs repeat customer rate: Spearman +0.11 (n=24)
- Dish ratings on PROMOTION: 3.96 (33,674 ratings)
- Dish ratings on NO_PROMOTION: 3.96 (76,192 ratings)
- By time period: Breakfast 7-10 3.94; Lunch 11-14 3.96; Afternoon 15-17 3.95; Dinner 18-22 3.97
- Lowest-rated restaurant: DineIQ Ikoyi (3.81); highest: DineIQ Festac (4.16).
