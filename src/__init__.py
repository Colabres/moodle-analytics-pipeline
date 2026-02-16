"""
This file makes the `src` directory a Python package.

It allows imports like:
    from src.db import connect
    from src.parse import extract_user_id

Even though modern Python can sometimes work without this file
(implicit namespace packages), we keep it explicitly for clarity
and compatibility across environments.
"""