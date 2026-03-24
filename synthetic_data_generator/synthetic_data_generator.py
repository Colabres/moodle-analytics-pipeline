import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# poistaa ID:t kuvauksista ja korvaa merkillä X
def clean(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
              .astype(str)
              .str.replace(r"'?\d+'?", "X", regex=True)
              .str.replace(r"\s+", " ", regex=True)
              .str.strip()
    )


def fit_hierarchy(df: pd.DataFrame) -> dict: ## Tätä käytetään hierarkia rakenteen asettamiseen Komponentti -> Tapahtuman nimi -> Kuvaus
    d = df.copy()
    comp = "Komponentti"
    event_col = "Tapahtuman nimi"
    desc = "Kuvaus"

    d[comp] = d[comp].fillna("").astype(str).str.strip()
    d[event_col] = d[event_col].fillna("").astype(str).str.strip()
    d[desc] = clean(d[desc]) # kuvausten putsaus

    p_comp = d[comp].value_counts(normalize=True) # Komponenteille (indeksi,frekvenssi)
    comps = p_comp.index.to_numpy() # indeksit
    comp_probs = p_comp.to_numpy() # frekvenssit

    event_given_component = {}
    for component, g in d.groupby(comp, dropna=False): # sama prosessi
        p_event = g[event_col].value_counts(normalize=True)
        events = p_event.index.to_numpy()
        event_probs = p_event.to_numpy()
        event_given_component[component] = (events, event_probs) # komponenttia kohden tapahtuman indeksi ja frekvenssi

    desc_given = {}
    for (component, event), g in d.groupby([comp, event_col], dropna=False): # sama homma kuvauksille
        p_desc = g[desc].value_counts(normalize=True)
        descs = p_desc.index.to_numpy()
        desc_probs = p_desc.to_numpy()
        desc_given[(component, event)] = (descs, desc_probs)

    return {
        "cols": (comp, event_col, desc),
        "comps": comps,
        "comp_probs": comp_probs,
        "ev_given_comp": event_given_component,
        "desc_given": desc_given
    }


def sample_hierarchy(model: dict, n: int, rng: np.random.Generator) -> pd.DataFrame: # luodaan synteettinen data otoksien avulla
    col_comp, col_event, col_desc = model["cols"]

    comps = rng.choice(model["comps"], # otos syötetyn "model" sanakirjan komponenteista
                       size=n, # otosten määrä
                       p=model["comp_probs"], # komponentin valitsemisen todennäköisyys frekvenssin mukaan
                       replace=True # sama komponentti voidaan valita monta kertaa
                       )

    events = []
    descs = []
    for component in comps:
        event_vals, event_probs = model["ev_given_comp"][component]
        event = rng.choice(event_vals, p=event_probs) # toistetaan samaa kuin edellä
        events.append(event)

        desc_vals, desc_probs = model["desc_given"][(component, event)]
        desc = rng.choice(desc_vals, p=desc_probs)
        descs.append(desc)


    return pd.DataFrame({col_comp: comps, col_event: events, col_desc: descs}) 


# otoksia otetaan toleranssilla, eli generoidun datan on muistutettava alkuperäistä (vain komponentin mukaan)
# Muiden sarakkeiden suhteen toleranssia ei lasketa, jotta data oikeasti pysyy synteettisenä (ja laskentanopeus pysyy siedettävänä)
def sample_with_component_tolerance(model: dict, n: int, tolerance: float, max_tries: int, rng: np.random.Generator) -> pd.DataFrame:
    col_comp, _, _ = model["cols"]
    target = pd.Series(model["comp_probs"], index=model["comps"])

    last = None
    for _ in range(max_tries):
        syn = sample_hierarchy(model, n=n, rng=rng) # Otos
        share = syn[col_comp].value_counts(normalize=True) # synteettisen datan indeksi, frekvenssi
        share = share.reindex(target.index, fill_value=0) # synteettisestä puuttuvat komponentit lisätään frekvenssillä 0 
        differences = share.sub(target).abs() # erot alkuperäisen ja synteettisen välillä komponenteittain
        if (differences <= tolerance).all(): # jos kaikki erot noudattavat toleranssia, synteettinen data palautetaan
            return syn
        last = syn

    return last


# Tämän voisi korvata hienostuneemmalla funktiolla
# Käytännössä generoidaan satunnaista aikadataa valitulle aikavälille.
def generate_timecol(n: int, start: datetime, end: datetime, rng: np.random.Generator | None = None) -> pd.Series:
    if rng is None:
        rng = np.random.default_rng()
    seconds = int((end - start).total_seconds()) # aikaväli sekunteina
    offsets = rng.integers(low=0, high=seconds, size=n) # generoidaan n lukua [0,seconds] väliltä
    times = [start + timedelta(seconds=int(time)) for time in offsets] # luodaan ajat
    formatted = [
        f"{time.day:02}.{time.month:02}.{time.year}, {time.hour:02}.{time.minute:02}.{time.second:02}"
        for time in times] 

    return pd.Series(formatted)


# tämä funktio luo satunnaisia merkkijonoja (konteksti ja alkuperä sarakkeita varten)
def random_strings(n: int, length: int = 10, rng: np.random.Generator | None = None) -> pd.Series:
    if rng is None:
        rng = np.random.default_rng()
    alphabet = np.array(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
    arr = rng.choice(alphabet, size=(n, length))
    strings = ["".join(row) for row in arr]
    return pd.Series(strings)

# luo satunaisia ID numeroita
def fill_ids(desc: pd.Series, rng: np.random.Generator,
                    low: int = 100000, high: int = 999_999) -> pd.Series:
    pat = re.compile(r"\bX\b")
    def repl(joku):
        return f"'{rng.integers(low, high + 1)}'"
    return desc.astype(str).map(lambda s: pat.sub(repl, s))


#####################################################################################################################


df = pd.read_csv("ALL_logs_kurssidata.csv", sep=";")

model = fit_hierarchy(df)

os.makedirs("synthetic", exist_ok=True)

base = "synthetic_"
for i in range(10):
    n = 100000
    rng = np.random.default_rng(1000 + i)
    synthetic = sample_with_component_tolerance(model, n=n, tolerance=0.10, max_tries=200, rng=rng)
    synthetic['Aika']=generate_timecol(n=n, start=datetime(2015+i, 1, 1), end=datetime(2016+i,1,1))
    synthetic['Tapahtuman konteksti']=random_strings(n=n, length=20)
    synthetic['Alkuperä']=random_strings(n=n, length=3)
    synthetic['Kuvaus'] = fill_ids(synthetic['Kuvaus'], rng)
    path = f'synthetic/{base}{i}.csv'
    synthetic.to_csv(path, index=False, sep=';')
    print('wrote', path)