# Phase 2 automated test results

**53 / 53 checks passed**

| Group | Check | Result | Detail |
|---|---|---|---|
| A invariants | orders: order_id unique | PASS |  |
| A invariants | orders: all COMPLETED | PASS |  |
| A invariants | orders: no missing date, all inside the valid period | PASS |  |
| A invariants | orders: every restaurant id valid | PASS |  |
| A invariants | orders: payment_method never NULL | PASS |  |
| A invariants | orders: is_guest matches customer_id NULL | PASS |  |
| A invariants | order_items: order_line_id unique | PASS |  |
| A invariants | order_items: quantity > 0 | PASS |  |
| A invariants | order_items: unit_price > 0 | PASS |  |
| A invariants | order_items: item_id always a known menu item | PASS |  |
| A invariants | order_items: discount between 0 and gross | PASS |  |
| A invariants | order_items: line_total = qty x price - discount | PASS |  |
| A invariants | order_items: every line belongs to a clean order | PASS |  |
| A invariants | orders: every clean order has at least one line | PASS |  |
| A invariants | orders: subtotal = sum of line gross | PASS |  |
| A invariants | orders: discount_total = sum of line discounts | PASS |  |
| A invariants | orders: total = subtotal - discount + delivery fee | PASS |  |
| A invariants | no near-duplicate transactions left in clean orders | PASS | found 0 |
| A invariants | wastage: unit always 'portion' and 0 < qty <= prepared | PASS |  |
| A invariants | wastage: ids valid | PASS |  |
| A invariants | inventory: unit portion, stock >= 0, closing = max(open+repl-cons,0) | PASS |  |
| A invariants | ratings: values 1..5 and restaurant ids valid | PASS |  |
| A invariants | pricing_history: all prices positive | PASS |  |
| A invariants | quarantine tables carry a reason | PASS |  |
| B reconciliation | orders: raw unique ids = clean + cancelled + quarantined | PASS | 386,585 = 368,132 + 17,195 + 1,258 |
| B reconciliation | order_items: raw unique ids = clean + cancelled + quarantined | PASS | 1,154,089 = 1,096,701 + 51,309 + 6,079 |
| B reconciliation | no id is in two outputs | PASS |  |
| B reconciliation | ratings: raw = clean + quarantined | PASS |  |
| B reconciliation | wastage: raw = clean + quarantined | PASS |  |
| B reconciliation | inventory: raw = clean + quarantined | PASS |  |
| C known answers | DQ found planted 'orders.exact_duplicate_order_rows' | PASS | report 1,545 vs planted 1,545 |
| C known answers | DQ found planted 'orders.near_duplicate_transactions' | PASS | report 331 vs planted 332 |
| C known answers | DQ found planted invalid dates | PASS |  |
| C known answers | DQ found planted 'orders.invalid_location_id' | PASS | report 376 vs planted 376 |
| C known answers | DQ found planted 'orders.missing_location_id' | PASS | report 234 vs planted 234 |
| C known answers | DQ found planted 'order_items.exact_duplicate_line_rows' | PASS | report 3,462 vs planted 3,462 |
| C known answers | DQ found planted 'order_items.negative_or_zero_quantity' | PASS | report 602 vs planted 602 |
| C known answers | DQ found planted 'order_items.invalid_unit_price' | PASS | report 469 vs planted 464 |
| C known answers | DQ found planted 'order_items.extreme_unit_price' | PASS | report 207 vs planted 205 |
| C known answers | DQ found planted 'order_items.missing_item_id' | PASS | report 1,104 vs planted 1,102 |
| C known answers | DQ unknown item ids >= planted (copies of planted lines add a few) | PASS |  |
| C known answers | DQ incorrect discounts >= planted (zero-price lines add a few) | PASS |  |
| C known answers | DQ found planted 'ratings.invalid_rating_value' | PASS | report 294 vs planted 294 |
| C known answers | DQ found planted 'wastage.inconsistent_units' | PASS | report 8,106 vs planted 8,106 |
| C known answers | DQ found planted 'wastage.impossible_quantities' | PASS | report 50 vs planted 50 |
| C known answers | DQ found planted 'inventory.negative_closing_stock' | PASS | report 96 vs planted 96 |
| C known answers | DQ found planted 'inventory.inconsistent_units' | PASS | report 3,873 vs planted 3,873 |
| C known answers | DQ found planted 'pricing_history.invalid_price_rows' | PASS | report 6 vs planted 6 |
| C known answers | DQ found planted 'customers.duplicate_rows' | PASS | report 110 vs planted 110 |
| C known answers | loss-making best-sellers are still loss-making after cleaning | PASS | profit -12,363,346 NGN |
| C known answers | manual-discount anomalies were NOT cleaned away | PASS | 137 orders with >50% discount and no promotion |
| C known answers | catering anomalies survive: some orders above 500k NGN | PASS | 21 orders |
| C known answers | ratings without a purchase are kept and flagged | PASS |  |
