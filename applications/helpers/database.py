from databases.database import SQLiteManager


def initialize_database(config) -> SQLiteManager:
    """
    Initialize and return the SQLiteManager instance.
    """
    return SQLiteManager(db_path=config.database)
