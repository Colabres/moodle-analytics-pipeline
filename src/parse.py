import re
import pandas as pd

# Strict: only accept exactly "... user with id '<number>' ..."
USER_WITH_ID_PATTERN = re.compile(
    r"user\s+with\s+id\s+'(\d+)'",
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
    """
    Returns int only when pattern is present:
      ... user with id '<number>' ...
    Otherwise returns None.
    """
    if not isinstance(description, str) or not description:
        return None

    m = USER_WITH_ID_PATTERN.search(description)
    if not m:
        return None

    return int(m.group(1))