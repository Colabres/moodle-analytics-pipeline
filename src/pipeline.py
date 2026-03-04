import polars as pl

def get_ids_dropsome(data: pl.DataFrame) -> pl.DataFrame:
    # Replaces 'Kuvaus' column with user id's extracted from kuvaus. Also drops 'Alkuperä' column.
    descriptions = ["The user with id", "Käyttäjä"]
    labels_alt = "|".join(map(pl.escape_regex, descriptions))
    pattern = (
        rf"(?i)"
        rf"(?:^|[^0-9A-Za-z])(?:{labels_alt})"
        rf"\s*[:= -]?\s*"
        rf"'?\s*([0-9]+)\s*'?"
        rf"(?:$|[^0-9])"
    )
    return data.with_columns(
        pl.col("Kuvaus")
          .fill_null("")
          .str.extract(pattern, 1)
          .alias("Kayttaja_id")
          ).drop(["Kuvaus", "Alkuperä"]) # pitää lisätä vielä muutama sarake

def find_ids(data: pl.DataFrame, names: list) -> pl.DataFrame:
    # finds id's associated with given list of event names
    return (
        data
        .filter(pl.col("Tapahtuman nimi").is_in(names))
        .select("Kayttaja_id")
        .unique()
        .to_series()
        .to_list()
    )

def drop_admins(data: pl.DataFrame) -> pl.DataFrame:
    # Deletes log entries that are associated with admin id's
    admin_names = [
        'Participation report viewed',
        'Arviointitaulukko on nähty',
        'Tentin raporttia katsottu',
        'Lokiraportti katsottu',
        'Tapahtuma luotu',
        'Paikka luotu',
        'Kurssin moduuli luotu',
        'Tentin poikkeuspääsy poistettu',
        'Osion sekoitus päivitetty',
        'Tentin arviointi päivitetty',
        'Kysymys luotu',
        'Aktiviteettiraportti nähty',
        'Arviointilomake on nähty',
        'Kysymyskategoria luotu',
        'Tentin muokkaussivua katsottu',
        'Arviointikohde luotu',
        'Kurssin moduuli päivitetty',
        'Arviointikohde päivitetty',
        'Kurssin varmuuskopio luotu',
        'Paikka poistettu',
        'Nähty arvioijan raportti',
        'Statistics report viewed',
        'Kurssin osio päivitettiin',
        'Kysymyskategoria katsottu',
        'Tentin poikkeuspääsy luotu',
        'Kysymys katsottu',
        'Kysymys päivitetty',
        'Kurssin osio luotiin',
        'Kysymys poistettu',
        'Kurssin moduuli poistettu',
        'Tentin suorituskerta arvioitu uudelleen',
        'Suorituskerta katsottu uudelleen',
        'Tentin esikatselu aloitettu',
        'Arviointikohde poistettu',
        'Kurssin osio poistettiin',
        'Arvosana poistettu',
        'Palautus on arvioitu.',
        'Käyttäjä poistettu kurssilta',
        'Kaikki palautukset ladatataan',
        'Kysymys siirretty',
        'Rooli määrätty',
        'Tapahtuma päivitetty'
    ]
    admin_ids = find_ids(data, admin_names)
    new_data = data.filter(~pl.col("Kayttaja_id").is_in(admin_ids))
    return new_data

def create_activity(data: pl.DataFrame) -> pl.DataFrame:
    # Creates 'Aktiivinen' column that stores the activity of the users in a boolean variable.
    active_names = [
        "Jotain sisältöä on lähetetty",
        "Tiedosto on lisätty",
        "Palautus on lähetetty",
        "Palautus on luotu",
        "Tenttivastaus on palautettu",
        "Kommentti luotiin"
    ]
    active_ids = find_ids(data, active_names)
    return data.with_columns(
        pl.col("Kayttaja_id")
        .is_in(active_ids)
        .alias("Aktiivinen")
    )

def to_datetime(data: pl.DataFrame) -> pl.DataFrame:
    # Converts 'Aika' column data type to datetime. NaT for invalid rows.
    return data.with_columns(pl.col('Aika')
                             .str.strptime(pl.Datetime, format='%d.%m.%Y, %H.%M.%S', strict=False)
                             .alias('Aika'))

def pipeline(filename: str) -> pl.DataFrame:
    data = pl.read_csv(filename, separator=";")
    data = get_ids_dropsome(data)
    data = drop_admins(data)
    data = create_activity(data)
    data = to_datetime(data)
    return data



