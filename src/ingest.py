from typing import Tuple, Optional, Mapping, Any
import polars as pl
import streamlit as st

from src.parse import parse_aika_pl, extract_user_id_pl
from src.event_buckets import EVENT_BUCKETS
from src.db import (
    connect,
    insert_ingest_file,
    insert_events,
    ensure_users,
    fetch_admin_user_ids,
    set_users_active,
    set_users_admin,
    fetch_all_file_ids,
    fetch_ingest_files,
    
)

def delete_ingest_files(cur, file_ids: list[int]) -> None:
    cur.execute(
        """
        DELETE FROM moodle.event
        WHERE file_id = ANY(%s);
        """,
        (file_ids,)
    )

    cur.execute(
        """
        DELETE FROM moodle.ingest_file
        WHERE file_id = ANY(%s);
        """,
        (file_ids,)
    )

def ensure_ingest_file_schema(cur) -> None:
    cur.execute("""
        ALTER TABLE moodle.ingest_file
        ADD COLUMN IF NOT EXISTS user_count INT;
    """)
    cur.execute("""
        ALTER TABLE moodle.ingest_file
        ADD COLUMN IF NOT EXISTS active_user_count INT;
    """)

def find_user_ids(df: pl.DataFrame, event_names: list[str]) -> list[int]:
    """
    Return unique user_id values for rows where 'Tapahtuman nimi' is in event_names.
    """
    if "Tapahtuman nimi" not in df.columns or "user_id" not in df.columns:
        return []

    return (
        df.filter(pl.col("Tapahtuman nimi").is_in(event_names))
          .select("user_id")
          .drop_nulls()
          .unique()
          .to_series()
          .to_list()
    )


def _get_optional_str(row: Mapping[str, Any], col: str) -> Optional[str]:
    """
    Safely return a string value from a row dict.
    Returns None if column missing, null, or empty.
    """
    if col not in row:
        return None

    value = row[col]
    if value is None:
        return None

    value = str(value).strip()
    if value == "" or value.lower() == "nan":
        return None

    return value

def get_all_file_ids() -> set[int]:
    """
    Returns all existing file_id values from moodle.ingest_file.
    These currently act as Course IDs.
    """
    with connect() as conn:
        with conn.cursor() as cur:
            existing_ids = fetch_all_file_ids(cur)

    return existing_ids

def get_ingest_files(search: str | None = None) -> list[tuple[int, str]]:
    """
    Returns ingest files as (file_id, filename).

    If search is provided, only matching filenames are returned.
    """
    with connect() as conn:
        with conn.cursor() as cur:
            return fetch_ingest_files(cur, search=search)
        
