from typing import Literal, Optional, List
from datetime import date

import dspy


class NewsAppSignature(dspy.Signature):

    # INPUT FIELD
    article_text: str = dspy.InputField(desc="Full article text for analysis.")

    # BASIC IDENTIFIERS
    generated_title: str = dspy.OutputField(
        desc="Article title or a generated one if not found."
    )

    snippet: str = dspy.OutputField(desc="Short high level overview")

    publication_date: Optional[date] = dspy.OutputField(desc="Publication date.")

    # CATEGORIZATION
    primary_category: Literal[
        "world",
        "entertainment",
        "science",
        "health",
        "business",
        "sports",
        "politics",
        "technology",
        "legal",
        "community",
        "public_safety",
    ] = dspy.OutputField(desc="Primary subject category of the article.")

    content_type: Literal[
        "editorial",
        "opinion",
        "analysis",
        "reporting",
        "interview",
        "investigative",
        "press_release",
        "blog_post",
    ] = dspy.OutputField(desc="Type of article content.")

    keywords: List[str] = dspy.OutputField(
        desc="Keywords or phrases for classification and retrieval."
    )

    # ENTITY MENTIONS
    mentioned_people: Optional[List[str]] = dspy.OutputField(
        desc="Names of key individuals mentioned. Use names of famous individuals in their most recognized forms."
    )

    mentioned_organizations: Optional[List[str]] = dspy.OutputField(
        desc="Names of key organizations mentioned."
    )

    mentioned_legislation: Optional[List[str]] = dspy.OutputField(
        desc="Laws, bills, or policies mentioned."
    )

    mentioned_locations: Optional[List[str]] = dspy.OutputField(
        desc="Geographic locations named in the article."
    )

    # SENTIMENT ANALYSIS
    sentiment_tone: Optional[Literal["positive", "neutral", "negative"]] = (
        dspy.OutputField(desc="Overall sentiment expressed in the article.")
    )

    # ADDITIONAL CONTEXTUAL INFORMATION
    extracted_quotes: Optional[List[str]] = dspy.OutputField(
        desc="Notable direct quotes from the article."
    )


NewsAppSignature.__doc__ = """
You are provided with the text of a news article.
Help provide the requested information for cataloging and retrieval.
Ensure information is focused on quality retrieval results -- accuracy, specificity, disambiguation.
Correct simple grammar or formatting mistakes.
"""
