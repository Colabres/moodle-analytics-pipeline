import os
import streamlit as st
import psycopg

st.title("Moodle Analytics Dev")

db_url = os.getenv("DATABASE_URL")
if not db_url:
    st.error("DATABASE_URL missing (check docker-compose.yml).")
    st.stop()

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
    st.success("Connected to PostgreSQL ✅")
    st.code(version)
except Exception as e:
    st.error("Could not connect to PostgreSQL ❌")
    st.code(str(e))
