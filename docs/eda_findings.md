# Exploratory Data Analysis (EDA) Executive Report

**Module**: `src/marketplace_intelligence/eda_generator.py`  
**Scope**: Statistical Distributions, Operational Friction, and Commercial Hypotheses  
**Data Population**: 99,441 Orders (96,478 Delivered Orders)  

---

## Finding 1: Delivery Delay vs Customer Satisfaction (CSAT)

![Delay vs CSAT](figures/01_delay_vs_csat.png)

- **Business Question**: How does delivery timeliness affect customer review scores, and what is the tolerance threshold before reviews collapse to 1 star?
- **Methodology**: Evaluated `delivery_delay_days = (delivered_date - estimated_date)` across star ratings 1 to 5. Clipped outliers at [-25, +25] days.
- **Quantified Result**: 5-star reviews arrive on average **13.2 days ahead of the promised estimate**. In contrast, 1-star reviews have a median delay of **+3.5 days late**.
- **Significance**: E-commerce customers do not merely want on-time delivery; early arrival creates customer delight. Once an order crosses into late delivery, review scores collapse immediately.
- **Limitations**: Some 1-star reviews occur even when deliveries are early due to damaged products or incorrect items.

---

## Finding 2: Freight-to-Price Friction across Product Categories

![Freight Friction](figures/02_freight_ratio_distribution.png)

- **Business Question**: Which merchandise categories experience the highest shipping cost friction relative to item value?
- **Methodology**: Calculated median `freight_ratio = (freight / total_order_value)` across categories with at least 500 orders.
- **Quantified Result**: Bulky categories like `furniture_decor`, `office_furniture`, and `home_appliances_2` have median freight ratios between **22.5% and 27.8%**. In contrast, luxury and small tech categories (`watches_gifts`, `computers_accessories`) have freight ratios under **12.0%**.
- **Significance**: High freight ratios directly suppress conversion rates and customer satisfaction. Bulky category logistics require regional consolidation fulfillment centers.

---

## Finding 3: Seller Volume vs Late Delivery Rate (The Scale Curve)

![Seller Volume vs Delay](figures/03_seller_volume_vs_delay_rate.png)

- **Business Question**: Does merchant fulfillment scale improve delivery timeliness or create logistical bottlenecks?
- **Methodology**: Plotted seller order volume against historical late-delivery rate on a logarithmic scale with GMV color coding.
- **Quantified Result**: Low-volume merchants (< 30 orders) have massive variance (0% to 50% late rates). High-volume merchants (> 500 orders) converge between **6.0% and 10.0%**, but several large merchants exhibit severe failure rates (> 20% late rate with > $40k GMV).
- **Significance**: Proves that large volume does not guarantee operational excellence. Vendor monitoring must track high-volume merchants with persistent delivery SLA breaches.

---

## Finding 4: Top Product Categories: GMV vs Net Contribution Margin

![Revenue vs Margin](figures/04_category_revenue_vs_margin.png)

- **Business Question**: Which categories generate the largest top-line merchandise value, and which generate the highest net cash contribution after payment fees and delivery remedy vouchers?
- **Methodology**: Compared gross GMV against estimated net margin (12% commission - 1.8% payment fees - $15 BRL per late order).
- **Quantified Result**: `health_beauty` and `watches_gifts` lead the marketplace with over **$105k BRL net contribution** each, maintaining high margin efficiency (8.6% to 9.2% net take-rate).
- **Significance**: Demonstrates that high top-line GMV in categories with high delay rates (e.g., `bed_bath_table`) suffers from disproportionate customer remedy costs.

---

## Finding 5: Regional Delivery Speed & Distance Friction (Brazil Macro-Regions)

![Regional Performance](figures/05_regional_delivery_speed.png)

- **Business Question**: How does delivery speed and SLA failure vary across Brazil's 5 macro-regions?
- **Methodology**: Mapped Brazilian destination states to their official macro-regions (Southeast, South, Northeast, Central-West, North).
- **Quantified Result**: Southeast deliveries take **9.2 days** on average (6.1% late rate). North deliveries take **25.8 days** on average (**16.8% late rate**).
- **Significance**: Brazilian e-commerce fulfillment is heavily geographically polarized. Because most sellers are clustered in São Paulo/Paraná, long-distance logistics to the North and Northeast face severe transit friction.

---

## Finding 6: Root-Cause Attribution: Seller Processing vs Carrier Transit Duration

![Seller vs Carrier](figures/06_seller_dispatch_vs_late_rate.png)

- **Business Question**: When an order is delivered late, is the bottleneck caused by the seller's internal packing/dispatch time or the carrier's transit time?
- **Methodology**: Decomposed fulfillment into `seller_dispatch_duration_hours` (purchase to carrier handoff) and `carrier_transit_duration_days` (carrier to doorstep).
- **Quantified Result**: For late orders, sellers took an average of **4.8 days** to dispatch (vs 2.8 days for on-time orders). **43.2% of late orders were already late being dispatched** by the seller before the carrier even scanned the box.
- **Significance**: Disproves the common belief that logistics delays are purely the courier's fault. Seller dispatch latency is a major leading indicator of doorstep delivery failure.

---

## Finding 7: Merchant Revenue Concentration: Lorenz Curve & Gini Coefficient

![Lorenz Curve](figures/07_pareto_concentration_curve.png)

- **Business Question**: How severe is marketplace seller revenue inequality?
- **Methodology**: Constructed a Lorenz curve of cumulative seller percentage against cumulative GMV percentage, computing the Gini coefficient.
- **Quantified Result**: Gini coefficient = **0.76**. The top **19.8% of sellers generate 80.0% of total marketplace GMV**.
- **Significance**: Highlights vendor concentration risk. If a handful of top sellers leave or suffer operational failure, marketplace revenue is heavily impacted.

---

## Finding 8: Customer Lifetime Spend: One-Time vs Repeat Buyers

![Customer Spend](figures/08_customer_spend_comparison.png)

- **Business Question**: What is the commercial value of repeat buyers compared to one-time buyers?
- **Methodology**: Compared total cumulative monetary spend between one-time buyers and repeat buyers (identified via `customer_unique_id`).
- **Quantified Result**: Repeat buyers have a median total spend **32.4% higher** than one-time buyers ($218 BRL vs $164 BRL).
- **Significance**: Confirms that while repeat buyers represent only 3.1% of the customer base, they have significantly higher lifetime commercial value.