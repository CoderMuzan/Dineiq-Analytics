# Feature catalogue (SRS Step 7)

Parameters: {'DATE_MIN': '2025-10-01', 'DATE_MAX': '2026-09-30', 'SNAPSHOT': '2026-10-01', 'TREND_DAYS': '56', 'RECENT_DAYS': '90', 'RATING_WINDOW': '90', 'NEW_ITEM_DAYS': '60'}

Profit = contribution margin = revenue after discount minus ingredient cost (from the price/cost valid on the order date). Platform commission is an order-level cost, so it appears only in order and restaurant features (`margin_after_fees`).


## order_features  (368,132 rows)

| Column | Type | Meaning |
|---|---|---|
| order_id | string | Order key |
| order_ts | timestamp | Order timestamp |
| order_date | date | Order date |
| order_month | string | Order month (yyyy-MM) |
| order_hour | int | Hour of day 0-23 |
| day_of_week | int | 0 = Monday ... 6 = Sunday |
| is_weekend | boolean | Saturday or Sunday |
| is_peak_hour | boolean | Order placed 12:00-14:59 or 18:00-21:59 (peak-hour definition, editable in 04_order_features.sql) |
| location_id | string | Restaurant |
| channel | string | DINE_IN / TAKEAWAY / WEBSITE_APP / THIRD_PARTY_DELIVERY |
| customer_id | string | Customer (NULL for guests) |
| is_guest | boolean | No customer id |
| payment_method | string | Payment method ('UNKNOWN' when missing in raw data) |
| promo_id | string | Applied promotion (NULL = none) |
| has_promo | boolean | A promotion was applied |
| promo_type | string | Type of the applied promotion |
| has_campaign_promo | boolean | A public campaign promotion (excludes the automatic welcome and loyalty entitlements) |
| party_size | double | Dine-in party size |
| basket_lines | bigint | Number of order lines |
| basket_units | bigint | Total quantity ordered (basket size) |
| n_categories | bigint | Distinct menu categories in the basket |
| gross_revenue | double | Sum of quantity x price before discount |
| discount_total | double | Total line discounts |
| revenue | double | Gross revenue minus discounts (food revenue) |
| ingredient_cost | double | Sum of quantity x unit cost valid on the order date |
| contribution_margin | double | revenue - ingredient_cost |
| delivery_fee | double | Delivery fee charged to the customer |
| platform_fee | double | Commission paid to the delivery / app platform (restaurant cost) |
| total_amount | double | Amount paid = revenue + delivery_fee |
| margin_after_fees | double | contribution_margin - platform_fee |
| margin_pct | double | margin_after_fees / revenue |
| discount_pct | double | discount_total / gross_revenue |

## item_features  (168 rows)

| Column | Type | Meaning |
|---|---|---|
| item_id | string | Menu item key |
| item_name | string | Dish name |
| category_id | string | Category key |
| category_name | string | Category name |
| season_tag | string | NONE / COLD_WEATHER / HOT_WEATHER / LIMITED_TIME |
| is_active | boolean | False = discontinued |
| available_from | date | Start of availability window (new / limited items) |
| available_to | date | End of availability window (limited / discontinued items) |
| units_sold | bigint | Units sold (completed orders) |
| revenue | double | Revenue after discount |
| ingredient_cost | double | Ingredient/preparation cost of the units sold |
| contribution_margin | double | revenue - ingredient_cost |
| profit_pct | double | contribution_margin / revenue (profit percentage) |
| margin_per_unit | double | contribution_margin / units_sold |
| n_orders | bigint | Orders containing the item |
| order_frequency | double | n_orders / all orders |
| popularity_share | double | units_sold / all units sold |
| popularity_rank_pct | double | Percent rank of units_sold among items (1.0 = best seller) |
| n_locations | bigint | Restaurants that sold it |
| active_days | bigint | Days with at least one sale |
| first_sale_date | date | First sale |
| last_sale_date | date | Last sale |
| days_of_history | int | Days from first sale to the snapshot date (small = new item with little history) |
| is_new_item | boolean | days_of_history < 60 |
| days_since_last_sale | int | Days from last sale to the snapshot date |
| repeat_purchase_rate | double | Share of identified buyers who bought it in 2+ different orders |
| n_identified_buyers | bigint | Identified (non-guest) buyers |
| avg_rating | double | Average rating from ratings linked to a real purchase |
| n_ratings | bigint | Number of those ratings |
| rating_trend | double | Average rating last 90 days minus previous 90 days (NULL if fewer than 5 ratings in either window) |
| avg_rating_all | double | Average rating including unverified ratings (no purchase) |
| n_unverified_ratings | bigint | Ratings with no order_id (suspicious) |
| wasted_portions | double | Portions wasted (clean wastage records) |
| wastage_cost | double | Cost of the wasted portions |
| wastage_pct | double | wasted / (sold + wasted) |
| promotion_dependency | double | Share of units sold on a discounted line |
| avg_discount_pct | double | discount_total / gross revenue of the item |
| weekend_share | double | Share of units sold on Saturday/Sunday |
| recent_units | bigint | Units in the last 56 days |
| prior_units | bigint | Units in the 56 days before that |
| sales_trend_pct | double | recent_units / prior_units - 1 (NULL if prior < 20 units) |
| relative_sales_trend_pct | double | item trend relative to the whole chain's trend (removes seasonality and growth shared by all items) |
| first_list_price | double | List price on the first day it was priced |
| last_list_price | double | List price on the last day |
| n_price_changes | bigint | Number of distinct list-price changes |
| price_change_pct | double | last_list_price / first_list_price - 1 |
| cost_change_pct | double | Unit cost change over the period |

