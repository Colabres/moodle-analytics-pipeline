from typing import Tuple, Optional
import pandas as pd

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

    # 3️⃣ Build rows for DB insert
    rows = []

    for _, r in df2.iterrows():
        ts = r["ts"].to_pydatetime()
        user_id = r["user_id"]  # int or None

        context = _get_optional_str(r, "Tapahtuman konteksti")
        component = _get_optional_str(r, "Komponentti")
        event_name = _get_optional_str(r, "Tapahtuman nimi")
        description = _get_optional_str(r, "Kuvaus")
        origin = _get_optional_str(r, "Alkuperä")

        if not event_name:
            skipped_rows += 1
            continue

        rows.append(
            (ts, user_id, context, component, event_name, description, origin)
        )

    if not rows:
        return 0, 0, skipped_rows

    # 4️⃣ Insert into DB
    with connect() as conn:
        with conn.cursor() as cur:

            # Insert new file row (no dedup logic)
            file_id = insert_ingest_file(cur, filename=filename)

            # Add file_id to each row
            rows_with_file = [
                (file_id, ts, user_id, context, component, event_name, description, origin)
                for (ts, user_id, context, component, event_name, description, origin) in rows
            ]

            insert_events(cur, rows_with_file)

        conn.commit()

    return file_id, len(rows_with_file), skipped_rows
