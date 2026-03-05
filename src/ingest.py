from typing import Tuple, Optional, Mapping, Any
import polars as pl
import streamlit as st
from src.parse import parse_aika_pl, extract_user_id_pl
from src.db import connect, insert_ingest_file, insert_events



def _get_optional_str(row: Mapping[str, Any], col: str) -> Optional[str]:
    """
    Safely return a string value from a row.
    Returns None if column missing, NaN, or empty.
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




def transfer_to_db(df: pl.DataFrame, filename: str) -> Tuple[int, int, int]:
    """
    Transfer dataframe rows into Postgres.

    Returns:
        (file_id, inserted_rows, skipped_rows)

    Skips:
        - rows with invalid timestamp in column 'Aika'
        - rows missing required 'Tapahtuman nimi'
    """

    if "Aika" not in df.columns:
        raise ValueError("Missing required column 'Aika'.")

    if "Tapahtuman nimi" not in df.columns:
        raise ValueError("Missing required column 'Tapahtuman nimi'.")

    

    # 1️⃣ Parse timestamps (Polars)
    df = df.with_columns(
        parse_aika_pl(pl.col("Aika").fill_null("")).alias("ts")
    )

    # count rows with invalid timestamp
    invalid_ts = df.filter(pl.col("ts").is_null()).height
    skipped_rows = int(invalid_ts)

    # keep only valid timestamps
    df = df.filter(pl.col("ts").is_not_null())

    if df.height == 0:
        return 0, 0, skipped_rows

    # 2️⃣ Extract strict numeric user_id from Kuvaus (Polars)
    if "Kuvaus" in df.columns:
        df = df.with_columns(
            extract_user_id_pl(pl.col("Kuvaus")).alias("user_id")
        )
    else:
        df = df.with_columns(
            pl.lit(None).cast(pl.Int64).alias("user_id")
        )

    IGNORE_VALUES_SET = {
        179434, 179631, 44240, 14552, 14294, 4688, 54402,
        39644, 87979, 15115, 31281, 173796, 2067, 204691,
        48118,0,-1
    }

    before = df.height

    df = df.filter(
        pl.col("user_id").is_not_null() &
        (~pl.col("user_id").is_in(list(IGNORE_VALUES_SET)))
    )

    filtered_blacklist = before - df.height
    skipped_rows += int(filtered_blacklist)

    # 2.5️⃣ Drop rows missing event name (Polars)
    before_event = df.height
    df = df.filter(
        pl.col("Tapahtuman nimi").is_not_null() &
        (pl.col("Tapahtuman nimi").cast(pl.Utf8).str.strip_chars() != "")
    )
    skipped_rows += int(before_event - df.height)

    # 3️⃣ Build rows for DB insert (Polars -> Python rows)
    rows = []

    # iterate as dicts: {"ts": ..., "user_id": ..., ...}
    for r in df.to_dicts():
        ts = r.get("ts")  # python datetime, or None
        user_id = r.get("user_id")  # int or None

        # ensure python int or None
        if user_id is not None:
            user_id = int(user_id)

        context = _get_optional_str(r, "Tapahtuman konteksti")
        component = _get_optional_str(r, "Komponentti")
        event_name = _get_optional_str(r, "Tapahtuman nimi")
        description = _get_optional_str(r, "Kuvaus")
        origin = _get_optional_str(r, "Alkuperä")


        # ts should be datetime already; keep guard anyway
        if ts is None:
            skipped_rows += 1
            continue

        rows.append((ts, user_id, context, component, event_name, description, origin))

    if not rows:
        return 0, 0, skipped_rows

    # 4️⃣ Insert into DB (batch + isolate bad rows)
    inserted_ok = 0
    bad_rows = []

    with connect() as conn:
        with conn.cursor() as cur:
            file_id = insert_ingest_file(cur, filename=filename)

            rows_with_file = [
                (file_id, ts, user_id, context, component, event_name, description, origin)
                for (ts, user_id, context, component, event_name, description, origin) in rows
            ]

            BATCH = 5000
            for start in range(0, len(rows_with_file), BATCH):
                batch = rows_with_file[start:start + BATCH]

                cur.execute("SAVEPOINT sp_batch")
                try:
                    insert_events(cur, batch)
                    inserted_ok += len(batch)
                    cur.execute("RELEASE SAVEPOINT sp_batch")
                except Exception as e:
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
