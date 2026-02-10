def _ensure_database_initialized(db_path: str) -> None:
    """
    Ensure SQLite database exists and has correct schema.

    Args:
        db_path: Path to SQLite database file
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if database exists and has tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]

        if not table_names:
            # Database is empty, create schema
            logger.info(f"Creating database schema at {db_path}")
            from htmlgraph.db.schema import HtmlGraphDB

            db = HtmlGraphDB(db_path)
            db.connect()
            db.create_tables()
            db.disconnect()
            logger.info("Database schema created successfully")
        else:
            logger.debug(f"Database already initialized with tables: {table_names}")

        conn.close()

    except sqlite3.Error as e:
        logger.warning(f"Database check warning: {e}")
        # Try to create anyway
        try:
            from htmlgraph.db.schema import HtmlGraphDB

            db = HtmlGraphDB(db_path)
            db.connect()
            db.create_tables()
            db.disconnect()
        except Exception as create_error:
            logger.error(f"Failed to create database: {create_error}")
            raise
