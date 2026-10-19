# DineIQ dataset validation report

## 1. SRS minimum requirements

| Requirement | Required | Actual | Result |
|---|---|---|---|
| Order-line records | 1,000,000 | 1,157,551 | 
| Unique orders | 100,000 | 386,585 | 
| Customers | 50,000 | 55,000 | 
| Menu items | 150 | 168 |
| Menu categories | 10 | 12 |
| Restaurant locations | 20 | 24 |
| Months of history | 12 | 12 |
| Rating records | 100,000 | 140,565 |
| Wastage records | 50,000 | 90,318 |
| Pricing records (multiple per item) | 169 | 437 |
| Promotion campaigns (multiple) | 2 | 17 |

## 2. Primary / foreign key health (raw data - problems here are PLANTED)

| Check | Violations | Share |
|---|---|---|
| orders.order_id duplicated | 1,545 | 0.398% |
| order_items.order_line_id duplicated | 3,462 | 0.299% |
| order_items.order_id not in orders | 0 | 0.000% |
| order_items.item_id missing or unknown | 2,268 | 0.196% |
| orders.location_id missing or unknown | 610 | 0.157% |
| orders.customer_id null (guest orders + dirt) | 46,704 | 12.033% |
| orders.customer_id not in customers (non-null) | 0 | 0.000% |
| orders.promo_id not in promotions (non-null) | 0 | 0.000% |
| ratings.item_id not in menu (non-null) | 0 | 0.000% |
| wastage.location_id unknown | 38 | 0.042% |
| customers.customer_id duplicated | 110 | 0.200% |

## 3. Planted menu cases (clean completed orders only)

**Top 12 items by units sold**

| Item | Planted type | Units | Margin | Avg rating | Waste % |
|---|---|---|---|---|---|
| Cola 50cl | VOLUME | 53,688 | 32.7% | 3.61 | 2.7% |
| French Fries | STAR | 49,531 | 74.8% | 4.41 | 4.5% |
| Chapman | STAR | 42,757 | 74.0% | 4.23 | 3.2% |
| Fried Rice | STAR | 37,635 | 73.3% | 4.24 | 5.3% |
| Malt Drink | BASE | 34,210 | 76.1% | 3.83 | 2.3% |
| Fresh Orange Juice | WASTE_HEAVY | 31,806 | 76.0% | 3.96 | 16.9% |
| Coleslaw | BASE | 28,402 | 72.4% | 3.86 | 5.8% |
| Grilled Chicken Half | STAR | 28,389 | 69.7% | 4.32 | 5.0% |
| Classic Beef Burger | VOLUME | 25,845 | 21.0% | 3.95 | 3.9% |
| Moi Moi | WASTE_HEAVY | 23,782 | 67.2% | 3.71 | 19.7% |
| Cappuccino | STAR | 22,838 | 73.2% | 4.38 | 2.4% |
| Fruit Salad | WASTE_HEAVY | 22,584 | 70.0% | 3.95 | 21.0% |

**Summary by planted archetype (mean over items)**

| Archetype | Items | Avg units | Avg margin | Avg rating | Avg waste % |
|---|---|---|---|---|---|
| BASE | 125 | 7,098 | 66.6% | 3.92 | 6.2% |
| HIDDEN_GEM | 8 | 1,638 | 78.8% | 4.33 | 12.8% |
| LOSS_MAKER | 2 | 10,750 | -10.0% | 4.18 | 3.5% |
| LOW_PERFORMER | 12 | 1,464 | 33.6% | 3.11 | 13.3% |
| STAR | 10 | 27,055 | 72.6% | 4.31 | 4.6% |
| VOLUME | 6 | 24,732 | 27.8% | 3.64 | 3.6% |
| WASTE_HEAVY | 5 | 21,681 | 68.6% | 3.92 | 19.5% |

High-selling loss-making dishes (Double Cheeseburger, Beef Shawarma Wrap): profit < 0 and top-40 seller -> **PASS**
Hidden gems: avg margin 78.8% vs overall 62.9%; avg units 1,638 vs 8,731 -> **PASS**
Waste-heavy popular dishes: waste 19.5% vs overall 7.2% -> **PASS**

