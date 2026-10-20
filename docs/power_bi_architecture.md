# Power BI Executive Dashboard Architecture & DAX Specification

## 1. Executive Overview & Data Model Architecture
This document establishes the enterprise Power BI reporting architecture for the **Marketplace Profitability & Delivery Intelligence Engine**.

The data model follows the classic **Kimball Star Schema** pattern with strict 1-to-many single-direction filtering:

```text
               +-----------------------+
               |       dim_date        |
               +-----------------------+
                           │ 1
                           │
                           ▼ *
+--------------------+   +------------------------------------+   +-------------------------+
|   dim_geography    |──▶|      fact_order_intelligence       |◀──|   dim_seller_summary    |
+--------------------+ 1 |     (99,441 Order Grain Rows)      | 1 +-------------------------+
                         +------------------------------------+
                                           ▲
                                           │ *
                                           │ 1
                               +-------------------------+
                               |  dim_category_summary   |
                               +-------------------------+
```

---

## 2. Enterprise DAX Measures Library
All metrics are defined as explicit DAX measures housed in a dedicated `_Measures` table organized into functional display folders:

### Folder: `01. Financial & Commercial`
```dax
-- Gross Merchandise Value (GMV)
Total GMV = SUM(fact_order_intelligence[order_total_item_value])

-- Total Shipping Fees Charged
Total Freight = SUM(fact_order_intelligence[order_total_freight_value])

-- Total Order Value (GMV + Freight)
Total Order Value = SUM(fact_order_intelligence[order_total_value])

-- Platform Gross Commission Revenue (12% Take-Rate on GMV)
Gross Revenue = SUM(fact_order_intelligence[gross_platform_revenue_brl])

-- Payment Processing Costs
Payment Processing Cost = SUM(fact_order_intelligence[payment_processing_fee_brl])

-- Expected Late Remedy Liability ($20 per expected incident)
Expected Remedy Cost = SUM(fact_order_intelligence[expected_late_remedy_cost_brl])

-- Platform Net Contribution Margin
Net Contribution Margin = SUM(fact_order_intelligence[expected_net_contribution_brl])

-- Effective Platform Take-Rate (%)
Effective Take-Rate Pct = 
DIVIDE([Net Contribution Margin], [Total GMV], 0) * 100

-- Average Order Value (AOV)
Average Order Value = DIVIDE([Total GMV], [Total Orders], 0)
```

### Folder: `02. Logistics & Delivery Performance`
```dax
-- Total Orders
Total Orders = COUNTROWS(fact_order_intelligence)

-- Delivered Orders
Delivered Orders = 
CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[is_delivered] = TRUE)

-- Late Delivery Count
Late Delivery Orders = 
CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[is_late_delivery] = 1)

-- Late Delivery Rate (%)
Late Delivery Rate Pct = 
DIVIDE([Late Delivery Orders], [Delivered Orders], 0) * 100

-- On-Time Delivery Rate (%)
On-Time Delivery Rate Pct = 100 - [Late Delivery Rate Pct]

-- Average Carrier Transit Duration (Days)
Avg Carrier Transit Days = AVERAGE(fact_order_intelligence[carrier_transit_duration_days])

-- Average Seller Dispatch Latency (Hours)
Avg Seller Dispatch Hours = AVERAGE(fact_order_intelligence[seller_dispatch_duration_hours])

-- Average Delivery Delay (Days)
Avg Delivery Delay Days = AVERAGE(fact_order_intelligence[delivery_delay_days])
```

### Folder: `03. Risk & Strategic Quadrants`
```dax
-- Average Operational Vulnerability Index (OVI)
Avg OVI = AVERAGE(fact_order_intelligence[operational_vulnerability_index])

-- Danger Zone (Q2) GMV
Danger Zone GMV = 
CALCULATE([Total GMV], LEFT(fact_order_intelligence[strategic_quadrant], 2) = "Q2")

-- Danger Zone GMV Share (%)
Danger Zone GMV Share Pct = 
DIVIDE([Danger Zone GMV], [Total GMV], 0) * 100

-- Crown Jewels (Q1) GMV Share (%)
Crown Jewels GMV Share Pct = 
DIVIDE(CALCULATE([Total GMV], LEFT(fact_order_intelligence[strategic_quadrant], 2) = "Q1"), [Total GMV], 0) * 100

-- High Vulnerability Orders (OVI >= 50)
High Vulnerability Orders = 
CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[operational_vulnerability_index] >= 50)
```

### Folder: `04. Customer Experience (CSAT)`
```dax
-- Average Customer Rating (Stars)
Average CSAT = AVERAGE(fact_order_intelligence[review_score])

-- Total Reviews Logged
Total Reviews = COUNT(fact_order_intelligence[review_score])

-- Negative Review Count (1-2 Stars)
Negative Reviews = 
CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[review_score] IN {1, 2})

-- Negative Review Share (%)
Negative Review Share Pct = DIVIDE([Negative Reviews], [Total Reviews], 0) * 100

-- Delivery Issue Complaint Rate (%)
Delivery Issue Rate Pct = 
DIVIDE(CALCULATE(COUNTROWS(fact_order_intelligence), fact_order_intelligence[is_delivery_issue] = TRUE), [Total Reviews], 0) * 100
```

---

## 3. Four-Page Dashboard Blueprints & Visual Layout

