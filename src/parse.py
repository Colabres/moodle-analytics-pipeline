import polars as pl

# Polars: parse Moodle time strings into Datetime (NaT -> null)
def parse_aika_pl(expr: pl.Expr) -> pl.Expr:
    return expr.str.strptime(pl.Datetime, format="%d.%m.%Y, %H.%M.%S", strict=False)

# Polars: extract user id from Kuvaus (strict English rule like your pandas version)
# Returns Int64 or null
def extract_user_id_pl(expr: pl.Expr) -> pl.Expr:
    descriptions = ["The user with id", "Käyttäjä"]
    labels_alt = "|".join(map(pl.escape_regex, descriptions))

    pattern = (
        rf"(?i)"
        rf"(?:^|[^0-9A-Za-z])(?:{labels_alt})"
        rf"\s*[:= -]?\s*"
        rf"'?\s*(([+-]?[0-9]+))\s*'?"
        rf"(?:$|[^0-9])"
    )

    return (
        expr.fill_null("")
            .str.extract(pattern, 1)
            .cast(pl.Int64, strict=False)
    )
