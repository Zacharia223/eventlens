"""MySQL connection helpers for EventLens.

The database is *optional*. If MySQL is unreachable, the app still runs — the
storage layer (see ``storage.py``) falls back to an in-memory store. These
helpers therefore never hide connection errors; callers decide how to react.
"""

import os

import pymysql
from dotenv import load_dotenv

load_dotenv()  # read values from .env


def get_connection(use_database: bool = True):
    """Open a new PyMySQL connection. Raises if the server is unreachable."""
    kwargs = dict(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=3,
    )
    if use_database:
        kwargs["database"] = os.getenv("DB_NAME", "eventlens")
    return pymysql.connect(**kwargs)


def init_db() -> None:
    """Create the database and ``reports`` table if they do not yet exist.

    Raises the underlying pymysql error if the server cannot be reached, so the
    caller can decide whether to continue without persistence.
    """
    db_name = os.getenv("DB_NAME", "eventlens")

    # Connect without selecting a database so we can create it if needed.
    conn = get_connection(use_database=False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(f"USE `{db_name}`")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id           INT AUTO_INCREMENT PRIMARY KEY,
                    filename     VARCHAR(255) NOT NULL,
                    uploaded_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    row_count    INT NOT NULL,
                    column_count INT NOT NULL,
                    report_json  LONGTEXT NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()
