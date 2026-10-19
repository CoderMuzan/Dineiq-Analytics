# DineIQ Analytics - Data Dictionary (raw layer)

Currency NGN. Period 2025-10-01 .. 2026-09-30. Raw tables are intentionally dirty; the planted problems are listed in `raw_data/_ground_truth/injection_log.json`.


## menu_categories
Menu categories (12).

| Column | Type | Key | Notes |
|---|---|---|---|
| category_id | string | PK | C01..C12 |
| category_name | string |  | Starters, Soups & Stews, ... |
| perishability | string |  | LOW / MEDIUM / HIGH - how quickly the food spoils |
| meal_period | string |  | ALL_DAY or BREAKFAST |

## menu_items
Menu items (168).

| Column | Type | Key | Notes |
|---|---|---|---|
| item_id | string | PK | M001..M168 |
| item_name | string |  | Dish name (unique) |
| category_id | string | FK -> menu_categories |  |
| description | string |  | ~3% missing (planted) |
| base_price | float |  | List price in NGN at the start of the year |
| base_cost | float |  | Ingredient/prep cost at start of year |
| portion_weight_g | int |  | Used to convert kg/g units in wastage and inventory |
| prep_time_min | int |  |  |
| is_vegetarian | bool |  |  |
| launch_date | date |  | Date the dish first appeared on the menu |
| available_from | date |  | Only set for new / limited-time items |
| available_to | date |  | Only set for limited-time or discontinued items |
| is_active | bool |  | False = discontinued during the year |
| season_tag | string |  | NONE / COLD_WEATHER / HOT_WEATHER / LIMITED_TIME |

## restaurants
Restaurant locations (24, one opens during the year).

| Column | Type | Key | Notes |
|---|---|---|---|
| location_id | string | PK | L01..L24 |
| restaurant_name | string |  |  |
| area | string |  |  |
| city | string |  |  |
| state | string |  |  |
| region | string |  |  |
| opening_date | date |  | L24 opens 2026-03-01 |
| seating_capacity | int |  |  |
| size_tier | string |  | SMALL / MEDIUM / LARGE |

## customers
Anonymised customer profiles (55,000 + a few planted duplicate rows).

| Column | Type | Key | Notes |
|---|---|---|---|
| customer_id | string | PK | CU000001.. |
| signup_date | date |  | Negative history = signed up before the year |
| age_band | string |  | ~4% missing (planted) |
| home_location_id | string | FK -> restaurants |  |
| city | string |  |  |
| preferred_channel | string |  |  |
| acquisition_source | string |  | ORGANIC / PROMOTION / REFERRAL / SOCIAL_MEDIA / WALK_IN |
| marketing_opt_in | bool |  |  |
| loyalty_member | bool |  | Eligible for the Loyalty Reward promotion |

## pricing_history
One row per price/cost period of every menu item.

| Column | Type | Key | Notes |
|---|---|---|---|
| price_id | string | PK | PR00001.. |
| item_id | string | FK -> menu_items |  |
| effective_from | date |  |  |
| effective_to | date |  | NULL = still current |
| price | float |  | NGN. 6 rows are deliberately invalid (0, negative, absurd) |
| unit_cost | float |  | Cost of one portion in that period |
| change_reason | string |  | INITIAL / PRICE_INCREASE / COST_INCREASE / PRICE_AND_COST_INCREASE |

## promotions
Promotion campaigns (17).

| Column | Type | Key | Notes |
|---|---|---|---|
| promo_id | string | PK | P001..P017 |
| promo_name | string |  |  |
| promo_type | string |  | PERCENT_OFF / CATEGORY_DISCOUNT / FREE_DELIVERY / NEW_CUSTOMER / LOYALTY |
| discount_pct | float |  | 0.40 = 40% off |
| start_date | date |  |  |
| end_date | date |  |  |
| applicable_days | string |  | e.g. WED, or NULL = every day |
| channel_restriction | string |  | NULL = all channels |
| target_segment | string |  | ALL / NEW_CUSTOMERS / LOYALTY_MEMBERS |
| promo_code | string |  |  |

## promotion_items
Which menu items each promotion applies to (bridge table).

| Column | Type | Key | Notes |
|---|---|---|---|
| promo_id | string | PK, FK -> promotions |  |
| item_id | string | PK, FK -> menu_items |  |

