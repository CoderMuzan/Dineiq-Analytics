# Phase 4B - pricing, promotions and locations (generated from the data)

## Price sensitivity (Steps 25-26)

- Weekly regression of ln(item share of chain units) on ln(price relative to the chain price index) for 167 dishes. Classes: INSUFFICIENT_PRICE_VARIATION 70, LOW_PRICE_SENSITIVITY 49, INSUFFICIENT_EVIDENCE 28, MODERATELY_PRICE_SENSITIVE 17, HIGHLY_PRICE_SENSITIVE 4.
- Dishes with no clear price change, a seasonal pattern, or too few promotion-free weeks are reported as INSUFFICIENT_*, not guessed. (Jollof Spaghetti, for example, is covered by a recurring Friday promotion, which removes most of its weeks from the regression; the price-change event table still shows what happened after each of its price rises.)
- Highly price-sensitive dishes: Chicken Shawarma Wrap (elasticity -2.7), Malt Drink (elasticity -2.0), Fried Plantain (elasticity -1.9), Sweet Potato Fries (elasticity -1.8).
- 222 price changes were studied (28 days before vs after, relative to the whole chain); 53 price rises were followed by a demand change of 15% or more, in 45 dishes.

## Promotion effectiveness and traps (Steps 27-28)

**Limit:** the data covers one year only, so holidays and seasons cannot be separated from the effect of all-menu promotions (for example Black Friday and the festive season coincide with busy periods). Promotions that cover only some products are judged per order, which removes most calendar effects. With a second year of data, compare with the same period of the previous year.

Each promotion is compared with up to 28 matching days before it (same weekdays, excluding days of other big promotions) and 14 days after it. A rise in sales alone never makes a promotion 'successful': profit after platform fees, margin %, wastage, post-promotion demand and sales shifted from better products are all checked.

| Promotion | Orders/day | Profit/day | Margin % (before -> during) | Traps | Verdict |
|---|---|---|---|---|---|
| P001 Independence Day Treat | - | - | - | - | INSUFFICIENT_BASELINE |
| P002 Burger Bonanza 40% Off | +16% | -12% | 58.6% -> 49.6% | SALES_UP_PROFIT_DOWN; CUSTOMERS_UP_MARGIN_COLLAPSES; SHIFTS_SALES_FROM_MORE_PROFITABLE_PRODUCT | MISLEADING |
| P003 Black Friday Feast | +46% | +38% | 58.6% -> 56.1% | - | EFFECTIVE |
| P004 Festive Season Combo | +46% | +33% | 58.7% -> 56.2% | - | EFFECTIVE |
| P005 Healthy Start Brunch | -19% | -17% | 58.7% -> 58.3% | - | EFFECTIVE |
| P006 Valentine Dinner for Two | -0% | +2% | 58.6% -> 58.2% | - | EFFECTIVE |
| P007 App Launch Offer 30% Off | +25% | +3% | 58.7% -> 54.4% | CUSTOMERS_UP_MARGIN_COLLAPSES; DISCOUNT_DEPENDENT_DEMAND | MISLEADING |
| P008 Easter Weekend Combo | +59% | +56% | 58.8% -> 57.4% | - | NOT_PROFITABLE |
| P009 Free Delivery Fortnight | +13% | +13% | 59.1% -> 57.6% | - | EFFECTIVE |
| P010 Wing Wednesday 25% Off Starters | +3% | +7% | 58.5% -> 58.4% | INCREASES_WASTAGE; SHIFTS_SALES_FROM_MORE_PROFITABLE_PRODUCT | MISLEADING |
| P011 Democracy Day Mega Sale | +21% | -37% | 58.6% -> 42.7% | SALES_UP_PROFIT_DOWN; CUSTOMERS_UP_MARGIN_COLLAPSES | MISLEADING |
| P012 Rainy Day Soups | +5% | +5% | 58.7% -> 58.0% | - | EFFECTIVE |
| P015 Dessert Duo 30% Off | +24% | +27% | 58.7% -> 58.3% | - | EFFECTIVE |
| P016 Pizza & Pasta Fridays | -10% | -5% | 58.6% -> 56.7% | - | EFFECTIVE |
| P017 September Weekday Lunch | +69% | +70% | 58.7% -> 57.8% | - | EFFECTIVE |

## Location scorecard (Step 33)

Nine standardised indicators (z-scores, signs flipped so that higher is always better); composite = their mean; a location is flagged when any indicator is 2 or more standard deviations from the chain average.

| Rank | Restaurant | Composite | Flagged reasons |
|---|---|---|---|
| 1 | L01 DineIQ Lekki Phase 1 | +0.54 | - |
| 2 | L09 DineIQ Festac | +0.25 | - |
| 3 | L14 DineIQ Gbagada | +0.22 | - |
| 4 | L23 DineIQ GRA Benin | +0.19 | margin_after_fees_pct unusually good |
| 5 | L06 DineIQ Ajah | +0.19 | - |
| 6 | L15 DineIQ Ojodu Berger | +0.19 | - |
| 7 | L05 DineIQ Yaba | +0.18 | - |
| 8 | L22 DineIQ Independence Layout | +0.17 | - |
| 9 | L03 DineIQ Ikeja GRA | +0.15 | cancellation_rate unusually weak |
| 10 | L17 DineIQ Maitama | +0.15 | - |
| 11 | L04 DineIQ Surulere | +0.10 | - |
| 12 | L02 DineIQ Victoria Island | +0.09 | - |
| 13 | L10 DineIQ Magodo | +0.09 | - |
| 14 | L11 DineIQ Ogudu | +0.06 | - |
| 15 | L07 DineIQ Ikoyi | +0.02 | - |
| 16 | L20 DineIQ Rumuola | -0.04 | - |
| 17 | L21 DineIQ Bodija | -0.06 | - |
| 18 | L08 DineIQ Maryland | -0.08 | - |
| 19 | L16 DineIQ Wuse II | -0.12 | - |
| 20 | L13 DineIQ Apapa | -0.18 | - |
| 21 | L19 DineIQ GRA Phase 2 | -0.31 | - |
| 22 | L18 DineIQ Garki | -0.34 | avg_order_value unusually weak |
| 23 | L12 DineIQ Ikorodu | -0.66 | margin_after_fees_pct unusually weak; order_trend_pct unusually weak |
| 24 | L24 DineIQ Jabi Lake | -0.80 | revenue_per_seat unusually weak; repeat_customer_rate unusually weak; wastage_pct unusually weak; profit_driver_share unusually good; order_trend_pct unusually good |
