import polars as pl

# Polars: parse Moodle time strings into Datetime (NaT -> null)
def parse_aika_pl(expr: pl.Expr) -> pl.Expr:
    return expr.str.strptime(pl.Datetime, format="%d.%m.%Y, %H.%M.%S", strict=False)

# Polars: extract user id from Kuvaus (strict English rule like your pandas version)
# Returns Int64 or null
def extract_user_id_pl(expr: pl.Expr) -> pl.Expr:
    # Same rule as USER_WITH_ID_PATTERN: user with id '<1..6 digits>'
    pattern = r"user\s+with\s+id\s+'(\d{1,6})'"
    return (
        expr.fill_null("")
            .str.extract(pattern, 1)
            .cast(pl.Int64, strict=False)
    )