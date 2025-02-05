from datetime import datetime
from pathlib import Path
from typing import Optional

import dspy
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
from sqlmodel import Field, Session
from tenacity import retry, stop_after_attempt, wait_fixed

from ..base import ApplicationStuff, stuff
from databases.utils.sql_converter import SignatureToSQLModel
from databases.database import SQLiteManager

from .signature import NewsAppSignature

tracer = trace.get_tracer(__name__)


# Load DSPy Program
def load_program():
    program = dspy.ChainOfThought(NewsAppSignature)
    program.load(Path(__file__).resolve().parent / "states" / "miprov2_llama32_3b.json")
    return program


@tracer.start_as_current_span("news")
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

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def parser_with_retry(self, article_text: str):
        return self.parser(article_text=article_text)

    @tracer.start_as_current_span("process")
    def process(self, data: dict):
        """
        Process the input data, parse metadata, and insert into the database.
        """
        with tracer.start_as_current_span("parser"):
            input_text = data.get("text", "")
            url = data.get("url", "")
            # Attach attributes to this sub-span
            sub_span = trace.get_current_span()
            sub_span.set_attribute("input_text_length", len(input_text))
            sub_span.set_attribute("input_url", url)
            try:
                # Parse metadata and convert to dictionary
                metadata = self.parser_with_retry(article_text=input_text).toDict()
                metadata["article_text"] = input_text
            except Exception as e:
                parse_span = trace.get_current_span()
                parse_span.record_exception(e)
                parse_span.set_status(Status(StatusCode.ERROR, str(e)))
                Status(StatusCode.ERROR, "Failed to parse article text")
                raise

        with tracer.start_as_current_span("store_in_db"):
            try:
                # Create the News object
                news_entry = self._NewsModel(
                    text=input_text,
                    url=url,
                    timestamp=datetime.utcnow(),
                    **metadata,
                )
                # Insert into the database
                with Session(self.db.engine) as session:
                    session.add(news_entry)
                    session.commit()
            except Exception as e:
                db_span = trace.get_current_span()
                db_span.record_exception(e)
                db_span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

        # Return a summary
        summary = f"Summarized: {input_text[:50]}..."
        return {"summary": summary}