def transfer_to_db(df: pl.DataFrame,file_id: int ,filename: str) -> Tuple[int, int, int]:
    """
    Transfer dataframe rows into Postgres.

    Returns:
        (file_id, inserted_rows, skipped_rows)

    Skips:
        - invalid timestamp in 'Aika' (ts becomes null)
        - missing/empty 'Tapahtuman nimi'
        - rows with null user_id
        - rows for users marked as admin in moodle.user_dim
    """
    if "Aika" not in df.columns:
        raise ValueError("Missing required column 'Aika'.")
    if "Tapahtuman nimi" not in df.columns:
        raise ValueError("Missing required column 'Tapahtuman nimi'.")

    # 1️⃣ Parse timestamps
    df = df.with_columns(
        parse_aika_pl(pl.col("Aika").fill_null("")).alias("ts")
    )

    invalid_ts = df.filter(pl.col("ts").is_null()).height
    skipped_rows = int(invalid_ts)

    df = df.filter(pl.col("ts").is_not_null())
    if df.height == 0:
        return 0, 0, skipped_rows

    # 2️⃣ Extract numeric user_id from Kuvaus
    if "Kuvaus" in df.columns:
        df = df.with_columns(
            extract_user_id_pl(pl.col("Kuvaus")).alias("user_id")
        )
    else:
        df = df.with_columns(
            pl.lit(None).cast(pl.Int64).alias("user_id")
        )

    user_count = df.select(pl.col("user_id").n_unique()).item()

    # 2.1️⃣ Compute admin ids (from this file)
    admin_event_names = EVENT_BUCKETS.get("Admin activity", [])
    admin_ids_detected = set(find_user_ids(df, admin_event_names))

    # 2.2️⃣ Compute active ids (from this file) 
    active_event_names = (EVENT_BUCKETS.get("Quizzes / Exams", []) + EVENT_BUCKETS.get("Forums / Discussions", []))
    active_user_ids = set(find_user_ids(df, active_event_names))
    active_user_count = len(active_user_ids)

    # 2.3️⃣ All user ids present in this file (non-null only)
    all_user_ids = (
        df.select("user_id")
          .drop_nulls()
          .unique()
          .to_series()
          .to_list()
    )

    # Hardcoded ignore ids are treated as admins
    IGNORE_VALUES_SET = {
        179434, 179631, 44240, 14552, 14294, 4688, 54402,
        39644, 87979, 15115, 31281, 173796, 2067, 204691,
        48118, 0, -1
    }
    admin_ids_to_mark = admin_ids_detected | IGNORE_VALUES_SET

    # 2.5️⃣ Drop rows missing event name
    before_event = df.height
    df = df.filter(
        pl.col("Tapahtuman nimi").is_not_null() &
        (pl.col("Tapahtuman nimi").cast(pl.Utf8).str.strip_chars() != "")
    )
    skipped_rows += int(before_event - df.height)

    inserted_ok = 0
    bad_rows: list[tuple[str, tuple]] = []

    with connect() as conn:
        with conn.cursor() as cur:
            # Create ingest_file row
            ensure_ingest_file_schema(cur)
            file_id = insert_ingest_file(cur,file_id=file_id ,filename=filename, user_count=user_count, active_user_count=active_user_count)
            
            # Update moodle.user_dim (3 steps)
            if all_user_ids:
                ensure_users(cur, all_user_ids)

            if active_user_ids:
                set_users_active(cur, list(active_user_ids))

            if admin_ids_to_mark:
                set_users_admin(cur, list(admin_ids_to_mark))

            # Persistent admin filter from DB
            admin_ids_db = fetch_admin_user_ids(cur)

            # Filter df BEFORE building event rows
            before_filter = df.height

            df = df.filter(pl.col("user_id").is_not_null())
            if admin_ids_db:
                df = df.filter(~pl.col("user_id").is_in(list(admin_ids_db)))

            skipped_rows += int(before_filter - df.height)

            if df.height == 0:
                conn.commit()
                return file_id, 0, skipped_rows

            # Build rows for DB insert
            rows: list[tuple] = []
            for r in df.to_dicts():
                ts = r.get("ts")
                user_id = r.get("user_id")
                if user_id is not None:
                    user_id = int(user_id)

                context = _get_optional_str(r, "Tapahtuman konteksti")
                component = _get_optional_str(r, "Komponentti")
                event_name = _get_optional_str(r, "Tapahtuman nimi")
                description = _get_optional_str(r, "Kuvaus")
                origin = _get_optional_str(r, "Alkuperä")

                if ts is None:
                    skipped_rows += 1
                    continue

                rows.append((ts, user_id, context, component, event_name, description, origin))

            if not rows:
                conn.commit()
                return file_id, 0, skipped_rows

            rows_with_file = [
                (file_id, ts, user_id, context, component, event_name, description, origin)
                for (ts, user_id, context, component, event_name, description, origin) in rows
            ]

            # Insert events in batches
            BATCH = 5000
            for start in range(0, len(rows_with_file), BATCH):
                batch = rows_with_file[start:start + BATCH]

                cur.execute("SAVEPOINT sp_batch")
                try:
                    insert_events(cur, batch)
                    inserted_ok += len(batch)
                    cur.execute("RELEASE SAVEPOINT sp_batch")
                except Exception:
                    cur.execute("ROLLBACK TO SAVEPOINT sp_batch")

                    for row in batch:
                        cur.execute("SAVEPOINT sp_row")
                        try:
                            insert_events(cur, [row])
                            inserted_ok += 1
                            cur.execute("RELEASE SAVEPOINT sp_row")
                        except Exception as e_row:
                            cur.execute("ROLLBACK TO SAVEPOINT sp_row")
                            bad_rows.append((str(e_row), row))
                            cur.execute("RELEASE SAVEPOINT sp_row")

                    cur.execute("RELEASE SAVEPOINT sp_batch")

        conn.commit()

    if bad_rows:
        st.warning(f"{len(bad_rows)} row(s) failed to insert. Showing first 3:")
        for err, row in bad_rows[:3]:
            st.write("Error:", err)
            st.write("Row:", row)

    return file_id, inserted_ok, skipped_rows + len(bad_rows)

