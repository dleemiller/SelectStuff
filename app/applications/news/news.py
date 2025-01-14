from pathlib import Path
import json

import dspy

from app.applications import ApplicationStuff, stuff
from .signature import NewsAppSignature


def load_program():
    program = dspy.ChainOfThought(NewsAppSignature)
    program.load(Path(__file__).resolve().parent / "miprov2_llama32_3b.json")
    return program


@stuff("news")
class NewsApp(ApplicationStuff):
    parser = load_program()

    @property
    def schema(self) -> str:
        """
        Schema definition for the news table.
        JSON is used instead of TEXT[] for array-like fields.
        """
        return f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            hash TEXT PRIMARY KEY,
            text TEXT,
            url TEXT,
            timestamp TIMESTAMP,
            generated_title TEXT NOT NULL,
            publication_date DATE,
            primary_category TEXT NOT NULL,
            content_type TEXT NOT NULL,
            keywords JSON,
            mentioned_people JSON,
            mentioned_organizations JSON,
            mentioned_legislation JSON,
            mentioned_locations JSON,
            sentiment_tone TEXT,
            extracted_quotes JSON
        )
        """

    def process(self, data: dict):
        """
        Process the input data, parse metadata, and insert into the database.

        Args:
            data (dict): Input data containing text and optional URL.

        Returns:
            dict: A summary of the processing results.
        """
        input_text = data.get("text", "")
        url = data.get("url", "")

        # Parse metadata and convert to dictionary
        metadata = self.parser(article_text=input_text).toDict()

        # Add basic fields to the row
        row = {
            "hash": self.db_manager.compute_hash(input_text),
            "text": input_text,
            "url": url,
            "timestamp": self.db_manager.utcnow(),
        }
        row.update(metadata)

        # Fields to store as JSON
        json_fields = [
            "keywords",
            "mentioned_people",
            "mentioned_organizations",
            "mentioned_legislation",
            "mentioned_locations",
            "extracted_quotes",
        ]

        # Convert JSON fields to JSON strings
        for field in json_fields:
            if field in row:
                row[field] = json.dumps(row[field])

        # Insert into the database
        self.db_manager.insert(self.table_name, row)

        # Return a summary
        summary = f"Summarized: {input_text[:50]}..."
        return {"summary": summary}
