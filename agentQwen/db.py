import os
import sqlite3

# Lue DB‑polku ympäristömuuttujasta, oletus paikallinen polku kontissa
DB_PATH = os.environ.get("DATABASE_PATH", "/root/.ollama/ollama.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

# Esimerkki: alustustoiminto (jos tarvitset)
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # luo taulut vain jos niitä ei ole (muokkaa tarpeen mukaan)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS example (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT,
        value TEXT
    )
    """)
    conn.commit()
    conn.close()