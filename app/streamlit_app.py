import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Moodle Log Explorer", layout="wide")
st.title("Moodle Log Explorer")

# Fixed ignore values
IGNORE_VALUES = [
    "179434", "179631", "44240", "14552", "14294", "4688", "54402",
    "39644", "87979", "15115", "31281", "173796", "2067", "204691",
    "48118", "-1"
]

def load_csv(file) -> pd.DataFrame:
    try:
        return pd.read_csv(file, sep=";", dtype=str)
    except Exception:
        file.seek(0)
        return pd.read_csv(file, dtype=str)


def filter_by_kuvaus_contains_ids(df, kuvaus_col="Kuvaus"):
    if kuvaus_col not in df.columns:
        st.error(f"Column '{kuvaus_col}' not found.")
        return df, 0

    # Build regex for matching full numbers only
    pattern = r"(?<!\d)(" + "|".join(map(re.escape, IGNORE_VALUES)) + r")(?!\d)"

    mask_block = df[kuvaus_col].fillna("").str.contains(pattern, regex=True)
    filtered_df = df[~mask_block]

    return filtered_df, mask_block.sum()


# --- UI ---
uploaded = st.file_uploader("Drop a Moodle CSV file here", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to preview and filter it.")
    st.stop()

df = load_csv(uploaded)

st.subheader("Raw Preview")
st.dataframe(df.head(), use_container_width=True)

if st.button("Run Kuvaus filter", type="primary"):
    filtered_df, removed_count = filter_by_kuvaus_contains_ids(df, "Kuvaus")

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows (raw)", len(df))
    c2.metric("Rows (filtered)", len(filtered_df))
    c3.metric("Removed", removed_count)

    st.subheader("Filtered Preview")
    st.dataframe(filtered_df.head(200), use_container_width=True)
