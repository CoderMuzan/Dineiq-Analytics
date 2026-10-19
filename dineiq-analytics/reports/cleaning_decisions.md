# Cleaning decisions

Every rule applied by `spark_jobs/03_clean_data.py`, in execution order, with the number of rows it touched.

Actions: **REMOVE** exact duplicate | **REPAIR** value derived from other data | **QUARANTINE** moved to `quarantine/` with a reason | **ROUTE** valid but not revenue (cancelled etc.) | **FLAG** kept, marked by a column.

| Rule | Table | Condition | Action | Rows | Why |
|---|---|---|---|---|---|
| C-01 | customers | same customer_id repeated | REMOVE | 110 | identical copies of a profile; one is enough |
| C-02 | customers | age_band is NULL | REPAIR | 2,152 | filled with 'UNKNOWN' so group-bys do not silently drop customers |
| P-01 | pricing_history | price <= 0 or outside 0.5x..3.0x base price | QUARANTINE | 6 | wrong price; the previous valid period's price is used for that period via the as-of lookup (rule L-05) |
| O-01 | orders | same order_id repeated | REMOVE | 1,545 | exact copies of an order header |
| L-01 | order_items | same order_line_id repeated | REMOVE | 3,462 | exact copies of an order line |
| O-03 | orders | order date outside 2025-10-01..2026-09-30 | QUARANTINE | 64 | future / ancient dates are impossible for this dataset |
| O-04 | orders | location_id missing or not in restaurants | QUARANTINE | 610 | cannot be attributed to a restaurant; guessing would corrupt location analysis |
| O-02 | orders | order_datetime missing or impossible (e.g. 2026-13-45) | QUARANTINE | 125 | an order without a date cannot be placed in time; the date cannot be guessed |
| O-05 | orders | same customer, restaurant, channel, basket and total again within 200s | QUARANTINE | 331 | a double-submitted transaction; the first one is kept, the repeat would double-count revenue |
| O-06 | orders | order_status = VOID | ROUTE | 2,208 | valid record but not revenue; kept in clean_data/cancelled_orders for cancellation analysis |
| O-06 | orders | order_status = CANCELLED | ROUTE | 11,415 | valid record but not revenue; kept in clean_data/cancelled_orders for cancellation analysis |
| O-06 | orders | order_status = REFUNDED | ROUTE | 3,572 | valid record but not revenue; kept in clean_data/cancelled_orders for cancellation analysis |
| L-03 | order_items | parent order quarantined (invalid date) | QUARANTINE | 378 | lines follow their order |
| L-03 | order_items | parent order quarantined (invalid location) | QUARANTINE | 1,804 | lines follow their order |
| L-03 | order_items | parent order quarantined (near-duplicate) | QUARANTINE | 974 | lines follow their order |
| L-03 | order_items | parent order quarantined (date out of period) | QUARANTINE | 181 | lines follow their order |
| L-04 | order_items | item_id not in menu_items | QUARANTINE | 1,116 | unknown dish: no cost, category or price to analyse (a NEW item in hidden data should be added to the menu first) |
| L-04 | order_items | quantity <= 0 or NULL | QUARANTINE | 573 | negative / zero quantity is not a sale; not repairable |
| L-04 | order_items | item_id is NULL | QUARANTINE | 1,053 | cannot tell what was sold; item-level and profit analysis would be wrong |
| L-05 | order_items | unit_price <= 0 or outside 0.5x..2.0x of the list price on the order date | REPAIR | 631 | replaced by the list price valid on the order date (pricing_history as-of lookup) |
| L-06 | order_items | discount < 0 or discount > quantity x price | REPAIR | 548 | recomputed from the order's promotion (discount_pct x gross if the item is in promotion scope, else 0). Large but valid discounts (e.g. manual 60-90%) are NOT changed - they are anomalies to detect later |
| L-07 | order_items | line_total recomputed | REPAIR | 1,096,701 | line_total = quantity x unit_price - discount_amount for every kept line |
| L-08 | order_items | lines of cancelled / refunded / void orders | ROUTE | 51,309 | stored in clean_data/cancelled_order_items |
| O-07 | orders | no valid line left after line cleaning (or no lines at all) | QUARANTINE | 128 | an order without items has no analytical value |
| O-08 | orders | payment_method is NULL | REPAIR | 7,412 | filled with 'UNKNOWN' |
| O-09 | orders | customer_id is NULL | FLAG | 44,253 | kept; column is_guest = true (guest checkout is legitimate, but excluded from customer analytics) |
| O-10 | orders | order totals recomputed from the cleaned lines | REPAIR | 2,624 | subtotal, discount_total and total_amount now equal the sum of the kept lines; originals kept in *_original columns |
| R-01 | ratings | rating_value not in 1..5 | QUARANTINE | 294 | impossible score; cannot know the real one |
| R-03 | ratings | location_id invalid but order_id points to a valid order | REPAIR | 75 | restaurant taken from the rated order |
| R-04 | ratings | order_id is NULL (no purchase) | FLAG | 879 | kept; has_purchase_link = false. Used later by rating-anomaly detection (do NOT delete: these may be fake reviews) |
| W-01 | wastage | item_id is NULL | QUARANTINE | 52 | cannot attribute waste to a dish |
| W-01 | wastage | location_id not in restaurants | QUARANTINE | 38 | cannot attribute waste to a restaurant |
| W-02 | wastage | quantity <= 0, larger than the prepared quantity, or > 1000 portions (after unit conversion) | QUARANTINE | 50 | physically impossible; cannot be repaired |
| W-03 | wastage | unit is kg / g / pcs / Portion / PORTION / portions (anything but exactly 'portion') | REPAIR | 8,089 | all quantities converted to portions: kg x 1000 / portion_weight_g, g / portion_weight_g, pcs and spelling variants = portions |
| I-01 | inventory | location_id not in restaurants | QUARANTINE | 106 | cannot attribute stock to a restaurant |
| I-02 | inventory | unit = kg | REPAIR | 3,870 | converted to portions with portion_weight_g |
| I-03 | inventory | closing_stock < 0 | REPAIR | 96 | recomputed: max(opening + replenished - consumed, 0) |

## Row reconciliation

- **orders (unique ids)**: 386,585 raw = 368,132 clean + cancelled 17,195 + quarantined 1,258
- **order_items (unique ids)**: 1,154,089 raw = 1,096,701 clean + cancelled 51,309 + quarantined 6,079
