"""
Automated Validation Tests for Portuguese Text Processing & Qualitative Extraction.

Tests verify:
1. Normalization function correctly strips diacritics and cleans whitespace.
2. Regex patterns accurately detect delivery delays, product defects, and praise.
3. Enriched dataset preserves record count, original raw text, and adds valid features.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.marketplace_intelligence.text_processing import (
    DELIVERY_ISSUE_REGEX,
    POSITIVE_REGEX,
    PRODUCT_ISSUE_REGEX,
    normalize_portuguese_text,
)

PROCESSED_DIR = Path("data/processed")

pytestmark = pytest.mark.skipif(
    not (PROCESSED_DIR / "order_reviews_enriched.parquet").exists(),
    reason="order_reviews_enriched.parquet not present in environment",
)


def test_portuguese_normalization():
    """Confirms Portuguese diacritics, accents, and whitespace are normalized correctly."""
    sample_text = "  Não recebi o produto!   Muito ÓTIMO e PARABÉNS... \n Atrasou!  "
    normalized = normalize_portuguese_text(sample_text)

    # Must be lowercased, stripped of accents (nao, otimo, parabens), and clean spaces
    assert "nao" in normalized
    assert "otimo" in normalized
    assert "parabens" in normalized
    assert "atrasou" in normalized
    assert "\n" not in normalized
    assert "  " not in normalized


def test_keyword_pattern_matching():
    """Confirms regex detectors correctly identify operational themes in Portuguese."""
    delivery_text = "o produto esta fora do prazo e ainda nao recebi minha compra"
    defect_text = "veio com defeito e a peca esta quebrada produto pessimo"
    praise_text = "chegou antes do prazo super recomendo excelente loja"

    # Test delivery delay pattern
    assert DELIVERY_ISSUE_REGEX.search(delivery_text) is not None
    assert DELIVERY_ISSUE_REGEX.search(praise_text) is None

    # Test product defect pattern
    assert PRODUCT_ISSUE_REGEX.search(defect_text) is not None
    assert PRODUCT_ISSUE_REGEX.search(praise_text) is None

    # Test praise pattern
    assert POSITIVE_REGEX.search(praise_text) is not None
    assert POSITIVE_REGEX.search(delivery_text) is None


def test_enriched_reviews_dataset_integrity():
    """Confirms enriched dataset maintains row count, preserves raw text, and generates all features."""
    enriched_path = PROCESSED_DIR / "order_reviews_enriched.parquet"
    assert enriched_path.exists(), "order_reviews_enriched.parquet was not created."

    df = pd.read_parquet(enriched_path)
    assert len(df) == 99224, "Enriched reviews must match original 99,224 row count."

    # Verify original raw text is preserved
    assert "review_comment_title" in df.columns
    assert "review_comment_message" in df.columns

    # Verify qualitative derived features
    expected_cols = [
        "review_char_length",
        "review_word_count",
        "is_delivery_issue",
        "is_product_quality_issue",
        "is_positive_experience",
        "csat_category",
        "operational_feedback_tag",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing derived column '{col}' in enriched reviews."

    # Non-negative length and word count assertions
    assert (df["review_char_length"] >= 0).all()
    assert (df["review_word_count"] >= 0).all()

    # Categorical domain validations
    assert set(df["csat_category"].unique()).issubset(
        {"negative", "neutral", "positive"}
    )