## orders
Order headers (~386k clean orders + planted duplicates).

| Column | Type | Key | Notes |
|---|---|---|---|
| order_id | string | PK | ORD00000001.. (ORD9xxxxxxx = planted near-duplicate) |
| customer_id | string | FK -> customers | NULL = guest order (about 12%) |
| location_id | string | FK -> restaurants | Some invalid / missing (planted) |
| order_datetime | string |  | YYYY-MM-DD HH:MM:SS - a few invalid strings (planted), so it is NOT typed as a timestamp in raw data |
| channel | string |  | DINE_IN / TAKEAWAY / WEBSITE_APP / THIRD_PARTY_DELIVERY |
| delivery_platform | string |  | PARTNER_A/B/C for third-party delivery, else NULL |
| order_status | string |  | COMPLETED / CANCELLED / REFUNDED / VOID |
| promo_id | string | FK -> promotions | NULL = no promotion |
| party_size | float |  | Dine-in only |
| subtotal | float |  | Sum of quantity x unit_price before discounts |
| discount_total | float |  |  |
| delivery_fee | float |  | Charged to the customer; 0 under FREE_DELIVERY |
| platform_fee | float |  | Restaurant cost: 22% commission on third-party delivery, 4% on website/app |
| total_amount | float |  | subtotal - discount_total + delivery_fee |
| payment_method | string |  | ~2% missing (planted) |

## order_items
Order lines (~1.15M clean lines + planted dirt).

| Column | Type | Key | Notes |
|---|---|---|---|
| order_line_id | string | PK | OL000000001.. |
| order_id | string | FK -> orders |  |
| item_id | string | FK -> menu_items | Some missing or unknown (planted) |
| quantity | int |  | Some zero / negative (planted) |
| unit_price | float |  | Price when the order was placed. Some invalid (planted) |
| discount_amount | float |  | Line discount in NGN |
| line_total | float |  | quantity x unit_price - discount_amount |

## ratings
Customer ratings of items or whole restaurants.

| Column | Type | Key | Notes |
|---|---|---|---|
| rating_id | string | PK | RT00000001.. |
| order_id | string | FK -> orders | NULL for ratings with no purchase (planted anomaly) |
| customer_id | string | FK -> customers |  |
| item_id | string | FK -> menu_items | NULL = rating of the restaurant, not a dish |
| location_id | string | FK -> restaurants |  |
| rating_value | int |  | Valid range 1-5; a few invalid values (planted) |
| rating_date | date |  |  |
| source | string |  | APP / QR_CODE / EMAIL_SURVEY / DELIVERY_PLATFORM |

## wastage
Food wastage events per day, restaurant and item.

| Column | Type | Key | Notes |
|---|---|---|---|
| wastage_id | string | PK | WS00000001.. |
| wastage_date | date |  |  |
| location_id | string | FK -> restaurants |  |
| item_id | string | FK -> menu_items |  |
| shift | string |  | MORNING / AFTERNOON / EVENING |
| prep_quantity | float |  | Portions prepared that day (sold + wasted) |
| quantity_wasted | float |  | Inconsistent units + impossible values are planted |
| unit | string |  | portion (main), pcs, kg, g, Portion/PORTION/portions - convert with menu_items.portion_weight_g |
| wastage_cost | float |  | NGN, quantity x unit cost on that date |
| reason | string |  | OVERPRODUCTION / SPOILAGE / EXPIRED / PREP_ERROR / DROPPED_OR_SPILLED / CUSTOMER_RETURN |

## inventory
Weekly stock position per restaurant and item.

| Column | Type | Key | Notes |
|---|---|---|---|
| inventory_id | string | PK | INV00000001.. |
| week_start_date | date |  |  |
| location_id | string | FK -> restaurants |  |
| item_id | string | FK -> menu_items |  |
| opening_stock | float |  |  |
| replenished_qty | float |  |  |
| consumed_qty | float |  | Portions sold + wasted that week |
| closing_stock | float |  | A few negatives (planted) |
| reorder_level | float |  |  |
| stockout_flag | bool |  | True = consumption exceeded available stock |
| unit | string |  | portion (main) or kg (planted inconsistency) |
