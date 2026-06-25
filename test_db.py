"""Manual smoke test for the MySQL connection.

Run with `python test_db.py` after configuring .env and starting MySQL.
This is intentionally not part of the automated pytest suite, since the app
runs fine without a database.
"""

from db import get_connection

if __name__ == "__main__":
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION() AS version")
        print("Connected! MySQL version:", cur.fetchone()["version"])
    conn.close()
