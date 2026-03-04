# src/event_buckets.py
# Buckets for grouping Moodle event_name values into analytics-friendly categories.
# Keep strings exactly matching moodle.event.event_name.

EVENT_BUCKETS: dict[str, list[str]] = {
    # 1) Admin activity
    "Admin activity": [
        'Participation report viewed',
        'Arviointitaulukko on nähty'
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
        'Käyttäjä rekisteröity kurssille',
        'Tapahtuma päivitetty',
        'Kurssikuvaus nähty'
    ],

    # 2) Moodle page views
    "Moodle page views": [
        'Kurssi nähty',
        'Osio katsottu',
        'Kurssin aktiviteettien suoritus -asetuksia on päivitetty',
        'Osallistujalista nähty',
        'Kurssin osallistujaraportti nähty'
    ],

    # 3) Assignments & Submissions
    "Assignments & Submissions": [
        'Käyttäjä arvosteltu'
    ],

    # 5) Quizzes / Exams
    "Quizzes / Exams": [
        
    ],

    # 6) Forums & Discussions
    "Forums & Discussions": [

    ],

    # 7) Reports & Logs Viewed
    "Reports & Logs Viewed": [

    ],

    # 8) Misc
    "Misc": [
        'Ryhmän jäsen lisättiin',
        'Ryhmän jäsen poistettiin'
    ],
}


def expand_buckets(selected_buckets: list[str]) -> list[str]:
    """
    Convert bucket names -> flat list of event_name strings (unique, stable order).
    """
    names: list[str] = []
    for b in selected_buckets:
        names.extend(EVENT_BUCKETS.get(b, []))

    seen = set()
    out: list[str] = []
    for x in names:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out