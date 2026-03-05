import re
import pandas as pd

# Strict: only accept exactly "... user with id '<number>' ..."
USER_WITH_ID_PATTERN = re.compile(
    r"user\s+with\s+id\s+'(\d{1,6})'",
    flags=re.IGNORECASE
)

def parse_aika(series: pd.Series) -> pd.Series:
    """
    Parse Moodle time strings into datetime.
    Expected example: '3.02.2026, 11.48.49'
    Returns pandas datetime with NaT for invalid rows.
    """
    return pd.to_datetime(series, format="%d.%m.%Y, %H.%M.%S", errors="coerce")

def extract_user_id(description: str):
    if not isinstance(description, str) or not description:
        return None

    m = USER_WITH_ID_PATTERN.search(description)
    if not m:
        return None

    s = m.group(1)
    
    # Debug rule: reject IDs longer than 6 digits
    if len(s) > 6:
        print(f"[DEBUG] Rejected suspicious user_id: {s}")
        return None

    return int(s)

