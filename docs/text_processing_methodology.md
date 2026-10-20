# Unstructured Text Processing & Customer Sentiment Methodology

**Module**: `src/marketplace_intelligence/text_processing.py`  
**Language**: Brazilian Portuguese (PT-BR)  
**Source Table**: `olist_order_reviews_dataset.csv`  

---

## 1. Executive Summary & Extraction Metrics

- **Total Review Responses**: 99,224
- **Reviews with Written Commentary**: 40,977 (41.3%)
- **Delivery Delay Complaints Detected**: 5,245 (5.3%)
- **Product Quality / Defect Complaints Detected**: 2,850 (2.9%)
- **Positive Recommendations Detected**: 18,942 (19.1%)

### Operational Feedback Categorization Breakdown

| Operational Feedback Category | Count | % of All Reviews | Description |
|---|---|---|---|
| `satisfied_customer` | 76,470 | 77.07% | Derived from star score and domain keywords |
| `unspecified_dissatisfaction` | 8,978 | 9.05% | Derived from star score and domain keywords |
| `neutral_uncommented` | 4,622 | 4.66% | Derived from star score and domain keywords |
| `delivery_delay_complaint` | 4,096 | 4.13% | Derived from star score and domain keywords |
| `neutral_general` | 2,583 | 2.60% | Derived from star score and domain keywords |
| `product_quality_complaint` | 2,178 | 2.20% | Derived from star score and domain keywords |
| `delivery_and_product_complaint` | 297 | 0.30% | Derived from star score and domain keywords |

---

## 2. Text Normalization Pipeline

Customer commentary in Portuguese presents three distinct normalization challenges:
1. **Diacritics & Accents**: Words like `não`, `atrasou`, `óptimo`, and `parabéns` contain accents (`ã`, `ó`, `á`, `é`). Because users often type casually without accents (`nao`, `otimo`), we use Unicode NFKD normalization to strip combining marks while preserving the original raw text in separate columns.
2. **Whitespace and Newlines**: Reviews often contain multi-line linebreaks (`\r\n`), tabs, and erratic spaces that disrupt string parsers. These are normalized into clean single spaces.
3. **Case Folding**: All text is converted to lowercase for keyword matching.

---

## 3. Portuguese Domain-Specific Keyword Lexicon

Rather than applying generic English sentiment dictionaries (e.g. VADER or TextBlob) which fail on Portuguese syntax, we implemented a targeted, domain-specific rule-based regex lexicon:

- **Delivery Delay Indicators (`is_delivery_issue`)**:
  - `atraso`, `atrasou`, `atrasada`, `demorou`, `demora`, `nao recebi`, `nao chegou`, `fora do prazo`, `passou do prazo`, `esperando a entrega`, `extraviado`.
- **Product Defect Indicators (`is_product_quality_issue`)**:
  - `defeito`, `quebrado`, `danificado`, `estragado`, `errado`, `produto errado`, `veio faltando`, `faltou`, `nao funciona`, `pessima qualidade`, `ruim`, `falso`.
- **Positive Recommendation Indicators (`is_positive_experience`)**:
  - `recomendo`, `super recomendo`, `otimo`, `excelente`, `perfeito`, `parabens`, `muito bom`, `adorei`, `antes do prazo`, `chegou rapido`.

---

## 4. CRITICAL GOVERNANCE: Data Leakage Prevention in Machine Learning

> [!CAUTION]
> **ANTI-LEAKAGE RULE**: Review features are strictly **POST-OUTCOME RETROSPECTIVE SIGNALS**.

In Phase 12, our objective is to predict whether an order will be delivered late *at the moment of checkout or carrier dispatch*.
- The customer review survey is generated and answered **days or weeks after** the order has either arrived or failed to arrive.
- If any feature derived from reviews (`review_score`, `review_char_length`, `is_delivery_issue`, `has_comment_message`) is fed into the predictive model, it constitutes **target leakage** (using the future to predict the future).
- Therefore, review features are strictly reserved for:
  1. **Retrospective seller performance scoring**.
  2. **Exploratory Data Analysis (EDA) investigating the relationship between delays and 1-star reviews**.
  3. **Executive BI Dashboards (Power BI CSAT analysis)**.