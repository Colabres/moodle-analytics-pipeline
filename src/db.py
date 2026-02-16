import os
import psycopg

def get_database_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set (check .env and docker-compose).")
    return db_url

def connect():
    # psycopg v3 connection
    return psycopg.connect(get_database_url())


def insert_ingest_file(cur, filename: str) -> int:
    cur.execute(
        """
        INSERT INTO moodle.ingest_file (filename)
        VALUES (%s)
        RETURNING file_id
        """,
        (filename,),
    )
    return cur.fetchone()[0]

def insert_events(cur, rows):
    """
    rows: iterable of tuples:
      (file_id, ts, user_id, context, component, event_name, description, origin)
    """
    cur.executemany(
        """
        INSERT INTO moodle.event
          (file_id, ts, user_id, context, component, event_name, description, origin)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )
