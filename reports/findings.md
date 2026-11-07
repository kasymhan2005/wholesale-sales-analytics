# Findings and proposed follow-up

## Monthly sales

Confirmed order value: RUB 2,038,231,821.56; 309 confirmed orders; average value RUB 6,596,219.49. Canceled orders: 37 of 346 (10.69%). These metrics use distinct orders, not order-line counts.

## A spike with a possible operational explanation

March 13: 19 cancellations and 5 confirmations. March 14: 34 confirmations and no cancellations. Exact matching identifies 16 next-day pairs, representing 47.06% of March 14 confirmed orders. All 16 have a unique counterpart under the selected rule. Their confirmed value totals RUB 115,285,027.45.

Interpretation: repeat submission is consistent with the records. The observations do not prove an outage, automatic cancellation, or incremental recovery of otherwise lost revenue. Five orders still confirmed on March 13, so a claim that all orders failed that day would be incorrect.

Proposed follow-up: inspect incident logs and cancellation reasons for March 13; confirm the matching pairs with CRM records; monitor sudden changes in cancellation rates in future periods.

## Assortment

425 products in class A account for approximately 80% of revenue; 357 in B account for the next approximately 15%; 398 in C account for the remainder. There are 497 catalog products with no confirmed sales in this month.

Among brands with at least 15 catalog products, the no-sales share exceeds 50% for Marantz (19/22), Dali (49/67), Pioneer (70/103) and KEF (54/82).

Proposed follow-up: review product availability, listing quality and several months of demand before changing the range. Sales absence alone does not show that inventory is obsolete. No stock or holding-cost data are available.

## Managers and customers

Маргарита Камертонова leads revenue (17.04% of total), while Виктор Тромбонов leads confirmed orders (50, or 16.18%). Differences may reflect account allocation or basket size. Review both volume and value, with cancellation reasons, rather than using a single ranking for compensation.

There are 74 purchasing clients. The top five contribute 15.56% of confirmed value. This is a descriptive concentration measure, not evidence of churn risk.

## Evidence

Computed tables: `daily.csv`, `pairs.csv`, `product_sales.csv`, `coverage.csv`, `managers.csv`, `clients.csv`. Source manifest: `input_manifest.csv`. All are rebuilt by `python run_analysis.py`.
