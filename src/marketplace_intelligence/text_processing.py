"""
Portuguese Customer Review Text Processing and Qualitative Extraction Module.

Extracts retrospective customer-experience features from unstructured Portuguese reviews:
- Text normalization (accent stripping, whitespace cleansing, lowercase).
- Quantitative text metrics (character count, word count).
- Domain-specific Portuguese operational issue indicators (delivery failure, product defects, positive feedback).
- Customer sentiment and experience categorization.
- Anti-leakage governance: documents why review features are retrospective and strictly prohibited
  from early late-delivery predictive models.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# Domain-Specific Portuguese Lexicon Patterns (Compiled for High Performance)
# ==============================================================================
# Delivery issues: delay, late arrival, non-receipt, deadline exceeded
DELIVERY_ISSUE_REGEX = re.compile(
    r"\b("
    r"atras(o|ou|ada|ado|ar|am)|"
    r"demor(a|ou|ado|ar|am)|"
    r"nao (recebi|chegou|entreg(ue|ou|aram))|"
    r"nunca chegou|"
    r"ainda nao|"
    r"fora do prazo|"
    r"passou do prazo|"
    r"esperando a entrega|"
    r"extraviad(o|a)|"
    r"nao foi entregue"
    r")\b",
    re.IGNORECASE,
)

# Product quality issues: broken, defective, incorrect item, missing parts
PRODUCT_ISSUE_REGEX = re.compile(
    r"\b("
    r"defeit(o|uoso|uosa)|"
    r"quebrad(o|a)|"
    r"danificad(o|a)|"
    r"estragad(o|a)|"
    r"errad(o|a)|"
    r"produto errado|"
    r"veio faltando|"
    r"faltou|"
    r"faltando|"
    r"nao funciona|"
    r"pessim(o|a)|"
    r"ruim|"
    r"fals(o|a)|"
    r"diferente do anunciado|"
    r"qualidade ruim|"
    r"baixa qualidade"
    r")\b",
    re.IGNORECASE,
)

# Positive experience: recommendations, fast shipping, praise
POSITIVE_REGEX = re.compile(
    r"\b("
    r"recomendo|"
    r"super recomendo|"
    r"otim(o|a)|"
    r"excelente|"
    r"perfeit(o|a)|"
    r"parabens|"
    r"muito bo(m|a)|"
    r"adorei|"
    r"gostei muito|"
    r"antes do prazo|"
    r"chegou rapido|"
    r"rapida|"
    r"pontual"
    r")\b",
    re.IGNORECASE,
)


def normalize_portuguese_text(text: Any) -> str:
    """Normalizes Portuguese text by stripping diacritics, extra whitespace, and lowercasing."""
    if not isinstance(text, str) or not text.strip():
        return ""

    # Replace newlines, carriage returns, and tabs with single space
    cleaned = re.sub(r"[\r\n\t]+", " ", text).strip().lower()

    # Strip Portuguese accents (e.g. 'não' -> 'nao', 'ótimo' -> 'otimo', 'açúcar' -> 'acucar')
    # Using Unicode Normalization Form KD (NFKD) decomposes characters into base + combining mark
    normalized = unicodedata.normalize("NFKD", cleaned)
    ascii_text = normalized.encode("ASCII", "ignore").decode("utf-8")

    # Clean multiple spaces and non-standard punctuation
    return re.sub(r"\s+", " ", ascii_text).strip()


class ReviewTextProcessor:
    """Processes customer review text and creates retrospective qualitative features."""

    def __init__(self, processed_dir: Path | str = "data/processed", docs_dir: Path | str = "docs"):
        self.processed_dir = Path(processed_dir)
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def process(self) -> pd.DataFrame:
        """Loads cleaned reviews, extracts text features, and exports enriched datasets."""
        input_file = self.processed_dir / "order_reviews_cleaned.parquet"
        logger.info(f"Loading cleaned reviews from {input_file}...")
        df = pd.read_parquet(input_file)
        initial_len = len(df)

        logger.info("Computing text length and word count metrics...")
        # Quantitative metrics on original message
        df["review_char_length"] = df["review_comment_message"].fillna("").str.len()
        df["review_word_count"] = (
            df["review_comment_message"].fillna("").apply(lambda s: len(s.split()) if s.strip() else 0)
        )

        logger.info("Normalizing Portuguese text for operational keyword extraction...")
        # Combine title and message for comprehensive keyword scanning
        combined_text = (df["review_comment_title"].fillna("") + " " + df["review_comment_message"].fillna("")).str.strip()
        df["normalized_text"] = combined_text.apply(normalize_portuguese_text)

        logger.info("Tagging domain operational issue indicators...")
        # Keyword detection on normalized text
        df["is_delivery_issue"] = df["normalized_text"].apply(lambda t: bool(DELIVERY_ISSUE_REGEX.search(t)) if t else False)
        df["is_product_quality_issue"] = df["normalized_text"].apply(lambda t: bool(PRODUCT_ISSUE_REGEX.search(t)) if t else False)
        df["is_positive_experience"] = df["normalized_text"].apply(lambda t: bool(POSITIVE_REGEX.search(t)) if t else False)

        # CSAT categorization based on review_score (1-5)
        conditions = [
            df["review_score"].isin([1, 2]),
            df["review_score"] == 3,
            df["review_score"].isin([4, 5]),
        ]
        choices = ["negative", "neutral", "positive"]
        df["csat_category"] = np.select(conditions, choices, default="unknown")

        # Operational complaint classification
        def classify_complaint(row: pd.Series) -> str:
            if row["csat_category"] == "positive":
                return "satisfied_customer"
            if row["csat_category"] == "neutral" and not row["has_comment_message"]:
                return "neutral_uncommented"
            if row["is_delivery_issue"] and row["is_product_quality_issue"]:
                return "delivery_and_product_complaint"
            if row["is_delivery_issue"]:
                return "delivery_delay_complaint"
            if row["is_product_quality_issue"]:
                return "product_quality_complaint"
            if row["csat_category"] == "negative":
                return "unspecified_dissatisfaction"
            return "neutral_general"

        df["operational_feedback_tag"] = df.apply(classify_complaint, axis=1)

        # Verification of record retention
        assert len(df) == initial_len, "Record count changed during text processing!"

        # Export enriched dataset
        enriched_parquet = self.processed_dir / "order_reviews_enriched.parquet"
        enriched_csv = self.processed_dir / "order_reviews_enriched.csv"
        df.to_parquet(enriched_parquet, index=False)
        df.to_csv(enriched_csv, index=False)
        logger.info(f"Enriched reviews exported to {enriched_parquet.name} ({len(df):,} rows)")

        # Generate documentation
        self._generate_methodology_report(df)
        return df

    def _generate_methodology_report(self, df: pd.DataFrame) -> Path:
        """Documents text processing methodology, dictionary coverage, and anti-leakage rules."""
        report_path = self.docs_dir / "text_processing_methodology.md"
        total_reviews = len(df)
        with_comments = int(df["has_comment_message"].sum())
        delivery_issues = int(df["is_delivery_issue"].sum())
        product_issues = int(df["is_product_quality_issue"].sum())
        positives = int(df["is_positive_experience"].sum())

        feedback_counts = df["operational_feedback_tag"].value_counts().to_dict()

        lines: list[str] = [
            "# Unstructured Text Processing & Customer Sentiment Methodology",
            "",
            "**Module**: `src/marketplace_intelligence/text_processing.py`  ",
            "**Language**: Brazilian Portuguese (PT-BR)  ",
            "**Source Table**: `olist_order_reviews_dataset.csv`  ",
            "",
            "---",
            "",
            "## 1. Executive Summary & Extraction Metrics",
            "",
            f"- **Total Review Responses**: {total_reviews:,}",
            f"- **Reviews with Written Commentary**: {with_comments:,} ({with_comments / total_reviews:.1%})",
            f"- **Delivery Delay Complaints Detected**: {delivery_issues:,} ({delivery_issues / total_reviews:.1%})",
            f"- **Product Quality / Defect Complaints Detected**: {product_issues:,} ({product_issues / total_reviews:.1%})",
            f"- **Positive Recommendations Detected**: {positives:,} ({positives / total_reviews:.1%})",
            "",
            "### Operational Feedback Categorization Breakdown",
            "",
            "| Operational Feedback Category | Count | % of All Reviews | Description |",
            "|---|---|---|---|",
        ]

        for tag, count in feedback_counts.items():
            pct = (count / total_reviews) * 100
            lines.append(f"| `{tag}` | {count:,} | {pct:.2f}% | Derived from star score and domain keywords |")

        lines.extend([
            "",
            "---",
            "",
            "## 2. Text Normalization Pipeline",
            "",
            "Customer commentary in Portuguese presents three distinct normalization challenges:",
            "1. **Diacritics & Accents**: Words like `não`, `atrasou`, `óptimo`, and `parabéns` contain accents (`ã`, `ó`, `á`, `é`). Because users often type casually without accents (`nao`, `otimo`), we use Unicode NFKD normalization to strip combining marks while preserving the original raw text in separate columns.",
            "2. **Whitespace and Newlines**: Reviews often contain multi-line linebreaks (`\\r\\n`), tabs, and erratic spaces that disrupt string parsers. These are normalized into clean single spaces.",
            "3. **Case Folding**: All text is converted to lowercase for keyword matching.",
            "",
            "---",
            "",
            "## 3. Portuguese Domain-Specific Keyword Lexicon",
            "",
            "Rather than applying generic English sentiment dictionaries (e.g. VADER or TextBlob) which fail on Portuguese syntax, we implemented a targeted, domain-specific rule-based regex lexicon:",
            "",
            "- **Delivery Delay Indicators (`is_delivery_issue`)**:",
            "  - `atraso`, `atrasou`, `atrasada`, `demorou`, `demora`, `nao recebi`, `nao chegou`, `fora do prazo`, `passou do prazo`, `esperando a entrega`, `extraviado`.",
            "- **Product Defect Indicators (`is_product_quality_issue`)**:",
            "  - `defeito`, `quebrado`, `danificado`, `estragado`, `errado`, `produto errado`, `veio faltando`, `faltou`, `nao funciona`, `pessima qualidade`, `ruim`, `falso`.",
            "- **Positive Recommendation Indicators (`is_positive_experience`)**:",
            "  - `recomendo`, `super recomendo`, `otimo`, `excelente`, `perfeito`, `parabens`, `muito bom`, `adorei`, `antes do prazo`, `chegou rapido`.",
            "",
            "---",
            "",
            "## 4. CRITICAL GOVERNANCE: Data Leakage Prevention in Machine Learning",
            "",
            "> [!CAUTION]",
            "> **ANTI-LEAKAGE RULE**: Review features are strictly **POST-OUTCOME RETROSPECTIVE SIGNALS**.",
            "",
            "In Phase 12, our objective is to predict whether an order will be delivered late *at the moment of checkout or carrier dispatch*.",
            "- The customer review survey is generated and answered **days or weeks after** the order has either arrived or failed to arrive.",
            "- If any feature derived from reviews (`review_score`, `review_char_length`, `is_delivery_issue`, `has_comment_message`) is fed into the predictive model, it constitutes **target leakage** (using the future to predict the future).",
            "- Therefore, review features are strictly reserved for:",
            "  1. **Retrospective seller performance scoring**.",
            "  2. **Exploratory Data Analysis (EDA) investigating the relationship between delays and 1-star reviews**.",
            "  3. **Executive BI Dashboards (Power BI CSAT analysis)**.",
        ])

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Text processing methodology report written to {report_path.resolve()}")
        return report_path


if __name__ == "__main__":
    processor = ReviewTextProcessor(processed_dir="data/processed", docs_dir="docs")
    processor.process()
