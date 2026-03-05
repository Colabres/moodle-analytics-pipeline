# src/event_buckets.py
# Buckets for grouping Moodle event_name values into analytics-friendly categories.
# Keep strings exactly matching moodle.event.event_name.

EVENT_BUCKETS: dict[str, list[str]] = {
    # 1) Course Structure & Management
    "Course Structure & Management": [
        "Kurssi nähty",
        "Kurssikuvaus nähty",
        "Kurssin tiedot päivitettiin",
        "Kurssin varmuuskopio luotu",
        "Kurssin moduuli luotu",
        "Kurssin moduuli päivitetty",
        "Kurssin moduuli poistettu",
        "Kurssin moduuli nähty",
        "Kurssin osio luotiin",
        "Kurssin osio päivitettiin",
        "Kurssin osio poistettiin",
        "Osio katsottu",
        "Osion sekoitus päivitetty",
    ],

    # 2) Enrollment & Users
    "Enrollment & Users": [
        "Käyttäjä rekisteröity kurssille",
        "Käyttäjä poistettu kurssilta",
        "Käyttäjän rekisteröitymistila päivitetty",
        "Käyttäjäprofiili katsottu",
        "Rooli määrätty",
        "Roolia ei ole määritetty",
        "Ryhmän jäsen lisättiin",
        "Ryhmän jäsen poistettiin",
    ],

    # 3) Assignments & Submissions
    "Assignments & Submissions": [
        "Palautus on luotu",
        "Palautus on lähetetty",
        "Palautus on arvioitu",
        "Palautus poistettu",
        "Palautuksen tila on nähty",
        "Palautuksen tila on päivitetty",
        "Palautuslomake on nähty",
        "Kaikki palautukset ladatataan",
        "Käyttäjä on tallentanut palautuksensa",
    ],

    # 4) Grading & Assessment
    "Grading & Assessment": [
        "Arviointikohde päivitetty",
        "Arviointikohde poistettu",
        "Arvosana poistettu",
        "Grade overview report viewed",
        "Nähty arvioijan raportti",
        "Käyttäjä arvosteltu",
        "Käyttäjän arviointiraportti nähty",
        "Arvosanajakauma katsottu",
    ],

    # 5) Quizzes / Exams
    "Quizzes / Exams": [
        "Tenttiin vastaaminen aloitettu",
        "Tenttivastaus palautettu",
        "Tentin suorituskerta katsottu",
        "Tentin suorituskerta tallennettu automaattisesti",
        "Tentin suorituskerta arvioitu uudelleen",
        "Tentin arviointi päivitetty",
        "Tentin raporttia katsottu",
        "Tentin muokkaussivua katsottu",
        "Tentin esikatselu aloitettu",
        "Tentin poikkeuspääsy luotu",
        "Tentin poikkeuspääsy poistettu",
    ],

    # 6) Forums & Discussions
    "Forums & Discussions": [
        "Keskustelu luotiin",
        "Keskustelu katsottu",
        "Keskustelualue tilattiin",
        "Keskustelualueen tilaus poistettiin",
        "Kommentti luotiin",
    ],

    # 7) Reports & Logs Viewed
    "Reports & Logs Viewed": [
        "Lokiraportti katsottu",
        "Raporttia katsottu",
        "Participation report viewed",
        "Statistics report viewed",
        "Kurssin osallistujaraportti nähty",
        "Osallistujalista nähty",
    ],

    # 8) Content Interaction / Viewing
    "Content Interaction / Viewing": [
        "Kurssimoduulin esiintymien lista katsottu",
        "Kohde luotu",
        "Kohde poistettu",
        "Palaute on nähty",
        "Kurssi nähty",
        "Tiedosto on lisätty",
        "Jotain sisältöä on lähetetty",
    ],

    # 9) Misc / System
    "Misc / System": [
        "Tapahtuma luotu",
        "Tapahtuma päivitetty",
        "Tapahtuma poistettu",
        "Tilaus luotiin",
        "Valinta on tehty",
        "Valinta on poistettu",
        "Suorituskerta katsottu uudelleen",
        "Suorituskerran yhteenveto katsottu",
        "Luettujen viestien seuranta käytössä",
        "Luettujen viestien seuranta pois käytöstä",
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