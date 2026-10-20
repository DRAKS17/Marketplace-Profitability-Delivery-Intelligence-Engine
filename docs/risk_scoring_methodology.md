# Business Risk Layer & Composite Operational Vulnerability Index (OVI)

## 1. Executive Summary & Architectural Overview
The **Business Risk Layer** translates machine learning predictions ($P_{\text{late}}$) and commercial unit economics into an actionable operational triage system.

Rather than treating delivery risk as an isolated binary outcome, this architecture couples **operational vulnerability** with **commercial contribution margin** to categorize every marketplace order into a **2x2 Strategic Action Matrix**.

---

## 2. Composite Operational Vulnerability Index (OVI) Mathematical Contract

The Operational Vulnerability Index ($0 \le \text{OVI} \le 100$) integrates four independent failure dimensions:

$$\text{OVI} = S_{\text{delay}} + S_{\text{freight}} + S_{\text{seller}} + S_{\text{route}}$$

| Risk Dimension | Max Score | Mathematical Formulation | Operational Rationale |
|---|---|---|---|
| **Predicted Delay Risk** | **40 pts** | $S_{\text{delay}} = P_{\text{late}} \times 40$ | Direct ML output from trained Decision Tree at carrier dispatch. |
| **Freight Friction** | **25 pts** | $S_{\text{freight}} = \min\left(\frac{\text{freight\_ratio}}{0.50}, 1.0\right) \times 25$ | Shipping exceeding 50% of basket value triggers extreme buyer dissatisfaction. |
| **Merchant Unreliability** | **20 pts** | $S_{\text{seller}} = \min\left(\frac{\text{seller\_prior\_late\_rate}}{0.25}, 1.0\right) \times 20$ | Chronic dispatch tardiness indicates systemic merchant fulfillment failure. |
| **Route Complexity** | **15 pts** | $S_{\text{route}} = \left(0.5 \frac{\text{dist}}{2500\text{km}} + 0.5 \cdot \text{interstate}\right) \times 15$ | Long-haul interstate line-haul corridors face multi-hub transit friction. |

---

## 3. Commercial Net Contribution Formulation

Every order is evaluated for its forward-looking **Expected Net Contribution Margin**:

$$\text{Net Expected CM} = (\text{GMV} \times 0.12) - \text{Payment Fee} - (P_{\text{late}} \times \$20.00)$$

Where:
- **Payment Fee**: 2.0% on credit cards; 1.0% on Boleto/Debit/Vouchers.
- **Expected Incident Cost**: $P_{\text{late}} \times (\$15\text{ voucher} + \$5\text{ CS labor})$.

---

## 4. The 2x2 Strategic Profit-Risk Action Matrix

Orders are segmented at carrier dispatch scan into four operational quadrants:

| Strategic Quadrant | Orders | Order % | Total GMV | GMV % | Avg OVI | Avg Net CM | Actual Late Rate % | Strategic Playbook |
|---|---|---|---|---|---|---|---|---|
| **Q1: Crown Jewels (High Profit, Low Risk)** | 27,651 | 27.8% | $7,418,830.50 | 54.6% | 26.2 | $21.32 | **4.10%** | Protect & Delight: VIP tracking, loyalty perks. |
| **Q2: Danger Zone (High Profit, High Risk)** | 4,842 | 4.9% | $1,854,959.30 | 13.6% | 52.1 | $25.57 | **16.80%** | Proactive Carrier Triage: Expedited hub sorting, preemptive SMS. |
| **Q3: Value Drains (Low Profit, High Risk)** | 28,810 | 29.0% | $2,018,330.51 | 14.8% | 56.4 | $-5.76 | **14.73%** | Friction Elimination: Freight surcharges, seller SLA audits. |
| **Q4: Steady Workhorses (Low Profit, Low Risk)** | 38,138 | 38.4% | $2,299,523.39 | 16.9% | 31.4 | $-0.51 | **4.84%** | Automated Efficiency: Standard low-touch fulfillment. |

---

## 5. Key Operational Findings

1. **The Crown Jewels Anchor the Business**: **Q1** represents **54.6% of all marketplace GMV** ($7.42M BRL) while sustaining a remarkably low late delivery rate of **4.10%**.
2. **Danger Zone Contains High Commercial Exposure**: **Q2** orders generate **$1.85M BRL GMV** with an average basket of **$383.10 BRL**, but suffer an actual failure rate of **16.80%** (over 4x higher than Q1). Prioritizing proactive courier intervention in Q2 prevents the majority of high-dollar customer escalations.
3. **Value Drains Produce Negative Unit Economics**: **Q3** orders average negative expected contribution ($-5.76 BRL per order) due to thin margins eroded by high shipping fees and a **14.73% delivery failure rate**.

---

## 6. PostgreSQL Star Schema Integration
The Business Risk Layer is materialized directly in PostgreSQL `marketplace_analytics`:
- **Target Table**: `mart.order_risk_profile` (99,441 records).
- **Executive Views**:
  - `mart.view_quadrant_executive_summary`
  - `mart.view_seller_risk_exposure`
  - `mart.view_category_risk_profile`