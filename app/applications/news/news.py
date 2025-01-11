from pathlib import Path

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
            keywords TEXT[],
            mentioned_people TEXT[],
            mentioned_organizations TEXT[],
            mentioned_legislation TEXT[],
            mentioned_locations TEXT[],
            sentiment_tone TEXT,
            extracted_quotes TEXT[]
        )
        """

    def process(self, data: dict):
        input_text = data.get("text", "")
        url = data.get("url", "")
        metadata = self.parser(article_text=input_text)
        row = {
            "hash": self.db_manager.compute_hash(input_text),
            "text": input_text,
            "url": url,
            "timestamp": self.db_manager.utcnow(),
        }
        row.update(metadata.toDict())

        summary = f"Summarized: {input_text[:50]}..."
        self.db_manager.insert(self.table_name, row)
        return {"summary": summary}
