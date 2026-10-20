-- ==============================================================================
-- 01_create_schemas.sql
-- Database: marketplace_analytics
-- Purpose: Establish Medallion / Multi-Layer analytical schema architecture
-- ==============================================================================

-- 1. STAGING LAYER (stg): Raw-shaped, typed mirrors of processed source tables
CREATE SCHEMA IF NOT EXISTS stg;

-- 2. CORE ANALYTICAL LAYER (core): Kimball Dimensional Model (Star Schema: Dimensions & Facts)
CREATE SCHEMA IF NOT EXISTS core;

-- 3. MART LAYER (mart): Aggregated executive reporting views and BI performance marts
CREATE SCHEMA IF NOT EXISTS mart;

COMMENT ON SCHEMA stg IS 'Staging layer: source-shaped relational tables reflecting cleaned pipeline ingestion.';
COMMENT ON SCHEMA core IS 'Core analytical layer: Kimball dimensional star schema (dim_*, fact_*).';
COMMENT ON SCHEMA mart IS 'Mart layer: high-performance business aggregation marts and BI reporting tables.';
