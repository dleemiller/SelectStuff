from app.applications import ApplicationStuff, stuff


@stuff("news")
class NewsApp(ApplicationStuff):
    @property
    def schema(self) -> str:
        return f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            hash TEXT PRIMARY KEY,
            text TEXT,
            url TEXT,
            timestamp TIMESTAMP
        )
        """

    def process(self, data: dict):
        input_text = data.get("text", "")
        url = data.get("url", "")

        summary = f"Summarized: {input_text[:50]}..."
        print(summary)
        self.db_manager.insert(
            self.table_name,
            {
                "hash": self.db_manager.create_hash(text),
                "text": input_text,
                "url": url,
                "timestamp": self.db_manager.utcnow(),
            },
        )
        return {"summary": summary}
