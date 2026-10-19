# DineIQ Analytics - Phase 1 guide: the dataset

Everything in this phase is the input of **your** pipeline. Read this once, then run the commands and read the code.
Evaluators may ask you to explain any line, so section 6 is a walkthrough you should be able to say in your own words.

## 1. What is in the project folder

```
dineiq-analytics/
  data_generator/
    config.py             all business assumptions + planted cases (edit this for "surprise modifications")
    generate_dataset.py   the generator (NumPy + Pandas, chunked CSV output)
    validate_dataset.py   quick pandas check of the SRS minimums and of the planted cases
    to_parquet.py         CSV -> Parquet (part files + a month-partitioned copy of orders)
    requirements.txt
  documentation/
    ER_diagram.mermaid    entity-relationship diagram (renders on GitHub)
    data_dictionary.md    every table and column, keys, planted problems
    validation_report.md  output of validate_dataset.py for the full dataset
    PHASE1_GUIDE.md       this file
  raw_data/               CSV files (orders and order_items are split into part files)
    _ground_truth/        answer keys for TESTING your analytics (never use as ML features)
  parquet_data/           Parquet version of everything
  sample_data/            first rows of every table (for GitHub, SRS item "raw sample data")
  AI_USAGE.md             declaration template (fill it in honestly)
```

## 2. How to run (about 15 seconds on a laptop)

```
pip install -r data_generator/requirements.txt
cd data_generator
python generate_dataset.py --out ..                 # writes ../raw_data  (seeded: same seed gives the same data on the same library versions)
python validate_dataset.py --root ..                # writes ../documentation/validation_report.md
python to_parquet.py --root ..                      # writes ../parquet_data
```
Options: `--scale 0.05` gives a 5% smoke-test dataset in a second; `--seed 7` gives a different dataset
with the same structure (useful to prove your pipeline is not tuned to one file); `--chunk-orders 30000` sets part-file size.

## 3. Dataset at a glance (seed 42, scale 1.0)

| Item | SRS minimum | Generated |
|---|---|---|
| Order-line records | 1,000,000 | 1,157,551 (raw, incl. planted duplicates) |
| Unique orders | 100,000 | 386,585 |
| Customers | 50,000 | 55,000 |
| Menu items / categories | 150 / 10 | 168 / 12 |
| Restaurant locations | 20 | 24 (L24 opens 2026-03-01) |
| History | 12 months | 2025-10-01 .. 2026-09-30 |
| Ratings | 100,000 | 140,565 |
| Wastage records | 50,000 | 90,318 |
| Inventory records (weekly) | - | 198,178 |
| Pricing history rows | multiple | 437 |
| Promotions | multiple | 17 |

Currency is Nigerian Naira. Orders have about 3 lines each, so a 1M-line dataset needs about 390k orders.

## 4. Where every "tricky case" from the SRS lives

Planted labels are in `raw_data/_ground_truth/items_truth.csv`, `customers_truth.csv`, `promotions_truth.csv`, `anomalies_truth.json`.
Use them only to **check** that your Spark/Python logic finds what was planted. `validate_dataset.py` prints the evidence.

