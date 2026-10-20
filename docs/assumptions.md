# Commercial Assumptions, Metric Taxonomy & Financial Governance

This document establishes the official financial governance, parameter definitions, and metric taxonomy for the **Marketplace Profitability & Delivery Intelligence Engine**.

---

## 1. Metric Taxonomy: Observed vs Derived vs Assumed

To maintain analytical integrity, every metric in this platform is strictly classified into one of three methodological tiers:

```text
+-----------------------+     +------------------------+     +------------------------+
| 1. OBSERVED DATA      | --> | 2. DERIVED METRICS     | --> | 3. ASSUMED PARAMETERS  |
| Raw system telemetry  |     | Deterministic math     |     | Modeled commercial P&L |
| 100% Fact-Based       |     | Calculated from facts  |     | Scenario Sensitivity   |
+-----------------------+     +------------------------+     +------------------------+
```

### Tier 1: Observed Data (Raw Truth)
Telemetry captured directly from transaction databases without modification:
- `price`: Exact sales price per line-item in Brazilian Real (BRL).
- `freight_value`: Shipping fee charged for each line-item in BRL.
- `payment_type`: Customer tender method (`credit_card`, `boleto`, `voucher`, `debit_card`).
- `payment_installments`: Financing installment count chosen by customer (1–24).
- `order_purchase_timestamp`: Exact checkout authorization moment.
- `order_delivered_carrier_date`: Timestamp of parcel scan at carrier hub.
- `order_delivered_customer_date`: Timestamp of physical parcel arrival at customer doorstep.
- `order_estimated_delivery_date`: Promised delivery SLA target communicated at checkout.
- `review_score`: Customer post-delivery rating (1 to 5 stars).

---

### Tier 2: Derived Metrics (Deterministic Calculations)
Mathematical transformations derived directly from Tier 1 observed data:
- **Gross Merchandise Value (GMV)**:
  $$\text{GMV} = \sum_{\text{items}} \text{price}$$
- **Total Order Value**:
  $$\text{Total Order Value} = \text{GMV} + \sum_{\text{items}} \text{freight\_value}$$
- **Freight Ratio**:
  $$\text{Freight Ratio} = \frac{\text{Total Freight}}{\text{Total Order Value}}$$
- **Delivery Delay (Days)**:
  $$\text{Delivery Delay} = \frac{\text{delivered\_date} - \text{estimated\_date}}{86,400\text{ seconds}}$$
  *(Positive = Late, Negative = Early/On-Time)*.
- **Binary Late Delivery Indicator (`is_late_delivery`)**:
  $$\text{is\_late\_delivery} = \begin{cases} 1 & \text{if Delivery Delay} > 0.0 \\ 0 & \text{if Delivery Delay} \le 0.0 \\ \text{NaN} & \text{if undelivered} \end{cases}$$
- **Haversine Distance**: Great-circle distance between customer and seller postal district centroids in kilometers.

---

### Tier 3: Assumed Parameters (Modeled Commercial P&L)
Marketplace economic parameters established to evaluate platform contribution margin where internal proprietary financial records are private:

| Commercial Parameter | Base Scenario | Conservative (Stress) | Optimistic | Business Rationale & Benchmark |
|---|---|---|---|---|
| **Marketplace Take-Rate ($\tau$)** | **12.0%** | **10.0%** | **15.0%** | Standard Latin American e-commerce commission (Mercado Libre / Magazine Luiza charge 10–16%). Charged on GMV. |
| **Credit Card Processing Fee ($\gamma_{\text{cc}}$)** | **2.0%** | **2.5%** | **1.8%** | Merchant acquirer interchange fee charged on total transaction value. |
| **Boleto / Debit Processing Fee ($\gamma_{\text{bol}}$)** | **1.0%** | **1.2%** | **0.8%** | Standard Brazilian banking clearing fee for Boleto Bancário. |
| **Customer Service Overhead ($\kappa$)** | **\$5.00 BRL** | **\$8.00 BRL** | **\$3.00 BRL** | Operational labor cost per order filing an explicit delivery/product defect review. |
| **Late Delivery Remedy Voucher ($\rho$)** | **\$15.00 BRL** | **\$25.00 BRL** | **\$10.00 BRL** | Proactive goodwill coupon or shipping rebate credited to customer to prevent account churn. |

---

## 2. Platform Contribution Margin Formula Contract

From the perspective of the **Platform Operator (Olist)**:

### Platform Net Revenue
$$\text{Net Revenue} = \text{GMV} \times \tau$$

### Direct Variable Fulfillment Expenses
$$\text{Variable Cost} = \text{Payment Fee} + \text{Customer Support Cost} + \text{Late Delivery Voucher Cost}$$

Where:
- $\text{Payment Fee} = \sum \begin{cases} \text{Total Value} \times \gamma_{\text{cc}} & \text{if Credit Card} \\ \text{Total Value} \times \gamma_{\text{bol}} & \text{if Boleto / Debit / Voucher} \end{cases}$
- $\text{Support Cost} = \text{Orders with Complaints} \times \kappa$
- $\text{Voucher Cost} = \text{Late Delivered Orders} \times \rho$

### Platform Net Contribution Margin (CM)
$$\text{Net Contribution Margin} = \text{Net Revenue} - \text{Variable Cost}$$

$$\text{Net Margin \% (Effective Take-Rate)} = \frac{\text{Net Contribution Margin}}{\text{GMV}} \times 100$$

---

## 3. Disproving the "Late GMV = Lost Revenue" Myth

> [!WARNING]
> **ANALYTICAL INTEGRITY WARNING**:
> In interviews, never claim: *"We had \$1.1 Million of GMV delivered late, so the marketplace lost \$1.1 Million of revenue."*

### Why This Claim is Financially False:
1. **The Transaction Still Settled**: An order that arrives 2 days late is still received by the customer. The customer keeps the product, the seller gets paid, and the platform retains its 12% commission.
2. **Cancellation vs Delay**: Only orders with `order_status = 'canceled'` (approx. 625 orders) represent canceled transactions. Delivered orders that are late are **fulfilled orders with degraded customer experience**, not refunded cancellations.
3. **The True Economic Impact of Late Deliveries**:
   - **Direct Cash Expense**: Cost of customer service tickets and appeasement vouchers ($\approx \$117\text{k BRL}$).
   - **Indirect Opportunity Loss**: Customer dissatisfaction (CSAT collapsing from 4.29 to 2.57), reducing repeat purchase probability and future Customer Lifetime Value (LTV).
