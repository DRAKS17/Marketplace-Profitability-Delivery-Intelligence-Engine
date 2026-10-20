# Model Card: Late Delivery Risk Decision Tree Classifier

## 1. Model Details
- **Model Identifier**: `LateDelivery-DecisionTree-v1`
- **Model Architecture**: Scikit-Learn `DecisionTreeClassifier` with `ColumnTransformer` preprocessing.
- **Hyperparameters**: `max_depth=6`, `min_samples_leaf=100`, `class_weight='balanced'`, `random_state=42`.
- **Prediction Moment**: Parcel Handover / Carrier Hub Scan (`order_delivered_carrier_date`).
- **Target Variable**: `is_late_delivery` $\in \{0, 1\}$ (Binary classification: delivered past estimated SLA).
- **Model Release Date**: October 2026.

---

## 2. Intended Use & Governance
- **Primary Purpose**: Preemptively identify in-transit orders at severe risk of late delivery at the moment they enter the carrier network.
- **Intended Users**: Marketplace logistics operations team, merchant support desks, automated CRM communication pipelines.
- **Out-of-Scope Uses**: Automated punitive financial penalties against couriers without human verification; real-time checkout latency estimation before dispatch.

### Strict Anti-Leakage Boundary
The following post-dispatch outcome attributes are **strictly prohibited** from the model's feature store:
- `review_score`, `review_comment_message`, `is_delivery_issue` (Captured weeks after doorstep delivery).
- `order_delivered_customer_date` (The terminal outcome timestamp).
- `delivery_delay_days`, `carrier_transit_duration_days`, `actual_delivery_duration_days`.

---

## 3. Data & Validation Strategy
- **Data Source**: Brazilian E-Commerce public dataset (Olist).
- **Training Population**: Orders strictly delivered with confirmed outcome timestamps (96,476 total orders).
- **Validation Strategy**: Strict **Temporal (Chronological) Split** (80% Train / 20% Test by purchase timestamp).
  - **Train Period**: September 2016 – May 26, 2018 (77,180 orders; 8.82% late delivery rate).
  - **Test Period**: May 26, 2018 – August 2018 (19,296 orders; 5.29% late delivery rate).
- **Rationale for Temporal Split**: Random splits leak future carrier network enhancements and seasonality back into training data. Temporal splitting mirrors real-world production forecasting.

---

## 4. Quantitative Performance Metrics

### Comparison against Benchmarks on Chronological Test Set (19,296 orders):

| Model Pipeline | ROC-AUC | PR-AUC | Positive Recall (Late) | Positive Precision | F1-Score |
|---|---|---|---|---|---|
| **Dummy Baseline** | 0.4936 | 0.0524 | 7.54% | 4.56% | 0.0568 |
| **Unweighted Tree** | 0.6773 | 0.2521 | 16.45% | 73.68% | 0.2690 |
| **Balanced Tree (Production)** | 0.7491 | 0.2843 | 57.20% | 8.28% | 0.1447 |

> [!NOTE]
> **PR-AUC Lift**: The Balanced Decision Tree achieves a **PR-AUC of 0.2843**, representing a **5.4x lift** over the test prevalence baseline (0.0524).

---

## 5. Decision Threshold Sensitivity & Risk Cost Optimization

In e-commerce delivery logistics, costs are highly asymmetric: missing a late delivery ($FN cost = $20 BRL) is far more damaging than sending a precautionary alert ($FP cost = $1 BRL).

|   Threshold |   Precision |   Recall |   F1-Score |   True Positives (TP) |   False Positives (FP) |   False Negatives (FN) | Estimated Risk Cost (BRL)   |
|------------:|------------:|---------:|-----------:|----------------------:|-----------------------:|-----------------------:|:----------------------------|
|         0.2 |      0.0625 |   0.9882 |     0.1176 |                  1009 |                  15134 |                     12 | $15,374.00                  |
|         0.3 |      0.073  |   0.9422 |     0.1355 |                   962 |                  12221 |                     59 | $13,401.00                  |
|         0.4 |      0.0819 |   0.9295 |     0.1506 |                   949 |                  10632 |                     72 | $12,072.00                  |
|         0.5 |      0.0828 |   0.572  |     0.1447 |                   584 |                   6467 |                    437 | $15,207.00                  |
|         0.6 |      0.1208 |   0.5083 |     0.1952 |                   519 |                   3777 |                    502 | $13,817.00                  |
|         0.7 |      0.1402 |   0.4594 |     0.2148 |                   469 |                   2876 |                    552 | $13,916.00                  |
|         0.8 |      0.3524 |   0.2174 |     0.2689 |                   222 |                    408 |                    799 | $16,388.00                  |