| SRS case | How it is planted | Where to look |
|---|---|---|
| High-selling, loss-making dish | Double Cheeseburger (about 15,000 units, top 12% of items) and Beef Shawarma Wrap (mid-volume, about 6,400 units): unit cost climbs above price over the year; repriced only on day 300. Both end with about -10% margin | `pricing_history` cost vs price, `order_items` volume |
| Highly profitable but rarely purchased | 8 hidden gems (Ofada Rice, Ayamase Stew, Tiramisu, Zobo, Shakshuka, Asun Peppered Goat, Peppered Snail, Banga Soup) | low units, about 79% margin, rating about 4.3-4.7 |
| Popular dish with excessive wastage | Garden Salad, Fresh Orange Juice, Fruit Salad, Moi Moi, Pepper Soup Catfish | `wastage` vs units sold |
| Highly rated but poor profitability | Double Cheeseburger (rating about 4.6, negative margin) | `ratings` + profit |
| Low rated but high sales | Hot Dog Classic (rating about 2.9, volume item) | `ratings` + units |
| Promotion-dependent dish | Veggie Supreme Pizza, Chicken Alfredo, Banana Split, Brownie with Ice Cream (about 58-70% of units sold on discounted lines vs about 37% for Margherita Pizza) | `order_items.discount_amount` |
| Dish performing differently by location | Suya Platter (Abuja strong), Pepper Soup Catfish (Port Harcourt strong), Grilled Salmon and Lamb Chops (premium areas), Ewa Agoyin, Ofada Rice | units by `location_id` |
| Weekend-only dish | BBQ Ribs, Mixed Grill Platter, Full English Breakfast, Pancake Stack, Waffle & Syrup, Boli & Fish (about 80% of units on Sat/Sun) | day of week |
| Seasonal item | Turkey Wings, Chin Chin Jar, Hot Lemon Honey, Watermelon Juice, Smoothie Mango only exist in windows; soups and hot drinks peak in rainy months, cold drinks in the hot months | `menu_items.available_from/to`, monthly units |
| New item with little history | Gourmet Truffle Burger (Aug 17), Suya Pizza (Aug 24), Kids Milkshake (Sep 5) | first order date |
| Price-sensitive item | Chicken Shawarma Wrap, Jollof Spaghetti, Ice Cream Sundae, Malt Drink, Sweet Potato Fries, Fried Plantain: two big price rises, demand falls sharply; premium items (Beef Steak, Grilled Salmon, Lamb Chops) barely react | `pricing_history` vs daily units |
| Promotion that raises sales but cuts profit | P002 Burger Bonanza (also pulls sales away from grills), P011 Democracy Day Mega Sale | profit per day during promo vs before |
| Customers up, margin collapses | P007 App Launch Offer | order margin in March |
| Promotion that increases wastage | P010 Wing Wednesday (starters over-prepared) | wastage on Wednesdays Jun-Aug |
| Customers who buy only while discounted | PROMO_DRIVEN customers: orders concentrate in big promotions, then a 3-week dip | customer order dates vs promo dates |
| Churned / at-risk / new / loyal customers | hidden customer behaviour types | recency, frequency, monetary |
| Rating anomalies | fake 5-star burst on Gourmet Truffle Burger (Aug 20-21, no matching orders); 1-star run on Grilled Tilapia at L05 (Mar 10-16); one account posting 60 identical Tiramisu ratings; 400 five-star ratings at L09 in one day | `ratings` |
| Sales anomalies | L08 one-day event spike (May 23); L07 closed Feb 3-9; L12 loses 55% of orders from Jul 15; 60 corporate catering orders with huge values; 150 orders at L13 with 60-90% manual discounts and no promotion; Suya Pizza goes viral Aug 26-Sep 1 | `orders` |
| Multi-location differences | traffic weights, planted dish preferences, one new restaurant | `orders` by location |

Note on baselines: December is a busy month and a promotion that follows another promotion sees a dip. A naive "14 days before vs during"
comparison can mislead (for example P005 Healthy Start Brunch). Good analytics compare against a proper baseline - that is part of the exercise.

## 5. Dirty data planted in the raw files (counts for seed 42)

Your Step 4 (data quality) must find these. Exact counts are in `raw_data/_ground_truth/injection_log.json`.
Cancelled / refunded / void orders and guest orders (no customer id) are also present as natural complexity.

| Table | Problem | Rows |
|---|---|---|
| `orders` | near duplicate transactions | 332 |
| `orders` | exact duplicate order rows | 1,545 |
| `orders` | invalid dates | 191 |
| `orders` | invalid location id | 376 |
| `orders` | missing location id | 234 |
| `order_items` | exact duplicate line rows | 3,462 |
| `order_items` | negative or zero quantity | 602 |
| `order_items` | invalid unit price | 464 |
| `order_items` | extreme unit price | 205 |
| `order_items` | discount exceeds line value | 566 |
| `order_items` | missing item id | 1,102 |
| `order_items` | unknown item id | 1,161 |
| `ratings` | invalid rating value | 294 |
| `ratings` | invalid location id | 75 |
| `wastage` | inconsistent units | 8,106 |
| `wastage` | impossible quantities | 50 |
| `wastage` | invalid location id | 38 |
| `wastage` | missing item id | 52 |
| `inventory` | negative closing stock | 96 |
| `inventory` | invalid location id | 106 |
| `inventory` | inconsistent units | 3,873 |
| `customers` | duplicate rows | 110 |
| `customers` | missing age band | 2,152 |
| `pricing_history` | invalid price rows | 6 |

