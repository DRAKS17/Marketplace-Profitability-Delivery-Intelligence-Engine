# Entity-Relationship (ER) Architecture Diagram

This diagram documents the relational architecture, cardinalities, primary keys, and foreign keys of the 9 Olist source entities, verified via empirical data testing.

---

## 1. Relational ER Diagram (Mermaid)

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : "places (1 : 1 token)"
    ORDERS ||--o{ ORDER_ITEMS : "contains (1 : N)"
    ORDERS ||--o{ ORDER_PAYMENTS : "paid via (1 : N)"
    ORDERS ||--o{ ORDER_REVIEWS : "reviewed by (1 : N)"
    PRODUCTS ||--o{ ORDER_ITEMS : "ordered in (1 : N)"
    SELLERS ||--o{ ORDER_ITEMS : "fulfilled by (1 : N)"
    PRODUCTS }o--o| CATEGORY_TRANSLATIONS : "translated by (N : 0..1)"
    GEOLOCATION }o--o{ CUSTOMERS : "spatially maps (M : N prefix)"
    GEOLOCATION }o--o{ SELLERS : "spatially maps (M : N prefix)"

    CUSTOMERS {
        string customer_id PK "Order-level customer proxy token (1:1 with orders)"
        string customer_unique_id "Real human customer identifier (96,096 unique individuals)"
        int customer_zip_code_prefix FK "5-digit Brazilian postal code prefix"
        string customer_city "Customer residential city"
        string customer_state "Customer Brazilian state (UF, e.g., SP, RJ)"
    }

    ORDERS {
        string order_id PK "Unique marketplace order identifier (99,441 orders)"
        string customer_id FK "Foreign key to CUSTOMERS (1:1 relationship)"
        string order_status "Lifecycle status (delivered, shipped, canceled, invoiced, etc.)"
        timestamp order_purchase_timestamp "Moment the order was placed"
        timestamp order_approved_at "Moment payment approval was confirmed"
        timestamp order_delivered_carrier_date "Carrier handoff / dispatch timestamp"
        timestamp order_delivered_customer_date "Actual delivery to customer (NULL if in-transit/canceled)"
        timestamp order_estimated_delivery_date "Promised delivery estimate communicated at checkout"
    }

    ORDER_ITEMS {
        string order_id PK,FK "Order identifier"
        int order_item_id PK "Sequential line-item index (1, 2, ... N per order)"
        string product_id FK "Product identifier"
        string seller_id FK "Seller identifier fulfilling this item"
        timestamp shipping_limit_date "Seller dispatch deadline before penalty"
        decimal price "Item sales price in BRL (excluding freight)"
        decimal freight_value "Item shipping cost in BRL"
    }

    ORDER_PAYMENTS {
        string order_id PK,FK "Order identifier"
        int payment_sequential PK "Payment sequence number (1, 2, ... N)"
        string payment_type "Payment tender (credit_card, boleto, voucher, debit_card)"
        int payment_installments "Selected installment count (1-24)"
        decimal payment_value "Monetary amount paid on this transaction line"
    }

    ORDER_REVIEWS {
        string review_id PK "Review survey identifier"
        string order_id PK,FK "Order identifier surveyed"
        int review_score "Customer satisfaction rating (1 to 5 stars)"
        string review_comment_title "Optional survey comment heading"
        string review_comment_message "Customer textual feedback in Portuguese"
        timestamp review_creation_date "Moment review invitation was generated"
        timestamp review_answer_timestamp "Moment customer submitted feedback"
    }

    PRODUCTS {
        string product_id PK "Unique product SKU identifier (32,951 products)"
        string product_category_name FK "Category name in Portuguese (73 categories)"
        int product_name_lenght "Character count of product title"
        int product_description_lenght "Character count of product description"
        int product_photos_qty "Number of product photos in listing"
        decimal product_weight_g "Product weight in grams"
        decimal product_length_cm "Package length in cm"
        decimal product_height_cm "Package height in cm"
        decimal product_width_cm "Package width in cm"
    }

    SELLERS {
        string seller_id PK "Unique merchant / seller identifier (3,095 sellers)"
        int seller_zip_code_prefix FK "5-digit seller postal code prefix"
        string seller_city "Seller business municipality"
        string seller_state "Seller Brazilian state (UF)"
    }

    CATEGORY_TRANSLATIONS {
        string product_category_name PK "Category name in Portuguese"
        string product_category_name_english "Standardized English translation"
    }

    GEOLOCATION {
        int geolocation_zip_code_prefix "5-digit postal code prefix (non-unique)"
        decimal geolocation_lat "Latitude coordinate"
        decimal geolocation_lng "Longitude coordinate"
        string geolocation_city "Postal municipality"
        string geolocation_state "Postal state (UF)"
    }
```

---

## 2. Cardinality Summary Table

| Relationship | Cardinality | Key / Join Condition | Enforced In Integrity Audit |
|---|---|---|---|
| `CUSTOMERS` ➔ `ORDERS` | **1 : 1** | `customer_id` | ✅ 0 orphans; exactly 1 order per `customer_id`. |
| `UNIQUE_PERSON` ➔ `CUSTOMERS` | **1 : N** | `customer_unique_id` | ✅ 96,096 individuals generate 99,441 customer order tokens. |
| `ORDERS` ➔ `ORDER_ITEMS` | **1 : N** | `order_id` | ✅ 0 orphans; max 21 items in a single order; 775 canceled orders have 0 items. |
| `PRODUCTS` ➔ `ORDER_ITEMS` | **1 : N** | `product_id` | ✅ 0 orphans; all 32,951 ordered products exist in catalog. |
| `SELLERS` ➔ `ORDER_ITEMS` | **1 : N** | `seller_id` | ✅ 0 orphans; all 3,095 sellers exist in merchant registry. |
| `ORDERS` ➔ `ORDER_PAYMENTS` | **1 : N** | `order_id` | ✅ 0 orphans; max 29 payment splits in a single order; 1 order has 0 payments. |
| `ORDERS` ➔ `ORDER_REVIEWS` | **1 : N (Composite PK)** | `order_id` | ✅ 0 orphans; 98,410 unique review IDs; 814 shared across multi-order surveys. |
| `PRODUCTS` ➔ `CATEGORY_TRANSLATIONS`| **N : 0..1** | `product_category_name` | ⚠️ 71 categories mapped; 2 categories (`portateis_cozinha_e_preparadores_de_alimentos`, `pc_gamer`) missing translation. |
| `CUSTOMERS / SELLERS` ➔ `GEOLOCATION` | **N : M** | `zip_code_prefix` | ⚠️ Geolocation contains multiple coordinates per prefix; 157 customer zip prefixes missing in geo table. |