---

## 6. Feature Importance & Operational Attribution

The top 10 features driving decision splits (Gini Impurity Reduction):

| Feature | Relative Importance (%) | Domain Interpretation |
|---|---|---|
| `is_seller_late_dispatch` | 25.91% | Seller operational breach of shipping deadline |
| `customer_state_SP` | 19.43% | Destination in high-density, high-speed logistics hub (São Paulo) |
| `estimated_delivery_duration_days` | 16.45% | Promised SLA window buffer communicated at checkout |
| `seller_prior_late_rate` | 13.10% | Expanding historical delay track record of primary seller |
| `seller_dispatch_duration_hours` | 7.70% | Physical hours elapsed before merchant handed parcel to courier |
| `customer_state_MG` | 6.83% | Destination in Minas Gerais regional transit corridor |
| `haversine_distance_km` | 5.92% | Great-circle distance between merchant and customer centroids |
| `is_interstate_delivery` | 2.35% | Cross-border interstate line-haul requirement |
| `seller_state_RJ` | 0.72% | Origin in Rio de Janeiro carrier sorting hub |
| `seller_state_MG` | 0.64% | Origin in Minas Gerais regional network |

---

## 7. Extracted Tree Business Logic (Top 3 Decision Layers)

```text
|--- is_seller_late_dispatch <= 0.50
|   |--- customer_state_SP <= 0.50
|   |   |--- seller_prior_late_rate <= 0.05
|   |   |   |--- customer_state_MG <= 0.50
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- customer_state_MG >  0.50
|   |   |   |   |--- truncated branch of depth 3
|   |   |--- seller_prior_late_rate >  0.05
|   |   |   |--- estimated_delivery_duration_days <= 27.21
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- estimated_delivery_duration_days >  27.21
|   |   |   |   |--- truncated branch of depth 3
|   |--- customer_state_SP >  0.50
|   |   |--- estimated_delivery_duration_days <= 21.19
|   |   |   |--- haversine_distance_km <= 146.79
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- haversine_distance_km >  146.79
|   |   |   |   |--- truncated branch of depth 3
|   |   |--- estimated_delivery_duration_days >  21.19
|   |   |   |--- seller_state_RJ <= 0.50
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- seller_state_RJ >  0.50
|   |   |   |   |--- truncated branch of depth 3
|--- is_seller_late_dispatch >  0.50
|   |--- seller_dispatch_duration_hours <= 198.55
|   |   |--- customer_state_SP <= 0.50
|   |   |   |--- estimated_delivery_duration_days <= 31.38
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- estimated_delivery_duration_days >  31.38
|   |   |   |   |--- truncated branch of depth 3
|   |   |--- customer_state_SP >  0.50
|   |   |   |--- estimated_delivery_duration_days <= 24.06
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- estimated_delivery_duration_days >  24.06
|   |   |   |   |--- truncated branch of depth 3
|   |--- seller_dispatch_duration_hours >  198.55
|   |   |--- estimated_delivery_duration_days <= 30.34
|   |   |   |--- seller_dispatch_duration_hours <= 287.67
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- seller_dispatch_duration_hours >  287.67
|   |   |   |   |--- truncated branch of depth 3
|   |   |--- estimated_delivery_duration_days >  30.34
|   |   |   |--- seller_dispatch_duration_hours <= 669.49
|   |   |   |   |--- truncated branch of depth 3
|   |   |   |--- seller_dispatch_duration_hours >  669.49
|   |   |   |   |--- class: 1
```

---

## 8. Limitations & Recommended Mitigations
1. **Courier Scan Drift Artifacts**: As identified in Phase 9, 23 orders have carrier scan dates recorded after doorstep arrival due to manual courier batch synchronization. Handled through input bounds clipping.
2. **State-Level Granularity**: Distance calculation is based on postal district centroids. Sub-district routing density is not captured.
3. **Cold-Start Merchants**: New sellers have `seller_prior_late_rate = 0.0`. Imputed with system prior to prevent cold-start bias.