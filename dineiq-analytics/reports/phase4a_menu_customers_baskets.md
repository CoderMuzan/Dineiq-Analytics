# Phase 4A - menu, customers, baskets, peaks, wastage (generated from the data)

## Menu performance (Steps 9-11, 32, 34)

Thresholds computed from the data: demand cut 17.6 units/day (70% of the average dish), chain profit % 62.4%, chain wastage % 6.9%, chain rating 3.96.

- **Profit Driver** (57 dishes, 48% of revenue, 54% of margin) - keep, protect and feature: French Fries, Chapman, Fried Rice, Malt Drink, Coleslaw, Grilled Chicken Half.
- **Volume Driver** (26 dishes, 27% of revenue, 23% of margin) - review price or recipe cost: Cola 50cl, Fresh Orange Juice, Classic Beef Burger, Moi Moi, Fruit Salad, White Rice & Stew.
- **Hidden Opportunity** (14 dishes, 4% of revenue, 4% of margin) - promote and make more visible: Crepe Nutella, Chocolate Lava Cake, Green Tea, BBQ Chicken Pizza, French Toast, Beans & Plantain.
- **Low Performer** (71 dishes, 22% of revenue, 19% of margin) - fix, reprice or remove: Double Cheeseburger, Beef Shawarma Wrap, Bruschetta, Egg Fried Rice, Akara Bites, Puff Puff & Chocolate.

- High-selling but loss-making: 2 - Double Cheeseburger, Beef Shawarma Wrap
- Profitable but rarely purchased: 15 - Akara & Pap, Ofada Rice, Kids Sausage Roll, Veggie Supreme Pizza, Tiramisu, Asun Peppered Goat, Yam & Egg, Peppered Snail ...
- Popular with excessive wastage: 5 - Moi Moi, Pepper Soup Catfish, Garden Salad, Fruit Salad, Fresh Orange Juice
- Highly rated but poor profitability: 2 - Double Cheeseburger, Beef Shawarma Wrap
- Low rated but high sales: 1 - Hot Dog Classic
- Promotion-dependent: 4 - Chicken Alfredo, Veggie Supreme Pizza, Brownie with Ice Cream, Banana Split
- Weekend-only: 6 - Boli & Fish, Full English Breakfast, Mixed Grill Platter, Waffle & Syrup, BBQ Ribs, Pancake Stack
- Seasonal: 27 - Ogbono Soup, Chicken Shawarma Wrap, Chin Chin Jar, Chicken Noodle Soup, Okra Soup, Veggie Burger, Watermelon Juice, Smoothie Mango ...
- New with insufficient history: 3 - Gourmet Truffle Burger, Suya Pizza, Kids Milkshake
- Performs differently across restaurants: 12 - Kids Pasta, Ofada Rice, Lamb Chops, Pepper Soup Catfish, Cheesecake, Chocolate Malt Drink, Fisherman Rice, Zobo ...
- Slow-moving: 34 - Oatmeal Bowl, Apple Pie, Mushroom Cream Soup, Concoction Rice, Akara & Pap, Ofada Rice, Kids Sausage Roll, Efo Riro ...

## Customers (Steps 15, 16, 36)

| Segment | Customers | Share | Revenue share | Avg orders | Avg spend | Avg days since last order |
|---|---|---|---|---|---|---|
| HIGH_VALUE_LOYAL | 6,677 | 12.3% | 31.7% | 15.1 | 260,443 | 17 |
| AT_RISK | 5,625 | 10.4% | 20.0% | 11.8 | 195,751 | 104 |
| PROMOTION_DRIVEN | 5,906 | 10.9% | 13.0% | 7.3 | 121,233 | 48 |
| OCCASIONAL | 16,610 | 30.6% | 11.5% | 2.2 | 37,987 | 158 |
| LOST_CUSTOMER | 5,566 | 10.3% | 9.3% | 5.7 | 92,230 | 238 |
| NEW_CUSTOMER | 11,653 | 21.5% | 8.4% | 2.2 | 39,547 | 27 |
| FREQUENT | 2,256 | 4.2% | 6.0% | 8.8 | 146,802 | 62 |

- 12,905 customers with 3+ orders show HIGH churn risk; they have spent 1,424,532,348 NGN in the year.

## Bundles and cross-sell (Steps 17-18)

- **Combo Meal**: Ogbono Soup + Pounded Yam - bought together in 489 orders; support 0.13%, confidence 19.1%, lift 6.0
- **Combo Meal**: Egusi Soup + Pounded Yam - bought together in 1995 orders; support 0.54%, confidence 18.9%, lift 5.9
- **Combo Meal**: Full English Breakfast + Americano - bought together in 631 orders; support 0.17%, confidence 18.1%, lift 5.7
- **Combo Meal**: Double Cheeseburger + French Fries - bought together in 3462 orders; support 0.94%, confidence 30.7%, lift 3.1
- **Combo Meal**: Pancake Stack + Latte - bought together in 699 orders; support 0.19%, confidence 11.3%, lift 6.7
- **Combo Meal**: Classic Beef Burger + French Fries - bought together in 5298 orders; support 1.44%, confidence 27.4%, lift 2.7
- **Combo Meal**: Efo Riro + Eba - bought together in 300 orders; support 0.08%, confidence 12.2%, lift 6.1
- **Frequently Paired**: Full English Breakfast + Pancake Stack - bought together in 382 orders; support 0.1%, confidence 10.9%, lift 6.5

## Peak periods (Step 19)

- Peak hours (25%+ above the average hour): 12:00, 13:00, 18:00, 19:00, 20:00, 21:00.
- Peak days: Sat; busiest weekday Sat (index 1.35).
- Busiest month 2025-12 (index 1.44); quietest 2026-06 (0.75).

## Wastage (Step 23)

- The 5 dishes with the highest wastage COST: Pepper Soup Catfish (4.6% of waste cost), Garden Salad (3.8% of waste cost), Fruit Salad (3.5% of waste cost), Double Cheeseburger (3.0% of waste cost), Classic Beef Burger (2.8% of waste cost).
- Highest wastage % by category: Desserts 12.3%, Breakfast & Brunch 9.8%, Sides 9.4%.

## Ordering channels (Step 35)

- THIRD_PARTY_DELIVERY: 20% of orders, average order 18,156 NGN, 3.8 units per basket, margin after fees 40.4%.
- WEBSITE_APP: 21% of orders, average order 15,330 NGN, 3.7 units per basket, margin after fees 56.6%.
- TAKEAWAY: 17% of orders, average order 15,340 NGN, 3.6 units per basket, margin after fees 62.7%.
- DINE_IN: 42% of orders, average order 18,022 NGN, 4.3 units per basket, margin after fees 63.1%.
