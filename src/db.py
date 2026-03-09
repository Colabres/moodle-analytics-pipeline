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


def insert_ingest_file(cur, file_id: int, filename: str) -> int:
    cur.execute(
        """
        INSERT INTO moodle.ingest_file (file_id, filename)
        VALUES (%s, %s)
        RETURNING file_id
        """,
        (file_id, filename),
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

def fetch_events_by_file(cur, file_id: int, limit: int = 200):
    """
    Fetch a preview of events belonging to one uploaded file.
    Returns list of tuples in the same order as the SELECT.
    """
    cur.execute(
        """
        SELECT id, ts, user_id, context, component, event_name, description, origin
        FROM moodle.event
        WHERE file_id = %s
        ORDER BY id ASC
        LIMIT %s
        """,
        (file_id, limit),
    )
    return cur.fetchall()

def ensure_users(cur, user_ids: list[int]) -> int:
    """
    Inserts user_ids into moodle.user_dim if missing.
    Returns how many rows were attempted (not exactly inserted).
    """
    rows = [(int(uid),) for uid in user_ids]
    cur.executemany(
        """
        INSERT INTO moodle.user_dim (user_id)
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
        """,
        rows,
    )
    return len(rows)

def set_users_active(cur, active_user_ids: list[int]) -> int:
    rows = [(int(uid),) for uid in active_user_ids]
    cur.executemany(
        """
        UPDATE moodle.user_dim
        SET is_active = TRUE
        WHERE user_id = %s
        """,
        rows,
    )
    return len(rows)    

def set_users_admin(cur, admin_user_ids: list[int]) -> int:
    rows = [(int(uid),) for uid in admin_user_ids]
    cur.executemany(
        """
        UPDATE moodle.user_dim
        SET is_admin = TRUE
        WHERE user_id = %s
        """,
        rows,
    )
    return len(rows)

def fetch_admin_user_ids(cur) -> set[int]:
    cur.execute(
        """
        SELECT user_id
        FROM moodle.user_dim
        WHERE is_admin = TRUE
        """
    )
    return {int(r[0]) for r in cur.fetchall() if r[0] is not None}

def fetch_all_file_ids(cur) -> set[int]:
    cur.execute(
        """
        SELECT file_id
        FROM moodle.ingest_file
        """
    )
    return {int(r[0]) for r in cur.fetchall() if r[0] is not None}

def fetch_ingest_files(cur, search: str | None = None) -> list[tuple[int, str]]:
    """
    Returns ingest files as (file_id, filename), ordered by newest id first.

    If search is provided, filters filename with ILIKE.
    """
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        cur.execute(
            """
            SELECT file_id, filename
            FROM moodle.ingest_file
            WHERE filename ILIKE %s
            ORDER BY file_id DESC
            """,
            (pattern,),
        )
    else:
        cur.execute(
            """
            SELECT file_id, filename
            FROM moodle.ingest_file
            ORDER BY file_id DESC
            """
        )

    return [
        (int(r[0]), str(r[1]))
        for r in cur.fetchall()
        if r[0] is not None and r[1] is not None
    ]