### Page 1: Executive Overview & Commercial Health
- **Header KPI Cards**: `Total GMV` (\$13.59M), `Total Orders` (99.4k), `Net Contribution Margin` (\$1.17M), `Effective Take-Rate` (8.77%), `Avg CSAT` (4.09 ★).
- **Visual 1 (Area/Line Chart)**: Monthly GMV vs Net Contribution Margin over time with dynamic Take-Rate line.
- **Visual 2 (2x2 Matrix / Scatter)**: The Strategic Profit-Risk Matrix (X-Axis: Expected Net CM, Y-Axis: OVI, Bubble Size: GMV, Color: Quadrant).
- **Visual 3 (Horizontal Bar Chart)**: Top 10 Product Categories by Net Cash Contribution Margin.
- **Visual 4 (Donut Chart)**: GMV Concentration by Strategic Quadrant (showing 54.6% Crown Jewels vs 13.6% Danger Zone).

### Page 2: Delivery Intelligence & Logistics Operations
- **Header KPI Cards**: `Late Delivery Rate` (8.11%), `On-Time Rate` (91.89%), `Avg Transit Time` (12.1 days), `Avg Dispatch Latency` (79.2 hours).
- **Visual 1 (Dual-Axis Combo Chart)**: Carrier Transit Duration (Days) vs Seller Dispatch Hours by Destination State.
- **Visual 2 (Choropleth Map / Shape Map)**: Brazil State Late Delivery Rate (%) heatmap (visualizing high delay risk in Northern/Northeastern corridors).
- **Visual 3 (Histogram / Column Chart)**: Delivery Delay Distribution in Days (clipped from -20 to +20 days with vertical SLA target marker).
- **Visual 4 (Decomposition Tree)**: Delivery SLA Failure root-cause breakdown: Interstate vs Intrastate $\rightarrow$ Customer Macro Region $\rightarrow$ Seller Late Dispatch.

### Page 3: Customer Experience & Sentiment Intelligence
- **Header KPI Cards**: `Avg CSAT` (4.09), `Promoter Share` (77.2% 4-5 stars), `Detractor Share` (14.2% 1-2 stars), `Delivery Complaints` (5,245 tickets).
- **Visual 1 (Box Plot / Scatter)**: Customer Rating vs Delivery Delay (demonstrating the collapse from 4.29 to 2.57 stars when delay > 0 days).
- **Visual 2 (Stacked Bar Chart)**: CSAT Rating distribution (1 to 5 stars) split by Delivery Timeliness (On-Time vs Late).
- **Visual 3 (Treemap / Bar Chart)**: NLP Issue Category breakdown (`delivery_issue` vs `product_quality_issue` vs `positive_experience`).
- **Visual 4 (Table Visual)**: Recent negative customer feedback verbatim with sentiment classification and seller attribution.

### Page 4: Merchant & Seller Risk Audit
- **Header KPI Cards**: `Total Active Sellers` (3,095), `High-Risk Sellers` (312), `Danger Zone Exposure GMV` (\$1.85M), `Avg Seller Late Rate` (8.3%).
- **Visual 1 (Scatter Plot)**: Seller Order Volume vs Historical Delay Rate (log scale, identifying chronic operational offenders).
- **Visual 2 (Lorenz / Pareto Curve)**: Cumulative Merchant GMV concentration (confirming top 20% of merchants generate 84% of platform GMV).
- **Visual 3 (Audit Table Visual)**: Top 20 Merchants with highest Q2 Danger Zone GMV exposure, with columns for `Total Orders`, `GMV`, `Danger Zone Orders`, `Danger Zone %`, `Avg Late Rate`, and `Probation Status Flag`.

---

## 4. Visual Design System & Color Palette

| Role | Color Name | Hex Code | Usage |
|---|---|---|---|
| **Primary Brand** | Slate Navy | `#1E293B` | Titles, card headers, primary text, navigation bar |
| **Secondary Accent** | Royal Blue | `#2563EB` | GMV trends, Q1 Crown Jewels visuals, primary bars |
| **Risk / Failure** | Crimson Red | `#DC2626` | Late deliveries, Q2 Danger Zone, 1-2 star CSAT alerts |
| **Warning / Moderate** | Amber Orange | `#F59E0B` | Q3 Value Drains, 3-star CSAT, moderate vulnerability |
| **Success / Safe** | Emerald Green | `#10B981` | On-time deliveries, Q4 Workhorses, 5-star CSAT |
| **Neutral Canvas** | Ice White | `#F8FAFC` | Page background canvas, card containers |

---

## 5. How to Connect in Power BI Desktop

### Method A: High-Performance CSV Import (Recommended for offline / portable `.pbix`)
1. Open **Power BI Desktop**.
2. Click **Get Data** $\rightarrow$ **Text/CSV**.
3. Select `data/power_bi/fact_order_intelligence.csv`.
4. Repeat for `dim_date.csv`, `dim_geography.csv`, `dim_seller_summary.csv`, and `dim_category_summary.csv`.
5. Navigate to **Model View** and verify 1-to-many single-direction relationships from dimensions to fact table on keys (`order_purchase_date` $\rightarrow$ `date`, `customer_state` $\rightarrow$ `state_code`, `seller_id`, `primary_product_category`).

### Method B: PostgreSQL Direct Connection
1. In Power BI Desktop, select **Get Data** $\rightarrow$ **PostgreSQL Database**.
2. Server: `localhost:5432` | Database: `marketplace_analytics`.
3. Select Data Connectivity mode: **Import** (or **DirectQuery**).
4. Check views in schema `mart`: `mart.view_powerbi_orders`, `mart.view_powerbi_monthly_trend`, and `mart.view_powerbi_regional_logistics`.