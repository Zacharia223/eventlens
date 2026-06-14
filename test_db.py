from db import get_connection

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT VERSION() AS version")
    print("Connected! MySQL version:", cur.fetchone()["version"])
conn.close()