from typing import Tuple, Optional
import pandas as pd
import streamlit as st
from src.parse import parse_aika, extract_user_id
from src.db import connect, insert_ingest_file, insert_events


def _get_optional_str(row: pd.Series, col: str) -> Optional[str]:
    """
    Safely return a string value from a row.
    Returns None if column missing, NaN, or empty.
    """
    if col not in row.index:
        return None

    value = row[col]

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    value = str(value).strip()
    if value == "" or value.lower() == "nan":
        return None

    return value


def transfer_to_db(df: pd.DataFrame, filename: str) -> Tuple[int, int, int]:
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

    df2 = df.copy()

    # 1️⃣ Parse timestamps
    df2["ts"] = parse_aika(df2["Aika"].fillna(""))
    valid_mask = df2["ts"].notna()
    skipped_rows = int((~valid_mask).sum())
    df2 = df2[valid_mask]

    if len(df2) == 0:
        return 0, 0, skipped_rows

    # 2️⃣ Extract strict numeric user_id from Kuvaus
    if "Kuvaus" in df2.columns:
        df2["user_id"] = df2["Kuvaus"].apply(extract_user_id)
    else:
        df2["user_id"] = None

    IGNORE_VALUES_SET = {
        179434, 179631, 44240, 14552, 14294, 4688, 54402,
        39644, 87979, 15115, 31281, 173796, 2067, 204691,
        48118,0,-1
    }

    before = len(df2)

    df2 = df2[
        df2["user_id"].notna() &                 # remove NaN
        ~df2["user_id"].isin(IGNORE_VALUES_SET)  # remove blacklisted IDs
    ]

    filtered_blacklist = before - len(df2)
    skipped_rows += filtered_blacklist


    # 3️⃣ Build rows for DB insert
    rows = []
    for _, r in df2.iterrows():
        ts = r["ts"].to_pydatetime()
        user_id = r["user_id"]  # int or None
        
        if user_id is None or pd.isna(user_id):
            user_id = None
        else:
            user_id = int(user_id)

        context = _get_optional_str(r, "Tapahtuman konteksti")
        component = _get_optional_str(r, "Komponentti")
        event_name = _get_optional_str(r, "Tapahtuman nimi")
        description = _get_optional_str(r, "Kuvaus")
        origin = _get_optional_str(r, "Alkuperä")

        if not event_name:
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