## 4. Promotion traps - daily profit during promo vs the 14 days before

| Promo | Planted truth | Orders/day | Profit/day | In-scope units/day | Margin before -> during |
|---|---|---|---|---|---|
| P002 Burger Bonanza 40% Off | TRAP_SALES_UP_PROFIT_DOWN_AND_CANNIBALISES_GRILLS | +16% | -9% | +203% | 63.9% -> 55.2% |
| P003 Black Friday Feast | GOOD_VOLUME_GAIN_NOTE_POST_PROMO_DIP_BASELINE | +36% | +49% | +111% | 59.2% -> 61.8% |
| P004 Festive Season Combo | NEUTRAL | +34% | +24% | n/a | 63.7% -> 61.6% |
| P005 Healthy Start Brunch | GOOD | -44% | -39% | -4% | 61.8% -> 63.4% |
| P006 Valentine Dinner for Two | GOOD | +24% | +25% | +57% | 63.4% -> 63.3% |
| P007 App Launch Offer 30% Off | TRAP_CUSTOMERS_UP_MARGIN_COLLAPSES | +29% | +7% | n/a | 63.4% -> 59.4% |
| P008 Easter Weekend Combo | GOOD | +42% | +67% | +65% | 60.3% -> 63.0% |
| P009 Free Delivery Fortnight | NEUTRAL | +10% | +14% | n/a | 63.6% -> 63.5% |
| P011 Democracy Day Mega Sale | TRAP_SALES_UP_PROFIT_DOWN | +62% | -10% | n/a | 63.2% -> 48.2% |
| P012 Rainy Day Soups | GOOD | +4% | +3% | +27% | 63.4% -> 62.9% |
| P015 Dessert Duo 30% Off | GOOD_RAISES_BASKET_VALUE | +15% | +18% | +91% | 62.8% -> 63.3% |

P010 Wing Wednesday: starters wastage per Wednesday 62 vs per Tuesday 12 (x5.1) -> **PASS**

## 5. Price-sensitive vs low-sensitivity items (units change in the 30 days after the first price increase, relative to ALL items to remove seasonality)

| Item | Type | Price change | Units/day change |
|---|---|---|---|
| Chicken Shawarma Wrap | price sensitive | +16% | -25% |
| Jollof Spaghetti | price sensitive | +15% | -15% |
| Malt Drink | price sensitive | +17% | -28% |
| Grilled Salmon | low sensitivity | +12% | -4% |
| Beef Steak | low sensitivity | +14% | -2% |
| Lamb Chops | low sensitivity | +13% | +4% |

## 6. Location differences, customers and anomalies

Pepper Soup Catfish units: Port Harcourt (L19+L20) 4,967 vs Lagos (L01..L15) 2,873 (L19 per-location 3,550, L04 133)
Orders per location range: min 360 (L99) .. max 25,750 (L02); new location L24 has 4,068 orders, first on 2026-03-01
L07 Ikoyi outage Feb 3-9: 0 orders in the window (normal ~337/week)
L08 event day 2026-05-23 orders at L08: 223 (typical day ~48)

| Planted segment | Customers | Avg orders | Avg recency (days) |
|---|---|---|---|
| AT_RISK | 5,510 | 8.6 | 99 |
| CHURNED | 6,651 | 5.5 | 245 |
| FREQUENT | 6,543 | 9.5 | 48 |
| LOYAL | 3,294 | 20.9 | 22 |
| NEW | 6,582 | 2.9 | 15 |
| OCCASIONAL | 17,608 | 2.0 | 112 |
| PROMO_DRIVEN | 8,123 | 6.7 | 78 |

Order value: median 13,950 NGN, 99.9th pct 104,491, max 7,762,785 (catering anomalies)
Orders with no promo but discount_total > 50% of subtotal: 138
Ratings with no order_id (inconsistent with purchases): 879
Suya Pizza units/day: launch week 5, viral week 43, after 24

Average basket: 2.98 lines/order, 3.97 units/order
Channel share of orders: DINE_IN 42%, TAKEAWAY 17%, THIRD_PARTY_DELIVERY 20%, WEBSITE_APP 21%