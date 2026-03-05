# src/event_buckets.py
# Buckets for grouping Moodle event_name values into analytics-friendly categories.
# Keep strings exactly matching moodle.event.event_name.

EVENT_BUCKETS: dict[str, list[str]] = {
    # 1) Moodle page views
    "Moodle page views": [
        'Kurssi nähty',
        'Osio katsottu',
        'Kurssin aktiviteettien suoritus -asetuksia on päivitetty',
        'Osallistujalista nähty',
        'Kurssin osallistujaraportti nähty',
        'Käyttäjäprofiili katsottu',
        'Kurssin moduuli nähty',
        'Keskustelu katsottu',
        'Kurssimoduulin esiintymien lista katsottu',
        'Palautuksen tila on nähty'
    ],

    # 2) Assignments & Exams
    "Quizzes / Exams": [
        'Käyttäjä arvosteltu',
        'Käyttäjän arviointiraportti nähty',
        'Kommentti luotu', #Palautukseen lisätty kommentti
        'Palautuslomake on nähty',
        'Palautus on lähetetty',
        'Palaute on nähty',
        'Palautuksen tila on päivitetty',
        'Tentin suorituskerta katsottu', #Valtava logi
        'Tentin suorituskerta päivitetty', #Valtava logi
        'Tentin suorituskerta tallennettu automaattisesti',
        'Suorituskerran yhteenveto katsottu',
        'Tenttivastaus palautettu',
        'Tenttiin vastaaminen aloitettu',
        'Tiedosto on lisätty.',
        'Palautus on luotu',
        'Käyttäjä on tallentanut palautuksensa'
    ],

    # 3) Forums & Discussions
    "Forums & Discussions": [
        'Jotain sisältöä on lähetetty.',
        'Keskustelu luotiin',
        'Keskustelualue tilattiin',
        'Tilaus luotiin',
        'Luettujen viestien seuranta pois käytöstä',
        'Keskustelualueen tilaus poistettiin',
        'Kommentti luotiin',
        'Luettujen viestien seuranta käytössä'
    ],

    # 4) Misc
    "Misc": [
        'Ryhmän jäsen lisättiin',
        'Ryhmän jäsen poistettiin',
        'Osio suoritettu',
        'Palaute lähetetty',
        'Valinta on tehty', #Ryhmävalinta
        'Valinta on poistettu', #Ryhmävalinta
        'Grade overview report viewed'
    ],
    # 5) Admin activity
    "Admin activity": [
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
        'Käyttäjä rekisteröity kurssille',
        'Tapahtuma päivitetty',
        'Kurssikuvaus nähty',
        'Tapahtuma poistettu',
        'Kurssin tiedot päivitettiin',
        'Roolia ei ole määritetty',
        'Käyttäjän rekisteröitymistila päivitetty',
        'Kohde poistettu',
        'Kohde luotu',
        'Palautus poistettu',
        'Nähty palautuksen poistovahvistus'
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
