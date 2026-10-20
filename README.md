# Marketplace Profitability & Delivery Intelligence Engine

An enterprise-grade analytical and predictive intelligence system built on the Brazilian E-Commerce public dataset (Olist, ~100k historical orders from 2016 to 2018).

---

## 1. Business Objective

Modern e-commerce marketplaces face complex trade-offs between commercial growth and operational fulfillment reliability. This project answers the central business question:

> **"Which sellers, products, categories, locations, and orders create the most business value or operational risk, and which orders are likely to experience late delivery?"**

The engine provides an end-to-end analytical pipeline:
- Ingestion, relational integrity validation, and profiling across 9 source entities.
- Systematic data cleaning, Portuguese text processing, and feature engineering.
- Relational dimensional modeling (Star Schema) hosted on PostgreSQL.
- Advanced SQL analytical marts (cohorts, GMV trends, seller concentration, window functions).
- Retrospective exploratory data analysis and scenario-based contribution margin modeling.
- Machine Learning classification predicting late-delivery risk strictly prior to outcome realization.
- Interactive multi-page Power BI executive intelligence dashboards.

---

## 2. Technology Stack

- **Operating System**: Windows 11 (PowerShell)
- **Programming & Analysis**: Python 3.13 (`pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`)
- **Database & Data Modeling**: PostgreSQL 18, SQLAlchemy, `psycopg2-binary`, pgAdmin 4
- **Business Intelligence**: Power BI Desktop
- **Testing & Code Quality**: `pytest`, `ruff`
- **Environment & Version Control**: Python `venv`, Git, GitHub

---

## 3. Project Directory Architecture

```text
marketplace-profitability-intelligence/
├── data/
│   ├── raw/               <- Immutable Olist source CSVs (CC BY-NC-SA 4.0)
│   ├── processed/         <- Cleaned, transformed, feature-engineered datasets
│   ├── external/          <- Third-party reference data
│   └── README.md          <- Data storage contracts and licensing
├── src/
│   └── marketplace_intelligence/
│       └── __init__.py    <- Core modular package
├── sql/                   <- DDL, DML, dimensional models, and analytical queries
├── notebooks/             <- Exploratory Data Analysis & experiments
├── tests/                 <- Automated test suites (pytest)
├── docs/                  <- Architecture, data dictionary, metrics, and model cards
├── dashboard/             <- Power BI templates and documentation
├── .env.example           <- Template for PostgreSQL and environment configurations
├── .gitignore             <- Strict exclusion for heavy data, virtual environments, and secrets
├── requirements.txt       <- Pinned project dependencies
└── README.md              <- Master project documentation
```

---

## 4. Environment Setup & Reproduction Guide

To reproduce this environment on another machine, follow these steps:

### Step 1: Clone Repository
```powershell
git clone <repository-url>
cd marketplace-profitability-intelligence
```

### Step 2: Download Dataset
Download the Olist Brazilian E-Commerce dataset from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place the 9 CSV files into `data/raw/`.

### Step 3: Create & Activate Virtual Environment
```powershell
# Create isolated environment
python -m venv .venv

# Activate in PowerShell
.\.venv\Scripts\Activate.ps1
```

> **Note for PowerShell execution policy**: If script execution is blocked on Windows, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```

### Step 4: Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment Secrets
Copy `.env.example` to `.env` and configure your local PostgreSQL credentials:
```powershell
Copy-Item .env.example .env
```
*(Ensure `.env` is never committed to Git).*