## customer_features  (54,293 rows)

| Column | Type | Meaning |
|---|---|---|
| customer_id | string | Customer key |
| signup_date | date | Registration date |
| age_band | string | Age band ('UNKNOWN' when missing) |
| home_location_id | string | Home restaurant |
| acquisition_source | string | How the customer was acquired |
| loyalty_member | boolean | Eligible for loyalty rewards |
| days_since_signup | int | Customer age in days at the snapshot |
| recency_days | int | R: days since the last order (snapshot minus last order date) |
| frequency | bigint | F: number of completed orders |
| monetary | double | M: total amount paid |
| r_score | bigint | RFM score 1-5 for recency (5 = most recent) |
| f_score | bigint | RFM score 1-5 for frequency (5 = most orders) |
| m_score | bigint | RFM score 1-5 for monetary value (5 = highest spend) |
| avg_order_value | double | monetary / frequency |
| first_order_date | date | First order |
| last_order_date | date | Last order |
| span_days | int | Days between first and last order |
| active_days | bigint | Distinct days with an order |
| active_months | bigint | Distinct months with an order |
| avg_days_between_orders | double | span_days / (frequency - 1); NULL for one-order customers |
| avg_basket_units | double | Average units per order |
| avg_basket_lines | double | Average lines per order |
| promo_order_share | double | Share of orders with ANY promotion (includes welcome / loyalty entitlements) |
| campaign_promo_share | double | Share of orders with a public campaign promotion = promotion sensitivity |
| avg_discount_pct | double | Average discount share of gross revenue |
| peak_hour_share | double | Share of orders in peak hours |
| weekend_order_ratio | double | Share of orders on Saturday/Sunday |
| online_order_share | double | Share of orders through the app or delivery platforms |
| n_channels | bigint | Distinct channels used |
| n_locations | bigint | Distinct restaurants visited |
| preferred_channel | string | Most used channel |
| favorite_category | string | Category with most units |
| category_diversity | bigint | Distinct categories bought |
| orders_recent | bigint | Orders in the last 90 days |
| orders_prior | bigint | Orders in the 90 days before that |
| frequency_change | bigint | orders_recent - orders_prior (negative = declining engagement, churn signal) |
| spend_recent | double | Spend in the last 90 days |
| spend_prior | double | Spend in the 90 days before that |
| spend_change_pct | double | spend_recent / spend_prior - 1 (NULL if no prior spend) |

## location_features  (24 rows)

| Column | Type | Meaning |
|---|---|---|
| location_id | string | Restaurant key |
| restaurant_name | string | Name |
| city | string | City |
| region | string | Region |
| size_tier | string | SMALL / MEDIUM / LARGE |
| seating_capacity | int | Seats |
| opening_date | date | Opening date |
| n_orders | bigint | Completed orders |
| revenue | double | Revenue after discount |
| contribution_margin | double | revenue - ingredient cost |
| margin_after_fees | double | contribution margin - platform fees |
| margin_after_fees_pct | double | margin_after_fees / revenue |
| units_sold | bigint | Units sold |
| avg_order_value | double | Average amount paid per order |
| n_customers | bigint | Distinct identified customers |
| repeat_customer_rate | double | Share of its customers with 2+ orders at this restaurant |
| avg_discount_pct | double | Average order discount share |
| promo_order_share | double | Share of orders with a promotion |
| online_order_share | double | Share of app/delivery orders |
| weekend_order_share | double | Share of weekend orders |
| first_order_date | date | First order (late = new restaurant) |
| trading_days | bigint | Days with orders |
| orders_per_trading_day | double | n_orders / trading_days |
| revenue_per_trading_day | double | revenue / trading_days |
| revenue_per_seat | double | revenue / seating_capacity |
| n_cancelled_orders | bigint | Cancelled / refunded / void orders |
| cancellation_rate | double | cancelled / (completed + cancelled) |
| wasted_portions | double | Portions wasted |
| wastage_cost | double | Cost of waste |
| wastage_pct | double | wasted / (sold + wasted) |
| wastage_cost_pct_revenue | double | wastage_cost / revenue |
| avg_restaurant_rating | double | Average restaurant-level rating (verified purchases only) |
| avg_item_rating | double | Average dish rating (verified purchases only) |
| n_ratings | bigint | Verified ratings |
| n_items_sold | bigint | Distinct dishes sold |
| orders_recent | bigint | Orders in the last 56 days |
| orders_prior | bigint | Orders in the 56 days before that |
| order_trend_pct | double | orders_recent / orders_prior - 1 (NULL if prior < 50 orders) |
