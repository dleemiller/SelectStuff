from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlmodel import Session, select, Field

import dspy

from app.applications import ApplicationStuff, stuff
from .signature import NewsAppSignature
from app.applications.sql_converter import SignatureToSQLModel
from app.database import SQLiteManager


# Load DSPy Program
def load_program():
    program = dspy.ChainOfThought(NewsAppSignature)
    program.load(Path(__file__).resolve().parent / "miprov2_llama32_3b.json")
    return program


@stuff("news")
class NewsApp(ApplicationStuff):
    parser = load_program()
    base_fields = {
        "id": (Optional[int], Field(default=None, primary_key=True)),
        # "text": (str, Field()),
        "url": (Optional[str], Field(default=None)),
        "timestamp": (datetime, Field()),
    }

    def __init__(self, db_manager: "SQLiteManager", table_name: str):
        self.db = db_manager

        self._NewsModel = SignatureToSQLModel.to_sqlmodel(
            NewsAppSignature, table_name=table_name, base_fields=self.base_fields
        )

        self.db.create_all(self._NewsModel)

        ## Create FTS index for text search
        # self.db.create_fts_index(
        #    "news_fts",
        #    ["text", "generated_title"],  # columns to index
        #    content_table="news",  # external content mode
        #    overwrite=True  # recreate if exists
        # )

    def process(self, data: dict):
        """
        Process the input data, parse metadata, and insert into the database.
        """
        input_text = data.get("text", "")
        url = data.get("url", "")

        # Parse metadata and convert to dictionary
        metadata = self.parser(article_text=input_text).toDict()
        metadata["article_text"] = input_text

        # Create the News object
        news_entry = self._NewsModel(
            text=input_text, url=url, timestamp=datetime.utcnow(), **metadata
        )

        # Insert into the database
        with Session(self.db.engine) as session:
            session.add(news_entry)
            session.commit()

        # Return a summary
        summary = f"Summarized: {input_text[:50]}..."
        return {"summary": summary}