## 6. How the generator works (explain-it-yourself)

1. **config.py** - menu catalog, planted archetypes, location list, promotions, time patterns and dirt rates. No logic.
2. **build_menu / build_price_history** - creates 168 items with a popularity weight, cost ratio, rating quality, wastage rate, elasticity and
   availability window. Price history stores every price and cost period; daily matrices `PRICE[day,item]` and `COST[day,item]` are derived from it.
3. **build_promotions** - turns the promotion list into arrays: which items are discounted, demand boost, traffic lift, channel shift,
   wastage over-preparation and a post-promotion dip for promo-driven customers.
4. **build_demand_matrices** - the demand model. Probability of choosing an item =
   popularity x season x weekend x launch ramp x viral spike x price effect x location affinity x hour-of-day effect x promotion boost x basket pairing.
   The price effect is `(price relative to its category)^elasticity`, so price-sensitive items lose demand after increases.
5. **build_customers** - 55,000 customers, each with a hidden behaviour type (loyal, frequent, promo-driven, occasional, new, churned, at-risk),
   an active window and an order count drawn from a gamma-Poisson mix.
6. **build_order_headers** - draws each order's day from a weighted calendar (weekday, month, holiday, growth, promotion traffic lift), then assigns
   location, channel, hour, promotion, status and basket size; applies closures, the sales decline and the extra anomaly orders; sorts orders chronologically.
7. **generate_orders_and_lines** - works in chunks of 30,000 orders. For each basket slot it samples an item from the demand matrix (the first slot favours mains,
   later slots favour sides, drinks and desserts, and pair multipliers create associations such as Egusi Soup + Pounded Yam). It computes prices, discounts
   and order totals, injects line-level dirt, writes the CSV part files and accumulates clean sales per day, location and item.
8. **build_ratings / build_wastage / build_inventory** - derived from the simulated sales, so the tables agree with each other. Wastage = over-preparation
   plus buffer, higher for perishable and "waste heavy" dishes and during Wing Wednesday; inventory is a weekly stock simulation.
9. **Dirt and ground truth** - dirt rates come from `config.DIRTY`; every injection is counted in `injection_log.json`.

## 7. Honest limitations

- The data is synthetic: patterns are simple multiplicative rules. Real data is messier, and the hidden evaluation dataset will differ
  (new locations, price changes, unknown items). Re-run the generator with `--seed` to test your pipeline on different data.
- Tested: full scale with seeds 42 and 7 (all SRS minimums pass), plus small scales 0.05 and 0.1 (at small scale the SRS minimums fail by design).
  The `--scale` option exists to approach the 5M-line scalability requirement, but that size was NOT tested - try it on your own machine
  before claiming it in your report. The shipped `parquet_data` is the reference copy of the dataset.
- Orders have about 3 lines each, so the 100k-orders minimum is exceeded by a wide margin.
- The `_ground_truth` folder is for evaluation only. Training on it would defeat your own results.

## 8. Next steps

1. Commit this today (code, docs, sample data, `AI_USAGE.md`). Large folders (`raw_data`, `parquet_data`) can go to external storage with a link,
   as the SRS allows.
2. Fill in `AI_USAGE.md` and read each module until you can explain it. Make one small change yourself (for example add a location in `config.py`
   and regenerate) so you have practised a "surprise modification".
3. Phase 2: Spark setup, explicit schemas, loading the Parquet / CSV parts, data-quality report, cleaning rules, joins, features.
